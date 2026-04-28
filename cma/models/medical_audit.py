import logging
from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class MedicalAudit(models.Model):
    _name = 'clinizone.medical_audit'
    _description = 'clinizone.medical_audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    visit_date = fields.Date("Visit Date", tracking=True)
    branch_id = fields.Many2one("clinizone.branch", "Old Branch (DON'T USE FOR IMPORT)", required=False, tracking=True)
    prime_care_branch_id = fields.Many2one("clinizone.prime_care_branch", "Prime Care Branch", required=True, tracking=True)
    patient_name = fields.Char("Patient Name", required=True, tracking=True)
    mobile_no = fields.Char("Mobile No", required=True, tracking=True)
    doctor_name = fields.Char("Doctor Name", required=True, tracking=True)
    chief_complaint = fields.Text("Chief Complaint", required=False, tracking=True)
    medical_history = fields.Text("Medical History", tracking=True)
    doctor_note = fields.Text("Doctor Note", tracking=True)
    treatment_plan = fields.Text("Treatment Plan", required=False, tracking=True)
    significant_sign = fields.Text("Significant Sign", tracking=True)
    diagnosis = fields.Text("Diagnosis", required=True, tracking=True)
    mrno = fields.Char("MRNO", required=True, tracking=True)
    age = fields.Float("Age", tracking=True)
    department = fields.Char("Department", required=True, tracking=True)
    speciality = fields.Char("Speciality", tracking=True)
    services = fields.Char("Services", tracking=True)
    risk_factor = fields.Char("Risk factor", tracking=True)
    chief_complaint1 = fields.Char("Chief complain", tracking=True)
    comorbidities = fields.Char("Comorbidities", tracking=True)
    diagnosis2 = fields.Selection([('Yes', 'Yes'), ('No', 'No')], "Diagnosis", tracking=True)
    diagnosis_accuracy = fields.Selection([('Yes', 'Yes'), ('No', 'No')], "Diagnosis accuracy", tracking=True)
    chief_complaint2 = fields.Selection([('Yes', 'Yes'), ('No', 'No'), ('VNR', 'VNR')], "Chief complain2", tracking=True)
    treatment_plan2 = fields.Selection([('Yes', 'Yes'), ('No', 'No')], "treatment plan", tracking=True)
    allergy = fields.Selection([('Yes', 'Yes'), ('No', 'No')], "Allergy", tracking=True)
    clinical_examination = fields.Selection([('Yes', 'Yes'), ('No', 'No')], "Clinical Examination", tracking=True)
    history = fields.Selection([('Yes', 'Yes'), ('No', 'No')], "History", tracking=True)
    services_requested = fields.Integer("Services Requested", tracking=True)
    services_done = fields.Integer("Services Done", tracking=True)
    services_required = fields.Integer("Services Required", tracking=True)
    recommendation_for_clinical_variance = fields.Char("Recommendation for clinical variance", tracking=True)
    recommendation_for_leakage = fields.Char("Recommendation for leakage", tracking=True)
    recommendation_for_comprehensiveness = fields.Char("Recommendation for comprehensivness", tracking=True)
    recommendation_for_ttp = fields.Char("Recommendation for TTP", tracking=True)
    recommendation_for_wellness = fields.Char("Recommendation for Wellness", tracking=True)
    next_visit_date = fields.Date("next visit date", tracking=True)
    long_term_plan = fields.Char("Long Term Plan", tracking=True)
    lttp_date = fields.Date("LTTP date", tracking=True)
    medical_audit_recommendations = fields.Char("Medical Audit Recommendations", tracking=True)

    lead_id = fields.Many2one("crm.lead", "Lead", tracking=True)
    lttp_lead_id = fields.Many2one("crm.lead", "LTTP Lead", tracking=True)


    def write(self, vals):
        if not self.env.context.get('skip_validation', False):
            required_string_fields = ['risk_factor', 'chief_complaint1', 'comorbidities', 'diagnosis2', 'diagnosis_accuracy', 'chief_complaint2', 'treatment_plan2', 'allergy', 'clinical_examination', 'history']
            for field in required_string_fields:
                if not getattr(self, field) and field not in vals.keys():
                    raise ValidationError(f"{self._fields[field].string} is required")
        return super(MedicalAudit, self).write(vals)

    def _create_leads_from_next_visit_date(self):
        batch_size = 100

        records = self.search([
            ('lead_id', '=', False),
            ('next_visit_date', '<=', fields.Date.today())
        ], order='id asc', limit=batch_size)

        if not records:
            _logger.info("No medical audit records to process")
            return

        for record in records:
            try:
                # Get company
                company_id = (
                    record.prime_care_branch_id.branch_id.company_id.id
                    if record.prime_care_branch_id and record.prime_care_branch_id.branch_id.company_id
                    else record.branch_id.company_id.id
                    if record.branch_id and record.branch_id.company_id
                    else False
                )

                if not company_id:
                    _logger.error(f"Company not found for record {record.id}")
                    continue

                # Get branch
                branch_id = record.prime_care_branch_id.branch_id if record.prime_care_branch_id else record.branch_id
                if not branch_id:
                    _logger.error(f"Branch not found for record {record.id}")
                    continue

                # Create Lead
                lead = self.env['crm.lead'].with_context(skip_constrains=True).create({
                    'company_id': company_id,
                    'name': record.patient_name,
                    'contact_name': record.patient_name,
                    'phone': record.mobile_no,
                    'branch_id': branch_id.id,
                    'city': branch_id.city_id.name if branch_id.city_id else False,
                    'source_id': self.env.ref('ramcrm.UTM_SOURCE_MEDICAL_AUDIT').id,
                    'lead_source_id': 14,
                    'type': 'opportunity',
                    'description': (
                        f"Original Visit Date: {record.visit_date} <br/>"
                        f"Original Chief Complaint: {record.chief_complaint} <br/>"
                        f"Original Doctor Note: {record.doctor_note} <br/>"
                        f"Original Medical History: {record.medical_history} <br/>"
                        f"Original Treatment Plan: {record.treatment_plan} <br/>"
                        f"Original Significant Sign: {record.significant_sign} <br/>"
                        f"Original Diagnosis: {record.diagnosis} <br/>"
                        f"Age: {record.age} <br/>"
                        f"Recommendation for Clinical Variance: {record.recommendation_for_clinical_variance} <br/>"
                        f"Recommendation for Leakage: {record.recommendation_for_leakage} <br/>"
                        f"Recommendation for Comprehensiveness: {record.recommendation_for_comprehensiveness} <br/>"
                        f"Recommendation for TTP: {record.recommendation_for_ttp} <br/>"
                        f"Recommendation for Wellness: {record.recommendation_for_wellness} <br/>"
                    ),
                    'user_id': False,
                    'topic': record.chief_complaint1,
                    'treating_doctor': record.doctor_name,
                    'speciality': record.speciality,
                    'patient_id': record.mrno,
                })

                # Update record (optimized)
                record.with_context(
                    skip_validation=True,
                    tracking_disable=True
                ).write({'lead_id': lead.id})

            except Exception as e:
                _logger.error(f"Error processing record {record.id}: {str(e)}")

        self.env.cr.commit()


    def _create_leads_from_lttp_date(self):
        records = self.env['clinizone.medical_audit'].search([('lttp_lead_id', '=', False), ('lttp_date', '<=' , fields.Date.today())])
        for record in records:
            company_id_id = record.prime_care_branch_id.branch_id.company_id.id if record.prime_care_branch_id else False
            if not company_id_id:
                company_id_id = record.branch_id.company_id.id if record.branch_id and record.branch_id.company_id else False
            if not company_id_id:
                _logger.error(f"Company not found for medical audit record {record.id} - {record.patient_name}")
                continue
            branch_id = record.prime_care_branch_id.branch_id if record.prime_care_branch_id else False
            if not branch_id:
                branch_id = record.branch_id
            if not branch_id:
                _logger.error(f"Branch not found for medical audit record {record.id} - {record.patient_name}")
                continue
            lead = self.env['crm.lead'].with_context({'skip_constrains': True}).create({
                'company_id': company_id_id,
                'name': record.patient_name,
                'contact_name': record.patient_name,
                'phone': record.mobile_no,
                'branch_id': branch_id.id,
                'city': branch_id.city_id.name,
                'source_id': self.env.ref('ramcrm.UTM_SOURCE_MEDICAL_AUDIT').id,
                'lead_source_id': 14,
                'type': 'opportunity',
                'description':
                    f"Original Visit Date: {record.visit_date} <br/>"
                    f"Original Chief Complaint: {record.chief_complaint} <br/>"
                    f"Original Doctor Note: {record.doctor_note} <br/>"
                    f"Original Medical History: {record.medical_history} <br/>"
                    f"Original Treatment Plan: {record.treatment_plan} <br/>"
                    f"Original Significant Sign: {record.significant_sign} <br/>"
                    f"Original Diagnosis: {record.diagnosis} <br/>"
                    f"Age: {record.age} <br/>"
                    f"Treatment Plan: {record.treatment_plan} <br/>"
                    f"Significant Sign: {record.significant_sign} <br/>"
                    f"Diagnosis: {record.diagnosis} <br/>"
                ,
                'user_id': False,
                'topic': record.chief_complaint1,
                'treating_doctor': record.doctor_name,
                'speciality': record.speciality,
                'patient_id': record.mrno,
            })
            record.with_context({'skip_validation': True}).write({'lttp_lead_id': lead.id})

    @api.constrains('doctor_name', 'mrno' , 'patient_name', 'speciality', 'visit_date', 'create_date')
    def validate_no_duplicates_within_x_days(self):
        for record in self:
            records = self.env['clinizone.medical_audit'].search_count([
                ('doctor_name', '=', record.doctor_name),
                ('mrno', '=', record.mrno),
                ('patient_name', '=', record.patient_name),
                ('speciality', '=', record.speciality),
                ('visit_date', '=', record.visit_date),
                ('create_date', '>=', self.env.cr.now() - timedelta(days=3))
            ])
            if records > 1:
                raise ValidationError(f"Duplicate record found within 3 days: Patient Name: {record.patient_name}, MRNO: {record.mrno}, Doctor Name: {record.doctor_name}, Speciality: {record.speciality}, Visit Date: {record.visit_date}")

    def action_create_leads_in_crm_py(self):
        from datetime import date
        for record in self:
            if not record.next_visit_date or record.next_visit_date > date.today():
                continue
            if record.lead_id:
                continue

            company_id = (
                record.prime_care_branch_id.branch_id.company_id.id
                if record.prime_care_branch_id and record.prime_care_branch_id.branch_id.company_id
                else record.branch_id.company_id.id if record.branch_id and record.branch_id.company_id
                else False
            )
            if not company_id:
                raise ValidationError(f"Company not found for record {record.id} - {record.patient_name}")

            branch_id = record.prime_care_branch_id.branch_id if record.prime_care_branch_id else record.branch_id
            if not branch_id:
                raise ValidationError(f"Branch not found for record {record.id} - {record.patient_name}")

            lead = self.env['crm.lead'].with_context({'skip_constrains': True}).create({
                'company_id': company_id,
                'name': record.patient_name,
                'contact_name': record.patient_name,
                'phone': record.mobile_no,
                'branch_id': branch_id.id,
                'city': branch_id.city_id.name if branch_id.city_id else False,
                'source_id': self.env.ref('ramcrm.UTM_SOURCE_MEDICAL_AUDIT').id,
                'lead_source_id': 14,
                'type': 'opportunity',
                'description': (
                    f"Original Visit Date: {record.visit_date} <br/>"
                    f"Original Chief Complaint: {record.chief_complaint} <br/>"
                    f"Original Doctor Note: {record.doctor_note} <br/>"
                    f"Original Medical History: {record.medical_history} <br/>"
                    f"Original Treatment Plan: {record.treatment_plan} <br/>"
                    f"Original Significant Sign: {record.significant_sign} <br/>"
                    f"Original Diagnosis: {record.diagnosis} <br/>"
                    f"Age: {record.age} <br/>"
                    f"Recommendation for Clinical Variance: {record.recommendation_for_clinical_variance} <br/>"
                    f"Recommendation for Leakage: {record.recommendation_for_leakage} <br/>"
                    f"Recommendation for Comprehensiveness: {record.recommendation_for_comprehensiveness} <br/>"
                    f"Recommendation for TTP: {record.recommendation_for_ttp} <br/>"
                    f"Recommendation for Wellness: {record.recommendation_for_wellness} <br/>"
                ),
                'user_id': False,
                'topic': record.chief_complaint1,
                'treating_doctor': record.doctor_name,
                'speciality': record.speciality,
                'patient_id': record.mrno,
            })
            record.with_context({'skip_validation': True}).write({'lead_id': lead.id})

