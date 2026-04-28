# -*- coding: utf-8 -*-

import time
from datetime import datetime

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
# from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo.exceptions import RedirectWarning


class HrShift(models.Model):    

    _inherit = "hr.employee"
    

    # @api.multi
    def action_button_hr(self):
        self.ensure_one()
        action = self.env.ref("odoo_hr_employee_shift.request_shift_action_ot").read([])[0]
        action['domain'] = [('employee_id','=',self.id)]
        return action
