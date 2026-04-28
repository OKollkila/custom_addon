# -*- coding: utf-8 -*-
from odoo import http


class Reviews(http.Controller):
    @http.route('/api/prime_care/checkout', auth='api_key', type='json', methods=['POST'], cors='*', csrf=False)
    def checkout(self):
        r = http.request.httprequest.json
        required_fields = ['mrno', 'patient_name', 'mobile_number', 'department', 'branch']
        for field in required_fields:
            if field not in r:
                return {'success': False, 'message': f'{field} is required'}

        department_id = http.request.env['clinizone.department'].search([('prime_care_code', '=', r['department'])], limit=1)
        if not department_id:
            return {'success': False, 'message': 'Department is invalid'}

        branch_id = http.request.env['clinizone.branch'].search([('prime_care_code', '=', r['branch'])], limit=1)
        if not branch_id:
            return {'success': False, 'message': 'Branch is invalid'}

        m = http.request.env['clinizone.checkout'].create({
            'mrno': r['mrno'],
            'patient_name': r['patient_name'],
            'mobile_number': r['mobile_number'],
            'department_id': department_id.id,
            'branch_id': branch_id.id,
            'doctor_name': r.get('doctor_name'),
            'machine_name': r.get('machine_name'),
            'technician_name': r.get('technician_name'),
            'payment_type_string': r.get('payment_type_string'),
        })

        return {'success': True, 'data': m.read([
            'mrno',
            'patient_name',
            'mobile_number',
            'department_id',
            'branch_id',
            'doctor_name',
            'machine_name',
            'technician_name',
            'payment_type_string'
        ])[0]}
