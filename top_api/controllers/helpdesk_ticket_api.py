# -*- coding: utf-8 -*-
"""
Custom route for creating helpdesk tickets with PrimeCare-style payload.
POST /api/helpdesk/ticket/create
"""
import logging

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError

from .api_generic import (
    _coerce_relational,
    _handle_attachments,
    _json,
    _parse_body,
)

_logger = logging.getLogger(__name__)

# Field mapping: payload key -> helpdesk.ticket field (if different)
HELPDESK_TICKET_FIELD_MAP = {
    "name": "name",  # primecare task id
    "partner_name": "partner_name",
    "partner_phone": "partner_phone",
    "patient_national_id": "patient_national_id",
    "company_id": "company_id",
    "branch_id": "branch_id",
    "creation_note": "creation_note",
    "description": "description",
    "ticket_type_id": "ticket_type_id",
    "team_id": "team_id",
    "invid": "invid",
    "ram_id": "ram_id",
    "workflow_level_id": "workflow_level_id",
    "stage_id": "stage_id",
}


class HelpdeskTicketAPI(http.Controller):
    @http.route(
        "/api/helpdesk/ticket/create",
        type="http",
        auth="bearer",
        methods=["POST"],
        cors="*",
        csrf=False,
    )
    def create_ticket(self, **kwargs):
        """Create a helpdesk ticket from PrimeCare-style payload."""
        try:
            body = _parse_body(kwargs)
            Model = http.request.env["helpdesk.ticket"]
            model_name = "helpdesk.ticket"

            # Build vals from payload. EXCLUDE branch_id from create so ram_case doesn't
            # overwrite team_id with branch's team (which would force wrong company).
            vals = {}
            branch_id_from_body = None
            for payload_key, field_name in HELPDESK_TICKET_FIELD_MAP.items():
                if payload_key not in body:
                    continue
                if field_name not in Model._fields:
                    continue
                raw = body[payload_key]
                if raw is None:
                    continue
                if field_name == "branch_id":
                    branch_id_from_body = raw
                    continue  # Add via update after; avoid ram_case overwriting team
                field = Model._fields[field_name]
                if field.type in ("many2one", "many2many", "one2many"):
                    coerced = _coerce_relational(Model, field_name, raw)
                    if coerced not in (False, None):
                        vals[field_name] = coerced
                else:
                    vals[field_name] = raw

            # Ensure partner_id (customer) matches ticket company (or is shared) to avoid:
            # "The customer cannot belong to a different company than the ticket."
            # We resolve/create a partner using phone/name and set partner_id accordingly.
            def _resolve_partner_id(company_id):
                Partner = http.request.env["res.partner"].sudo()
                phone = (body.get("partner_phone") or "").strip()
                name = (body.get("partner_name") or "").strip() or phone or "Customer"
                # Always use a SHARED partner (company_id=False) to avoid multi-company constraint
                # errors during ticket creation.
                if phone:
                    p = Partner.search(
                        ["&", ("company_id", "=", False), "|", ("phone", "=", phone), ("mobile", "=", phone)],
                        limit=1,
                    )
                    if p:
                        return p.id
                p = Partner.create({"name": name, "phone": phone or False, "company_id": False})
                return p.id

            # Company: posted company_id takes priority over branch. When both sent and
            # branch is in another company, use a branch in posted company.
            desired_company_id = None
            branch_rec = None
            Branch = http.request.env["clinizone.branch"].sudo()
            raw_company = body.get("company_id")
            if raw_company not in (None, "", 0) and "company_id" in Model._fields:
                try:
                    coerced = _coerce_relational(Model, "company_id", raw_company)
                    if isinstance(coerced, int) and coerced > 0:
                        desired_company_id = coerced
                except Exception:
                    pass
            if desired_company_id is None and branch_id_from_body is not None:
                try:
                    coerced_branch = _coerce_relational(Model, "branch_id", branch_id_from_body)
                    if isinstance(coerced_branch, int) and coerced_branch > 0:
                        branch_rec = Branch.browse(coerced_branch)
                        if branch_rec.exists() and branch_rec.company_id:
                            desired_company_id = branch_rec.company_id.id
                except Exception:
                    pass

            if desired_company_id:
                Model = Model.with_context(
                    allowed_company_ids=[desired_company_id],
                    default_company_id=desired_company_id,
                    force_company=desired_company_id,
                )

            # Set partner_id if field exists and wasn't provided explicitly
            if "partner_id" in Model._fields and "partner_id" not in vals:
                try:
                    vals["partner_id"] = _resolve_partner_id(desired_company_id)
                except Exception:
                    pass

            # Resolve team for company only when team_id was NOT sent in body (respect shared team_id).
            resolved_owner_id = None
            team_id_from_body = "team_id" in vals
            if desired_company_id and "team_id" in Model._fields and not team_id_from_body:
                try:
                    owner_rec = (
                        http.request.env["helpdesk.team"]
                        .sudo()
                        .search([("company_id", "=", desired_company_id)], limit=1)
                    )
                    if owner_rec:
                        resolved_owner_id = owner_rec.id
                        vals["team_id"] = resolved_owner_id
                except Exception:
                    pass

            rec = Model.create(vals)

            # Force team after create only when we set it (not when user sent team_id in body).
            if desired_company_id and resolved_owner_id is not None and not team_id_from_body:
                try:
                    rec.sudo().write({"team_id": resolved_owner_id})
                except Exception:
                    pass

            # Update with branch_id. If posted branch is in another company, use a branch
            # in desired_company_id so ram_case doesn't overwrite team_id when we write.
            if branch_id_from_body is not None and "branch_id" in Model._fields:
                try:
                    coerced_branch = _coerce_relational(Model, "branch_id", branch_id_from_body)
                    if isinstance(coerced_branch, int) and coerced_branch > 0:
                        branch_rec = branch_rec or Branch.browse(coerced_branch)
                        branch_to_write = coerced_branch
                        if branch_rec.exists() and branch_rec.company_id and desired_company_id:
                            if branch_rec.company_id.id != desired_company_id:
                                # Branch in another company; use branch in desired company
                                alt = Branch.search([
                                    ("company_id", "=", desired_company_id),
                                    ("helpdesk_team_id", "=", resolved_owner_id),
                                ], limit=1) if resolved_owner_id else None
                                if alt:
                                    branch_to_write = alt.id
                        rec.sudo().write({"branch_id": branch_to_write})
                except Exception:
                    pass

            # Attachments (if any)
            attachments = body.get("attachments") or []
            if attachments:
                _handle_attachments(
                    attachments, model_name, rec.id, mode=body.get("attachments_mode", "append")
                )

            # Response with details only: id, company_id, and key fields
            detail_fields = [
                "id", "name", "case_no", "company_id", "branch_id", "team_id",
                "partner_name", "partner_phone", "patient_national_id",
                "ticket_type_id", "stage_id", "description", "creation_note",
                "invid", "ram_id", "workflow_level_id",
            ]
            available = [f for f in detail_fields if f in rec._fields]
            try:
                data = rec.sudo().read(available)[0] if available else {"id": rec.id}
            except Exception:
                data = {"id": rec.id}
            # Normalize many2one to id (Odoo read returns [id, name])
            for key in ("company_id", "branch_id", "team_id", "ticket_type_id", "stage_id", "workflow_level_id"):
                if key in data and isinstance(data[key], (list, tuple)) and data[key]:
                    data[key] = data[key][0]
            company_id = data.get("company_id") or (rec.company_id.id if rec.company_id else None)

            return _json({
                "ok": True,
                "id": rec.id,
                "company_id": company_id,
                "data": data,
            })

        except (AccessError, MissingError) as e:
            status = 403 if isinstance(e, AccessError) else 404
            return _json({
                "ok": False,
                "error": str(e),
                "error_type": "access_error" if isinstance(e, AccessError) else "missing_error",
                "error_code": "ACCESS_ERROR" if isinstance(e, AccessError) else "MISSING_ERROR",
            }, status=status)
        except (UserError, ValidationError) as e:
            return _json({
                "ok": False,
                "error": str(e),
                "error_type": "validation_error",
                "error_code": "VALIDATION_ERROR",
            }, status=400)
        except Exception as e:
            _logger.exception("Helpdesk ticket create failed: %s", e)
            return _json({
                "ok": False,
                "error": str(e),
                "error_type": "server_error",
                "error_code": "SERVER_ERROR",
            }, status=500)
