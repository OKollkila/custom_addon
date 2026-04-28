from odoo import http


class Login(http.Controller):

    @http.route('/agent', type='http', auth="user")
    def portal_user_home(self):
        return http.request.render('ramcrm.portal_user_home', {})
