# -*- coding: utf-8 -*-

import odoo.addons.decimal_precision as dp

from datetime import datetime
from odoo import models, fields, api, _

class TravelAdvancePayment(models.Model):
    _name = 'travel.advance.payment'
    _description = 'Travel Advance Payment'
    
    # @api.multi
    @api.depends('unit_price','quantity')
    def _compute_total_line_expense(self):
        for rec in self:
            amount_line = rec.unit_price * rec.quantity
            rec.total_amount = amount_line
    
    product_id = fields.Many2one(
        'product.product',
        required=True,
        string='Expense',
    )
    description = fields.Char(
        'Description',
    )
    unit_price = fields.Float(
        string='Unit Price',
        required=True,
        #digits=dp.get_precision('Product Price'),
        digits='Product Price',
    )
    quantity = fields.Float(
        required=True,
        string='Quantity',
        #digits=dp.get_precision('Product Unit of Measure'),
        digits='Product Unit of Measure',
        default=1,
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        readonly=True,
        default=lambda self: self.env['uom.uom'].search([], limit=1, order='id')
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='travel_request_id.company_id.currency_id',
        readonly=True,
    )
    total_amount = fields.Float(
        string='Subtotal',
        compute=_compute_total_line_expense,
    )
    travel_request_id = fields.Many2one(
        'employee.travel.request',
    )
    company_id = fields.Many2one(related='travel_request_id.company_id', string='Company', store=True, readonly=True)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            rec.description = rec.product_id.name
            if rec.travel_request_id.company_id.currency_id != rec.travel_request_id.currency_id:
                amount = rec.travel_request_id.company_id.currency_id.compute(rec.product_id.standard_price, rec.travel_request_id.currency_id)
                rec.unit_price = amount
            else:
                rec.unit_price = rec.product_id.standard_price
