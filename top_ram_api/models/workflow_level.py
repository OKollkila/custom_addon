# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WorkflowLevel(models.Model):
    _name = 'workflow.level'
    _description = 'Workflow Level'
    _order = 'sequence, code'

    code = fields.Char(string='ID', required=True, size=32, help='Unique code for API (e.g. 1, 2, 3, 4)')
    name = fields.Char(string='Name', required=True, help='Display name (e.g. Level 1, Level 2)')
    sequence = fields.Integer(string='Sequence', default=10, help='Order for levels (used to determine next level)')
    escalation_hours = fields.Integer(
        string='Escalation (hours)',
        default=0,
        help='If a ticket stays at this level without update for this many hours, the action below is run. 0 = disabled.'
    )
    escalation_action = fields.Selection(
        [
            ('upgrade_only', 'Upgrade to next level only'),
            ('email_only', 'Send email only'),
            ('upgrade_and_email', 'Upgrade to next level and send email'),
        ],
        string='After escalation',
        default='upgrade_only',
        help='What to do when escalation time is reached.'
    )
    escalation_email_user_id = fields.Many2one(
        'res.users',
        string='Send email to',
        help='User to notify by email when escalation time is reached (for email actions).'
    )

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'The code must be unique.'),
    ]

    @api.constrains('code')
    def _check_code(self):
        for level in self:
            if level.code and not level.code.strip():
                raise ValidationError(_('Code cannot be empty.'))

    @api.constrains('escalation_action', 'escalation_email_user_id')
    def _check_escalation_email_user(self):
        for level in self:
            if level.escalation_action in ('email_only', 'upgrade_and_email') and not level.escalation_email_user_id:
                raise ValidationError(_('Please set "Send email to" when action is "Send email only" or "Upgrade and send email".'))

    def name_get(self):
        return [(r.id, f"[{r.code}] {r.name}") for r in self]

    def _calculate_actual_work_hours(self, start_date, end_date):
        """
        تحسب الساعات الفعلية المنقضية مع تجميد العداد في:
        الجمعة (كاملة) والسبت (حتى 10 صباحاً)
        """
        if not start_date or not end_date:
            return 0

        actual_hours = 0
        check_date = start_date

        while check_date < end_date:
            # تعريف فترة التوقف:
            # Friday (weekday 4)
            # Saturday (weekday 5) before 10 AM
            is_weekend = (check_date.weekday() == 4) or \
                         (check_date.weekday() == 5 and check_date.hour < 10)

            if not is_weekend:
                actual_hours += 1

            # الانتقال للساعة التالية
            check_date += datetime.timedelta(hours=1)

        return actual_hours

    def _check_and_escalate_tickets(self):
        now = datetime.datetime.now()

        # 1. إذا كان الوقت الحالي إجازة، لا داعي لتشغيل الفانكشن أصلاً
        if (now.weekday() == 4) or (now.weekday() == 5 and now.hour < 10):
            return

        # 2. البحث عن التذاكر المفتوحة التي لها نظام تصعيد
        tickets = self.env['ticket.model'].search([
            ('is_closed', '=', False),
            ('workflow_level_id.escalation_hours', '>', 0)
        ])

        for ticket in tickets:
            # حساب الساعات التي مرت فعلياً (بدون ساعات الإجازة)
            passed_work_hours = self._calculate_actual_work_hours(ticket.create_date, now)

            limit_hours = ticket.workflow_level_id.escalation_hours

            if passed_work_hours >= limit_hours:
                # تنفيذ التصعيد
                self._perform_escalation(ticket)
