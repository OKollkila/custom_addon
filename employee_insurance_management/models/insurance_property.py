# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import datetime


class EmployeeInsuranceProperty(models.Model):
    _name = "employee.insurance.property"
    _description = 'Insurance Property'

    name = fields.Char(
        string="Name",
        required=True,
        copy=False
    )

class EmployeeInsurancePropertyLine(models.Model):
    _name = "employee.insurance.property.line"
    _description = 'Employee Insurance Property Line'

    property_id = fields.Many2one(
        'employee.insurance.property',
        string="Employee Insurance Property",
        required=True
    )
    # insurance_id = fields.Many2one(
    #     'maintenance.equipment.insurance', 
    #     string='Insurance',
    #     copy=False 
    # )
    insurance_id = fields.Many2one(
        'employee.insurance', 
        string='Insurance',
        copy=False 
    )
    value = fields.Char(
        string="Value"
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
