import json
import base64
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import ValidationError, UserError, AccessError, MissingError
from psycopg2 import IntegrityError
import traceback
import re
import logging
# ---- SECURITY: allow all or restrict to selected models ----
ALLOW_ALL_MODELS = True
ALLOWED_MODELS = {
    "crm.lead",
    "helpdesk.ticket",
    "res.partner",
}

# Binary fields you may want to exclude by default
DEFAULT_BINARY_FIELD_BLOCKLIST = {
    "image_1920", "image_1024", "image_512", "image_256", "image_128",
}

_logger = logging.getLogger(__name__)


def _json(payload, status=200):
    return Response(
        json.dumps(payload, default=str),
        status=status,
        content_type="application/json; charset=utf-8",
    )


def _normalize_model_name(name):
    """Accept 'crm.lead', 'crm_lead', 'crm/lead' and return a valid model name."""
    if not name:
        return None
    variants = {name, name.replace("/", "."), name.replace("_", ".")}
    for cand in variants:
        if cand in request.env:
            return cand
    return name if name in request.env else None


def _get_model(model_name):
    m = _normalize_model_name(model_name)
    if not m:
        raise ValueError(f"Unknown model: {model_name}")
    if not (ALLOW_ALL_MODELS or m in ALLOWED_MODELS):
        raise ValueError(f"Access to model '{m}' is not allowed")
    return request.env[m], m


def _looks_base64(s):
    if not isinstance(s, str):
        return False
    try:
        base64.b64decode(s, validate=True)
        return True
    except Exception:
        return False


def _handle_attachments(attachments, res_model, res_id, mode="append"):
    if not attachments:
        return
    Attach = request.env["ir.attachment"]
    if mode == "replace":
        old = Attach.search([("res_model", "=", res_model), ("res_id", "=", res_id)])
        if old:
            old.unlink()
    for att in attachments:
        name = att.get("name") or "attachment"
        mimetype = att.get("mimetype") or "application/octet-stream"
        data = att.get("data")
        if not data:
            continue
        datas = data if _looks_base64(data) else base64.b64encode(str(data).encode()).decode()
        Attach.create({
            "name": name,
            "mimetype": mimetype,
            "datas": datas,
            "res_model": res_model,
            "res_id": res_id,
        })


def _coerce_relational(Record, field_name, raw):
    """Coerce many2one/many2many/one2many values from flexible JSON forms."""
    f = Record._fields[field_name]

    # -------- many2one: get-or-create behavior --------
    if f.type == "many2one":
        M = request.env[f.comodel_name]
        # Res.company lookups use sudo so the requested company can be resolved
        # regardless of current user's company context (multi-company).
        if f.comodel_name == "res.company":
            M = M.sudo()

        def _sanitize_vals(vals):
            return {k: v for k, v in (vals or {}).items() if k in M._fields}

        # 1) Direct integer id
        if isinstance(raw, int):
            return raw

        # 2) Dict forms
        if isinstance(raw, dict):
            # 2.a) Explicit id
            if raw.get("id"):
                return int(raw["id"])

            # 2.b) Domain lookup (+ optional create)
            if isinstance(raw.get("domain"), list):
                rec = M.search(raw["domain"], limit=1)
                if rec:
                    return rec.id
                if raw.get("create"):
                    return M.create(_sanitize_vals(raw["create"])).id
                return False

            # 2.c) Lookup/value (+ optional create)
            if raw.get("value") is not None:
                lookup = raw.get("lookup") or "name"
                # Support direct id lookup and numeric strings
                if lookup == "id":
                    val = raw.get("value")
                    if isinstance(val, int):
                        return val
                    if isinstance(val, str) and val.isdigit():
                        return int(val)
                rec = M.search([(lookup, "=", raw["value"])], limit=1)
                if rec:
                    return rec.id
                if raw.get("create"):
                    vals = _sanitize_vals(raw["create"])
                    vals.setdefault(lookup, raw["value"])
                    return M.create(vals).id
                if raw.get("create_if_missing"):
                    return M.create({lookup: raw["value"]}).id
                return False

            # 2.d) Name-based lookup (+ optional create)
            if raw.get("name"):
                rec = M.search([("name", "=", raw["name"])], limit=1)
                if rec:
                    return rec.id
                if raw.get("create"):
                    vals = _sanitize_vals(raw["create"])
                    vals.setdefault("name", raw["name"])
                    return M.create(vals).id
                if raw.get("create_if_missing"):
                    return M.create({"name": raw["name"]}).id
                return False

            # 2.e) Unconditional create
            if raw.get("create"):
                return M.create(_sanitize_vals(raw["create"])).id

            return False

        # 3) String shorthand treated as name
        if isinstance(raw, str):
            # If numeric string, treat as id
            if raw.isdigit():
                return int(raw)
            # RamCRM CSV ids (INQUIRY, MEDICAL_COMPLAINT, …) are xml ids ramcrm.<key>
            if f.comodel_name == "helpdesk.ticket.type":
                try:
                    return request.env.ref(f"ramcrm.{raw.strip()}").id
                except ValueError:
                    pass
            rec = M.search([("name", "=", raw)], limit=1)
            if rec:
                return rec.id
            if f.comodel_name == "helpdesk.ticket.type":
                rec = M.search([("name", "ilike", raw)], limit=1)
                return rec.id or False
            return False

        return False

    # -------- many2many --------
    if f.type == "many2many":
        M = request.env[f.comodel_name]
        ids = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, int):
                    ids.append(item)
                elif isinstance(item, dict):
                    if item.get("id"):
                        ids.append(int(item["id"]))
                    elif item.get("name"):
                        rec = M.search([("name", "=", item["name"])], limit=1)
                        if rec:
                            ids.append(rec.id)
                    elif item.get("domain"):
                        recs = M.search(item["domain"])
                        ids += recs.ids
                    elif item.get("create"):
                        vals = {k: v for k, v in item["create"].items() if k in M._fields}
                        ids.append(M.create(vals).id)
                elif isinstance(item, str):
                    rec = M.search([("name", "=", item)], limit=1)
                    if rec:
                        ids.append(rec.id)
        return [(6, 0, list(set(map(int, ids))))]

    # -------- one2many --------
    if f.type == "one2many":
        if isinstance(raw, list):
            cmds = []
            for item in raw:
                if isinstance(item, (list, tuple)):
                    cmds.append(item)
                    continue
                if isinstance(item, dict):
                    if "create" in item:
                        vals = item["create"]
                        cmds.append([0, 0, vals])
                    elif "link" in item:
                        cmds.append([4, int(item["link"]), 0])
                    elif "unlink" in item:
                        cmds.append([3, int(item["unlink"]), 0])
                    elif "delete" in item:
                        cmds.append([2, int(item["delete"]), 0])
                    elif "replace" in item and isinstance(item["replace"], list):
                        cmds.append([6, 0, list(map(int, item["replace"]))])
                    elif "update" in item and isinstance(item["update"], dict):
                        _id = int(item["update"].get("id"))
                        _vals = item["update"].get("vals") or {}
                        cmds.append([1, _id, _vals])
            return cmds
        return False

    return False


def _build_vals(Model, payload):
    """Build create/write vals from payload (ignores unknown keys)."""
    fields_map = Model._fields
    vals = {}
    for k, v in payload.items():
        if k in ("defaults", "attachments", "attachments_mode"):
            continue
        if k not in fields_map:
            continue
        f = fields_map[k]
        if f.type in ("char", "text", "html", "float", "integer", "boolean",
                      "selection", "date", "datetime", "monetary", "binary"):
            vals[k] = v
        elif f.type in ("many2one", "many2many", "one2many"):
            coerced = _coerce_relational(Model, k, v)
            if coerced not in (False, None):
                vals[k] = coerced
    return vals


def _parse_body(kwargs):
    """
    Robust JSON body parser for type='http' routes.
    - If Content-Type is application/json: read raw body and json.loads it.
    - Else: fall back to kwargs (for form-data / x-www-form-urlencoded).
    """
    try:
        httpreq = request.httprequest  # Werkzeug request
        if (httpreq.mimetype or "").lower() == "application/json":
            raw = httpreq.get_data(cache=False, as_text=True)
            if raw:
                return json.loads(raw)
    except Exception:
        pass

    # If not JSON, check if 'params' key exists in kwargs and use that as the body
    if 'params' in kwargs and isinstance(kwargs['params'], dict):
        return kwargs['params']

    return kwargs or {}


def _prepare_fields_for_output(Model, requested_fields):
    """Determine which fields to output and avoid heavy binaries by default."""
    if requested_fields:
        fields_list = [f for f in requested_fields if f in Model._fields]
    else:
        fields_list = [
            n for n, f in Model._fields.items()
            if getattr(f, "store", False)
               and not (f.type == "binary" and n in DEFAULT_BINARY_FIELD_BLOCKLIST)
        ]
    return fields_list


def _serialize_record(rec, fields_list):
    row = {}
    for f in fields_list:
        if f not in rec._fields:
            continue
        field = rec._fields[f]
        val = rec[f]
        if field.type == "many2one":
            row[f] = {"id": val.id, "name": val.display_name} if val else None
        elif field.type in ("many2many", "one2many"):
            row[f] = [{"id": x.id, "name": x.display_name} for x in val]
        else:
            row[f] = val
    return row


def _serialize_partner_min(p):
    return {"id": p.id, "name": p.display_name} if p else None


def _get_chatter_data(rec, limit=20):
    """Get chatter data for a record"""
    if not hasattr(rec, 'message_ids'):
        return {"messages": [], "notes": [], "activities": []}

    chatter_data = {"messages": [], "notes": [], "activities": []}

    # Get messages and notes
    try:
        all_msgs = rec.message_ids.sorted(key=lambda x: x.id, reverse=True)[:limit]

        # Get subtype info for determining internal vs external
        Subtype = request.env["mail.message.subtype"].sudo()
        subtype_ids = all_msgs.mapped("subtype_id").ids
        subtype_map = {}
        if subtype_ids:
            for st in Subtype.browse(subtype_ids):
                is_internal = getattr(st, 'internal', False)
                subtype_map[st.id] = bool(is_internal)

        def _serialize_message(m):
            is_internal = False
            if m.subtype_id:
                is_internal = subtype_map.get(m.subtype_id.id, False)
            kind = "note" if is_internal else "message"

            # Get attachments
            atts = m.attachment_ids if hasattr(m, 'attachment_ids') else []
            att_data = []
            for a in atts:
                att_data.append({
                    "id": a.id,
                    "name": a.name,
                    "mimetype": getattr(a, 'mimetype', 'application/octet-stream'),
                    "file_size": getattr(a, 'file_size', 0)
                })

            # Get author info
            author = _serialize_partner_min(m.author_id) if hasattr(m, 'author_id') and m.author_id else None

            return {
                "id": m.id,
                "date": m.date if hasattr(m, 'date') else m.create_date,
                "subject": getattr(m, 'subject', '') or "",
                "body": getattr(m, 'body', '') or "",
                "author": author,
                "subtype_id": {"id": m.subtype_id.id, "name": m.subtype_id.name} if m.subtype_id else None,
                "message_type": getattr(m, 'message_type', 'comment'),
                "attachment_count": len(atts),
                "attachments": att_data,
                "kind": kind,
            }

        # Serialize all messages and split
        serialized = [_serialize_message(m) for m in all_msgs]
        chatter_data["messages"] = [s for s in serialized if s["kind"] == "message"]
        chatter_data["notes"] = [s for s in serialized if s["kind"] == "note"]

    except Exception:
        pass

    # Get activities
    try:
        if hasattr(rec, 'activity_ids'):
            all_acts = rec.activity_ids.sorted(key=lambda x: x.id, reverse=True)[:limit]

            def _serialize_activity(a):
                return {
                    "id": a.id,
                    "activity_type": {
                        "id": a.activity_type_id.id,
                        "name": a.activity_type_id.name
                    } if a.activity_type_id else None,
                    "summary": getattr(a, 'summary', '') or "",
                    "note": getattr(a, 'note', '') or "",
                    "date_deadline": getattr(a, 'date_deadline', None),
                    "user": _serialize_partner_min(a.user_id.partner_id) if a.user_id and hasattr(a.user_id,
                                                                                                  'partner_id') else None,
                    "create_date": a.create_date,
                    "state": getattr(a, "state", None),
                }

            chatter_data["activities"] = [_serialize_activity(a) for a in all_acts]
    except Exception:
        pass

    return chatter_data


class GenericAPI(http.Controller):

    @http.route("/api/<string:model>/fields", type="http", auth="bearer", methods=["GET"], cors="*", csrf=False)
    def fields(self, model, **kwargs):
        try:
            Model, model_name = _get_model(model)
            meta = {}
            for name, f in Model._fields.items():
                meta[name] = {
                    "type": f.type,
                    "required": bool(getattr(f, "required", False)),
                    "relation": getattr(f, "comodel_name", None),
                    "store": bool(getattr(f, "store", False)),
                    "readonly": bool(getattr(f, "readonly", False)),
                }
            return _json({"ok": True, "model": model_name, "fields": meta})
        except Exception as e:
            return _json({"ok": False, "error": str(e)}, status=400)

    # ============================================================================================

    @http.route("/api/<string:model>/create", type="http", auth="bearer", methods=["POST"], cors="*", csrf=False)
    def create(self, model, **kwargs):
        try:
            Model, model_name = _get_model(model)
            body = _parse_body(kwargs)
            defaults = body.get("defaults") or {}
            attachments = body.get("attachments") or []
            attachments_mode = (body.get("attachments_mode") or "append").lower()

            # If company_id is provided, adjust context so defaults and constraints
            # honor the intended company instead of current user's default company.
            desired_company_id = None
            raw_company = (
                body.get("company_id")
                or defaults.get("company_id")
                or (body.get("data") or {}).get("company_id")
                or (body.get("params") or {}).get("company_id")
            )
            if raw_company is not None and "company_id" in Model._fields:
                try:
                    coerced_company = _coerce_relational(Model, "company_id", raw_company)
                    if isinstance(coerced_company, int) and coerced_company > 0:
                        desired_company_id = coerced_company
                except Exception:
                    pass

            if desired_company_id:
                Model = Model.with_context(
                    allowed_company_ids=[desired_company_id],
                    default_company_id=desired_company_id,
                    force_company=desired_company_id,
                )

            # If model's company_id is a related field (e.g., team_id.company_id),
            # resolve the owner (e.g. team) for the requested company so the posted company_id is applied.
            related_owner_field_name = None
            resolved_owner_id = None  # team_id or other owner id when company_id is related
            if "company_id" in Model._fields:
                _company_field = Model._fields["company_id"]
                related_expr = getattr(_company_field, "related", False)
                if related_expr and isinstance(related_expr, str):
                    parts = related_expr.split(".")
                    if parts:
                        related_owner_field_name = parts[0]

            if desired_company_id and related_owner_field_name and related_owner_field_name in Model._fields:
                owner_field = Model._fields[related_owner_field_name]
                owner_model = request.env[owner_field.comodel_name].sudo()
                try:
                    owner_rec = owner_model.search([("company_id", "=", desired_company_id)], limit=1)
                    if owner_rec:
                        resolved_owner_id = owner_rec.id
                        # If client did not send owner, set it in defaults so it is used
                        owner_given = (related_owner_field_name in body) or (related_owner_field_name in defaults)
                        if not owner_given:
                            defaults[related_owner_field_name] = resolved_owner_id
                    else:
                        return _json({
                            "ok": False,
                            "error_type": "required_field_error",
                            "error_code": "REQUIRED_FIELD_ERROR",
                            "error": f"No {related_owner_field_name} found for company_id={desired_company_id}. "
                                     f"Provide '{related_owner_field_name}' in payload for the desired company.",
                            "required_fields": [related_owner_field_name]
                        }, status=400)
                except Exception:
                    pass

            # Validate field names and data types before processing
            invalid_fields = []
            type_errors = []
            required_field_errors = []
            available_fields = Model._fields

            # Helper function to check required fields
            def check_required_fields(Model, provided_fields):
                """Check if all truly required fields are provided"""
                required_fields = []
                for field_name, field_info in Model._fields.items():
                    # Only check fields that are truly required and not computed
                    if (field_info.required and
                            field_name not in provided_fields and
                            not field_info.compute and  # Skip computed fields
                            not field_info.default and  # Skip fields with default values
                            field_name not in ['id', 'create_uid', 'create_date', 'write_uid', 'write_date',
                                               'kanban_state'] and  # Skip system fields and state fields
                            field_info.type not in ['one2many',
                                                    'many2many']):  # Skip relational fields that can be empty

                        # Additional check: only include fields that are commonly required for business logic
                        if field_info.type in ['char', 'text', 'many2one', 'selection', 'integer', 'float', 'date',
                                               'datetime']:
                            required_fields.append(field_name)

                return required_fields

            # Helper function to validate field types
            def validate_field_type(field_name, field_value, field_info):
                """Validate if field value matches expected field type"""
                if field_value is None:
                    return None  # None values are generally allowed

                field_type = field_info.type
                error_msg = None

                try:
                    if field_type == 'char' and not isinstance(field_value, str):
                        error_msg = f"Expected string, got {type(field_value).__name__}"
                    elif field_type == 'text' and not isinstance(field_value, str):
                        error_msg = f"Expected string, got {type(field_value).__name__}"
                    elif field_type == 'html' and not isinstance(field_value, str):
                        error_msg = f"Expected string, got {type(field_value).__name__}"
                    elif field_type == 'integer':
                        if not isinstance(field_value, (int, str)):
                            error_msg = f"Expected integer or string, got {type(field_value).__name__}"
                        else:
                            int(field_value)  # Test if it can be converted to int
                    elif field_type == 'float':
                        if not isinstance(field_value, (int, float, str)):
                            error_msg = f"Expected number or string, got {type(field_value).__name__}"
                        else:
                            float(field_value)  # Test if it can be converted to float
                    elif field_type == 'boolean':
                        if not isinstance(field_value, (bool, int, str)):
                            error_msg = f"Expected boolean, integer, or string, got {type(field_value).__name__}"
                    elif field_type == 'many2one':
                        if not isinstance(field_value, (int, str, dict)):
                            error_msg = f"Expected integer, string, or dict, got {type(field_value).__name__}"
                        elif isinstance(field_value, dict) and 'id' not in field_value:
                            error_msg = "Many2one dict must contain 'id' key"
                    elif field_type == 'many2many':
                        if not isinstance(field_value, (list, str)):
                            error_msg = f"Expected list or string, got {type(field_value).__name__}"
                    elif field_type == 'one2many':
                        if not isinstance(field_value, (list, str)):
                            error_msg = f"Expected list or string, got {type(field_value).__name__}"
                    elif field_type == 'selection':
                        if not isinstance(field_value, str):
                            error_msg = f"Expected string, got {type(field_value).__name__}"
                    elif field_type == 'date':
                        if not isinstance(field_value, str):
                            error_msg = f"Expected string (YYYY-MM-DD), got {type(field_value).__name__}"
                    elif field_type == 'datetime':
                        if not isinstance(field_value, str):
                            error_msg = f"Expected string (YYYY-MM-DD HH:MM:SS), got {type(field_value).__name__}"
                    elif field_type == 'binary':
                        if not isinstance(field_value, (str, bytes)):
                            error_msg = f"Expected string or bytes, got {type(field_value).__name__}"
                    elif field_type == 'monetary':
                        if not isinstance(field_value, (int, float, str)):
                            error_msg = f"Expected number or string, got {type(field_value).__name__}"
                        else:
                            float(field_value)  # Test if it can be converted to float
                except (ValueError, TypeError) as e:
                    error_msg = f"Invalid value for {field_type}: {str(e)}"

                return error_msg

            # Check defaults fields
            for field_name, field_value in defaults.items():
                if field_name not in available_fields:
                    invalid_fields.append(f"defaults.{field_name}")
                else:
                    field_info = available_fields[field_name]
                    type_error = validate_field_type(field_name, field_value, field_info)
                    if type_error:
                        type_errors.append(f"defaults.{field_name}: {type_error}")

            # Check main payload fields (excluding system fields)
            for field_name, field_value in body.items():
                if field_name not in ["defaults", "attachments", "attachments_mode"]:
                    if field_name not in available_fields:
                        invalid_fields.append(field_name)
                    else:
                        field_info = available_fields[field_name]
                        type_error = validate_field_type(field_name, field_value, field_info)
                        if type_error:
                            type_errors.append(f"{field_name}: {type_error}")

            # Check required fields (optional - can be disabled by adding skip_required_check=true to request)
            skip_required_check = body.get('skip_required_check', False)
            if not skip_required_check:
                all_provided_fields = set()
                all_provided_fields.update(defaults.keys())
                all_provided_fields.update([k for k in body.keys() if
                                            k not in ["defaults", "attachments", "attachments_mode",
                                                      "skip_required_check"]])

                missing_required_fields = check_required_fields(Model, all_provided_fields)
                if missing_required_fields:
                    required_field_errors.extend(missing_required_fields)

            # Return validation errors
            if invalid_fields or type_errors or required_field_errors:
                error_response = {
                    "ok": False,
                    "available_fields": list(available_fields.keys())
                }

                # Prioritize required field errors
                if required_field_errors:
                    error_response.update({
                        "error_type": "required_field_error",
                        "error_code": "REQUIRED_FIELD_ERROR",
                        "required_fields": required_field_errors,
                        "error": f"Required fields missing: {', '.join(required_field_errors)}"
                    })
                else:
                    error_response.update({
                        "error_type": "field_validation_error",
                        "error_code": "FIELD_VALIDATION_ERROR"
                    })

                if invalid_fields:
                    error_response["invalid_fields"] = invalid_fields
                    if not required_field_errors:
                        error_response["error"] = f"Invalid field names: {', '.join(invalid_fields)}"

                if type_errors:
                    error_response["type_errors"] = type_errors
                    if not required_field_errors:
                        if invalid_fields:
                            error_response["error"] += f"; Type errors: {'; '.join(type_errors)}"
                        else:
                            error_response["error"] = f"Field type errors: {'; '.join(type_errors)}"

                return _json(error_response, status=400)

            vals = dict(defaults)
            vals.update(_build_vals(Model, body))

            # If caller provided company_id: force it into vals (or the field that drives it).
            if desired_company_id and "company_id" in Model._fields:
                company_field = Model._fields["company_id"]
                if getattr(company_field, "related", False) and related_owner_field_name and resolved_owner_id is not None:
                    # company_id is related (e.g. team_id.company_id): set owner so posted company_id is applied
                    vals[related_owner_field_name] = resolved_owner_id
                elif not getattr(company_field, "related", False):
                    vals.setdefault("company_id", desired_company_id)

            # Debug: log final vals for troubleshooting
            try:
                _logger.info("Final vals to create %s: %s", model_name, {k: vals.get(k) for k in ["company_id", "team_id", "branch_id"]})
            except Exception:
                pass

            rec = Model.create(vals)

            # When company_id is related (e.g. team_id.company_id), the model's create() may overwrite
            # team_id. Force the posted company by writing the resolved team after create (API only).
            if desired_company_id and related_owner_field_name and resolved_owner_id is not None:
                try:
                    rec.sudo().write({related_owner_field_name: resolved_owner_id})
                except Exception:
                    pass

            if attachments:
                _handle_attachments(attachments, model_name, rec.id, mode=attachments_mode)

            stored_fields = []
            for name, field in rec._fields.items():
                if field.store and not field.compute:
                    stored_fields.append(name)

            if 'id' not in stored_fields:
                stored_fields.append('id')

            # Use sudo() for read/chatter: record was just created successfully; multi-company
            # record rules may block read for the current user's company context.
            rec_read = rec.sudo()
            try:
                record_data = rec_read.read(stored_fields)[0] if stored_fields else {'id': rec.id}
            except Exception:
                record_data = {
                    'id': rec.id,
                    'name': getattr(rec, 'name', '') if hasattr(rec, 'name') else ''
                }

            # Include chatter data by default
            include_chatter = kwargs.get("include_chatter", "true").lower() != "false"
            if include_chatter:
                chatter_limit = int(kwargs.get("chatter_limit", 20))
                record_data["chatter"] = _get_chatter_data(rec_read, chatter_limit)

            return _json({
                "ok": True,
                "model": model_name,
                "id": rec.id,
                "data": record_data
            })

        except (AccessError, MissingError) as e:
            # Access and Missing errors should be caught first
            error_type = "access_error" if isinstance(e, AccessError) else "missing_error"
            error_code = "ACCESS_ERROR" if isinstance(e, AccessError) else "MISSING_ERROR"
            status_code = 403 if isinstance(e, AccessError) else 404
            return _json({
                "ok": False,
                "error": str(e),
                "error_type": error_type,
                "error_code": error_code
            }, status=status_code)
        except UserError as e:
            return _json({
                "ok": False,
                "error": str(e),
                "error_type": "user_error",
                "error_code": "USER_ERROR"
            }, status=400)
        except ValidationError as e:
            # Check if it's actually a database constraint error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['duplicate', 'already exists', 'unique constraint']):
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "duplicate_error",
                    "error_code": "DUPLICATE_ERROR"
                }, status=400)
            elif any(keyword in error_msg for keyword in ['constraint', 'unique', 'foreign key']):
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "constraint_error",
                    "error_code": "CONSTRAINT_ERROR"
                }, status=400)
            else:
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "validation_error",
                    "error_code": "VALIDATION_ERROR"
                }, status=400)
        except IntegrityError as e:
            # Check if it's a duplicate key error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['duplicate key', 'unique constraint', 'already exists']):
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "duplicate_error",
                    "error_code": "DUPLICATE_ERROR"
                }, status=400)
            else:
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "integrity_error",
                    "error_code": "INTEGRITY_ERROR"
                }, status=400)
        except ValueError as e:
            # Handle model validation and field validation errors
            error_msg = str(e).lower()
            if 'unknown model' in error_msg or 'not allowed' in error_msg:
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "model_error",
                    "error_code": "MODEL_ERROR"
                }, status=400)
            else:
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "value_error",
                    "error_code": "VALUE_ERROR"
                }, status=400)
        except Exception as e:
            # Log the full traceback for debugging
            traceback.print_exc()
            return _json({
                "ok": False,
                "error": str(e),
                "error_type": "server_error",
                "error_code": "SERVER_ERROR",
                "exception_type": type(e).__name__
            }, status=500)

    # ============================================================================================

    @http.route("/api/<string:model>/<int:rec_id>", type="http", auth="bearer", methods=["GET"], cors="*", csrf=False)
    def read(self, model, rec_id, **kwargs):
        try:
            Model, model_name = _get_model(model)
            rec = Model.browse(rec_id)
            if not rec.exists():
                return _json({"ok": False, "error": "Record not found"}, status=404)

            fields_param = kwargs.get("fields")
            fields_list = _prepare_fields_for_output(Model, [f.strip() for f in
                                                             fields_param.split(",")] if fields_param else [])

            data = _serialize_record(rec, fields_list)

            # Include chatter data by default (can be disabled with include_chatter=false)
            include_chatter = kwargs.get("include_chatter", "true").lower() != "false"
            if include_chatter:
                chatter_limit = int(kwargs.get("chatter_limit", 20))
                data["chatter"] = _get_chatter_data(rec, chatter_limit)

            return _json({"ok": True, "model": model_name, "data": data})
        except Exception as e:
            return _json({"ok": False, "error": str(e)}, status=400)

    # ============================================================================================

    @http.route("/api/<string:model>/update/<int:rec_id>", type="http", auth="bearer", methods=["POST", "PUT", "PATCH"],
                cors="*", csrf=False)
    def update(self, model, rec_id, **kwargs):
        try:
            Model, model_name = _get_model(model)
            rec = Model.browse(rec_id)
            if not rec.exists():
                return _json({"ok": False, "error": "Record not found"}, status=404)

            body = _parse_body(kwargs)
            attachments = body.get("attachments") or []
            attachments_mode = (body.get("attachments_mode") or "append").lower()

            # If company_id is provided in update, widen context to that company so write honors it
            desired_company_id = None
            if "company_id" in body and "company_id" in Model._fields:
                try:
                    coerced_company = _coerce_relational(Model, "company_id", body.get("company_id"))
                    if isinstance(coerced_company, int) and coerced_company > 0:
                        desired_company_id = coerced_company
                except Exception:
                    pass
            if desired_company_id:
                Model = Model.with_context(
                    allowed_company_ids=[desired_company_id],
                    default_company_id=desired_company_id,
                    force_company=desired_company_id,
                )
                rec = Model.browse(rec_id)
                if not rec.exists():
                    return _json({"ok": False, "error": "Record not found"}, status=404)

            # Validate field names and data types before processing
            invalid_fields = []
            type_errors = []
            required_field_errors = []
            available_fields = Model._fields

            # Helper function to check required fields (for update, we only check if required fields are being set to None/empty)
            def check_required_fields_update(Model, provided_fields):
                """Check if required fields are being set to None or empty values"""
                required_field_errors = []
                for field_name, field_value in provided_fields.items():
                    if field_name in Model._fields:
                        field_info = Model._fields[field_name]
                        if field_info.required and (field_value is None or field_value == "" or field_value == []):
                            required_field_errors.append(field_name)
                return required_field_errors

            # Helper function to validate field types (reused from create method)
            def validate_field_type(field_name, field_value, field_info):
                """Validate if field value matches expected field type"""
                if field_value is None:
                    return None  # None values are generally allowed

                field_type = field_info.type
                error_msg = None

                try:
                    if field_type == 'char' and not isinstance(field_value, str):
                        error_msg = f"Expected string, got {type(field_value).__name__}"
                    elif field_type == 'text' and not isinstance(field_value, str):
                        error_msg = f"Expected string, got {type(field_value).__name__}"
                    elif field_type == 'html' and not isinstance(field_value, str):
                        error_msg = f"Expected string, got {type(field_value).__name__}"
                    elif field_type == 'integer':
                        if not isinstance(field_value, (int, str)):
                            error_msg = f"Expected integer or string, got {type(field_value).__name__}"
                        else:
                            int(field_value)  # Test if it can be converted to int
                    elif field_type == 'float':
                        if not isinstance(field_value, (int, float, str)):
                            error_msg = f"Expected number or string, got {type(field_value).__name__}"
                        else:
                            float(field_value)  # Test if it can be converted to float
                    elif field_type == 'boolean':
                        if not isinstance(field_value, (bool, int, str)):
                            error_msg = f"Expected boolean, integer, or string, got {type(field_value).__name__}"
                    elif field_type == 'many2one':
                        if not isinstance(field_value, (int, str, dict)):
                            error_msg = f"Expected integer, string, or dict, got {type(field_value).__name__}"
                        elif isinstance(field_value, dict) and 'id' not in field_value:
                            error_msg = "Many2one dict must contain 'id' key"
                    elif field_type == 'many2many':
                        if not isinstance(field_value, (list, str)):
                            error_msg = f"Expected list or string, got {type(field_value).__name__}"
                    elif field_type == 'one2many':
                        if not isinstance(field_value, (list, str)):
                            error_msg = f"Expected list or string, got {type(field_value).__name__}"
                    elif field_type == 'selection':
                        if not isinstance(field_value, str):
                            error_msg = f"Expected string, got {type(field_value).__name__}"
                    elif field_type == 'date':
                        if not isinstance(field_value, str):
                            error_msg = f"Expected string (YYYY-MM-DD), got {type(field_value).__name__}"
                    elif field_type == 'datetime':
                        if not isinstance(field_value, str):
                            error_msg = f"Expected string (YYYY-MM-DD HH:MM:SS), got {type(field_value).__name__}"
                    elif field_type == 'binary':
                        if not isinstance(field_value, (str, bytes)):
                            error_msg = f"Expected string or bytes, got {type(field_value).__name__}"
                    elif field_type == 'monetary':
                        if not isinstance(field_value, (int, float, str)):
                            error_msg = f"Expected number or string, got {type(field_value).__name__}"
                        else:
                            float(field_value)  # Test if it can be converted to float
                except (ValueError, TypeError) as e:
                    error_msg = f"Invalid value for {field_type}: {str(e)}"

                return error_msg

            # Check main payload fields (excluding system fields)
            for field_name, field_value in body.items():
                if field_name not in ["attachments", "attachments_mode"]:
                    if field_name not in available_fields:
                        invalid_fields.append(field_name)
                    else:
                        field_info = available_fields[field_name]
                        type_error = validate_field_type(field_name, field_value, field_info)
                        if type_error:
                            type_errors.append(f"{field_name}: {type_error}")

            # Check required fields (for update, check if required fields are being set to None/empty)
            # Optional - can be disabled by adding skip_required_check=true to request
            skip_required_check = body.get('skip_required_check', False)
            if not skip_required_check:
                update_fields = {k: v for k, v in body.items() if
                                 k not in ["attachments", "attachments_mode", "skip_required_check"]}
                required_field_errors = check_required_fields_update(Model, update_fields)

            # Return validation errors
            if invalid_fields or type_errors or required_field_errors:
                error_response = {
                    "ok": False,
                    "available_fields": list(available_fields.keys())
                }

                # Prioritize required field errors
                if required_field_errors:
                    error_response.update({
                        "error_type": "required_field_error",
                        "error_code": "REQUIRED_FIELD_ERROR",
                        "required_fields": required_field_errors,
                        "error": f"Required fields cannot be empty: {', '.join(required_field_errors)}"
                    })
                else:
                    error_response.update({
                        "error_type": "field_validation_error",
                        "error_code": "FIELD_VALIDATION_ERROR"
                    })

                if invalid_fields:
                    error_response["invalid_fields"] = invalid_fields
                    if not required_field_errors:
                        error_response["error"] = f"Invalid field names: {', '.join(invalid_fields)}"

                if type_errors:
                    error_response["type_errors"] = type_errors
                    if not required_field_errors:
                        if invalid_fields:
                            error_response["error"] += f"; Type errors: {'; '.join(type_errors)}"
                        else:
                            error_response["error"] = f"Field type errors: {'; '.join(type_errors)}"

                return _json(error_response, status=400)

            vals = _build_vals(Model, body)

            # If caller provided company_id and field is writeable (not related), force it into vals
            if desired_company_id and "company_id" in Model._fields:
                company_field = Model._fields["company_id"]
                if not getattr(company_field, "related", False):
                    vals.setdefault("company_id", desired_company_id)

            # Debug: log final vals for troubleshooting
            try:
                _logger.info("Final vals to write %s(%s): %s", model_name, rec_id, {k: vals.get(k) for k in ["company_id", "team_id", "branch_id"]})
            except Exception:
                pass
            if vals:
                rec.write(vals)

            if attachments:
                _handle_attachments(attachments, model_name, rec.id, mode=attachments_mode)

            return _json({"ok": True, "model": model_name, "id": rec.id})
        except (AccessError, MissingError) as e:
            # Access and Missing errors should be caught first
            error_type = "access_error" if isinstance(e, AccessError) else "missing_error"
            error_code = "ACCESS_ERROR" if isinstance(e, AccessError) else "MISSING_ERROR"
            status_code = 403 if isinstance(e, AccessError) else 404
            return _json({
                "ok": False,
                "error": str(e),
                "error_type": error_type,
                "error_code": error_code
            }, status=status_code)
        except UserError as e:
            return _json({
                "ok": False,
                "error": str(e),
                "error_type": "user_error",
                "error_code": "USER_ERROR"
            }, status=400)
        except ValidationError as e:
            # Check if it's actually a database constraint error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['duplicate', 'already exists', 'unique constraint']):
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "duplicate_error",
                    "error_code": "DUPLICATE_ERROR"
                }, status=400)
            elif any(keyword in error_msg for keyword in ['constraint', 'unique', 'foreign key']):
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "constraint_error",
                    "error_code": "CONSTRAINT_ERROR"
                }, status=400)
            else:
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "validation_error",
                    "error_code": "VALIDATION_ERROR"
                }, status=400)
        except IntegrityError as e:
            # Check if it's a duplicate key error
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['duplicate key', 'unique constraint', 'already exists']):
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "duplicate_error",
                    "error_code": "DUPLICATE_ERROR"
                }, status=400)
            else:
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "integrity_error",
                    "error_code": "INTEGRITY_ERROR"
                }, status=400)
        except ValueError as e:
            # Handle model validation and field validation errors
            error_msg = str(e).lower()
            if 'unknown model' in error_msg or 'not allowed' in error_msg:
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "model_error",
                    "error_code": "MODEL_ERROR"
                }, status=400)
            else:
                return _json({
                    "ok": False,
                    "error": str(e),
                    "error_type": "value_error",
                    "error_code": "VALUE_ERROR"
                }, status=400)
        except Exception as e:
            # Log the full traceback for debugging
            traceback.print_exc()
            return _json({
                "ok": False,
                "error": str(e),
                "error_type": "server_error",
                "error_code": "SERVER_ERROR",
                "exception_type": type(e).__name__
            }, status=500)

    # ============================================================================================

    @http.route("/api/<string:model>/search_read", type="http", auth="bearer", methods=["POST"], cors="*", csrf=False)
    def search_read(self, model, **kwargs):
        try:
            Model, model_name = _get_model(model)
            body = _parse_body(kwargs)

            domain = body.get("domain") or []
            requested_fields = body.get("fields") or []
            limit = int(body.get("limit") or 80)
            offset = int(body.get("offset") or 0)
            order = body.get("order") or "id desc"

            fields_list = _prepare_fields_for_output(Model, requested_fields)

            total = Model.search_count(domain)
            recs = Model.search(domain, limit=limit, offset=offset, order=order)

            # Include chatter data in search results (can be disabled)
            include_chatter = body.get("include_chatter", True)
            chatter_limit = int(body.get("chatter_limit", 10))  # Smaller limit for search results

            data = []
            for r in recs:
                row_data = _serialize_record(r, fields_list)
                if include_chatter:
                    row_data["chatter"] = _get_chatter_data(r, chatter_limit)
                data.append(row_data)

            return _json({"ok": True, "model": model_name, "total": total, "returned": len(recs), "data": data})
        except Exception as e:
            return _json({"ok": False, "error": str(e)}, status=400)

    # ============================================================================================

    @http.route("/api/<string:model>/delete/<int:rec_id>", type="http", auth="bearer", methods=["DELETE"], cors="*",
                csrf=False)
    def delete(self, model, rec_id, **kwargs):
        try:
            Model, model_name = _get_model(model)
            rec = Model.browse(rec_id)
            if not rec.exists():
                return _json({"ok": False, "error": "Record not found"}, status=404)
            rec.unlink()
            return _json({"ok": True, "model": model_name, "deleted_id": rec_id})
        except Exception as e:
            return _json({"ok": False, "error": str(e)}, status=400)
