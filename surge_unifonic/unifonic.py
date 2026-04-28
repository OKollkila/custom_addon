import logging

import requests

_logger = logging.getLogger(__name__)

def send_whatsapp(company, recipient, template, params=[], options_params=[]):
    unifonic_public_id = company.unifonic_public_id
    unifonic_secret = company.unifonic_secret
    headers = {
        'Content-Type': 'application/json',
        'PublicID': unifonic_public_id,
        'Secret': unifonic_secret,
    }

    json = {
        "recipient": {
            "contact": recipient,
            "channel": "whatsapp"
        },
        "content": {
            "type": "template",
            "name": template,
            "language": {"code": "ar"},
            "components": [
                {
                    "type": "body",
                    "parameters": params
                },
                {
                    "type": "options",
                    "parameters": options_params
                }
            ]
        }
    }

    response = requests.post('https://apis.unifonic.com/v1/messages', headers=headers, json=json)
    response = response.json()
    _logger.info(response)
    return response
