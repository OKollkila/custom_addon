import logging
from datetime import datetime

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PendingReferral(models.Model):
    _name = 'cz.pending_referral'
    _description = 'Pending and Rejected Referrals'

    # Main fields from API
    from_doctor = fields.Char('From Doctor')
    to_doctor = fields.Char('To Doctor')
    visit_status = fields.Char('Visit Status')
    patient_name = fields.Char('Patient Name')
    mrno = fields.Char('MRN')
    service_name = fields.Char('Service Name')
    requested_date = fields.Datetime('Requested Date')
    priority = fields.Char('Priority')
    from_consultant_id = fields.Char('From Consultant ID')
    to_consultant_id = fields.Char('To Consultant ID')
    visit_date = fields.Datetime('Visit Date')
    action = fields.Char('Action')
    branch = fields.Char('Branch')
    department = fields.Char('Department')
    encounter_id = fields.Integer('Encounter ID')
    speciality = fields.Char('Speciality')
    patient_id = fields.Char('Patient ID')
    reason = fields.Text('Reason')
    status = fields.Selection([
        ('noshow', 'No Show'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending')
    ], string='Status', default='noshow')

    consultant_id = fields.Char('Consultant ID')
    branch_id_code = fields.Char('Branch ID Code')
    net_amt = fields.Float('Net Amount')
    invoice_id = fields.Char('Invoice ID')
    amount = fields.Float('Amount')
    visit_no = fields.Char('Visit Number')
    rejection_reason = fields.Text('Rejection Reason')
    
    # Computed fields
    date = fields.Date('Poll Date')
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

    @api.depends('patient_name', 'from_doctor', 'to_doctor', 'status', 'reason', 'requested_date')
    def _compute_description(self):
        for r in self:
            requested_date_formatted = r.requested_date.strftime('%Y-%m-%d %H:%M:%S') if r.requested_date else '-'
            visit_date_formatted = r.visit_date.strftime('%Y-%m-%d %H:%M:%S') if r.visit_date else '-'
            
            description = f"""
            <strong>Referral Information</strong><br/>
            Status: {r.status or '-'} <br/>
            Visit Status: {r.visit_status or '-'} <br/>
            <br/>
            <strong>Patient Information</strong><br/>
            Patient Name: {r.patient_name or '-'} <br/>
            MRN: {r.mrno or '-'} <br/>
            Patient ID: {r.patient_id or '-'} <br/>
            <br/>
            <strong>Doctors</strong><br/>
            From Doctor: {r.from_doctor or '-'} <br/>
            To Doctor: {r.to_doctor or '-'} <br/>
            From Consultant ID: {r.from_consultant_id or '-'} <br/>
            To Consultant ID: {r.to_consultant_id or '-'} <br/>
            <br/>
            <strong>Details</strong><br/>
            Service Name: {r.service_name or '-'} <br/>
            Speciality: {r.speciality or '-'} <br/>
            Branch: {r.branch or '-'} <br/>
            Department: {r.department or '-'} <br/>
            Priority: {r.priority or '-'} <br/>
            <br/>
            <strong>Dates</strong><br/>
            Requested Date: {requested_date_formatted} <br/>
            Visit Date: {visit_date_formatted} <br/>
            <br/>
            <strong>Reason</strong><br/>
            {r.reason or '-'} <br/>
            <br/>
            <strong>Rejection Reason</strong><br/>
            {r.rejection_reason or '-'} <br/>
            <br/>
            <strong>Financial</strong><br/>
            Amount: {r.amount or 0.0} <br/>
            Net Amount: {r.net_amt or 0.0} <br/>
            Invoice ID: {r.invoice_id or '-'} <br/>
            <br/>
            <strong>Other</strong><br/>
            Visit Number: {r.visit_no or '-'} <br/>
            Encounter ID: {r.encounter_id or '-'} <br/>
            Action: {r.action or '-'} <br/>
            """
            r.description = description

    def action_create_opportunities(self):
        """Create CRM opportunities from pending referrals in 'Untouched' stage"""
        _logger.warning(f"action_create_opportunities called on {self}")
        for referral in self:
            try:
                if referral.lead_id:
                    continue
                if not referral.branch_id or not referral.branch_id.id:
                    _logger.warning(f"No branch for referral {referral.id}")
                    continue
                if not referral.department_id or not referral.department_id.id:
                    _logger.warning(f"No dept for referral {referral.id}")
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
                    'company_id': referral.branch_id.company_id.id,
                    'source_id': self.env.ref('cz_pending_invoices.UTM_SOURCE_PENDING_REFERRAL', raise_if_not_found=False).id if self.env.ref('cz_pending_invoices.UTM_SOURCE_PENDING_REFERRAL', raise_if_not_found=False) else False,
                    'treating_doctor': referral.from_doctor,
                    'patient_id': referral.mrno,
                    'name': referral.patient_name,
                    'contact_name': referral.patient_name,
                    'title': f'Pending Referral - {referral.status}',
                    'campaign': referral.department_id.name,
                    'branch_id': referral.branch_id.id,
                    'bu': referral.branch_id.code,
                    'city_id': referral.branch_id.city_id.id if referral.branch_id.city_id else False,
                    'lead_source_id':82,
                    'user_id': False,
                    'topic': referral.reason,
                    'department_id': referral.department_id.id,
                    'description': referral.description,
                    'stage_id': untouched_stage.id if untouched_stage else False,
                    'expected_revenue': referral.amount or 0.0,
                })
                referral.lead_id = opportunity.id
                _logger.warning(f"Opportunity {opportunity.id} created for referral {referral.id} in '{untouched_stage.name}' stage")
            except Exception as e:
                _logger.error(f"Error for referral {referral.id}: {e}")

    def action_create_leads(self):
        """Legacy method - now calls action_create_opportunities"""
        return self.action_create_opportunities()

