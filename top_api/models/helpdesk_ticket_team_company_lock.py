# -*- coding: utf-8 -*-
"""
Option C.1: Prevent changing helpdesk team from auto-changing ticket company.
"""
from odoo import api, models
from odoo.exceptions import AccessError


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    def read(self, fields=None, load="_classic_read"):
        """
        Prevent form crash when ticket.team_id points to an unreadable team
        (multi-company rule on helpdesk.team).

        If reading with team_id fails, retry without team_id and return team_id=False
        for records where current user cannot read that team.
        """
        try:
            return super().read(fields=fields, load=load)
        except AccessError as e:
            if not fields or "team_id" not in fields:
                raise
            if "helpdesk.team" not in str(e):
                raise

            safe_fields = [f for f in fields if f != "team_id"]
            rows = super().read(fields=safe_fields, load=load)
            row_by_id = {row.get("id"): row for row in rows}

            for rec in self:
                row = row_by_id.get(rec.id)
                if not row:
                    continue
                team = rec.sudo().team_id
                if not team:
                    row["team_id"] = False
                    continue
                try:
                    team.with_env(self.env).check_access_rule("read")
                    row["team_id"] = [team.id, team.display_name]
                except AccessError:
                    row["team_id"] = False
            return rows

    def web_read(self, specification):
        """
        Odoo web client often uses web_read() for form loads.
        Apply the same safe fallback as read(): if team is unreadable due to
        multi-company rule, return team_id=False instead of raising AccessError.
        """
        try:
            return super().web_read(specification)
        except AccessError as e:
            if "helpdesk.team" not in str(e):
                raise
            if not isinstance(specification, dict):
                raise
            if "team_id" not in specification:
                raise

            safe_spec = dict(specification)
            safe_spec.pop("team_id", None)
            rows = super().web_read(safe_spec)
            row_by_id = {row.get("id"): row for row in rows}

            for rec in self:
                row = row_by_id.get(rec.id)
                if not row:
                    continue
                team = rec.sudo().team_id
                if not team:
                    row["team_id"] = False
                    continue
                try:
                    team.with_env(self.env).check_access_rule("read")
                    row["team_id"] = {"id": team.id, "display_name": team.display_name}
                except AccessError:
                    row["team_id"] = False
            return rows

    @api.onchange("team_id")
    def _top_api_onchange_team_id_keep_company(self):
        """
        Option C.1: When user changes team_id in the form, keep existing company_id.
        Opt-out: context allow_team_change_company=True.
        """
        if self.env.context.get("allow_team_change_company"):
            return
        for rec in self:
            old_company = rec._origin.company_id if rec._origin and rec._origin.id else rec.company_id
            if old_company:
                rec.company_id = old_company.id

    def write(self, vals):
        """
        Option C.1 on save: If team_id changes without explicit company_id, restore previous company_id.
        """
        if (
            "team_id" in vals
            and "company_id" not in vals
            and not self.env.context.get("allow_team_change_company")
        ):
            old_company_by_id = {r.id: r.company_id.id for r in self}
            res = super().write(vals)
            for r in self:
                old_company_id = old_company_by_id.get(r.id)
                if old_company_id and r.company_id.id != old_company_id:
                    super(HelpdeskTicket, r.with_context(allow_team_change_company=True)).write(
                        {"company_id": old_company_id}
                    )
            return res
        return super().write(vals)
