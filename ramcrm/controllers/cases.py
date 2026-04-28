import datetime

from odoo import http


class Cases(http.Controller):

    @http.route('/ram-cases/v1/case', type='json', auth="api_key", cors="*")
    def case_create(self):
        Case = http.request.env['helpdesk.ticket']
        r = http.request.httprequest.json
        if 'id' in r.keys():
            del r['id']
        if 'case_state_id' in r.keys():
            del r['case_state_id']
        if 'branch_id' in r.keys() and not r['branch_id']:
           del r['branch_id']
        if 'branch_id' in r.keys() and r['branch_id']:
           r['branch_id'] = int(r['branch_id'])

        mapping_api_to_model = {
            'patient_name': 'partner_name',
            'mobile': 'partner_phone',
            'email': 'partner_email',
            'case_description': 'description',
            'case_type': 'ticket_type_id',
            'creation_note':'creation_note',
            'branch_id': 'branch_id',
            'patient_national_id': 'patient_national_id',
        }

        for k, v in mapping_api_to_model.items():
            if k in r.keys():
                r[v] = r.pop(k)

        # Validation: Prevent duplicate tickets with same patient_national_id and ticket_type_id=5
        ticket_type_id = r.get('ticket_type_id')
        patient_national_id = r.get('patient_national_id')
        
        # Convert ticket_type_id to int if it's provided (might come as string from JSON)
        if ticket_type_id is not None:
            try:
                ticket_type_id = int(ticket_type_id)
            except (ValueError, TypeError):
                ticket_type_id = None
        
        if ticket_type_id == 5 and patient_national_id:
            # First, search for all existing tickets with same patient_national_id and ticket_type_id = 5
            existing_tickets = Case.search([
                ('ticket_type_id', '=', 5),
                ('patient_national_id', '=', patient_national_id)
            ])
            
            # Check the status (stage_id) of each existing ticket
            for ticket in existing_tickets:
                # Get the stage_id of the ticket
                stage_id = ticket.stage_id.id if ticket.stage_id else None
                
                # If stage_id != 5, prevent creation
                if stage_id != 5:
                    return {
                        'success': False,
                        'msg': f'A ticket already exists for patient with National ID: {patient_national_id}, case type 5, and stage_id ({stage_id}) != 5'
                    }

        try:
            case = Case.create(r)
        except Exception as e:
            return {
                'success': False,
                'msg': str(e)
            }

        # case.company_id = http.request.env.user.company_id.id

        case = case.read()[0]
        for api_field_name, model_field_name in mapping_api_to_model.items():
            if model_field_name in case.keys():
                if api_field_name in r.keys():
                    case[api_field_name] = r.pop(model_field_name)

        return {
            'success': True,
            'case': [case]
        }

    @http.route('/ram-cases/close', type='http', auth="public", cors="*")
    def case_close(self, **kw):
        Case = http.request.env['clinizone.ram_case'].sudo()
        case_id = kw.get('case_id')
        if not case_id:
            return 'Case ID is required'
        case = Case.browse(int(case_id))
        if not case.state == 'pending_patient_close':
            return 'Invalid case state'
        verification_code = kw.get('verification_code')
        if not verification_code:
            return 'Verification code is required'
        if case.verification_code != verification_code:
            return 'Invalid verification code'
        case.write({
            'state': 'patient_closed'
        })
        http.request.env['mail.activity'].create({
            'display_name': 'Patient Closed',
            'summary': 'Patient Closed',
            'activity_type_id': self.env.ref('ramcrm.review_case').id,
            'date_deadline': datetime.datetime.now(),
            'user_id': case.create_uid.id,
            'res_model_id': self.env.ref('ramcrm.model_clinizone_ram_case').id,
            'res_id': case.id,
        })

        return 'Case closed successfully'