import logging

from odoo import models, fields, api
from odoo.api import depends
from odoo.exceptions import UserError

_logger = logging.getLogger()

class Lead(models.Model):
    _name = 'crm.lead'
    _description = 'crm.lead'
    _inherit = ['crm.lead', 'mail.thread']

    company_id = fields.Many2one('res.company', string='Company', index=True, compute=False, readonly=False, store=True, required=True, default=lambda self: self.env.company)
    campaign_id = fields.Many2one('utm.campaign', string='Campaign', tracking=True, readonly=True)
    ad_set = fields.Char("Ad Set", tracking=True)
    doctor_reservation_no = fields.Char("Doctor Reservation No", tracking=True)
    installment_company = fields.Char("Installment Company", tracking=True)
    name = fields.Char("Name", tracking=True)
    topic = fields.Char("Topic", tracking=True)
    treating_doctor = fields.Char("Treating Doctor", tracking=True)
    city = fields.Char("City", compute='_compute_city', store=True)
    city_id = fields.Many2one(related='branch_id.city_id', string='City', store=False, readonly=True)
    bu = fields.Char("BU", tracking=True, readonly=True)
    speciality = fields.Char("Speciality", tracking=True)
    department_id = fields.Many2one('clinizone.department', string='Department', tracking=True)
    service_id = fields.Many2one('clinizone.service', string='Service', tracking=True)
    campaign = fields.Char("Campaign", tracking=True)
    campaign_activity = fields.Char("Campaign Activity", tracking=True)
    notes = fields.Char("Notes", tracking=True)
    lead_source = fields.Char("Lead Source", tracking=True, compute='_compute_lead_source', store=True, readonly=False, help='Textual Lead Source. It must not be entered manually')
    lead_source_id = fields.Many2one('clinizone.lead_source', "Lead Source (Canonical)", tracking=True, help='Lead source from the list of available sources')
    lead_source_level_1_id = fields.Many2one(related='lead_source_id.level_1_id', string='Lead Source Level 1', store=False, readonly=True)
    lead_source_level_2_id = fields.Many2one(related='lead_source_id.level_2_id', string='Lead Source Level 2', store=False, readonly=True)
    ads = fields.Char("Ads", tracking=True)
    nid = fields.Char("National ID", tracking=True)
    preferred_time = fields.Char("Preferred Time", tracking=True)
    patient_id = fields.Char("Patient ID", tracking=True)
    timestamp = fields.Datetime("Timestamp", tracking=True)
    created_date = fields.Date("Created Date", tracking=True)
    installment = fields.Char("Installment", tracking=True)
    branch_id = fields.Many2one('clinizone.branch', string='Branch', tracking=True, compute='_compute_branch_id', store=True, readonly=False)
    stage2 = fields.Selection([('untouched', 'Untouched'), ('touched', 'Touched'), ('booked', 'Booked'), ('lost', 'Lost')], compute='_compute_stage2', string='Stage2', store=True)
    stage3 = fields.Selection([('untouched', 'Untouched'), ('reached', 'Reached'), ('unreached', 'Unreached'), ('booked', 'Booked')], compute='_compute_stage3', string='Stage3', store=True)
    business_category_id = fields.Many2one('clinizone.business_category', string='Business Category', readonly=True, store=True)
    related_lead_ids = fields.One2many('crm.lead', 'id', compute='_compute_related_leads', string='Related Leads', context={'active_test': False})
    is_phone_blacklisted = fields.Boolean(compute='_compute_is_phone_blacklisted', string='Is Blacklisted')
    stage4_id = fields.Many2one('cz.lead.stage4', string='Stage4')
    status_id = fields.Many2one('cz.lead.status', string='Status')
    stage_count =  fields.Integer(string="Stage count", default=0)

    # def create(self, vals_list):
    #     if 'lead_source' in vals_list and not vals_list['lead_source'] and 'lead_source_id' in vals_list and vals_list['lead_source_id']:
    #         del vals_list['lead_source']
    #     return super(Lead, self).create(vals_list)

    def _write(self, vals):
        if 'lost_reason_id' in vals and 'active' in vals and not vals['active']:
            vals = vals.copy()
            vals['stage_id'] = self.env.ref('ramcrm.lost').id
            vals['stage2'] = 'lost'
        elif 'active' in vals and vals['active']:
            vals = vals.copy()
            vals['stage_id'] = self.env['crm.stage'].search([], limit=1, order='sequence').id
            vals['stage2'] = 'untouched'
        elif 'stage_id' in vals and vals['stage_id'] == self.env.ref('ramcrm.lost').id and 'lost_reason_id' not in vals:
            raise UserError('Lost Reason is required')
        return super(Lead, self)._write(dict(vals))

    @api.constrains('name')
    def _validate_name(self):
        if self.env.context.get('skip_constrains', False):
            return
        for r in self:
            if not r.name or len(r.name) < 1:
                raise UserError('Name must be at least 1 characters long')

    @api.constrains('phone')
    def _validate_phone(self):
        if self.env.context.get('skip_constrains', False):
            return
        for r in self:
            if not r.phone or len(r.phone) < 8:
                raise UserError('Phone must be at least 8 characters long')

    @api.constrains('topic')
    def _validate_topic(self):
        if self.env.context.get('skip_constrains', False):
            return
        for r in self:
            if not r.topic or len(r.topic) < 2:
                raise UserError('Topic must be at least 2 characters long')

    # @api.constrains('city')
    # def _validate_city(self):
    #     if self.env.context.get('skip_constrains', False):
    #         return
    #     for r in self:
    #         if not r.city or len(r.city) < 3:
    #             raise UserError('City must be at least 3 characters long')

    # @api.constrains('lead_source')
    # def _validate_lead_source(self):
    #     if self.env.context.get('skip_constrains', False):
    #         return
    #     for r in self:
    #         if not r.lead_source or len(r.lead_source) < 2:
    #             raise UserError('Lead Source must be at least 2 characters long')

    @api.constrains('campaign')
    def _validate_campaign(self):
        if self.env.context.get('skip_constrains', False):
            return
        for r in self:
            if not r.campaign or len(r.campaign) < 3:
                raise UserError('Campaign must be at least 3 characters long')


    @api.constrains('stage_id', 'patient_id')
    def _validate_patient_id(self):
        for r in self:
            if r.stage_id.is_won and (not r.patient_id or len(r.patient_id) < 1 or not r.patient_id[0].isalpha()):
                raise UserError('Patient ID must start with a letter if the lead is won')

    # @api.constrains('stage_id', 'branch_id')
    # def _validate_branch_id(self):
    #     for r in self:
    #         if r.stage_id and r.stage_id.is_won and not r.branch_id:
    #             raise UserError('Branch must be defined if the lead is won')

    def _compute_branch_id(self):
        for r in self:
            m = self.env['clinizone.branch'].search([('code', '=', r.bu)], limit=1)
            r.branch_id = m.id if m else False

    @depends('stage_id')
    def _compute_stage2(self):
        for r in self:
            r.stage2 = r.stage_id.stage2

    @depends('stage_id')
    def _compute_stage3(self):
        for r in self:
            r.stage3 = r.stage_id.stage3

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'mobile_number': self.phone,
            'email': self.email_from,
            'topic': self.topic,
            'treating_doctor': self.treating_doctor,
            'city': self.city,
            'bu': self.bu,
            'speciality': self.speciality,
            'campaign': self.campaign,
            'campaign_activity': self.campaign_activity,
            'notes': self.notes,
            'lead_source': self.lead_source,
            'ads': self.ads,
            'ad_set': self.ad_set,
            'patient_id': self.patient_id,
            'timestamp': self.timestamp,
            'created_date': self.created_date,
            'installment': self.installment,
        }

    def register_call(self, call_result, stage_id_id):
        if not self.env.user.has_group('base.group_portal') and not self.env.user.has_group('base.group_user'):
            return False, 'Only Internal Users or Portal Users can perform this action'
        if self.stage_id.stage2 == 'lost':
            return False, 'Cannot perform this action on a lost lead'
        call_activity_type = self.env.ref('mail.mail_activity_data_call').id
        self.sudo().activity_ids = [(0, 0, {
            'activity_type_id': call_activity_type,
            'res_id': self.id,
            'res_model_id': self.env.ref('crm.model_crm_lead').id,
            'summary': 'Call',
            'call_result': call_result,
        })]

        stage_id = self.env['crm.stage'].browse(stage_id_id)
        if stage_id.is_won and not self.branch_id:
            return False, 'Branch must be defined if the lead is won'

        if self.stage_id.id == stage_id_id:
            self._message_log(body='Another call with the same result')

        self.stage_id = stage_id_id
        return True, ''

    def action_booked(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('booked', 17)
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_satisfied(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('satisfied', self.env.ref('ramcrm.stage_satisfied').id)
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_no_answer(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('no_answer', 13)
            if ok:
                r.stage_count += 1
            else:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_call_again(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('call_again', 14)
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_inquiry(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('inquiry', self.env.ref('ramcrm.stage_inquiry').id)
            # r.lost_reason_id = 10
            # r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_out_of_service(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('out_of_service', 15)
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_switched_off(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('switched_off', 16)
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_busy(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('busy', self.env.ref('ramcrm.stage_busy').id)
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_waiting_list(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('waiting_list', self.env.ref('ramcrm.stage_waiting_list').id)
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_already_booked(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('already_booked', 21)
            r.lost_reason_id = 11
            r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_not_interested(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('not_interested', 21)
            r.lost_reason_id = 12
            r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_wrong_number(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('wrong_number', 21)
            r.lost_reason_id = 13
            r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_duplicated(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('duplicated', 21)
            r.lost_reason_id = 14
            r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_visited(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('visited', 21)
            r.lost_reason_id = 15
            r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_hang_up_the_phone(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('hang_up_the_phone', 21)
            r.lost_reason_id = self.env.ref('ramcrm.lost_reason_hang_up_the_phone').id
            r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_complaint(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('complaint', 21)
            r.lost_reason_id = self.env.ref('ramcrm.lost_reason_complaint').id
            r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_transferred_to_another_branch(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('transferred_to_another_branch', 21)
            r.lost_reason_id = self.env.ref('ramcrm.lost_reason_transferred_to_another_branch').id
            r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_will_call_back(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('will_call_back', 21)
            r.lost_reason_id = self.env.ref('ramcrm.lost_reason_will_call_back').id
            r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_price_issue(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('price_issue', 21)
            r.lost_reason_id = self.env.ref('ramcrm.lost_reason_price_issue').id
            r.action_set_lost()
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def action_rescheduled(self):
        ok, msg = True, ''
        for r in self:
            ok, msg = r.register_call('rescheduled', 18)
            if not ok:
                break
        return {
            'success': ok,
            'message': msg,
        }

    def _compute_related_leads(self):
        for r in self:
            r.related_lead_ids = self.env['crm.lead'].search([
                '|',
                '&', ('phone', '!=', ''), ('phone', '=', r.phone),
                '&', ('email_from', '!=', ''), ('email_from', '=', r.email_from),
                ('id', '!=', r.id),
                ('active', 'in', [True, False])
            ])

    @api.depends('phone')
    def _compute_is_phone_blacklisted(self):
        for r in self:
            if r.phone:
                r.is_phone_blacklisted = self.env['clinizone.blacklist'].search_count([('phone', '=', r.phone)]) > 0
            else:
                r.is_phone_blacklisted = False

    @api.depends('lead_source_id')
    def _compute_lead_source(self):
        for r in self:
            r.lead_source = r.lead_source_id.name if r.lead_source_id else ''

    @api.depends('branch_id', 'branch_id.city_id')
    def _compute_city(self):
        for r in self:
            r.city = r.branch_id.city_id.name if r.branch_id and r.branch_id.city_id else '???'

    def action_set_stage4_and_status(self):
        STAGE_UNTOUCHED = self.env['crm.stage'].search([('name', '=', 'Untouched')]).id
        STAGE_NEW = self.env['crm.stage'].search([('name', '=', 'New')]).id
        STAGE_BOOKED = self.env['crm.stage'].search([('name', '=', 'Booked')]).id
        STAGE_NO_ANSWER = self.env['crm.stage'].search([('name', '=', 'No Answer')]).id
        STAGE_CALL_AGAIN = self.env['crm.stage'].search([('name', '=', 'Call Again')]).id
        STAGE_OUT_OF_SERVICE = self.env['crm.stage'].search([('name', '=', 'Out of Service')]).id
        STAGE_SWITCHED_OFF = self.env['crm.stage'].search([('name', '=', 'Switched Off')]).id
        STAGE_RESCHEDULED = self.env['crm.stage'].search([('name', '=', 'Rescheduled')]).id
        STAGE_BUSY = self.env['crm.stage'].search([('name', '=', 'Busy')]).id
        STAGE_INQUIRY = self.env['crm.stage'].search([('name', '=', 'Inquiry')]).id
        STAGE_WAITING_LIST = self.env['crm.stage'].search([('name', '=', 'Waiting List')]).id
        STAGE_SATISFIED = self.env['crm.stage'].search([('name', '=', 'Satisfied')]).id
        STAGE_LOST = self.env['crm.stage'].search([('name', '=', 'Lost')]).id

        LOST_REASON_ALREADY_BOOKED = self.env['crm.lost.reason'].search([('name', '=', 'Already Booked')]).id
        LOST_REASON_NOT_INTERESTED = self.env['crm.lost.reason'].search([('name', '=', 'Not Interested')]).id
        LOST_REASON_WRONG_NUMBER = self.env['crm.lost.reason'].search([('name', '=', 'Wrong Number')]).id
        LOST_REASON_DUPLICATED = self.env['crm.lost.reason'].search([('name', '=', 'Duplicated')]).id
        LOST_REASON_VISITED = self.env['crm.lost.reason'].search([('name', '=', 'Visited')]).id
        LOST_REASON_HANG_UP_THE_PHONE = self.env['crm.lost.reason'].search([('name', '=', 'Hang up the phone')]).id
        LOST_REASON_COMPLAINT = self.env['crm.lost.reason'].search([('name', '=', 'Complaint')]).id
        LOST_REASON_WILL_CALL_BACK = self.env['crm.lost.reason'].search([('name', '=', 'Will call back')]).id
        LOST_REASON_PRICE_ISSUE = self.env['crm.lost.reason'].search([('name', '=', 'Price issue')]).id

        if not all(
            [STAGE_UNTOUCHED, STAGE_NEW, STAGE_BOOKED, STAGE_NO_ANSWER, STAGE_CALL_AGAIN, STAGE_OUT_OF_SERVICE, STAGE_SWITCHED_OFF, STAGE_RESCHEDULED,
             STAGE_BUSY, STAGE_INQUIRY, STAGE_WAITING_LIST, STAGE_SATISFIED, STAGE_LOST,
             LOST_REASON_ALREADY_BOOKED, LOST_REASON_NOT_INTERESTED, LOST_REASON_WRONG_NUMBER, LOST_REASON_DUPLICATED, LOST_REASON_VISITED,
             LOST_REASON_HANG_UP_THE_PHONE, LOST_REASON_COMPLAINT, LOST_REASON_WILL_CALL_BACK, LOST_REASON_PRICE_ISSUE]
        ):
            _logger.warning(f'''One or more stages or lost reasons are missing:
            STAGE_UNTOUCHED: {STAGE_UNTOUCHED}
            STAGE_NEW: {STAGE_NEW}
            STAGE_BOOKED: {STAGE_BOOKED}
            STAGE_NO_ANSWER: {STAGE_NO_ANSWER}
            STAGE_CALL_AGAIN: {STAGE_CALL_AGAIN}
            STAGE_OUT_OF_SERVICE: {STAGE_OUT_OF_SERVICE}
            STAGE_SWITCHED_OFF: {STAGE_SWITCHED_OFF}
            STAGE_RESCHEDULED: {STAGE_RESCHEDULED}
            STAGE_BUSY: {STAGE_BUSY}
            STAGE_INQUIRY: {STAGE_INQUIRY}
            STAGE_WAITING_LIST: {STAGE_WAITING_LIST}
            STAGE_SATISFIED: {STAGE_SATISFIED}
            STAGE_LOST: {STAGE_LOST}
            LOST_REASON_ALREADY_BOOKED: {LOST_REASON_ALREADY_BOOKED}
            LOST_REASON_NOT_INTERESTED: {LOST_REASON_NOT_INTERESTED}
            LOST_REASON_WRONG_NUMBER: {LOST_REASON_WRONG_NUMBER}
            LOST_REASON_DUPLICATED: {LOST_REASON_DUPLICATED}
            LOST_REASON_VISITED: {LOST_REASON_VISITED}
            LOST_REASON_HANG_UP_THE_PHONE: {LOST_REASON_HANG_UP_THE_PHONE}
            LOST_REASON_COMPLAINT: {LOST_REASON_COMPLAINT}
            LOST_REASON_WILL_CALL_BACK: {LOST_REASON_WILL_CALL_BACK}
            LOST_REASON_PRICE_ISSUE: {LOST_REASON_PRICE_ISSUE}
            ''')

        for r in self:
            if r.active and r.stage_id.id in [STAGE_UNTOUCHED, STAGE_NEW]:
                r.stage4_id = self.env.ref('ramcrm.stage4_untouched').id
            elif (r.active and r.stage_id.id in [STAGE_NO_ANSWER, STAGE_OUT_OF_SERVICE, STAGE_SWITCHED_OFF, STAGE_BUSY])\
                    or ((not r.active or r.stage_id.id == STAGE_LOST) and r.lost_reason_id.id in [LOST_REASON_ALREADY_BOOKED, LOST_REASON_WRONG_NUMBER, LOST_REASON_DUPLICATED, LOST_REASON_VISITED, LOST_REASON_HANG_UP_THE_PHONE, LOST_REASON_COMPLAINT, LOST_REASON_WILL_CALL_BACK]):
                r.stage4_id = self.env.ref('ramcrm.stage4_unreached').id
            elif (r.active and r.stage_id.id in [STAGE_BOOKED, STAGE_CALL_AGAIN,STAGE_RESCHEDULED, STAGE_INQUIRY, STAGE_WAITING_LIST, STAGE_SATISFIED])\
                    or ((not r.active or r.stage_id.id == STAGE_LOST) and r.lost_reason_id.id in [LOST_REASON_PRICE_ISSUE])\
                    or (not r.active and r.lost_reason_id and r.lost_reason_id.id == LOST_REASON_NOT_INTERESTED):
                r.stage4_id = self.env.ref('ramcrm.stage4_reached').id
            else:
                _logger.warning(f'Cannot set stage4 for this lead. Stage: {r.stage_id.name}, Active: {r.active} Lost Reason: {r.lost_reason_id.name}')

        for r in self:
            if r.active and r.stage_id.id in [STAGE_UNTOUCHED, STAGE_NEW]:
                r.status_id = self.env.ref('ramcrm.status_untouched').id
            elif r.active and r.stage_id.id == STAGE_BOOKED:
                r.status_id = self.env.ref('ramcrm.status_booked').id
            elif r.active and r.stage_id.id == STAGE_NO_ANSWER:
                r.status_id = self.env.ref('ramcrm.status_no_answer').id
            elif r.active and r.stage_id.id == STAGE_CALL_AGAIN:
                r.status_id = self.env.ref('ramcrm.status_call_again').id
            elif r.active and r.stage_id.id == STAGE_OUT_OF_SERVICE:
                r.status_id = self.env.ref('ramcrm.status_out_of_service').id
            elif r.active and r.stage_id.id == STAGE_SWITCHED_OFF:
                r.status_id = self.env.ref('ramcrm.status_switched_off').id
            elif r.active and r.stage_id.id == STAGE_RESCHEDULED:
                r.status_id = self.env.ref('ramcrm.status_rescheduled').id
            elif r.active and r.stage_id.id == STAGE_BUSY:
                r.status_id = self.env.ref('ramcrm.status_busy').id
            elif r.active and r.stage_id.id == STAGE_INQUIRY:
                r.status_id = self.env.ref('ramcrm.status_inquiry').id
            elif r.active and r.stage_id.id == STAGE_WAITING_LIST:
                r.status_id = self.env.ref('ramcrm.status_waiting_list').id
            elif r.active and r.stage_id.id == STAGE_SATISFIED:
                r.status_id = self.env.ref('ramcrm.status_satisfied').id
            elif not r.active or r.stage_id.id == STAGE_LOST:
                if r.lost_reason_id.id == LOST_REASON_ALREADY_BOOKED:
                    r.status_id = self.env.ref('ramcrm.status_lost_already_booked').id
                elif r.lost_reason_id.id == LOST_REASON_NOT_INTERESTED:
                    r.status_id = self.env.ref('ramcrm.status_lost_not_interested').id
                elif r.lost_reason_id.id == LOST_REASON_WRONG_NUMBER:
                    r.status_id = self.env.ref('ramcrm.status_lost_wrong_number').id
                elif r.lost_reason_id.id == LOST_REASON_DUPLICATED:
                    r.status_id = self.env.ref('ramcrm.status_lost_duplicated').id
                elif r.lost_reason_id.id == LOST_REASON_VISITED:
                    r.status_id = self.env.ref('ramcrm.status_lost_visited').id
                elif r.lost_reason_id.id == LOST_REASON_HANG_UP_THE_PHONE:
                    r.status_id = self.env.ref('ramcrm.status_lost_hang_up_the_phone').id
                elif r.lost_reason_id.id == LOST_REASON_COMPLAINT:
                    r.status_id = self.env.ref('ramcrm.status_lost_complaint').id
                elif r.lost_reason_id.id == LOST_REASON_WILL_CALL_BACK:
                    r.status_id = self.env.ref('ramcrm.status_lost_will_call_back').id
                elif r.lost_reason_id.id == LOST_REASON_PRICE_ISSUE:
                    r.status_id = self.env.ref('ramcrm.status_lost_price_issue').id
                else:
                    _logger.warning(f'Cannot set status for this lead. Stage: {r.stage_id.name}, Active: {r.active} Lost Reason: {r.lost_reason_id.name}')
            else:
                _logger.warning(f'Cannot set status for this lead. Stage: {r.stage_id.name}, Active: {r.active} Lost Reason: {r.lost_reason_id.name}')
