from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ram_api_bearer_token = fields.Char(
        string='RAM API Bearer Token',
        config_parameter='top_ram_api.bearer_token',
        help='Bearer token for authenticating with RAM Prime Care API'
    )
    
    ram_api_endpoint = fields.Char(
        string='RAM API Endpoint',
        config_parameter='top_ram_api.endpoint',
        default=' https://ramprimecare.com/HISAdmin/api/odooIntegration/updateRefundTask',
        help='Base URL for RAM Prime Care API endpoint'
        
    )
    

