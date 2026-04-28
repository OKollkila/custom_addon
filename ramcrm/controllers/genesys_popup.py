from odoo import http

class GenesysPopup(http.Controller):
    @http.route('/genesys/customer/<int:company_id>/<string:phone>', type='http', auth='public', website=False)
    def genesys_popup(self, company_id, phone):
        if not phone.isdigit() or len(phone) < 8:
            return "Invalid phone number"
        phone = phone[-10:]
        lead = http.request.env['crm.lead'].sudo().search([
            ('company_id', '=', company_id),
            ('phone', 'like', phone),
        ], order='id desc', limit=1)
        if not lead:
            return http.request.redirect('/agent#/leads/create?phone=%s' % phone)
        else:
            return http.request.redirect('/agent#/leads/update/%s/0' % lead.id)
