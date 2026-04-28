import logging
from datetime import datetime
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

from odoo import models, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MissedInvoiceLeads(models.Model):
    _inherit = 'crm.lead'
    service_detailes = fields.Html(string='Services Detailes')

    @api.model
    def fetch_invoices_and_create_leads(self, date=None, branch=None):
        """
        Fetch rejected invoices from external API and create CRM leads

        :param date: Target date (YYYY-MM-DD format), defaults to today
        :param branch: Target branch, defaults to system parameter
        :return: Dictionary with processing results
        """
        # Configuration
        target_date = date or datetime.now().strftime('%Y-%m-%d')
        default_branch = self.env['ir.config_parameter'].sudo().get_param(
            'missed_invoice.default_branch',
            'Doha Medical Complex'
        )
        target_branch = branch or default_branch

        # Get API configuration
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'missed_invoice.api_base_url',
            'http://15.184.10.121:8080/HISAdmin'
        )
        token = self.env['ir.config_parameter'].sudo().get_param('missed_invoice.api_token')
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('missed_invoice.api_timeout', '30'))

        if not token:
            _logger.error("[Missed Invoice Cron] ❌ API Token not configured in System Parameters!")
            raise UserError("API Token not configured. Please set 'missed_invoice.api_token' in System Parameters.")

        # Build API URL
        url = f"{base_url}/api/invoice/findRejectedServicesByDateAndBranch"
        params = {
            'fromDate': target_date,
            'branch': target_branch
        }
        headers = {"Authorization": f"Bearer {token}"}

        _logger.info(f"[Missed Invoice Cron] ▶ Fetching API for date: {target_date}, branch: {target_branch}")

        # Initialize result tracking
        result = {
            'total_records': 0,
            'leads_created': 0,
            'leads_skipped': 0,
            'leads_failed': 0,
            'errors': []
        }

        try:
            # Make API request with enhanced error handling
            response = self._make_api_request(url, headers, params, timeout)
            if not response:
                return result

            # Parse and validate response
            data = self._parse_api_response(response)
            if not data:
                return result

            result['total_records'] = len(data)
            _logger.info(f"[Missed Invoice Cron] ✅ Records received: {len(data)}")

            if not data:
                _logger.warning("[Missed Invoice Cron] ⚠ No records returned from API")
                return result

            # Process records in batch
            leads_to_create = []

            for record in data:
                try:
                    # Validate record data
                    if not self._validate_record_data(record):
                        result['leads_failed'] += 1
                        continue

                    mrno = record.get("mrno")
                    invoice_id = record.get("invoiceId")

                    # Skip duplicates
                    if self._is_duplicate_lead(mrno, invoice_id):
                        _logger.info(
                            f"[Missed Invoice Cron] ⏭ Skipping existing lead for MRNO: {mrno} / Invoice: {invoice_id}")
                        result['leads_skipped'] += 1
                        continue

                    # Prepare lead data
                    lead_vals = self._prepare_lead_values(record)
                    if lead_vals:
                        leads_to_create.append(lead_vals)
                    else:
                        result['leads_failed'] += 1

                except Exception as e:
                    _logger.error(
                        f"[Missed Invoice Cron] ❌ Error processing record {record.get('mrno', 'Unknown')}: {str(e)}")
                    result['leads_failed'] += 1
                    result['errors'].append(f"Record {record.get('mrno', 'Unknown')}: {str(e)}")

            # Bulk create leads
            if leads_to_create:
                try:
                    created_leads = self.sudo().create(leads_to_create)
                    result['leads_created'] = len(created_leads)
                    _logger.info(f"[Missed Invoice Cron] ✅ Successfully created {len(created_leads)} leads")
                except Exception as e:
                    _logger.error(f"[Missed Invoice Cron] ❌ Bulk create failed: {str(e)}")
                    result['leads_failed'] += len(leads_to_create)
                    result['errors'].append(f"Bulk create failed: {str(e)}")

            # Log summary
            _logger.info(f"[Missed Invoice Cron] 📊 Summary - Total: {result['total_records']}, "
                         f"Created: {result['leads_created']}, Skipped: {result['leads_skipped']}, "
                         f"Failed: {result['leads_failed']}")

            return result

        except Exception as e:
            _logger.error(f"[Missed Invoice Cron] ❌ Unexpected error: {str(e)}")
            result['errors'].append(f"Unexpected error: {str(e)}")
            return result

    def _make_api_request(self, url, headers, params, timeout):
        """Make API request with proper error handling and authentication debugging"""

        # Log token info (first/last 10 chars only for security)
        token = headers.get('Authorization', '').replace('Bearer ', '')
        if token:
            token_preview = f"{token[:10]}...{token[-10:]}" if len(token) > 20 else "TOKEN_TOO_SHORT"
            _logger.info(f"[Missed Invoice Cron] Using token: {token_preview}")
        else:
            _logger.error("[Missed Invoice Cron] ❌ No Authorization token found in headers")
            return None

        try:
            _logger.info(f"[Missed Invoice Cron] Making request to: {url}")
            _logger.info(f"[Missed Invoice Cron] With params: {params}")

            response = requests.get(url, headers=headers, params=params, timeout=timeout, verify=True)

            _logger.info(f"[Missed Invoice Cron] HTTP Status: {response.status_code}")

            if response.status_code == 401:
                _logger.error("[Missed Invoice Cron] ❌ Authentication failed (401 Unauthorized)")
                _logger.error("[Missed Invoice Cron] ❌ Check if token is valid and not expired")
                _logger.error(f"[Missed Invoice Cron] Response: {response.text[:500]}")
                return None
            elif response.status_code != 200:
                _logger.error(f"[Missed Invoice Cron] ❌ API Error: {response.status_code} - {response.text}")
                return None

            return response

        except ConnectionError:
            _logger.error("[Missed Invoice Cron] ❌ Connection Error: Unable to reach API server")
            return None
        except Timeout:
            _logger.error(f"[Missed Invoice Cron] ❌ Timeout Error: API request exceeded {timeout} seconds")
            return None
        except RequestException as e:
            _logger.error(f"[Missed Invoice Cron] ❌ Request Error: {e}")
            return None

    def _parse_api_response(self, response):
        """Parse and validate API response"""
        try:
            data = response.json()
            if not isinstance(data, list):
                _logger.error("[Missed Invoice Cron] ❌ Expected list response from API")
                return None
            return data
        except ValueError as e:
            _logger.error(f"[Missed Invoice Cron] ❌ JSON Decode Error: {e} - Response: {response.text[:500]}...")
            return None

    def _validate_record_data(self, record):
        """Validate required fields in API response"""
        required_fields = ['mrno', 'invoiceId', 'patientName']
        missing_fields = [field for field in required_fields if not record.get(field)]

        if missing_fields:
            _logger.warning(
                f"[Missed Invoice Cron] ⚠ Missing required fields: {missing_fields} in record: {record.get('mrno', 'Unknown')}")
            return False
        return True

    def _is_duplicate_lead(self, mrno, invoice_id):
        """Check if lead already exists for this patient and invoice"""
        return bool(self.search([
            ('patient_id', '=', mrno),
            ('description', 'ilike', invoice_id)
        ], limit=1))

    def _prepare_lead_values(self, record):
        """Prepare lead values from API record"""
        try:
            mrno = record.get("mrno")
            invoice_id = record.get("invoiceId")

            # Find Branch & Department
            branch_rec = self.env['clinizone.branch'].search([
                ('prime_care_code', '=', record.get("branch"))
            ], limit=1)

            department_rec = self.env['clinizone.department'].search([
                ('prime_care_code', '=', record.get("department"))
            ], limit=1)

            # Get default company ID
            default_company_id = int(self.env['ir.config_parameter'].sudo().get_param(
                'missed_invoice.default_company_id', '5'
            ))

            # Prepare description with better formatting
            description = self._format_lead_description(record, invoice_id, mrno)

            vals = {
                'company_id': branch_rec.company_id.id if branch_rec else default_company_id,
                'source_id': self.env.ref('cz_pending_invoices.UTM_SOURCE_PENDING_INVOICE',
                                          raise_if_not_found=False).id,
                'treating_doctor': record.get("consultantName"),
                'patient_id': mrno,
                'name': record.get("patientName"),
                'contact_name': record.get("patientName"),
                'phone': self._clean_phone_number(record.get("mobileNo")),
                'topic': 'Missed Invoice',
                'campaign': 'Missed Invoice',
                'branch_id': branch_rec.id if branch_rec else False,
                'bu': branch_rec.code if branch_rec else record.get("branch", "Unknown"),
                'city_id': branch_rec.city_id.id if branch_rec else 0,
                'lead_source': self.env.ref('cz_pending_invoices.LEAD_SOURCE_PENDING_INVOICE',
                                            raise_if_not_found=False).name,
                'lead_source_id': self.env.ref('cz_pending_invoices.LEAD_SOURCE_PENDING_INVOICE',
                                               raise_if_not_found=False).id,
                'user_id': False,
                'service_detailes':record.get("services"),
                'department_id': department_rec.id if department_rec else False,
                'description': description,
                'tag_ids': [(6, 0, [self.env.ref('cz_pending_invoices.TAG_MISSED_INVOICE',
                                                 raise_if_not_found=False).id])] if self.env.ref(
                    'cz_pending_invoices.TAG_MISSED_INVOICE', raise_if_not_found=False) else [],
            }

            # Remove None values and invalid references
            vals = {k: v for k, v in vals.items() if v is not None and v is not False}

            return vals

        except Exception as e:
            _logger.error(
                f"[Missed Invoice Cron] ❌ Error preparing lead values for MRNO {record.get('mrno', 'Unknown')}: {str(e)}")
            return None

    def _format_lead_description(self, record, invoice_id, mrno):
        """Format lead description with proper HTML structure"""
        return f"""
        <p>{record.get("services_html")}</p>
        """.strip()

    # def _format_lead_description(self, record, invoice_id, mrno):
    #     """Format lead description with proper HTML structure"""
    #     return f"""
    #     <p>{record.get("services_html")}</p>
    #     <div style="font-family: Arial, sans-serif;">
    #         <h4>📄 Missed Invoice Details</h4>
    #         <table style="border-collapse: collapse; width: 100%;">
    #
    #             <tr><td style="padding: 5px; font-weight: bold;">Invoice Date:</td><td style="padding: 5px;">{record.get("invoiceDate", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Invoice Date:</td><td style="padding: 5px;">{record.get("invoiceDate", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Invoice Date:</td><td style="padding: 5px;">{record.get("invoiceDate", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Invoice Date:</td><td style="padding: 5px;">{record.get("invoiceDate", "N/A")}</td></tr>
    #
    #
    #             <tr><td style="padding: 5px; font-weight: bold;">Invoice ID:</td><td style="padding: 5px;">{invoice_id}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Patient:</td><td style="padding: 5px;">{record.get("patientName", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">MRNO:</td><td style="padding: 5px;">{mrno}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Consultant:</td><td style="padding: 5px;">{record.get("consultantName", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Department:</td><td style="padding: 5px;">{record.get("department", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Invoice Status:</td><td style="padding: 5px;">{record.get("invoiceStatus", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Approval Status:</td><td style="padding: 5px;">{record.get("approvalStatus", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Gross Amount:</td><td style="padding: 5px;">{record.get("grossAmt", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Patient Share:</td><td style="padding: 5px;">{record.get("patientShare", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Company Share:</td><td style="padding: 5px;">{record.get("companyShare", "N/A")}</td></tr>
    #             <tr><td style="padding: 5px; font-weight: bold;">Invoice Date:</td><td style="padding: 5px;">{record.get("invoiceDate", "N/A")}</td></tr>
    #
    #
    #         </table>
    #     </div>
    #     """.strip()
    def _clean_phone_number(self, phone):
        """Clean and validate phone number"""
        if not phone:
            return False

        # Remove common separators and spaces
        cleaned = str(phone).replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")

        # Return only if it contains digits
        return cleaned if cleaned.isdigit() and len(cleaned) >= 7 else False

    @api.model
    def validate_api_token(self):
        """Validate API token and test connection - Use this to debug 401 errors"""
        token = self.env['ir.config_parameter'].sudo().get_param('missed_invoice.api_token')

        if not token:
            return {
                'success': False,
                'message': 'API Token not configured in System Parameters. Please set "missed_invoice.api_token"',
                'token_exists': False
            }

        # Get API configuration
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'missed_invoice.api_base_url',
            'http://15.184.10.121:8080/HISAdmin'
        )

        headers = {"Authorization": f"Bearer {token}"}
        test_url = f"{base_url}/api/invoice/findRejectedServicesByDateAndBranch"

        # Log token preview for debugging
        token_preview = f"{token[:10]}...{token[-10:]}" if len(token) > 20 else "TOKEN_TOO_SHORT"
        _logger.info(f"[Token Validation] Testing with token: {token_preview}")

        try:
            response = requests.get(
                test_url,
                headers=headers,
                params={'fromDate': datetime.now().strftime('%Y-%m-%d'), 'branch': 'Doha Medical Complex'},
                timeout=10
            )

            _logger.info(f"[Token Validation] HTTP Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    return {
                        'success': True,
                        'message': f'✅ Token is valid. API returned {len(data)} records',
                        'token_exists': True,
                        'records_count': len(data)
                    }
                except:
                    return {
                        'success': True,
                        'message': '✅ Token is valid. API responded successfully but response is not JSON',
                        'token_exists': True
                    }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': f'❌ Token is invalid or expired (401 Unauthorized). Response: {response.text[:200]}',
                    'token_exists': True,
                    'http_status': 401
                }
            else:
                return {
                    'success': False,
                    'message': f'❌ API returned status {response.status_code}: {response.text[:200]}',
                    'token_exists': True,
                    'http_status': response.status_code
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'❌ Connection error: {str(e)}',
                'token_exists': True
            }

    @api.model
    def test_api_connection(self):
        """Test API connection and authentication"""
        try:
            # First validate the token
            token_result = self.validate_api_token()
            if not token_result['success']:
                return token_result

            # Then try to fetch actual data
            result = self.fetch_invoices_and_create_leads()
            return {
                'success': True,
                'message': f"✅ API test successful. Found {result['total_records']} records.",
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"❌ API test failed: {str(e)}",
                'result': None
            }

    @api.model
    def debug_system_parameters(self):
        """Debug method to check all related system parameters"""
        params_to_check = [
            'missed_invoice.api_token',
            'missed_invoice.api_base_url',
            'missed_invoice.default_branch',
            'missed_invoice.default_company_id',
            'missed_invoice.api_timeout'
        ]

        result = {}
        for param in params_to_check:
            value = self.env['ir.config_parameter'].sudo().get_param(param)
            if param == 'missed_invoice.api_token' and value:
                # Mask token for security
                result[param] = f"{value[:10]}...{value[-10:]}" if len(value) > 20 else "TOKEN_EXISTS_BUT_TOO_SHORT"
            else:
                result[param] = value or "NOT_SET"

        return result
