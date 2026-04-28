from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    # Stops Model.write/create from calling _check_company() for this model (UserError
    # "Incompatible companies on records"). Pair with partner_id check_company=False below.
    _check_company_auto = False

    # Odoo 18+: helpdesk uses check_company on partner_id + model _check_company_auto.
    # That runs on every write (e.g. closing the ticket), not only @api.constrains.
    partner_id = fields.Many2one(check_company=False)

    def _check_company(self, fnames=None):
        """Do not enforce res.partner company against helpdesk.ticket company_id."""
        if fnames is None:
            fnames = [
                name
                for name, field in self._fields.items()
                if field.relational and field.check_company and name != 'partner_id'
            ]
            return super()._check_company(fnames)
        fnames = [n for n in fnames if n != 'partner_id']
        if not fnames:
            return
        return super()._check_company(fnames)

    @api.constrains('partner_id', 'company_id', 'team_id')
    def _check_partner_company(self):
        """Disable standard Helpdesk check: partner vs ticket company must match.

        Covers the legacy ``@api.constrains`` implementation; ``partner_id`` / ``_check_company``
        above cover Odoo 18+ automatic company checks on write (e.g. stage change to Solved/Closed).
        """
        return

    def _is_skipped_helpdesk_partner_company_error(self, exc):
        """Match Enterprise helpdesk ValidationError on partner vs ticket company."""
        msg = str(exc.args[0] if exc.args else exc).lower()
        if 'different company' not in msg or 'ticket' not in msg:
            return False
        return 'customer' in msg or 'belong' in msg

    def _validate_fields(self, field_names, excluded_names=()):
        """Run constraints but ignore helpdesk partner-vs-ticket company ValidationError.

        Belt-and-suspenders: if any other extension or registry state still runs the
        stock constraint, we do not block saves (close ticket, etc.).
        """
        field_names = set(field_names)
        excluded_names = set(excluded_names)
        for check in self._constraint_methods:
            if (
                not field_names.isdisjoint(check._constrains)
                and excluded_names.isdisjoint(check._constrains)
            ):
                try:
                    check(self)
                except ValidationError as e:
                    if self._is_skipped_helpdesk_partner_company_error(e):
                        continue
                    raise

    def _normalize_ticket_type_id(self, ticket_type_id):
        """APIs send ramcrm keys (INQUIRY, …); Many2one domains need integer ids."""
        if ticket_type_id is None or ticket_type_id is False:
            return ticket_type_id
        if isinstance(ticket_type_id, int):
            return ticket_type_id
        if isinstance(ticket_type_id, str):
            s = ticket_type_id.strip()
            if s.isdigit():
                return int(s)
            try:
                return self.env.ref(f"ramcrm.{s}").id
            except ValueError:
                pass
            Type = self.env["helpdesk.ticket.type"].sudo()
            t = Type.search([("name", "=", s)], limit=1)
            if not t:
                t = Type.search([("name", "ilike", s)], limit=1)
            if t:
                return t.id
            raise ValidationError(_("Unknown ticket type: %s") % s)
        return ticket_type_id

    # follow_up = fields.Char(
    #     string='Follow Up',
    #     compute='_compute_follow_up',
    #     store=False,
    #     readonly=True
    # )
    follow_up = fields.Text(
        string="Follow Up",
        compute="_compute_follow_up",
        store=False,
        readonly=True
    )

    patient_national_id = fields.Char(required=True)

    creation_note = fields.Text(
        string="Creation Note",
    )

    closing_note = fields.Text(
        string="Closing Note",
    )
    display_closing_note = fields.Boolean(
        compute='_compute_display_closing_note',
        store=False
    )
    admin_status = fields.Char(
        string="Admin Status",
        compute="_compute_admin_status",
        store=False,
        readonly=True
    )

    def _compute_admin_status(self):
        for rec in self:
            if rec.env.user.has_group('helpdesk.group_helpdesk_manager'):
                rec.admin_status = "Administrator"
            else:
                rec.admin_status = ""

    @api.depends('stage_id')
    def _compute_display_closing_note(self):
        for rec in self:
            rec.display_closing_note = rec.stage_id.name in ['Closed', 'Solved']

    # @api.depends('team_id')
    # def _compute_follow_up(self):
    #     for ticket in self:
    #         if ticket.team_id:
    #             partner_names = [partner.name for partner in ticket.team_id.message_partner_ids]
    #             ticket.follow_up = ', '.join(partner_names)

    @api.depends('team_id')
    def _compute_follow_up(self):
        for ticket in self:
            if ticket.team_id:
                partner_names = [partner.name or '' for partner in ticket.team_id.message_partner_ids]
                ticket.follow_up = ', '.join(partner_names)
            else:
                ticket.follow_up = False

    @api.model
    def create(self, vals):
        vals = dict(vals)
        if "ticket_type_id" in vals:
            vals["ticket_type_id"] = self._normalize_ticket_type_id(vals.get("ticket_type_id"))

        if not vals.get('creation_note'):
            raise ValidationError(_("Creation Note is required when creating a ticket."))

        national_id = vals.get('patient_national_id')
        ticket_type_id = vals.get('ticket_type_id')
        invid = vals.get('invid')
        if ticket_type_id !=28:
            if national_id and ticket_type_id:
                existing_ticket = self.search([
                    ('patient_national_id', '=', national_id),
                    ('ticket_type_id', '=', ticket_type_id),
                    ('invid', '=', invid),
                    ('stage_id.name', 'not in', ['Solved', 'Closed']),
                ], limit=1)

                if existing_ticket:
                    raise ValidationError(_(
                        "A ticket with the same National ID, Ticket Type, and Invoice already exists and is not yet solved or closed."
                    ))

        return super().create(vals)

    def write(self, vals):
        for ticket in self:
            new_stage_id = vals.get('stage_id') or ticket.stage_id.id
            new_stage = self.env['helpdesk.stage'].browse(new_stage_id)
            new_stage_name = new_stage.name

            if 'creation_note' in vals and ticket.creation_note:
                raise ValidationError(_("You cannot modify the Creation Note after it is saved."))

            if 'closing_note' in vals and ticket.closing_note:
                raise ValidationError(_("You cannot modify the Closing Note after it is saved."))

            if new_stage_name in ['Solved', 'Closed']:
                if not ticket.creation_note and not vals.get('creation_note'):
                    raise ValidationError(_("Creation Note is required before moving to a solved or closed stage."))
                if not ticket.closing_note and not vals.get('closing_note'):
                    raise ValidationError(_("Closing Note is required before moving to a solved or closed stage."))

        return super().write(vals)







