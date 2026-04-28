# -*- coding: utf-8 -*-

import requests
import base64
import json
from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class TopGoinfinitoSmsService(models.AbstractModel):
    """Service model for sending SMS via Goinfinito API."""
    _name = 'top.goinfinito.sms.service'
    _description = 'Goinfinito SMS Service'

    @api.model
    def _normalize_phone_number(self, phone):
        """
        Normalize phone number for API.
        Remove spaces, plus signs, dashes, and other non-digit characters.
        
        :param phone: Phone number (e.g., "+966 54 116 8537" or "966541168537")
        :return: Normalized phone number (e.g., "966541168537")
        """
        if not phone:
            return phone
        # Remove all non-digit characters
        normalized = ''.join(filter(str.isdigit, str(phone)))
        return normalized

    @api.model
    def _validate_message(self, message):
        """
        Validate and prepare message for SMS.
        SMS messages are typically limited to 160 characters for single SMS,
        or 1600 characters for concatenated SMS.
        
        :param message: Message text
        :return: Validated message (truncated if necessary)
        """
        if not message:
            return message
        
        # Maximum length for concatenated SMS (usually 1600 characters)
        # Some providers support more, but 1600 is a safe limit
        max_length = 1600
        
        if len(message) > max_length:
            _logger.warning(
                'SMS message too long (%d chars), truncating to %d characters',
                len(message),
                max_length
            )
            # Truncate and add ellipsis
            message = message[:max_length-3] + '...'
        
        return message

    @api.model
    def send_sms(self, to, message, sender, api_token, record=None):
        """
        Send SMS via Goinfinito API.
        
        :param to: Recipient phone number (e.g., "966568303446" or "+966 54 116 8537")
        :param message: SMS message body
        :param sender: Sender name (e.g., "SDCdental")
        :param api_token: API token for Basic Auth
        :param record: Optional record that triggered the SMS. If the record has case_source_id = 6, SMS will be skipped.
        :return: Tuple (success: bool, detail_message: str)
        """
        # Debug Log: Check Ticket Type Status
        if record and hasattr(record, 'ticket_type_id') and record.ticket_type_id:
            # Check for disable_sms field
            is_blocked = getattr(record.ticket_type_id, 'disable_sms', False)
            _logger.info(
                "Service SMS Check - Record: %s, Ticket Type: %s (ID: %s), Blocked (disable_sms): %s", 
                record.display_name if hasattr(record, 'display_name') else 'Unknown',
                record.ticket_type_id.name,
                record.ticket_type_id.id,
                is_blocked
            )

        # Skip SMS for excluded case_source_id
        if record and hasattr(record, 'case_source_id') and record.case_source_id and record.case_source_id.id == 6:
            _logger.info("SMS not sent for record %s because case_source_id is 6.", record.display_name if hasattr(record, 'display_name') else record)
            return False, "SMS not sent because case_source_id is 6."

        # Skip SMS for excluded ticket types (using disable_sms flag OR hardcoded list)
        if record and hasattr(record, 'ticket_type_id') and record.ticket_type_id:
            # 1. Check hardcoded list (Safety Net)
            EXCLUDED_IDS = [13, 23, 26, 27]
            if record.ticket_type_id.id in EXCLUDED_IDS:
                _logger.warning("SMS not sent for record %s because ticket_type_id %s is in HARDCODED EXCLUSION LIST.", 
                            record.display_name if hasattr(record, 'display_name') else record,
                            record.ticket_type_id.id)
                return False, f"SMS not sent because ticket type {record.ticket_type_id.id} is excluded (Hardcoded)."

            # 2. Check if the ticket type has disable_sms set to True
            if getattr(record.ticket_type_id, 'disable_sms', False):
                _logger.info("SMS not sent for record %s because ticket_type_id %s has disable_sms=True.", 
                            record.display_name if hasattr(record, 'display_name') else record,
                            record.ticket_type_id.id)
                return False, f"SMS not sent because ticket type has SMS disabled."

        if not all([to, message, sender, api_token]):
            error_msg = 'Missing required parameters for SMS sending'
            _logger.error(error_msg)
            return False, error_msg
        
        # Validate and prepare message
        message = self._validate_message(message)
        if not message:
            error_msg = 'Empty message after validation'
            _logger.error(error_msg)
            return False, error_msg
        
        # Normalize phone number
        normalized_phone = self._normalize_phone_number(to)
        if not normalized_phone:
            error_msg = f'Invalid phone number format: {to}'
            _logger.error(error_msg)
            return False, error_msg
        
        # Validate phone number length (should be at least 10 digits)
        if len(normalized_phone) < 10:
            error_msg = f'Phone number too short: {normalized_phone}'
            _logger.error(error_msg)
            return False, error_msg
        
        # Prepare Authorization header
        # Goinfinito supports both Basic Auth and Bearer Token
        # According to documentation, try Bearer Token first
        # Bearer Token: Authorization: Bearer <api_token>
        # Basic Auth (fallback): Authorization: Basic <base64(api_token:)>
        auth_header = f'Bearer {api_token}'
        
        # Also prepare Basic Auth as fallback
        auth_string = f"{api_token}:"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        auth_header_basic = f'Basic {auth_b64}'
        
        # Ensure message is properly encoded as UTF-8 string
        # Remove any control characters that might cause issues
        message_clean = message.encode('utf-8', errors='ignore').decode('utf-8')
        # Remove any null bytes or other problematic characters
        message_clean = message_clean.replace('\x00', '').strip()
        
        # Detect if message contains Unicode characters (Arabic, etc.)
        # Check if message contains non-ASCII characters
        has_unicode = any(ord(char) > 127 for char in message_clean)
        
        # Clean and validate sender name
        sender_clean = str(sender).strip()
        # Remove any special characters that might cause issues (keep alphanumeric and spaces)
        # Some APIs only allow alphanumeric sender names
        sender_clean = ''.join(c for c in sender_clean if c.isalnum() or c.isspace() or c in ['-', '_']).strip()
        if not sender_clean:
            error_msg = f'Invalid sender name after cleaning: {sender}'
            _logger.error(error_msg)
            return False, error_msg
        
        # Validate phone number format (should start with country code, no leading zeros after country code)
        if not normalized_phone.startswith('966') and len(normalized_phone) >= 10:
            _logger.warning(
                'Phone number %s (normalized: %s) may not be in correct format. '
                'Expected format: 966XXXXXXXXX (Saudi Arabia)',
                to,
                normalized_phone
            )
        
        # Determine coding value based on message content
        # 1 = Standard text (Latin characters)
        # 2 = Unicode text (Arabic, etc.)
        coding_value = 2 if has_unicode else 1
        
        # Build payload according to Goinfinito API documentation
        # Note: udh is Integer, property is String, coding is Integer
        payload = {
            "apiver": "1.0",
            "sms": {
                "ver": "2.0",
                "dlr": {"url": ""},
                "messages": [{
                    "udh": 0,  # Integer: 0 for text message
                    "coding": coding_value,  # Integer: 1 for text, 2 for Unicode
                    "text": message_clean,
                    "property": "0",  # String: "0" for normal, "1" for Flash SMS
                    "id": "1",  # String: Unique message ID
                    "addresses": [{
                        "from": sender_clean,
                        "to": normalized_phone,
                        "seq": "1",  # String: Unique address ID
                        "tag": ""
                    }]
                }]
            }
        }
        
        # API endpoint
        url = "https://api.goinfinito.me/unified/v2/send"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': auth_header,
        }
        
        try:
            # Try with Bearer token first
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30,
            )
            
            # If 401 Unauthorized, try Basic Auth as fallback
            if response.status_code == 401:
                _logger.info('Bearer token failed with 401, trying Basic Auth as fallback')
                headers['Authorization'] = auth_header_basic
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30,
                )
            
            # Log request payload for debugging (without sensitive data)
            _logger.debug(
                'Goinfinito SMS API request: URL=%s, Phone=%s, Sender=%s, Payload=%s',
                url,
                normalized_phone,
                sender,
                json.dumps({k: v for k, v in payload.items() if k != 'sms'})
            )
            
            # Check response status
            if response.status_code == 200:
                # Log response for debugging
                _logger.info(
                    'Goinfinito SMS API response: %s',
                    response.text
                )
                
                # Log to ir.logging
                self.env['ir.logging'].sudo().create({
                    'name': 'top_goinfinito_sms',
                    'type': 'server',
                    'level': 'info',
                    'message': f'SMS sent successfully to {normalized_phone}: {response.text}',
                    'path': 'top_goinfinito_sms',
                    'func': 'send_sms',
                    'line': '1',
                })
                
                success_msg = f'SMS sent successfully to {normalized_phone}. API Response: {response.text}'
                return True, success_msg
            else:
                # Log detailed error response
                error_response = response.text
                try:
                    # Try to parse JSON error response for more details
                    error_json = response.json()
                    error_details = json.dumps(error_json, indent=2, ensure_ascii=False)
                    
                    # Extract specific error messages if available
                    error_messages = []
                    if isinstance(error_json, dict):
                        if 'message' in error_json:
                            error_messages.append(f"Message: {error_json['message']}")
                        if 'error' in error_json:
                            error_messages.append(f"Error: {error_json['error']}")
                        if 'errors' in error_json:
                            error_messages.append(f"Errors: {error_json['errors']}")
                        if 'statustext' in error_json:
                            error_messages.append(f"Status Text: {error_json['statustext']}")
                    
                    if error_messages:
                        error_details = f"{error_details}\n\nExtracted Error Info:\n" + "\n".join(error_messages)
                except (ValueError, json.JSONDecodeError):
                    error_details = error_response
                
                error_msg = (
                    f'Failed to send SMS to {normalized_phone}: '
                    f'HTTP {response.status_code} - {error_details}'
                )
                
                # Log message length for debugging
                message_length = len(message_clean)
                _logger.error(
                    '%s\nMessage length: %d characters\nSender: %s\nRequest payload: %s',
                    error_msg,
                    message_length,
                    sender,
                    json.dumps(payload, indent=2, ensure_ascii=False)
                )
                
                # Log error to ir.logging
                self.env['ir.logging'].sudo().create({
                    'name': 'top_goinfinito_sms',
                    'type': 'server',
                    'level': 'error',
                    'message': f'{error_msg}\nMessage length: {message_length} chars\nResponse: {error_details}',
                    'path': 'top_goinfinito_sms',
                    'func': 'send_sms',
                    'line': '1',
                })
                
                # Create detailed error message with request info and troubleshooting tips
                troubleshooting_tips = []
                if response.status_code == 400:
                    troubleshooting_tips.extend([
                        '• Sender name may not be registered/approved with Goinfinito',
                        '• Phone number format may not match API requirements',
                        '• Message may contain unsupported characters',
                        '• API token may be invalid or expired',
                        '• Check Goinfinito dashboard for sender name approval status',
                        f'• Coding value used: {coding_value} ({"Unicode" if coding_value == 2 else "Standard"})',
                        '• Verify API token format - try Bearer token or Basic Auth'
                    ])
                
                detail_msg = (
                    f'Failed to send SMS: HTTP {response.status_code}\n'
                    f'{error_details}\n\n'
                    f'Request Details:\n'
                    f'- Normalized Phone: {normalized_phone}\n'
                    f'- Original Phone: {to}\n'
                    f'- Sender (original): {sender}\n'
                    f'- Sender (cleaned): {sender_clean}\n'
                    f'- Message Length: {message_length} chars\n'
                    f'- Has Unicode: {has_unicode}\n'
                    f'- Coding Value: {coding_value} ({"Unicode" if coding_value == 2 else "Standard"})\n'
                    f'- Message Preview: {message_clean[:100]}...\n'
                    f'- Auth Method: {"Bearer Token (fallback to Basic if 401)" if response.status_code != 401 else "Basic Auth (after Bearer failed)"}\n'
                    f'- Full Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n'
                )
                
                if troubleshooting_tips:
                    detail_msg += f'\nTroubleshooting Tips:\n' + '\n'.join(troubleshooting_tips)
                return False, detail_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f'Failed to send SMS to {normalized_phone}: {str(e)}'
            _logger.error(
                '%s\nRequest payload: %s',
                error_msg,
                json.dumps(payload, indent=2),
                exc_info=True
            )
            
            # Log error to ir.logging
            self.env['ir.logging'].sudo().create({
                'name': 'top_goinfinito_sms',
                'type': 'server',
                'level': 'error',
                'message': error_msg,
                'path': 'top_goinfinito_sms',
                'func': 'send_sms',
                'line': '1',
            })
            
            return False, error_msg
        except Exception as e:
            error_msg = f'Unexpected error sending SMS to {normalized_phone}: {str(e)}'
            _logger.error(error_msg, exc_info=True)
            
            # Log error to ir.logging
            self.env['ir.logging'].sudo().create({
                'name': 'top_goinfinito_sms',
                'type': 'server',
                'level': 'error',
                'message': error_msg,
                'path': 'top_goinfinito_sms',
                'func': 'send_sms',
                'line': '1',
            })
            
            return False, error_msg
