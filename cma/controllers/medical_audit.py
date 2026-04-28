import base64

import xlrd
from odoo import http

field_mapping = {
    "VISIT DATE": 'visit_date',
    "Branch": 'prime_care_branch_id',
    "PATIENT NAME": 'patient_name',
    "MOBILE NO": 'mobile_no',
    "DOCTOR NAME": 'doctor_name',
    "Chief Complaint": 'chief_complaint',
    "Medical History": 'medical_history',
    "Doctor Note": 'doctor_note',
    "Treatment Plan": 'treatment_plan',
    "Significant Sign": 'significant_sign',
    "DIAGNOSIS": 'diagnosis',
    "MRNO": 'mrno',
    "AGE": 'age',
    "Department": 'department',
    "Speciality": 'speciality',
    "SERVICES": 'services',
    "Risk factor": 'risk_factor',
    "Chief complain": 'chief_complaint1',
    "Comorbidities": 'comorbidities',
    "Diagnosis.": 'diagnosis2',
    "Diagnosis accuracy": 'diagnosis_accuracy',
    "Chief complain2": 'chief_complaint2',
    "treatment plan": 'treatment_plan2',
    "Allergy": 'allergy',
    "Clinical Examination": 'clinical_examination',
    "History": 'history',
    "Services Requested": 'services_requested',
    "Services Done": 'services_done',
    "Services Required": 'services_required',
    "Recommendation for clinical variance": 'recommendation_for_clinical_variance',
    "Recommendation for leakage": 'recommendation_for_leakage',
    "Recommendation for comprehensivness": 'recommendation_for_comprehensiveness',
    "Recommendation for TTP": 'recommendation_for_ttp',
    "Recommendation for Wellness": 'recommendation_for_wellness',
    "next visit date": 'next_visit_date',
    "Long Term Plan": 'long_term_plan',
    "LTTP date": 'lttp_date',
    "Medical Audit Recommendations": 'medical_audit_recommendations',
}

class MedicalAudit(http.Controller):
    @http.route('/api/medical-audit/am-i-member', type='json', auth="user", cors="*")
    def is_medical_audit_member(self):
        return {
            'success': True,
            'is_member': http.request.env.ref('cma.TEAM_MEDICAL_AUDIT').id in http.request.env.user.team_ids.mapped('id')
        }

    @http.route('/api/medical-audit', type='json', auth="user", cors="*")
    def get_medical_audit(self):
        if http.request.env.ref('cma.TEAM_MEDICAL_AUDIT').id not in http.request.env.user.team_ids.mapped('id'):
            return {
                'success': False,
                'msg': 'You are not a member of Medical Audit team'
            }

        medical_audits = http.request.env['clinizone.medical_audit'].search([])
        return {
            'success': True,
            'data': medical_audits.read()
        }

    @http.route('/api/medical-audit/<int:medical_audit_id>', type='json', auth="user", cors="*")
    def get_medical_audit_by_id(self, medical_audit_id):
        medical_audit = http.request.env['clinizone.medical_audit'].browse(medical_audit_id)
        return {
            'success': True,
            'data': medical_audit.read()
        }

    @http.route('/api/medical-audit/<int:medical_audit_id>/update', type='json', auth="user", cors="*")
    def update_medical_audit(self, medical_audit_id):
        r = http.request.httprequest.json
        medical_audit = http.request.env['clinizone.medical_audit'].browse(medical_audit_id)
        medical_audit.write(r)
        return {
            'success': True,
            'data': medical_audit.read()
        }

    @http.route('/api/medical-audit/import', type='json', auth="user", cors="*")
    def import_medical_audit(self):
        r = http.request.httprequest.json
        excel_file = r.get('excel_file')
        if not excel_file:
            return {
                'success': False,
                'msg': 'Excel file is required'
            }

        excel_file = base64.b64decode(excel_file)

        workbook = xlrd.open_workbook(file_contents=excel_file)
        sheet = workbook.sheet_by_index(0)

        header_row = sheet.row_values(0)

        new_records = []
        for row in range(1, sheet.nrows):
            medical_audit_row = sheet.row_values(row)
            medical_audit_data = {}
            for excel_col in field_mapping.keys():
                try:
                    col = header_row.index(excel_col)
                except ValueError:
                    continue
                model_field = field_mapping[excel_col]
                cell_value = medical_audit_row[col]

                if not cell_value:
                    continue

                if model_field == 'prime_care_branch_id':
                    prime_care_branch_id = http.request.env['clinizone.prime_care_branch'].search([('name', '=', cell_value)], limit=1)
                    if not prime_care_branch_id:
                        http.request.env.cr.rollback()
                        return {
                            'success': False,
                            'msg': 'PrimeCare Branch with name ' + cell_value + ' does not exist'
                        }
                    medical_audit_data[model_field] = prime_care_branch_id.id
                    continue

                if model_field in ['visit_date', 'next_visit_date', 'lttp_date']:
                    try:
                        cell_value = xlrd.xldate.xldate_as_datetime(cell_value, workbook.datemode).strftime('%Y-%m-%d')
                    except Exception as e:
                        http.request.env.cr.rollback()
                        return {
                            'success': False,
                            'msg': f'Invalid date format in {model_field} for {medical_audit_data.get("patient_name")}: {str(e)}'
                        }

                medical_audit_data[model_field] = cell_value

            try:
                new_records.append(http.request.env['clinizone.medical_audit'].create(medical_audit_data))
            except Exception as e:
                http.request.env.cr.rollback()
                return {
                    'success': False,
                    'msg': str(e)
                }

        return {
            'success': True,
            'new_records': new_records
        }

