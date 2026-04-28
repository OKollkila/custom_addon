import logging
from datetime import datetime

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class DnaAppointment(models.Model):
    _name = 'cz.dna_appointment'
    _description = 'DNA (Did Not Attend) Appointments'
    _rec_name = 'patient_name'

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
                department = self.env['clinizone.department'].search([('prime_care_code', '=', r.department.strip())],
                                                                     limit=1)
                r.department_id = department.id if department else False
            else:
                r.department_id = False

    @api.depends('patient_name', 'doctor_name', 'appointment_date', 'appointment_status')
    def _compute_description(self):
        for r in self:
            appointment_date_formatted = r.appointment_date.strftime('%Y-%m-%d %H:%M:%S') if r.appointment_date else '-'
            status_label = dict(self._fields['appointment_status'].selection).get(r.appointment_status) or '-'

            description = f"""
            <strong>DNA Appointment - Did Not Attend</strong><br/>
            <br/>
            <strong>Patient Information</strong><br/>
            Patient Name: {r.patient_name or '-'} <br/>
            MRN: {r.mrno or '-'} <br/>
            Patient ID: {r.patient_id or '-'} <br/>
            Mobile: {r.mobile_no or '-'} <br/>
            <br/>
            <strong>Appointment Details</strong><br/>
            Appointment ID: {r.appointment_id or '-'} <br/>
            Date: {appointment_date_formatted} <br/>
            Time: {r.appointment_time or '-'} <br/>
            Status: {status_label} <br/>
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

    def action_create_leads(self):
        """Create CRM leads from DNA appointments"""
        for appointment in self:
            try:
                if appointment.lead_id:
                    continue


                vals = {
                    'name': appointment.patient_name or 'DNA Appointment',
                    'contact_name': appointment.patient_name,
                    'phone': appointment.mobile_no,
                    'patient_id': appointment.mrno,
                    'treating_doctor': appointment.doctor_name,
                    'topic': f'DNA Appointment - {appointment.appointment_status}',
                    'campaign_id': self.env.ref('utm.utm_campaign_email_campaign_products',
                                                raise_if_not_found=False) and self.env.ref(
                        'utm.utm_campaign_email_campaign_products').id or False,
                    'lead_source_id': 36,
                    'description': appointment.description,
                }

                if appointment.branch_id:
                    vals.update({
                        'company_id': appointment.branch_id.company_id.id,
                        'branch_id': appointment.branch_id.id,
                        'bu': appointment.branch_id.code,
                        'city_id': appointment.branch_id.city_id.id if appointment.branch_id.city_id else False,
                    })

                if appointment.department_id:
                    vals['department_id'] = appointment.department_id.id

                lead = self.env['crm.lead'].create(vals)
                appointment.lead_id = lead.id
                _logger.info(f"Lead {lead.id} created for DNA appointment {appointment.id}")

            except Exception as e:
                _logger.error(f"Error for DNA appointment {appointment.id}: {e}")