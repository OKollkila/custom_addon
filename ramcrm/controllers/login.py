from odoo import http
from odoo.http import request
from odoo.tools import config


class Login(http.Controller):

    @http.route('/api/auth', type='json', cors="*", auth="none", csrf=False)
    def authenticate(self):
        r = http.request.httprequest.json
        login = r['username']
        password = r['password']
        uid  = request.session.authenticate(config.get("db_name", "RamCRM"), login, password)
        if uid:
            model = http.request.env['res.users'].sudo().search([('id', '=', uid)], limit=1)
            if len(model) != 1:
                request.session.logout()
                return {
                    "success": False,
                    'msg': "User is not found"
                }
            k = http.request.env['res.users.apikeys']._generate(scope=None, name='Login')
            return {
                'success': True,
                "sessionInfo": request.env['ir.http'].session_info(),
                'user_id': model.id,
                'name': model.partner_id.name,
                "api_key": k
            }
        else:
            return {
                "success": False,
                'msg': "Error in Username/Password"
            }

    @http.route('/api/allowed-companies', type='json', cors="*", auth="user", csrf=False)
    def allowed_companies(self):
        user = request.env.user
        allowed_companies = user.company_ids.read(['id', 'name'])
        return {
            'success': True,
            'allowed_companies': allowed_companies
        }