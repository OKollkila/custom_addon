# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

AVAILABLE_PRIORITIES = [
    ('0', '0'),
    ('1', 'Very Low'),
    ('2', 'Low'),
    ('3', 'Average'),
    ('4', 'Good'),
    ('5', 'Very Good')
    ]

class EmployeeVoteIdea(models.TransientModel):
    _name = 'ideas.comment'
    _description = 'Ideas Comment'

    employee_id = fields.Many2one('hr.employee', string="Employee")
    department_id = fields.Many2one('hr.department', string="Department")
    comments = fields.Text(required=True, string="Comments")
    rating = fields.Selection(AVAILABLE_PRIORITIES, index=True)
    today_date = fields.date.today()
    
    #@api.multi
    def create_employee_review(self):
        active_id = self._context.get('active_id')
        ideas_id = self.env['hr.ideas'].browse(active_id)
        employee = self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
        if ideas_id.dead_line and ideas_id.dead_line < self.today_date:
            raise ValidationError("Idea is already ended so you can not give vote now.")
        for r in ideas_id.ideas_review_ids:
            if r.employee_id == employee:
                raise ValidationError("You have already voted for this idea.")
        count = len(ideas_id.ideas_review_ids)
        total_vote = count
        if ideas_id.idea_type_id.maximum_vote <= total_vote:
            raise ValidationError("This idea is already reached maximum limit for votes. So now you can not give vote.")
        self.employee_id = employee
        self.department_id = employee.department_id.id
        if not self.department_id in ideas_id.idea_type_id.department_ids:
            raise ValidationError("You are not allowed give vote this idea (Department mismatch).")
        vals = {
                    'employee_id' : self.employee_id.id,
                    'department_id' : self.department_id.id,
                    'comments': self.comments,
                    'rating': self.rating,
                    'ideas_review_id': self._context.get('active_id')
              }
        review_obj = self.env['employee.idea.review'].create(vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
