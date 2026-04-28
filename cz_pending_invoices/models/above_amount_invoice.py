import logging
from datetime import datetime

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AboveAmountInvoice(models.Model):
    _name = 'cz.above_amount_invoice'
    _description = 'Invoice Above Amount'

    # Add your fields based on the API response structure
    # These are example fields - adjust according to your actual API response
    invoice_id = fields.Char('Invoice ID')
    invoice_number = fields.Char('Invoice Number')
    invoice_date = fields.Datetime('Invoice Date')
    patient_name = fields.Char('Patient Name')
    patient_id = fields.Char('Patient ID')
    amount = fields.Float('Amount')
    branch = fields.Char('Branch')
    department = fields.Char('Department')
    consultant_name = fields.Char('Consultant Name')
    payment_status = fields.Char('Payment Status')
    
    date = fields.Date('Date')
    branch_id = fields.Many2one('clinizone.branch', compute='_compute_branch_id', store=True)
    department_id = fields.Many2one('clinizone.department', compute='_compute_department_id', store=True)
    description = fields.Text('Description', compute='_compute_description')
    lead_id = fields.Many2one('crm.lead', 'Related Lead')

    @api.depends('branch')
    def _compute_branch_id(self):
        for r in self:
            if r.branch:
                branch = self.env['clinizone.branch'].search([('prime_care_code', '=', r.branch.strip())], limit=1)
                r.branch_id = branch.id if branch else False
            else:
                r.branch_id = False

    @api.depends('department')
    def _compute_department_id(self):
        for r in self:
            if r.department:
                department = self.env['clinizone.department'].search([('prime_care_code', '=', r.department.strip())], limit=1)
                r.department_id = department.id if department else False
            else:
                r.department_id = False

    @api.depends('invoice_id', 'patient_name', 'amount', 'invoice_date')
    def _compute_description(self):
        for r in self:
            invoice_date_formatted = r.invoice_date.strftime('%Y-%m-%d %H:%M:%S') if r.invoice_date else '-'
            description = f"""
            Invoice ID: {r.invoice_id or '-'} <br/>
            Invoice Number: {r.invoice_number or '-'} <br/>
            Patient Name: {r.patient_name or '-'} <br/>
            Patient ID: {r.patient_id or '-'} <br/>
            Amount: {r.amount or 0.0} <br/>
            Branch: {r.branch or '-'} <br/>
            Department: {r.department or '-'} <br/>
            Consultant Name: {r.consultant_name or '-'} <br/>
            Payment Status: {r.payment_status or '-'} <br/>
            Invoice Date: {invoice_date_formatted} <br/>
            """
            r.description = description

    def action_create_opportunities(self):
        """Create CRM opportunities from above amount invoices in 'Untouched' stage"""
        _logger.warning(f"action_create_opportunities called on {self}")
        for invoice in self:
            try:
                if invoice.lead_id:
                    continue
                if not invoice.branch_id or not invoice.branch_id.id:
                    _logger.warning(f"No branch for above amount invoice {invoice.id}")
                    continue
                if not invoice.department_id or not invoice.department_id.id:
                    _logger.warning(f"No dept for above amount invoice {invoice.id}")
                    continue
                
                # Find the 'Untouched' stage
                untouched_stage = self.env['crm.stage'].search([
                    ('name', 'ilike', 'untouched')
                ], limit=1)
                
                if not untouched_stage:
                    _logger.warning("'Untouched' stage not found, using default stage")
                    untouched_stage = self.env['crm.stage'].search([], limit=1)
                
                # Create opportunity instead of lead
                opportunity = self.env['crm.lead'].create({
                    'type': 'opportunity',  # This creates an opportunity instead of a lead
                    'company_id': invoice.branch_id.company_id.id,
                    'treating_doctor': invoice.consultant_name,
                    'patient_id': invoice.patient_id,
                    'name': invoice.patient_name,
                    'contact_name': invoice.patient_name,
                    'title': f'Above Amount Invoice - {invoice.invoice_number or invoice.invoice_id}',
                    'campaign': invoice.department_id.name,
                    'branch_id': invoice.branch_id.id,
                    'bu': invoice.branch_id.code,
                    'city_id': invoice.branch_id.city_id.id if invoice.branch_id.city_id else False,
                    'lead_source_id':83,
                    'user_id': False,
                    'topic':invoice.department_id.name,
                    'department_id': invoice.department_id.id,
                    'description': invoice.description,
                    'stage_id': untouched_stage.id if untouched_stage else False,
                    'expected_revenue': invoice.amount or 0.0,
                })
                invoice.lead_id = opportunity.id
                _logger.warning(f"Opportunity {opportunity.id} created for above amount invoice {invoice.id} in '{untouched_stage.name}' stage")
            except Exception as e:
                _logger.error(f"Error for above amount invoice {invoice.id}: {e}")

    def action_create_leads(self):
        """Legacy method - now calls action_create_opportunities"""
        return self.action_create_opportunities()

