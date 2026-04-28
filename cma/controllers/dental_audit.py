import base64
import logging

import xlrd
from odoo import http

field_mapping = {
    'Treatment Doctor': 'treatment_doctor',
    'MDR': 'mdr',
    'Patient Name': 'patient_name',
    'Mobile': 'mobile',
    'Ortho': 'ortho',
    'Bleaching': 'bleaching',
    'Scaling': 'scaling',
    'CF': 'cf',
    'Fixed': 'fixed',
    'RCT': 'rct',
    'ReRCT': 'rerct',
    'Pedo': 'pedo',
    'EX': 'ex',
    'Surgical EX': 'surgical_ex',
    'Surgery': 'surgery',
    'Impaction': 'impaction',
    'Apicectomy': 'apicectomy',
    'Gingivectomy': 'gingivectomy',
    'CR Lenthening': 'cr_lenthening',
    'Denture': 'denture',
    'Implant': 'implant',
    'GA': 'ga',
    'Perio': 'perio',
    'X-Ray': 'x_ray',
    'TMJ': 'tmj',
    'Night Guard': 'night_guard',
    '(Fixed)': 'fixed2',
    '(Implant)': 'implant2',
    'Maxillofacial': 'maxillofacial',
    'Next Visit': 'next_visit',
    'Branch': 'branch_id',
    'PrimeCare Branch': 'prime_care_branch_id',
    'Clinic': 'clinic',
    'Notes': 'notes',
    'Lead Source': 'lead_source',
    'Campaign': 'campaign',
}

field_mapping = {k.lower().replace(' ', '').replace('.', ''): v for k, v in field_mapping.items()}

_logger = logging.getLogger(__name__)

class DentalAudit(http.Controller):
    @http.route('/api/dental-audit/am-i-member', type='json', auth="user", cors="*")
    def is_dental_audit_member(self):
        return {
            'success': True,
            'is_member': http.request.env.ref('cma.TEAM_DENTAL_AUDIT').id in http.request.env.user.team_ids.mapped('id')
        }

    @http.route('/api/dental-audit', type='json', auth="user", cors="*")
    def get_dental_audit(self):
        if http.request.env.ref('cma.TEAM_DENTAL_AUDIT').id not in http.request.env.user.team_ids.mapped('id'):
            return {
                'success': False,
                'msg': 'You are not a member of Dental Audit team'
            }

        dental_audits = http.request.env['clinizone.dental_audit'].search([])
        return {
            'success': True,
            'data': dental_audits.read()
        }

    @http.route('/api/dental-audit/<int:dental_audit_id>', type='json', auth="user", cors="*")
    def get_dental_audit_by_id(self, dental_audit_id):
        dental_audit = http.request.env['clinizone.dental_audit'].browse(dental_audit_id)
        return {
            'success': True,
            'data': dental_audit.read()
        }

    @http.route('/api/dental-audit/<int:dental_audit_id>/update', type='json', auth="user", cors="*")
    def update_dental_audit(self, dental_audit_id):
        r = http.request.httprequest.json
        dental_audit = http.request.env['clinizone.dental_audit'].browse(dental_audit_id)
        dental_audit.write(r)
        return {
            'success': True,
            'data': dental_audit.read()
        }

    @http.route('/api/dental-audit/import', type='json', auth="user", cors="*")
    def import_dental_audit(self):
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
        _logger.info(f'Header row: {header_row}')
        header_row = [col.lower().replace(' ', '').replace('.', '') for col in header_row]
        _logger.info(f'Header row after processing: {header_row}')

        new_records = []
        for row in range(1, sheet.nrows):
            dental_audit_row = sheet.row_values(row)
            _logger.info(f'Processing row {row}: {dental_audit_row}')
            dental_audit_data = {}
            for excel_col2 in field_mapping.keys():
                excel_col = excel_col2.lower().replace(' ', '').replace('.', '')
                try:
                    col = header_row.index(excel_col)
                except ValueError:
                    _logger.info(f'Column {excel_col} not found in header')
                    continue
                model_field = field_mapping[excel_col]
                cell_value = dental_audit_row[col]
                _logger.info(f'Processing column {excel_col}: "{cell_value}"')

                if not cell_value:
                    continue

                if model_field == 'branch_id':
                    _logger.info(f'Branch is specified: {cell_value}')
                    branch = http.request.env['clinizone.branch'].search([('name', '=', cell_value)], limit=1)
                    if not branch:
                        http.request.env.cr.rollback()
                        return {
                            'success': False,
                            'msg': 'Branch with name ' + cell_value + ' does not exist'
                        }
                    _logger.info(f'Branch found: {branch.name}: {branch.id}')
                    dental_audit_data[model_field] = branch.id
                    continue

                if model_field == 'prime_care_branch_id':
                    _logger.info(f'PrimeCare Branch is specified: {cell_value}')
                    prime_care_branch = http.request.env['clinizone.prime_care_branch'].search([('name', '=', cell_value)], limit=1)
                    if not prime_care_branch:
                        http.request.env.cr.rollback()
                        return {
                            'success': False,
                            'msg': 'PrimeCare Branch with name ' + cell_value + ' does not exist'
                        }
                    _logger.info(f'PrimeCare Branch found: {prime_care_branch.name}: {prime_care_branch.id}')
                    dental_audit_data[model_field] = prime_care_branch.id
                    continue

                if model_field in ['next_visit']:
                    if isinstance(cell_value, str):
                        cell_value = cell_value.strip()
                    if not cell_value:
                        continue
                    try:
                        cell_value = xlrd.xldate.xldate_as_datetime(cell_value, workbook.datemode).strftime('%Y-%m-%d')
                    except Exception as e:
                        _logger.error(f'Error parsing date: {str(e)}')
                        http.request.env.cr.rollback()
                        return {
                            'success': False,
                            'msg': f'Error parsing date: "{cell_value}"'
                        }

                dental_audit_data[model_field] = cell_value

            try:
                _logger.info(f'Creating record with data: {dental_audit_data}')
                dental_audit_record = http.request.env['clinizone.dental_audit'].create(dental_audit_data)
                new_records.append(dental_audit_record)
                if not dental_audit_record.next_visit:
                    dental_audit_record._do_create_lead()
            except Exception as e:
                _logger.error(f'Error creating record: {str(e)}')
                http.request.env.cr.rollback()
                return {
                    'success': False,
                    'msg': str(e)
                }

        return {
            'success': True,
            'new_records': new_records
        }

