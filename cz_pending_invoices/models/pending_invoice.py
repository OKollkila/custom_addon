import logging
from datetime import datetime, timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

def json_to_html_table(json_list):
    if not json_list:
        return "<table><tr><td>No data available</td></tr></table>"
    headers = list(json_list[0].keys())
    html = "<table style='border: 1px solid lightgray; border-collapse: collapse;'>\n"
    html += "  <tr>\n"
    for header in headers:
        html += f"    <th style='border: 1px solid lightgray; padding: 1px;'>{header}</th>\n"
    html += "  </tr>\n"
    for item in json_list:
        html += "  <tr>\n"
        for header in headers:
            value = str(item.get(header, ""))
            html += f"    <td style='border: 1px solid lightgray; padding: 1px;'>{value}</td>\n"
        html += "  </tr>\n"
    html += "</table>"
    return html

class PendingInvoice(models.Model):
    _name = 'cz.pending_invoice'
    _description = 'Missed Invoice'

    consultant_name = fields.Char('Consultant Name')
    consultant_id = fields.Char('Consultant ID')
    patient_name = fields.Char('Patient Name')
    patient_id = fields.Char('Patient ID')
    insurance_company = fields.Char()
    insurance_tpa = fields.Char()
    invoice_status = fields.Char()
    approval_status = fields.Char()
    branch = fields.Char()
    invoice_id = fields.Char()
    mobile_no = fields.Char()
    mrno = fields.Char()
    nationality = fields.Char()
    nationality_id = fields.Char()
    department = fields.Char()
    payment_mode = fields.Char()
    payment_type = fields.Char()
    gross_amt = fields.Float()
    discount_amt = fields.Float()
    patient_share = fields.Float()
    patient_vat = fields.Float()
    patient_share_total = fields.Float()
    company_share = fields.Float()
    company_vat = fields.Float()
    company_share_total = fields.Float()
    sub_total = fields.Float()
    vat = fields.Float()
    total = fields.Float()
    balance = fields.Float()
    total_paid_cash = fields.Float()
    total_paid_wallet = fields.Float()
    total_paid_card = fields.Float()
    total_paid_installment = fields.Float()
    total_paid_online = fields.Float()
    invoice_date = fields.Char()
    services = fields.Text()
    services_json = fields.Json()

    date = fields.Date()
    branch_id = fields.Many2one('clinizone.branch', compute='_compute_branch_id')
    department_id = fields.Many2one('clinizone.department', compute='_compute_department_id')
    description = fields.Text('Description', compute='_compute_description')
    lead_id = fields.Many2one('crm.lead')

    def _compute_branch_id(self):
        for r in self:
            branch = self.env['clinizone.branch'].search([('prime_care_code', '=', r.branch)], limit=1)
            r.branch_id = branch.id if branch.id else None,

    def _compute_department_id(self):
        for r in self:
            department = self.env['clinizone.department'].search([('prime_care_code', '=', r.department)], limit=1)
            r.department_id = department.id if department.id else None,

    def _compute_description(self):
        for r in self:
            services_html = json_to_html_table(r.services_json) if r.services_json else '<p>No services</p>'
            invoice_date2 = datetime.fromtimestamp(int(r.invoice_date) / 1000).date() if r.invoice_date else '-'
            description = f"""
            Consultant Name: {r.consultant_name} <br/>
            Consultant ID: {r.consultant_id} <br/>
            Patient Name: {r.patient_name} <br/>
            Patient ID: {r.patient_id} <br/>
            Insurance Company: {r.insurance_company} <br/>
            Insurance TPA: {r.insurance_tpa} <br/>
            Invoice Status: {r.invoice_status} <br/>
            Approval Status: {r.approval_status} <br/>
            Branch: {r.branch} <br/>
            Invoice ID: {r.invoice_id} <br/>
            Mobile No: {r.mobile_no} <br/>
            MRNO: {r.mrno} <br/>
            Nationality: {r.nationality} <br/>
            Nationality ID: {r.nationality_id} <br/>
            Department: {r.department} <br/>
            Payment Mode: {r.payment_mode} <br/>
            Payment Type: {r.payment_type} <br/>
            Gross Amount: {r.gross_amt} <br/>
            Discount Amount: {r.discount_amt} <br/>
            Patient Share: {r.patient_share} <br/>
            Patient VAT: {r.patient_vat} <br/>
            Patient Share Total: {r.patient_share_total} <br/>
            Company Share: {r.company_share} <br/>
            Company VAT: {r.company_vat} <br/>
            Company Share Total: {r.company_share_total} <br/>
            Sub Total: {r.sub_total} <br/>
            VAT: {r.vat} <br/>
            Total: {r.total} <br/>
            Balance: {r.balance} <br/>
            Total Paid Cash: {r.total_paid_cash} <br/>
            Total Paid Wallet: {r.total_paid_wallet} <br/>
            Total Paid Card: {r.total_paid_card} <br/>
            Total Paid Installment: {r.total_paid_installment} <br/>
            Total Paid Online: {r.total_paid_online} <br/>
            Invoice Date: {invoice_date2} <br/>
            Services: {services_html}
            """
            r.description = description

    def action_create_opportunities(self):
        """Create CRM opportunities from pending invoices in 'Untouched' stage"""
        _logger.warning(f"action_create_opportunities called on {self}")
        for invoice in self:
            try:
                if invoice.lead_id:
                    continue
                if not invoice.branch_id or not invoice.branch_id.id:
                    _logger.warning(f"No branch for invoice {invoice.id}")
                    continue
                if not invoice.department_id or not invoice.department_id.id:
                    _logger.warning(f"No dept for invoice {invoice.id}")
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
                    'source_id': self.env.ref('cz_pending_invoices.UTM_SOURCE_PENDING_INVOICE').id,
                    'treating_doctor': invoice.consultant_name,
                    'patient_id': invoice.mrno,
                    'name': invoice.patient_name,
                    'contact_name': invoice.patient_name,
                    'phone': invoice.mobile_no,
                    'title': 'Missed Invoice',
                    'campaign_id': self.env['utm.campaign'].search([('name', '=', 'Missed Invoice')], limit=1).id,
                    'branch_id': invoice.branch_id.id,
                    'bu': invoice.branch_id.code,
                    'city_id': invoice.branch_id.city_id.id,
                    'lead_source_id': 87,  # Keep the existing hardcoded ID for now
                    'lead_source': "Missed Invoice",
                    'user_id': False,
                    'department_id': invoice.department_id.id,
                    'description': invoice.description,
                    'stage_id': untouched_stage.id if untouched_stage else False,
                    'expected_revenue': invoice.total or 0.0,
                })
                invoice.lead_id = opportunity.id
                _logger.warning(f"Opportunity {opportunity.id} created for invoice {invoice.id} in '{untouched_stage.name}' stage")
            except Exception as e:
                _logger.error(f"Error for invoice {invoice.id}: {e}")

    def action_create_leads(self):
        """Legacy method - now calls action_create_opportunities"""
        return self.action_create_opportunities()

    def create_opportunities_for_pending_invoices_from_yesterday(self):
        """Create opportunities for pending invoices from yesterday in 'Untouched' stage"""
        yesterday = datetime.today() - timedelta(days=1)
        pending_invoices = self.search([
            ('date', '=', yesterday.strftime('%Y-%m-%d')),
            ('lead_id', '=', False)
        ])
        
        # Find the 'Untouched' stage
        untouched_stage = self.env['crm.stage'].search([
            ('name', 'ilike', 'untouched')
        ], limit=1)
        
        if not untouched_stage:
            _logger.warning("'Untouched' stage not found, using default stage")
            untouched_stage = self.env['crm.stage'].search([], limit=1)
        
        for invoice in pending_invoices:
            if not invoice.branch_id.id:
                _logger.warning(f"Branch {invoice.branch} not identified for invoice {invoice.invoice_id}")
                continue
            if not invoice.department_id.id:
                _logger.warning(f"Department {invoice.department} not identified for invoice {invoice.invoice_id}")
                continue
            
            # Create opportunity instead of lead
            opportunity = self.env['crm.lead'].create({
                'type': 'opportunity',  # This creates an opportunity instead of a lead
                'company_id': invoice.branch_id.company_id.id,
                'source_id': self.env.ref('cz_pending_invoices.UTM_SOURCE_PENDING_INVOICE').id,
                'treating_doctor': invoice.consultant_name,
                'patient_id': invoice.mrno,
                'name': invoice.patient_name,
                'contact_name': invoice.patient_name,
                'phone': invoice.mobile_no,
                'title': 'Missed Invoice',
                'campaign_id': self.env['utm.campaign'].search([('name', '=', 'Missed Invoice')], limit=1).id,
                'branch_id': invoice.branch_id.id,
                'bu': invoice.branch_id.code,
                'city_id': invoice.branch_id.city_id.id,
                'lead_source_id': 87,
                'user_id': False,
                'department_id': invoice.department_id.id,
                'description': invoice.description,
                'stage_id': untouched_stage.id if untouched_stage else False,
                'expected_revenue': invoice.total or 0.0,
            })
            invoice.lead_id = opportunity.id
            _logger.warning(f"Opportunity {opportunity.id} created for invoice {invoice.id} in '{untouched_stage.name}' stage")

    def create_leads_for_pending_invoices_from_yesterday(self):
        """Legacy method - now calls create_opportunities_for_pending_invoices_from_yesterday"""
        return self.create_opportunities_for_pending_invoices_from_yesterday()
