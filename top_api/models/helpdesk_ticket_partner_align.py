# -*- coding: utf-8 -*-
"""
Avoid Odoo's multi-company check on helpdesk.ticket:
"The customer cannot belong to a different company than the ticket."

When partner_id is set for another company than the ticket (team/company), we swap to an
equivalent shared partner (company_id=False) with the same contact details.
"""
from odoo import api, fields, models


class HelpdeskTicketPartnerAlign(models.Model):
    _inherit = "helpdesk.ticket"

    partner_id = fields.Many2one("res.partner", string="Customer", required=False)

    @api.model
    def _ht_predict_ram_case_team_id(self, vals):
        ticket_type_id = vals.get("ticket_type_id")
        if not ticket_type_id:
            return vals.get("team_id")
        Rule = self.env["clinizone.ticket_team_assignment_rule"].sudo()
        return Rule.compute_team(
            ticket_type_id,
            vals.get("branch_id"),
            vals.get("case_source_id"),
        )

    @api.model
    def _ht_effective_company_id_vals(self, vals, record=None):
        if vals.get("company_id"):
            return vals["company_id"]
        team_id = False
        if vals.get("ticket_type_id"):
            team_id = self._ht_predict_ram_case_team_id(vals)
        if not team_id:
            team_id = vals.get("team_id")
        if team_id:
            team = self.env["helpdesk.team"].sudo().browse(team_id)
            if team.exists():
                return team.company_id.id
        if record and record.team_id:
            return record.team_id.company_id.id
        return self.env.context.get("default_company_id") or self.env.company.id

    @api.model
    def _ht_shared_partner_equivalent(self, partner):
        Partner = self.env["res.partner"].sudo()
        if not partner.company_id:
            return partner
        domain = [("company_id", "=", False)]
        if partner.email:
            domain.append(("email", "=", partner.email))
        elif partner.phone or partner.mobile:
            phone = partner.phone or partner.mobile
            domain.extend(["|", ("phone", "=", phone), ("mobile", "=", phone)])
        else:
            domain.append(("name", "=", partner.name))
        found = Partner.search(domain, limit=1)
        if found:
            return found
        return Partner.create(
            {
                "name": partner.name,
                "email": partner.email or False,
                "phone": partner.phone or False,
                "mobile": partner.mobile or False,
                "company_id": False,
            }
        )

    @api.model
    def _ht_align_partner_vals(self, vals, company_id):
        if not company_id:
            return vals
        pid = vals.get("partner_id")
        if not pid:
            return vals
        partner = self.env["res.partner"].sudo().browse(pid)
        if not partner.exists():
            return vals
        p_c = partner.company_id.id if partner.company_id else False
        if not p_c or p_c == company_id:
            return vals
        vals = dict(vals)
        vals["partner_id"] = self._ht_shared_partner_equivalent(partner).id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        aligned = []
        for vals in vals_list:
            v = dict(vals)
            tt = v.get("ticket_type_id")
            if isinstance(tt, str):
                try:
                    v["ticket_type_id"] = self.env.ref(f"ramcrm.{tt}").id
                except ValueError:
                    pass
            cs = v.get("case_source_id")
            if isinstance(cs, str):
                try:
                    v["case_source_id"] = self.env.ref(f"ramcrm.{cs}").id
                except ValueError:
                    pass
            company_id = self._ht_effective_company_id_vals(v)
            v = self._ht_align_partner_vals(v, company_id)
            aligned.append(v)
        return super().create(aligned)

    def write(self, vals):
        vals = dict(vals)
        for rec in self:
            company_id = self._ht_effective_company_id_vals(vals, record=rec)
            base = dict(vals)
            if "partner_id" not in base:
                base["partner_id"] = rec.partner_id.id if rec.partner_id else False
            aligned = self._ht_align_partner_vals(base, company_id)
            wvals = dict(vals)
            if aligned.get("partner_id") != base.get("partner_id"):
                wvals["partner_id"] = aligned["partner_id"]
            super(HelpdeskTicketPartnerAlign, rec).write(wvals)
        return True

    @api.onchange("partner_id", "team_id")
    def _onchange_ht_align_partner_company(self):
        for ticket in self:
            if not ticket.partner_id or not ticket.team_id:
                continue
            t_company = ticket.team_id.company_id
            pc = ticket.partner_id.company_id
            if pc and t_company and pc != t_company:
                ticket.partner_id = self._ht_shared_partner_equivalent(ticket.partner_id)
