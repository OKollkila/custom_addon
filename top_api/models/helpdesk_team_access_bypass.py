# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import AccessError


class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    def check_access_rights(self, operation, raise_exception=True):
        """
        Allow read rights on helpdesk.team across companies.
        Keep write/create/unlink protected.
        """
        if operation == "read":
            return True
        return super().check_access_rights(operation, raise_exception=raise_exception)

    def check_access_rule(self, operation):
        """
        Programmatic bypass for read access to helpdesk.team across companies.
        Keep write/create/unlink protected by standard rules.
        """
        if operation == "read":
            return True
        return super().check_access_rule(operation)

    def read(self, fields=None, load="_classic_read"):
        """
        Some read paths can still trigger multi-company checks deep in stack.
        Fallback to sudo() for read-only access.
        """
        try:
            return super().read(fields=fields, load=load)
        except AccessError:
            return self.sudo().read(fields=fields, load=load)

    def name_get(self):
        """Ensure many2one label resolution does not fail on multi-company team rules."""
        try:
            return super().name_get()
        except AccessError:
            return self.sudo().name_get()

    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Allow searching team names across companies for read use cases."""
        try:
            return super().name_search(name=name, args=args, operator=operator, limit=limit)
        except AccessError:
            return self.sudo().name_search(name=name, args=args, operator=operator, limit=limit)

    def search(self, args, offset=0, limit=None, order=None):
        """Fallback for list/form paths that search teams before read."""
        try:
            return super().search(args, offset=offset, limit=limit, order=order)
        except AccessError:
            return self.sudo().search(args, offset=offset, limit=limit, order=order)

