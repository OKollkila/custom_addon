# -*- coding: utf-8 -*-
import json
from datetime import datetime, date
from urllib.parse import urlencode

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError


PROMO_DEFAULT_URL = (
    "http://15.184.10.121:8080/HISAdmin/api/promotionorder/findPromotionOrderByDate"
)


class PromotionOrderSyncService(models.AbstractModel):
    _name = "promotion.order.sync.service"
    _description = "Service to fetch Promotion Orders and create CRM Leads"

    # You can override these via System Parameters:
    # clinic_promo_order.endpoint_url -> custom endpoint (optional)
    # clinic_promo_order.timeout -> request timeout seconds (default 30)
    def _get_endpoint(self):
        ICP = self.env["ir.config_parameter"].sudo()
        return ICP.get_param("clinic_promo_order.endpoint_url", default=PROMO_DEFAULT_URL)

    def _get_timeout(self):
        ICP = self.env["ir.config_parameter"].sudo()
        try:
            return int(ICP.get_param("clinic_promo_order.timeout", default="30"))
        except Exception:
            return 30

    def _today_str(self):
        # Respect server/user tz by using Odoo date util
        today = fields.Date.context_today(self)
        if isinstance(today, str):
            return today
        return today.strftime("%Y-%m-%d")

    def _ms_to_dt_str(self, ms_value):
        if not ms_value:
            return ""
        try:
            # orderDate is epoch milliseconds
            dt = datetime.utcfromtimestamp(int(ms_value) / 1000.0)
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            return str(ms_value)

    def _build_html_table_for_unmapped(self, payload_dict, consumed_keys):
        """Build an HTML table for any keys not mapped to CRM fields."""
        rows = []
        for key, val in payload_dict.items():
            if key in consumed_keys:
                continue
            # pretty the value
            if isinstance(val, (dict, list)):
                try:
                    val_str = json.dumps(val, ensure_ascii=False)
                except Exception:
                    val_str = str(val)
            else:
                val_str = "" if val is None else str(val)
            rows.append(f"<tr><td><b>{key}</b></td><td>{val_str}</td></tr>")
        if not rows:
            return ""
        table = (
            "<h4>Unmapped Fields</h4>"
            '<table border="1" cellpadding="4" cellspacing="0">'
            "<thead><tr><th>Field</th><th>Value</th></tr></thead>"
            "<tbody>{}</tbody></table>".format("".join(rows))
        )
        return table

    def _find_m2o_by_name(self, model, name):
        """Generic name-based resolver. Returns recordset or False."""
        if not name:
            return False
        rec = self.env[model].sudo().search([("name", "=", name)], limit=1)
        return rec or False

    def _prepare_lead_vals(self, item):
        """
        Map known fields to crm.lead.
        Unknown fields are appended to description as an HTML table.
        """
        consumed = set()

        # Known incoming keys from endpoint (example payload)
        # id, promotionName, promotionId, serviceCode, status, orderDate,
        # patientId, patientName, mrno, mobileNo, nationalityId, email, note,
        # branch, department, speciality, paymentReference, paymentStatus, amount,
        # packageOrder, orderType, companyId

        promotion_name = item.get("promotionName")
        patient_name = item.get("patientName")
        email = item.get("email")
        phone = item.get("mobileNo")
        amount = item.get("amount")
        note = item.get("note")
        department_name = item.get("department")
        branch_name = item.get("branch")
        speciality = item.get("speciality")
        order_date_str = self._ms_to_dt_str(item.get("orderDate"))

        # mark consumed keys as we map them
        for k in [
            "promotionName", "patientName", "email", "mobileNo", "amount",
            "note", "department", "branch", "speciality", "orderDate"
        ]:
            consumed.add(k)

        # Attempt to resolve M2O by name where it makes sense in your DB
        department_id = self._find_m2o_by_name("hr.department", department_name) or False
        branch_id = self._find_m2o_by_name("res.branch", branch_name) or False  # if you use branches module
        service_id = False
        # If you keep services in a model (e.g., clinic.service), uncomment and adjust:
        # service_id = self._find_m2o_by_name("clinic.service", item.get("serviceCode")) or False

        # Build description:
        desc_parts = []
        if note:
            desc_parts.append("<h4>Note</h4><p>{}</p>".format(note))

        # Always include the readable order date if present
        if order_date_str:
            desc_parts.append("<p><b>Order Date:</b> {}</p>".format(order_date_str))
            # also include as consumed
            consumed.add("orderDate")

        # Build an HTML table for unmapped keys
        desc_parts.append(self._build_html_table_for_unmapped(item, consumed))
        # Join and strip empties
        description_html = "\n".join([p for p in desc_parts if p])

        # Stage 'New' by name (fallback to first stage)
        stage = self.env["crm.stage"].sudo().search([("name", "ilike", "New")], limit=1)
        # Team: try default team or 'Sales'
        team = self.env["crm.team"].sudo().search([], limit=1) \
               or self.env["crm.team"].sudo().search([("name", "ilike", "Sales")], limit=1)

        vals = {
            # Basic lead identity
            "name": patient_name or promotion_name or _("Promotion Lead"),
            "topic": promotion_name or False,  # you have 'topic' in your CRM
            # Contact
            "email_from": email or False,
            "phone": phone or False,
            # Commercials
            "expected_revenue": amount or 0.0,
            "type": "opportunity",
            # Source (char in your CRM dump)
            "lead_source": "Promotion Order",
            # Optional mappings if your DB has these models/fields
            "department_id": department_id.id if department_id else False,
            "branch_id": branch_id.id if branch_id else False,
            "service_id": service_id.id if service_id else False,
            "speciality": speciality or False,  # your CRM has 'speciality' as char
            # Team / Stage
            "team_id": team.id if team else False,
            "stage_id": stage.id if stage else False,
            # Description with HTML table for anything unmapped
            "description": description_html or "",
        }
        return vals

    def _is_duplicate_today(self, vals):
        """Basic dedup: same phone + topic + source created today."""
        phone = vals.get("phone") or ""
        topic = vals.get("topic") or ""
        lead_source = vals.get("lead_source") or "Promotion Order"
        if not phone and not topic:
            return False
        today = fields.Date.context_today(self)
        domain = [
            ("type", "=", "opportunity"),
            ("lead_source", "=", lead_source),
            ("create_date", ">=", datetime.combine(today, datetime.min.time())),
        ]
        if phone:
            domain.append(("phone", "=", phone))
        if topic:
            domain.append(("topic", "=", topic))
        existing = self.env["crm.lead"].sudo().search(domain, limit=1)
        return bool(existing)

    @api.model
    def cron_sync_promotion_orders(self):
        """
        Scheduled entrypoint.
        Fetch today's Promotion Orders and create CRM leads.
        """
        endpoint = self._get_endpoint()
        timeout = self._get_timeout()
        from_date = self._today_str()

        # Build URL with query string
        url = f"{endpoint}?{urlencode({'fromDate': from_date})}"

        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
        except Exception as e:
            # Don't crash the cron forever; log and continue
            self.env.cr.rollback()
            _msg = f"[PromotionOrderSync] Request failed: {e}"
            self.env["ir.logging"].sudo().create({
                "name": "PromotionOrderSync",
                "type": "server",
                "level": "ERROR",
                "dbname": self.env.cr.dbname,
                "message": _msg,
                "path": "promotion.order.sync.service",
                "func": "cron_sync_promotion_orders",
                "line": 0,
            })
            return

        try:
            payload = resp.json()
        except Exception:
            try:
                payload = json.loads(resp.text or "[]")
            except Exception as e:
                self.env["ir.logging"].sudo().create({
                    "name": "PromotionOrderSync",
                    "type": "server",
                    "level": "ERROR",
                    "dbname": self.env.cr.dbname,
                    "message": f"[PromotionOrderSync] Invalid JSON: {e}",
                    "path": "promotion.order.sync.service",
                    "func": "cron_sync_promotion_orders",
                    "line": 0,
                })
                return

        if not isinstance(payload, list):
            # Endpoint returns list; if not, wrap best-effort
            payload = [payload]

        Lead = self.env["crm.lead"].sudo()
        created = 0
        for item in payload:
            if not isinstance(item, dict):
                continue
            vals = self._prepare_lead_vals(item)
            # Dedup today
            if self._is_duplicate_today(vals):
                continue
            Lead.create(vals)
            created += 1

        self.env["ir.logging"].sudo().create({
            "name": "PromotionOrderSync",
            "type": "server",
            "level": "INFO",
            "dbname": self.env.cr.dbname,
            "message": f"[PromotionOrderSync] Created {created} CRM lead(s) for {from_date}",
            "path": "promotion.order.sync.service",
            "func": "cron_sync_promotion_orders",
            "line": 0,
        })
