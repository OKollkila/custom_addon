# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.tools.float_utils import float_compare
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    it_operations_id = fields.Many2one('hr.it.operations', 'IT Operations')

class hr_it_operations_expenses(models.Model):

    _name = 'hr.it.operations.expenses'
    _description = 'Hr It Operations Expenses'
    
    product_id = fields.Many2one('product.product', string='Product', domain=[('can_be_expensed', '=', True)], required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', default=lambda self: self.env['uom.uom'].search([], limit=1, order='id'))
    # unit_amount = fields.Float(string='Unit Price', digits=dp.get_precision('Product Price'), required=True)
    unit_amount = fields.Float(string='Unit Price', digits='Product Price', required=True) #odoo13
    # quantity = fields.Float( digits=dp.get_precision('Product Unit of Measure'), default=1, required=True)
    quantity = fields.Float(digits='Product Unit of Measure', default=1, required=True) #odoo13
    expense_note = fields.Text('Expense Note', required=True)
    it_operations_id = fields.Many2one('hr.it.operations', string="IT Operations")
    expense_created = fields.Boolean('Expense Created', default=False)

class HrExpense(models.Model):

    _inherit = "hr.expense"
    it_operations_id = fields.Many2one('hr.it.operations', string="IT Operations")

class hr_it_operations_line(models.Model):

    _name = 'hr.it.operations.line'
    _description = 'HR It Operations Line'
    
    product_id = fields.Many2one('product.product', string="Product")
    product_uom = fields.Many2one('uom.uom', string='Product Unit of Measure', required=True)
    name = fields.Char('Description', required=True)
    # quantity = fields.Float('Product Quantity', digits_compute=dp.get_precision('Account'), required=True)
    quantity = fields.Float('Product Quantity', digits='Account', required=True) #odoo13
    it_operations_id = fields.Many2one('hr.it.operations', string="IT Operations")
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        self.name = self.product_id.name

class hr_it_operations(models.Model):
    
    @api.model
    def _employee_get(self):
        ids = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return ids

    _name = 'hr.it.operations'
    _description = 'Equipment Requests'
    #_inherit = ['mail.thread']
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']      #   odoo11
    _order = "id desc"

    _track = {
        'state': {
            'hr_it_operations.mt_hr_it_operations_new': lambda self, cr, uid, obj, ctx = None: obj['state'] == 'draft',
            'hr_it_operations.mt_hr_it_operations_confirm': lambda self, cr, uid, obj, ctx = None: obj['state'] == 'confirm',
            'hr_it_operations.mt_hr_it_operations_validate': lambda self, cr, uid, obj, ctx = None: obj['state'] == 'validate',
            'hr_it_operations.mt_hr_it_operations_approve': lambda self, cr, uid, obj, ctx = None: obj['state'] == 'approve',
            'hr_it_operations.mt_hr_it_operations_cancel': lambda self, cr, uid, obj, ctx = None: obj['state'] == 'refuse',
        },
        'stage_id': {
            'hr_it_operations.mt_hr_it_operations_stage': lambda self, cr, uid, obj, ctx = None: obj['state'] not in ['draft', 'confirm', 'validate', 'approve', 'done', 'cancel'],
        },
    }
                
    name = fields.Char('Name')
    type = fields.Selection([('hardware', 'Hardware'),('software', 'Software')], string='Request For', required=True, default='hardware')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True, default=_employee_get)
    employee_code = fields.Char('Employee Code', readonly=True)
    is_damage = fields.Boolean('Damage')
    job_id = fields.Many2one('hr.job', 'Job Position', readonly=False)
    department_id = fields.Many2one('hr.department', 'Department', readonly=False)
    description = fields.Text('Description', required=False)
    picking_ids = fields.One2many('stock.picking', 'it_operations_id', 'Picking List', help="", copy=False)
    expense_ids = fields.One2many('hr.expense', 'it_operations_id', 'Expense List', readonly=True, help="", copy=False)
    state = fields.Selection([('draft', 'Draft'),
                           ('confirm', 'Waiting for Approval'),
                           ('validate', 'Approved by Department'),
                           ('approve', 'Approved by HR'),
                            ('stock', 'Equipment Assigned'),
                           ('refuse', 'Refused'),
                           ('reject','Rejected'),], tracking=True, string="Status", default='draft', copy=False)
    create_uid = fields.Many2one('res.users', 'Created by', readonly=True)
    create_date = fields.Datetime('Created on', readonly=True)
    write_uid = fields.Many2one('res.users', 'Modified by', readonly=True)
    write_date = fields.Datetime('Modified on', readonly=True)
    validated_date = fields.Datetime('Validated on', readonly=True)
    validated_by = fields.Many2one('res.users', 'Validated by', readonly=True)
    approved_date = fields.Datetime('Approved on', readonly=True)
    approved_by = fields.Many2one('res.users', 'Approved by', readonly=True)
    refused_by = fields.Many2one('res.users', 'Refused by', readonly=True)
    refused_date = fields.Datetime('Refused on', readonly=True)
    location_src_id = fields.Many2one('stock.location', string="Source Location")
    location_dest_id = fields.Many2one('stock.location', string="Destination Location")
    product_lines = fields.One2many('hr.it.operations.line', 'it_operations_id', string="Products")
    expense_lines = fields.One2many('hr.it.operations.expenses', 'it_operations_id', string="Expenses")
    #expense_created = fields.Boolean('Expense Created', )#compute=_check_expense_line
    user_id = fields.Many2one('res.users', string="User")
    picking_created = fields.Boolean('Picking Created', copy=False)
    expense_generated = fields.Boolean('Expense Generated', copy=False)
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.user.company_id)

    # @api.multi #odoo13
    def name_get(self):
        res = []
        for operation in self:
            name = operation.employee_id and operation.employee_id.name or ''
            date = operation.create_date
            create_date = date.strftime('%Y-%m-%d')
            name = ''.join([name, ' - ', operation.type  or '' , ' - ', create_date or ''])
            res.append((operation.id, name))
        return res
    
    # @api.multi #odoo13
    def onchange_employee_id(self, employee_id):
        result = {'value': {'department_id': False, 'job_id': False, \
                            'employee_code':False, 'user_id': False}}
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            result['value'] = {
                'department_id': employee.department_id and employee.department_id.id or False,
                'job_id': employee.job_id and employee.job_id.id or False,
                'employee_code': employee.code or False,
                'user_id': employee.user_id.id or False,
                }
        return result
    
    # @api.multi #odoo13
    def validate_it_operations(self):
        today = datetime.today()
        # user_ids = self.employee_id.user_id.id
        user_ids = self.employee_id.user_id.partner_id.ids
        self.message_subscribe(user_ids)
        self.write({'state': 'validate', 'validated_by':self.env.uid, 'validated_date':today})
        # self.message_post(type='email', subtype='mail.mt_comment', body=_('Request Validated.'))
        # self.message_post(type='email', subtype_xmlid='mail.mt_comment', body=_('Request Validated.'))
        self.message_post(message_type='email', subtype_xmlid='mail.mt_comment', body=_('Request Validated.'))
        return True
    
    # @api.multi #odoo13
    def confirm_it_operations(self):
        self.write({'state': 'confirm'})
        # self.message_post(type='email', subtype='mail.mt_comment', body=_('Request Confirmed.'))
        # self.message_post(type='email', subtype_xmlid='mail.mt_comment', body=_('Request Confirmed.'))
        self.message_post(message_type='email', subtype_xmlid='mail.mt_comment', body=_('Request Confirmed.'))

        return True
    
    # @api.multi #odoo13
    def _create_stock_moves(self, picking):
        type_obj = self.env['stock.picking.type']
        type_id = type_obj.search([('code', '=', 'internal')], limit=1)
        if not self.location_src_id.id or not self.location_dest_id.id:
            raise UserError(_("Please setup stock/employee location."))
        for line in self.product_lines:
            template = {
                'name': line.name or '',
                'product_uom_qty': line.quantity,
                'product_id': line.product_id.id,
                # 'product_uom': line.uom_uom.id,
                'product_uom': line.product_uom.id,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.location_dest_id.id,
                'picking_id': picking.id,
                'state': 'draft',
                'company_id': self.env.user.company_id.id,
                # 'procurement_id': False, #odoo13
                'origin': line.it_operations_id.name,
            }
            self.env['stock.move'].create(template)
        return True

    # @api.multi #odoo13
    def create_picking(self):
        type_obj = self.env['stock.picking.type']
        if not self.location_src_id.id or not self.location_dest_id.id:
            raise UserError(_("Please setup stock/employee location."))
        self.state = 'stock'
        if self.employee_id:
            type_id = type_obj.search([('code', '=', 'internal')], limit=1)
            if not type_id:
                raise UserError(_("Please create atleast one internal picking type."))
            # if not self.employee_id.address_home_id:
            if not self.employee_id.address_id:
                raise UserError(_("Please configure home address on employee form."))
            if not self.product_lines:
                raise UserError(_("No lines found to create picking"))
            #create picking
            if not self.picking_created:
                picking_id = self.env['stock.picking'].create({\
                    # 'partner_id': self.employee_id.address_home_id.id, \
                    'partner_id': self.employee_id.address_id.id, \
                    'picking_type_id': type_id.id,\
                    'location_dest_id': self.location_dest_id.id, \
                    'location_id': self.location_src_id.id})
                self._create_stock_moves(picking_id)#create stock move
                self.write({'picking_ids': [(6,0,[picking_id.id])], 'picking_created': True})
                self.state = 'stock'

    # @api.one #odoo13
    def approve_it_operations(self):
        today = datetime.today()
        self.write({'state': 'approve', 'approved_by':self.env.uid, 'approved_date':today, })
        # self.message_post(type="email", subtype='mail.mt_comment', body=_('Request Approved.'))
        # self.message_post(type="email", subtype_xmlid='mail.mt_comment', body=_('Request Approved.'))
        self.message_post(message_type="email", subtype_xmlid='mail.mt_comment', body=_('Request Approved.'))
        return True
        
    # @api.one #odoo13
    def reject_it_operations(self):
        self.state = 'reject'

    # @api.multi #odoo13
    def generate_expense(self):
        for line in self.expense_lines:
            if not line.expense_created:
                expense_data = {
                    'employee_id': self.employee_id and self.employee_id.id or False,
                    'name': 'Expense - ' + self.name_get()[0][1],
                    'description':line.expense_note,
                    'product_id': line.product_id.id,
                    # 'unit_amount': line.unit_amount,
                    'total_amount_currency': line.unit_amount,
                    'quantity': line.quantity,
                    'it_operations_id': self.id,
                }
                expense_id = self.env['hr.expense'].create(expense_data)
                line.expense_created = True
        self.expense_generated = True 
        return True
    
    # @api.multi #odoo13
    def view_expense(self):
        return {
            'name': _('Employee Expenses'),
            'view_type': 'form',
            'view_mode': 'list',
            'res_model': 'hr.expense',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('it_operations_id', 'in', self.ids)],
        }
    
    # @api.one #odoo13
    def set_to_draft(self):
        self.write({'state': 'draft'})
        # self.message_post(type="email", subtype='mail.mt_comment', body=_('Request Created.'))
        # self.message_post(type="email", subtype_xmlid='mail.mt_comment', body=_('Request Created.'))
        self.message_post(message_type="email", subtype_xmlid='mail.mt_comment', body=_('Request Created.'))
        return True
    
    # @api.one #odoo13
    def refuse_it_operations(self):
        today = datetime.today()
        self.write({'state': 'refuse', 'refused_by':self.env.uid, 'refused_date':today})
        # self.message_post(type='email', subtype='mail.mt_comment', body=_('Request Refused.'))
        # self.message_post(type='email', subtype_xmlid='mail.mt_comment', body=_('Request Refused.'))
        self.message_post(message_type='email', subtype_xmlid='mail.mt_comment', body=_('Request Refused.'))

        return True
    
    # @api.multi #odoo13
    def view_internal_transfer(self):
        result = self.env.ref('stock.action_picking_tree_all')
        result = result.sudo().read()[0]
        # compute the number of delivery orders to display
        pick_ids = []
        for it in self:
            pick_ids += [picking.id for picking in it.picking_ids]
        # choose the view_mode accordingly
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = self.env.ref('stock.view_picking_form')
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
