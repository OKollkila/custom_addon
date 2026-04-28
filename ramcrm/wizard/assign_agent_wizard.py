from odoo import models, fields
from odoo.exceptions import ValidationError


class AssignAgentWizard(models.TransientModel):
    _name = 'ramcrm.assign_agent_wizard'
    _description = "Assign Agent Wizard"

    agent_id = fields.Many2one('res.users', string='Agent')
    activity_type_id = fields.Many2one('mail.activity.type', string='Activity Type', default=lambda self: self.env.ref('mail.mail_activity_data_call').id)
    date_deadline = fields.Date('Date Deadline', default=fields.Date.today)

    def action_do(self):
        for record in self:
            selected_ids = self.env.context.get('active_ids', [])
            selected_records = self.env['crm.lead'].browse(selected_ids)
            for lead in selected_records:
                # if lead.user_id:
                #     raise ValidationError("Agent already assigned for Lead %s (ID %s)" % (lead.name, lead.id))
                lead = lead.with_context(mail_auto_subscribe_no_notify=True)
                lead.user_id = record.agent_id.id
                # lead.activity_ids = [(0, 0, {
                #     'activity_type_id': record.activity_type_id.id,
                #     'res_id': lead.id,
                #     'res_model_id': self.env.ref('crm.model_crm_lead').id,
                #     'summary': 'Call',
                #     'date_deadline': record.date_deadline,
                #     'user_id': record.agent_id.id,
                # })]