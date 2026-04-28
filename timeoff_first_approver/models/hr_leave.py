from odoo import models, _
from odoo.exceptions import UserError


class HrLeave(models.Model):
    _inherit = "hr.leave"

    def action_approve(self):
        if self.env.user.has_group("timeoff_first_approver.group_timeoff_first_approver"):
            for leave in self:
                if leave.holiday_status_id and leave.holiday_status_id.name == "Sick Time Off":
                    raise UserError(_("You are not allowed to approve Sick Leave requests."))
                if leave.state in ['confirm', 'validate1']:
                    leave.action_validate()
            return True

        return super().action_approve()