from odoo import models, fields, api
from odoo.exceptions import AccessError
import logging
import datetime

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.model
    def _is_allowed_user(self):
        allowed = self.env.user.has_group(
            'top_access_helpdask.group_helpdesk_moderator'
        )
        _logger.info("User %s is moderator: %s", self.env.user.name, allowed)
        return allowed

    @api.model
    def _is_refund_user(self):
        allowed = self.env.user.has_group(
            'top_access_helpdask.group_helpdesk_refund'
        )
        _logger.info("User %s is refund user: %s", self.env.user.name, allowed)
        return allowed

    def write(self, vals):
        _logger.info("User %s trying to write: %s", self.env.user.name, vals)

        # 1️⃣ System / OdooBot bypass
        if self.env.context.get('bypass_write_restriction', False) or \
           self.env.context.get('system_change', False) or \
           self.env.user.login == 'odoo':
            _logger.info("Bypassing write restriction via context or OdooBot/system change")
            return super().write(vals)

        # 2️⃣ Moderator OR Refund → full access
        if self._is_allowed_user() or self._is_refund_user():
            _logger.info("Moderator or Refund user, full access granted")
            return super().write(vals)

        # 3️⃣ Allowed fields for normal users
        allowed_keys = {
            'stage_id',
            'closing_note',
            'activity_ids',
            'activity_state',
            'access_token',
        }

        if set(vals.keys()).issubset(allowed_keys):
            _logger.info("Only allowed fields being written: %s", vals)
            return super().write(vals)

        # 4️⃣ team_id special logic
        team_id_allowed = False
        if 'team_id' in vals:
            for rec in self:
                if rec.team_id.id == vals['team_id']:
                    _logger.info("team_id not changed, allowing")
                    team_id_allowed = True
                elif vals.get('stage_id') == self.env.ref(
                    'helpdesk.stage_solved'
                ).id:
                    _logger.info("team_id change allowed because stage changed to Solved")
                    team_id_allowed = True

        combined_keys = (
            allowed_keys.union({'team_id'})
            if team_id_allowed
            else allowed_keys
        )

        if set(vals.keys()).issubset(combined_keys):
            _logger.info("Allowed + system logic fields being written: %s", vals)
            return super().write(vals)

        # 5️⃣ Access denied
        _logger.warning("Access denied. Attempted fields: %s", vals.keys())
        raise AccessError(
            "You are only allowed to change the Stage or Closing Note."
        )

    def _escalate(self):
        now = datetime.datetime.now()

        is_weekend = (
                (now.weekday() == 3 and now.hour >= 22) or
                (now.weekday() == 4) or
                (now.weekday() == 5 and now.hour < 21)
        )

        if is_weekend:
            return

        tickets_to_escalate = self.search([
            ('stage_id.is_close', '=', False),
            ('team_id.escalate_after_minutes', '!=', False),
            ('team_id.escalate_team_id', '!=', False),
        ])

        for r in tickets_to_escalate:
            if not r.last_team_updated_on:
                continue

            total_minutes = (now - r.last_team_updated_on).total_seconds() / 60
            discount_minutes = 0
            check_date = r.last_team_updated_on

            while check_date < now:

                if (
                        (check_date.weekday() == 3 and check_date.hour >= 22) or
                        (check_date.weekday() == 4) or
                        (check_date.weekday() == 5 and check_date.hour < 21)
                ):
                    discount_minutes += 60

                check_date += datetime.timedelta(hours=1)

            actual_work_minutes = total_minutes - discount_minutes

            if actual_work_minutes >= r.team_id.escalate_after_minutes:
                new_team = r.team_id.escalate_team_id
                user = new_team.member_ids[:1]

                r.sudo().write({
                    'team_id': new_team.id,
                    'user_id': user.id if user else False
                })
                r.sudo()._notify_team_members()