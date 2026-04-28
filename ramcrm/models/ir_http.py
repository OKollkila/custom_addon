import base64

from odoo import models
from odoo.http import request
from werkzeug.exceptions import BadRequest


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_api_key(cls):
        api_key = request.httprequest.headers.get("Authorization")
        if not api_key:
            raise BadRequest("Authorization header with API key missing")
        user_id = request.env["res.users.apikeys"]._check_credentials(
            scope="rpc", key=api_key
        )
        if not user_id:
            raise BadRequest("API key invalid")
        request.update_env(user=user_id)
        request.update_context(**request.env.user.context_get())

    @staticmethod
    def _auth_method_basic():
        auth = request.httprequest.headers.get('Authorization')
        if auth:
            try:
                scheme, credentials = auth.split(' ')
                decoded_credentials = base64.b64decode(credentials).decode("utf-8")
                username, password = decoded_credentials.split(':')
                u2 = request.env["res.users"].sudo().search([
                    ("login", "=", username)
                ], limit=1)
                if not u2:
                    raise BadRequest("Invalid username or password")

                request.env.cr.execute("SELECT COALESCE(password, '') FROM res_users WHERE id=%s", [u2.id])
                [hashed] = request.env.cr.fetchone()
                if not u2._crypt_context().verify(password, hashed):
                    raise BadRequest("Invalid username or password")

                request.update_env(user=u2.id)
                request.update_context(**request.env.user.context_get())
            except Exception as e:
                raise BadRequest(f"Error: {str(e)}")

