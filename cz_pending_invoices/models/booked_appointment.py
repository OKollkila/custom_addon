import logging
from datetime import datetime

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class BookedAppointment(models.Model):
    _name = 'cz.booked_appointment'
    _description = 'Booked Appointments'

    # Patient Information
    patient_name = fields.Char('Patient Name')
    patient_id = fields.Char('Patient ID')
    mrno = fields.Char('MRN')
    mobile_no = fields.Char('Mobile Number')
    
    # Appointment Details
    appointment_id = fields.Char('Appointment ID')
    appointment_date = fields.Datetime('Appointment Date')
    appointment_time = fields.Char('Appointment Time')
    appointment_status = fields.Selection([
        ('noshow', 'No Show'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending')
    ], string='Status', default='noshow')

    booking_date = fields.Datetime('Booking Date')
    
    # Doctor & Service
    doctor_name = fields.Char('Doctor Name')
    doctor_id = fields.Char('Doctor ID')
    department = fields.Char('Department')
    service_name = fields.Char('Service Name')
    speciality = fields.Char('Speciality')
    
    # Location
    branch = fields.Char('Branch')
    branch_code = fields.Char('Branch Code')
    
    # Other Details
    visit_type = fields.Char('Visit Type')
    priority = fields.Char('Priority')
    reason = fields.Text('Reason')
    notes = fields.Text('Notes')
    confirmation_status = fields.Char('Confirmation Status')
    
    # System Fields
    date = fields.Date('Poll Date')
    branch_id = fields.Many2one('clinizone.branch', compute='_compute_branch_id', store=True)
    department_id = fields.Many2one('clinizone.department', compute='_compute_department_id', store=True)
    description = fields.Text('Description', compute='_compute_description')
    lead_id = fields.Many2one('crm.lead', 'Related Lead')

    @api.depends('branch', 'branch_code')
    def _compute_branch_id(self):
        for r in self:
            if r.branch or r.branch_code:
                search_code = (r.branch_code or r.branch or '').strip()
                branch = self.env['clinizone.branch'].search([('prime_care_code', '=', search_code)], limit=1)
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

    @api.depends('patient_name', 'doctor_name', 'appointment_date', 'appointment_status')
    def _compute_description(self):
        for r in self:
            appointment_date_formatted = r.appointment_date.strftime('%Y-%m-%d %H:%M:%S') if r.appointment_date else '-'
            booking_date_formatted = r.booking_date.strftime('%Y-%m-%d %H:%M:%S') if r.booking_date else '-'
            
            description = f"""
            <strong>Booked Appointment</strong><br/>
            <br/>
            <strong>Patient Information</strong><br/>
            Patient Name: {r.patient_name or '-'} <br/>
            MRN: {r.mrno or '-'} <br/>
            Patient ID: {r.patient_id or '-'} <br/>
            Mobile: {r.mobile_no or '-'} <br/>
            <br/>
            <strong>Appointment Details</strong><br/>
            Appointment ID: {r.appointment_id or '-'} <br/>
            Appointment Date: {appointment_date_formatted} <br/>
            Appointment Time: {r.appointment_time or '-'} <br/>
            Booking Date: {booking_date_formatted} <br/>
            Status: {r.appointment_status or '-'} <br/>
            Confirmation: {r.confirmation_status or '-'} <br/>
            <br/>
            <strong>Doctor &amp; Service</strong><br/>
            Doctor: {r.doctor_name or '-'} <br/>
            Doctor ID: {r.doctor_id or '-'} <br/>
            Department: {r.department or '-'} <br/>
            Service: {r.service_name or '-'} <br/>
            Speciality: {r.speciality or '-'} <br/>
            <br/>
            <strong>Location</strong><br/>
            Branch: {r.branch or '-'} <br/>
            Branch Code: {r.branch_code or '-'} <br/>
            <br/>
            <strong>Other Details</strong><br/>
            Visit Type: {r.visit_type or '-'} <br/>
            Priority: {r.priority or '-'} <br/>
            <br/>
            <strong>Reason</strong><br/>
            {r.reason or '-'} <br/>
            <br/>
            <strong>Notes</strong><br/>
            {r.notes or '-'} <br/>
            """
            r.description = description

    def action_create_opportunities(self):
        """Create CRM opportunities from booked appointments in 'Untouched' stage"""
        _logger.warning(f"action_create_opportunities called on {self}")
        for appointment in self:
            try:
                if appointment.lead_id:
                    continue
                if not appointment.branch_id or not appointment.branch_id.id:
                    _logger.warning(f"No branch for booked appointment {appointment.id}")
                    continue
                if not appointment.department_id or not appointment.department_id.id:
                    _logger.warning(f"No dept for booked appointment {appointment.id}")
                    continue
                
                # Find the 'Untouched' stage
                untouched_stage = self.env['crm.stage'].search([
                    ('name', 'ilike', 'Untouched')
                ], limit=1)
                
                if not untouched_stage:
                    _logger.warning("'Untouched' stage not found, using default stage")
                    untouched_stage = self.env['crm.stage'].search([], limit=1)
                
                # Create opportunity instead of lead
                opportunity = self.env['crm.lead'].create({
                    'type': 'opportunity',  # This creates an opportunity instead of a lead
                    'company_id': appointment.branch_id.company_id.id,
                    'treating_doctor': appointment.doctor_name,
                    'patient_id': appointment.mrno,
                    'name': appointment.patient_name,
                    'contact_name': appointment.patient_name,
                    'phone': appointment.mobile_no,
                    'title': f'Booked Appointment - {appointment.appointment_status or "Scheduled"}',
                    'campaign': appointment.department_id.name,
                    'branch_id': appointment.branch_id.id,
                    'bu': appointment.branch_id.code,
                    'city_id': appointment.branch_id.city_id.id if appointment.branch_id.city_id else False,
                    'lead_source_id': 64,
                    'user_id': False,
                    'topic':appointment.department_id.name,
                    'department_id': appointment.department_id.id,
                    'description': appointment.description,
                    'stage_id': untouched_stage.id if untouched_stage else False,
                })
                appointment.lead_id = opportunity.id
                _logger.warning(f"Opportunity {opportunity.id} created for booked appointment {appointment.id} in '{untouched_stage.name}' stage")
            except Exception as e:
                _logger.error(f"Error for booked appointment {appointment.id}: {e}")

    def action_create_leads(self):
        """Legacy method - now calls action_create_opportunities"""
        return self.action_create_opportunities()


   