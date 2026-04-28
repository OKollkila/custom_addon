import datetime

from odoo import models, fields, api


class StatsReportWizard(models.TransientModel):
    _name = 'ramcrm.stats_report_wizard'
    _description = "Stats Report Wizard"

    from_date = fields.Date(string='Report Start Date', required=True, default=lambda self: fields.Date.today() - datetime.timedelta(days=1))
    to_date = fields.Date(string='Report End Date', required=True, default=lambda self: fields.Date.today() - datetime.timedelta(days=1))

    def make_report(self):
        self.ensure_one()
        data = {
            'model_id': self.id,
            'from_date': self.from_date,
            'to_date': self.to_date,
        }
        return self.env.ref('ramcrm.action_stats_report_pdf').report_action(None, data=data)