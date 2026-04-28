import datetime
import logging
import random
import requests

from odoo import models, fields, api, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

class RamCase(models.Model):
    _name = "helpdesk.ticket"
    _sql_constraints = [('unique_case_no', 'unique(case_no)', 'Case No must be unique')]
    _inherit = ['helpdesk.ticket']

    name = fields.Char('Name', related='case_no', required=False, readonly=True)
    description = fields.Html(sanitize_attributes=False, tracking=False ,required=False)
    team_id = fields.Many2one(tracking=True)
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', required=True)
    case_source_id = fields.Many2one('clinizone.ram_case_source', tracking=True)
    source = fields.Char(string='Source')
    reporter_relation_with_patient = fields.Selection([
        ('SELF', 'SELF'),
        ('FATHER', 'FATHER'),
        ('MOTHER', 'MOTHER'),
        ('RELATIVE', 'RELATIVE'),
        ('FRIEND', 'FRIEND'),
        ('OTHER', 'OTHER'),
    ], required=True, tracking=True, string='Reporter Relation with Customer', default='SELF')
    patient_national_id = fields.Char(string = 'National ID', required=False, tracking=True)
    reporter_name = fields.Char(tracking=True)
    medical_file_no = fields.Char(tracking=True)
    treating_physician_name = fields.Char(tracking=True)
    case_time = fields.Datetime(required=True, tracking=True, default=fields.Datetime.now)
    branch_id = fields.Many2one('clinizone.branch', tracking=True, domain="[('helpdesk_team_id', '!=', False)]")
    section = fields.Selection([
        ('DENTAL', 'DENTAL'),
        ('DERMATOLOGY', 'DERMATOLOGY'),
        ('MEDICAL', 'MEDICAL'),
    ], tracking=True)
    case_no = fields.Char('Case Number', readonly=True, copy=False, index=True, tracking=True)
    last_team_updated_on = fields.Datetime('Last Team Updated On', readonly=True, copy=False, tracking=True)
    lead_id = fields.Many2one('crm.lead', 'Lead', readonly=True, copy=False, tracking=True)
    city = fields.Char(string='City')
    city_final = fields.Char(string='City', compute='_compute_city_final')
    ticket_type_save2_id = fields.Integer()
    insurance_company_id = fields.Many2one(
        'insurance.company',
        string='Insurance Company',
    )
    insurance_policy = fields.Char(
        string='Insurance Policy',
    )

    # -----------------------------
    @api.onchange('ticket_type_id')
    def _onchange_ticket_type_for_insurance(self):
        for ticket in self:
            if ticket.ticket_type_id.name in ['Insurance Pharmacy', 'Insurance Pharmacy Urgent']:
                ticket.insurance_company_id = ticket.insurance_company_id or False
                ticket.insurance_policy = ticket.insurance_policy or False

    # -----------------------------
    @api.constrains('ticket_type_id', 'insurance_company_id', 'insurance_policy')
    def _check_insurance_fields(self):
        for ticket in self:
            if ticket.ticket_type_id.name in ['Insurance Pharmacy', 'Insurance Pharmacy Urgent']:
                if not ticket.insurance_company_id or not ticket.insurance_policy:
                    raise ValidationError(
                        "Insurance Company and Insurance Policy are required for this type of ticket."
                    )


    # @api.constrains('ticket_type_id', 'branch_id')
    # def _validate_branch_for_inquiry_types(self):
    #     """Validate that branch is required for Inquiry and Urgent Inquiry ticket types"""
    #     for record in self:
    #         if (record.ticket_type_id and
    #                 record.ticket_type_id.name in ['Inquiry', 'Urgent Inquiry'] and
    #                 not record.branch_id):
    #             raise ValidationError('Branch is not defined')

    @api.model
    def create(self, vals):
        if 'user_id' in vals.keys():
            del vals['user_id']
        if self.env.user.has_group('helpdesk.group_helpdesk_user'):
            self = self.sudo()
        vals['case_no'] = str(random.randint(100000, 999999))
        vals['last_team_updated_on'] = datetime.datetime.now()

        ticket_type_id = vals.get('ticket_type_id')
        if isinstance(ticket_type_id, str):
            vals['ticket_type_id'] = self.env.ref(f'ramcrm.{ticket_type_id}').id

        case_source_id = vals.get('case_source_id')
        if isinstance(case_source_id, str):
            vals['case_source_id'] = self.env.ref(f'ramcrm.{case_source_id}').id

        vals['team_id'] = self.env['clinizone.ticket_team_assignment_rule'].compute_team(vals.get('ticket_type_id'), vals.get('branch_id'), vals.get('case_source_id'))

        case = super(RamCase, self).create(vals)

        case.sudo()._notify_team_members()

        return case

    def write(self, vals):
        if 'active' in vals.keys():
            if not self.env.user.has_group('ramcrm.group_helpdesk_archive_tickets'):
                raise UserError('You do not have permission to archive or unarchive tickets')

        if 'ticket_type_id' in vals.keys():
            if not self.env.user.has_group('ramcrm.group_helpdesk_change_type'):
                raise UserError('You do not have permission to change ticket type')

        if 'team_id' in vals.keys():
            vals['last_team_updated_on'] = datetime.datetime.now()

        if 'description' in vals.keys():
            original_converted_to_text = tools.html2plaintext(self.description)
            new_converted_to_text = tools.html2plaintext(vals['description'])
            if original_converted_to_text != new_converted_to_text:
                self.message_post(body_is_html=True, body=f"Description: {original_converted_to_text} --> {new_converted_to_text}")

        set_customer_care_center = False
        if 'stage_id' in vals.keys() and vals['stage_id'] == self.env.ref('helpdesk.stage_solved').id:
            set_customer_care_center = True

        t = super(RamCase, self).write(vals)

        if set_customer_care_center:
            new_team_id = self.env['helpdesk.team'].search([], limit=1, order='sequence').id
            self.with_context(system_change=True).write({'team_id': new_team_id})

        t = super(RamCase, self).write(vals)

        if 'ticket_type_id' in vals.keys() or 'branch_id' in vals.keys():
            if self.ticket_type_id.id == self.env.ref('ramcrm.MEDICAL_COMPLAINT').id:
                if self.branch_id:
                    if not self.branch_id.medical_director_team_id:
                        raise ValidationError('This branch does not have a medical director team')
                    self.team_id = self.branch_id.medical_director_team_id.id
                else:
                    raise ValidationError('Branch must be defined for medical complaints')
            else:
                if self.branch_id:
                    if not self.branch_id.helpdesk_team_id:
                        raise ValidationError('This branch does not have a helpdesk team')
                    self.team_id = self.branch_id.helpdesk_team_id.id
                else:
                    self.team_id = self.env['helpdesk.team'].sudo().search([], limit=1, order='sequence').id

        if set_customer_care_center:
            self.team_id = self.env['helpdesk.team'].search([], limit=1, order='sequence').id

        if self.user_id and self.team_id and self.user_id not in self.team_id.member_ids:
            self.user_id = False
        return t

    # @api.constrains('stage_id')
    # def stage_constraint(self):
    #     if self.stage_id.is_close and not html2plaintext(self.description):
    #         raise ValidationError('Description is required for closed tickets')

    def _compute_city_final(self):
        for r in self:
            if r.branch_id and r.branch_id.city_id:
                r.city_final = r.branch_id.city_id.name
            else:
                r.city_final = r.city

    def action_escalate(self):
        for r in self:
            if r.stage_id.is_close:
                continue
            if self.env.user.id not in r.team_id.member_ids.ids:
                raise UserError(f'You are not a member of team: {r.team_id.name}')
            if r.team_id.escalate_team_id:
                r.sudo().user_id = False
                r.sudo().team_id = r.team_id.escalate_team_id.id
            r.sudo()._notify_team_members()

    def _escalate(self):
        now = datetime.datetime.now()
        weekday = now.weekday()
        hour = now.hour

        if weekday == 4:
            return

        if weekday == 5 and hour < 8:
            return

        tickets_to_escalate = self.search([
            ('stage_id.is_close', '=', False),
            ('team_id.escalate_after_minutes', '!=', False),
            ('team_id.escalate_team_id', '!=', False),
            ('last_team_updated_on', '<', now - datetime.timedelta(minutes=1)),
        ])

        for r in tickets_to_escalate:
            time_limit = now - datetime.timedelta(minutes=r.team_id.escalate_after_minutes)
            if r.last_team_updated_on < time_limit:
                r.sudo().user_id = False
                r.sudo().team_id = r.team_id.escalate_team_id.id
                r.sudo()._notify_team_members()

    def _notify_team_members(self):
        for u in self.team_id.member_ids:
            self.env['mail.activity'].create({
                'display_name': 'New Ticket',
                'summary': 'New Ticket',
                'date_deadline': datetime.datetime.now(),
                'user_id': u.id,
                'res_model_id': self.env.ref('helpdesk.model_helpdesk_ticket').id,
                'res_id': self.id,
            })

    def action_convert_to_lead(self):
        for record in self:
            if record.lead_id:
                continue

            if record.branch_id.city_id:
                city = record.branch_id.city_id.name
            else:
                city = '???'

            x = self.env['crm.lead'].sudo().create({
                'name': record.partner_name,
                'phone': record.partner_phone,
                'city': city,
                'branch_id': record.branch_id.id,
                'email_from': record.partner_email,
                'patient_id': record.patient_national_id,
                'company_id': record.company_id.id,
                'description': f"Helpdesk Ticket No: {record.case_no}\n" + record.description,
                'lead_source_id': self.env.ref('ramcrm.LEAD_SOURCE_HELPDESK').id,
                'source_id': self.env.ref('ramcrm.UTM_SOURCE_HELPDESK').id,
                "lead_source": "Helpdesk",
                'treating_doctor': record.treating_physician_name,
            })
            record.lead_id = x.id

    def _send_sms(self):
        company = self.env.company
        if not company.infinito_from or not company.infinito_client_id or not company.infinito_client_password:
            _logger.error('Infinito credentials are not set')
            return
        if not self.partner_phone:
            _logger.error('Phone is not set')
            return
        if not self.stage_id.sms_template_id:
            _logger.warning('SMS Template is not set')
            return
        sms_body = self.stage_id.sms_template_id._render_field('body', [self.id], compute_lang=True)[self.id]
        payload = {
            "apiver": "1.0",
            "sms": {
                "ver": "2.0",
                "dlr": {
                    "url": ""
                },
                "messages": [
                    {
                        "udh": "0",
                        "text": sms_body,
                        "property": 0,
                        "id": "1",
                        "addresses": [
                            {
                                "from": company.infinito_from,
                                "to": self.partner_phone,
                                "seq": "1"
                            }
                        ]
                    }
                ]
            }
        }
        headers = {
                'Content-Type': 'application/json',
                'x-client-id': company.infinito_client_id,
                'x-client-password': company.infinito_client_password,
        }

        _logger.debug('Infinito Headers: {}'.format(headers))
        _logger.debug('Infinito Payload: {}'.format(payload))

        try:
            _logger.info('Calling Infinito API...')
            result = requests.post('https://api.goinfinito.me/unified/v2/send', json=payload, headers=headers)
            if result.status_code == 200:
                json = result.json()
                _logger.info('Infinito API Result: {}'.format(json))
                if json['status'] != 'Success' or json['statuscode'] != 200 or json['statustext'] != 'OK':
                    _logger.error('Infinito API Result: Status: {}, Status Code: {}, Status Text: {}'.format(json['status'], json['statuscode'], json['statustext']))
            else:
                _logger.error('Failed to call Infinito API: Status Code: {}'.format(result.status_code))
        except Exception as e:
            _logger.error('Failed to call Infinito API: {}'.format(str(e)))



class InsuranceCompany(models.Model):
    _name = 'insurance.company'
    _description = 'Insurance Company'

    name = fields.Char(string='Company Name', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
