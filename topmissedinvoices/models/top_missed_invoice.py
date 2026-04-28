# -*- coding: utf-8 -*-

import requests
import json
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TopMissedInvoice(models.Model):
    _name = 'top.missed.invoice'
    _description = 'Top Missed Invoice'
    _order = 'invoice_date desc'

    # Basic Information
    consultant_name = fields.Char('Consultant Name', required=True)
    consultant_id = fields.Char('Consultant ID', required=True)
    patient_name = fields.Char('Patient Name', required=True)
    patient_id = fields.Char('Patient ID', required=True)
    mobile_no = fields.Char('Mobile Number')
    mrno = fields.Char('MR Number', required=True)
    nationality = fields.Char('Nationality')
    nationality_id = fields.Char('Nationality ID')
    
    # Invoice Information
    invoice_id = fields.Char('Invoice ID', required=True)
    invoice_status = fields.Char('Invoice Status')
    approval_status = fields.Char('Approval Status')
    invoice_date = fields.Datetime('Invoice Date')
    invoice_date_timestamp = fields.Char('Invoice Date Timestamp')
    
    # Financial Information (simplified for CRM)
    total = fields.Float('Total Amount', digits=(16, 2))
    balance = fields.Float('Balance', digits=(16, 2))
    
    # Payment Information (simplified for CRM only)
    payment_mode = fields.Char('Payment Mode')
    payment_type = fields.Char('Payment Type')
    
    # Branch and Department Information
    branch = fields.Char('Branch')
    visited_branch = fields.Char('Visited Branch')
    department = fields.Char('Department')
    visit_no = fields.Char('Visit Number')
    
    # Insurance Information
    insurance_company = fields.Char('Insurance Company')
    insurance_tpa = fields.Char('Insurance TPA')
    
    # CRM Lead Information
    crm_lead_id = fields.Many2one('crm.lead', 'CRM Lead')
    lead_created = fields.Boolean('Lead Created', default=False)
    
    # Service Items
    service_items = fields.Html('Service Items', help='JSON data of service items')
    
    # Company Information
    company_id = fields.Integer('Company ID')
    
    # Additional fields for CRM integration
    description = fields.Text('Description')
    source_id = fields.Many2one('utm.source', 'Source')
    campaign_id = fields.Many2one('utm.campaign', 'Campaign')
    
    @api.model
    def fetch_rejected_services(self, from_date=None):
        """
        Fetch rejected services from the webhook API
        """
        try:
            # Get system parameters
            base_url = self.env['ir.config_parameter'].sudo().get_param('top_missed_invoices.api_base_url', 
                                                                       'https://ramprimecare.com/HISAdmin/api')
            bearer_token = self.env['ir.config_parameter'].sudo().get_param('top_missed_invoices.bearer_token')
            
            if not bearer_token:
                _logger.error('Bearer token not configured. Please set the system parameter "top_missed_invoices.bearer_token"')
                return []
            
            if not from_date:
                from_date = datetime.now().strftime('%Y-%m-%d')
            
            # Construct the API URL
            api_url = f"{base_url}/invoice/findRejectedServicesByDateAndBranch"
            params = {'fromDate': from_date}
            
            # Prepare headers
            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            _logger.info(f"Fetching rejected services from: {api_url} with params: {params}")
            
            # Make the API request
            response = requests.get(api_url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                _logger.info(f"Successfully fetched {len(data)} rejected services")
                return data
            else:
                _logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            _logger.error(f"Request exception: {str(e)}")
            return []
        except Exception as e:
            _logger.error(f"Unexpected error: {str(e)}")
            return []
    
    @api.model
    def process_rejected_services(self, from_date=None):
        """
        Process rejected services and create records
        """
        try:
            # Fetch data from API
            rejected_services = self.fetch_rejected_services(from_date)
            
            if not rejected_services:
                _logger.info("No rejected services found to process")
                return {
                    'records_created': 0,
                    'leads_created': 0
                }
            
            created_count = 0
            lead_count = 0
            
            for service_data in rejected_services:
                # Check if record already exists
                existing_record = self.search([
                    ('invoice_id', '=', service_data.get('invoiceId')),
                    ('patient_id', '=', service_data.get('patientId'))
                ], limit=1)
                
                if existing_record:
                    _logger.info(f"Record already exists for invoice {service_data.get('invoiceId')}")
                    continue
                
                # Convert timestamp to datetime
                invoice_timestamp = service_data.get('invoiceDate')
                invoice_date = None
                if invoice_timestamp:
                    try:
                        # Convert from milliseconds to seconds
                        invoice_date = datetime.fromtimestamp(invoice_timestamp / 1000)
                    except (ValueError, TypeError):
                        _logger.warning(f"Invalid timestamp format: {invoice_timestamp}")
                
                # Generate HTML table from items
                items_data = service_data.get('items', [])
                service_items_html = self._format_items_as_html_table(items_data)
                
                # Prepare record data
                record_data = {
                    'consultant_name': service_data.get('consultantName'),
                    'consultant_id': service_data.get('consultantId'),
                    'patient_name': service_data.get('patientName'),
                    'patient_id': service_data.get('patientId'),
                    'mobile_no': service_data.get('mobileNo'),
                    'mrno': service_data.get('mrno'),
                    'nationality': service_data.get('nationality'),
                    'nationality_id': service_data.get('nationalityId'),
                    'invoice_id': service_data.get('invoiceId'),
                    'invoice_status': service_data.get('invoiceStatus'),
                    'approval_status': service_data.get('approvalStatus'),
                    'invoice_date': invoice_date,
                    'invoice_date_timestamp': str(invoice_timestamp) if invoice_timestamp else '',
                    'total': service_data.get('total', 0.0),
                    'balance': service_data.get('balance', 0.0),
                    'payment_mode': service_data.get('paymentMode'),
                    'payment_type': service_data.get('paymentType'),
                    'branch': service_data.get('branch'),
                    'visited_branch': service_data.get('visitedBranch'),
                    'department': service_data.get('department'),
                    'visit_no': service_data.get('visitNo'),
                    'insurance_company': service_data.get('insuranceCompany'),
                    'insurance_tpa': service_data.get('insuranceTPA'),
                    'company_id': service_data.get('companyId'),
                    'service_items': service_items_html,
                    'description': f"Rejected service for patient {service_data.get('patientName')} - Invoice: {service_data.get('invoiceId')}",
                }
                
                try:
                    # Use savepoint to isolate errors and prevent transaction abort
                    with self.env.cr.savepoint():
                        # Create the record
                        record = self.create(record_data)
                        created_count += 1
                        
                        # Create CRM lead
                        lead = record.create_crm_lead()
                        if lead:
                            lead_count += 1
                            record.crm_lead_id = lead.id
                            record.lead_created = True
                        
                        _logger.info(f"Created record for invoice {service_data.get('invoiceId')}")
                    
                except Exception as e:
                    _logger.exception("Error creating record for invoice %s: %s", service_data.get('invoiceId'), str(e))
                    # Continue with next record instead of failing completely
                    # The savepoint ensures the transaction is not aborted
                    continue
            
            _logger.info(f"Processed {created_count} records and created {lead_count} CRM leads")
            return {
                'records_created': created_count,
                'leads_created': lead_count
            }
            
        except Exception as e:
            _logger.error(f"Error processing rejected services: {str(e)}", exc_info=True)
            return {
                'records_created': 0,
                'leads_created': 0,
                'error': str(e)
            }
    
    @api.model
    def _format_items_as_html_table(self, items_data):
        """
        Format items from API response as HTML table
        Can be called from model or instance context
        """
        if not items_data:
            return ''
        
        try:
            # Parse JSON if it's a string
            if isinstance(items_data, str):
                items = json.loads(items_data)
            else:
                items = items_data
            
            if not items or not isinstance(items, list):
                return ''
            
            # Build HTML table
            html = '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">'
            html += '<thead><tr style="background-color: #f0f0f0;">'
            html += '<th>Service Name</th>'
            html += '<th>Service Type</th>'
            html += '<th>Qty</th>'
            html += '<th>Price</th>'
            html += '<th>Gross Amount</th>'
            html += '<th>Discount Amount</th>'
            html += '<th>Discount %</th>'
            html += '<th>Sub Total</th>'
            html += '<th>VAT</th>'
            html += '<th>Total</th>'
            html += '<th>Policy Name</th>'
            html += '<th>Department</th>'
            html += '<th>Status</th>'
            html += '<th>Tooth No</th>'
            html += '<th>Category</th>'
            html += '</tr></thead><tbody>'
            
            for item in items:
                html += '<tr>'
                html += f'<td>{self._escape_html(item.get("serviceName", ""))}</td>'
                html += f'<td>{self._escape_html(item.get("serviceType", ""))}</td>'
                html += f'<td>{item.get("qty", 0)}</td>'
                html += f'<td>{item.get("price", 0.0)}</td>'
                html += f'<td>{item.get("grossAmt", 0.0)}</td>'
                html += f'<td>{item.get("discountAmt", 0.0)}</td>'
                html += f'<td>{item.get("discountPercentage", 0.0)}</td>'
                html += f'<td>{item.get("subTotal", 0.0)}</td>'
                html += f'<td>{item.get("vat", 0.0)}</td>'
                html += f'<td>{item.get("total", 0.0)}</td>'
                html += f'<td>{self._escape_html(item.get("policyName", ""))}</td>'
                html += f'<td>{self._escape_html(item.get("department", ""))}</td>'
                html += f'<td>{self._escape_html(item.get("status", ""))}</td>'
                html += f'<td>{self._escape_html(item.get("toothNo", "") or "")}</td>'
                html += f'<td>{self._escape_html(item.get("category", "") or "")}</td>'
                html += '</tr>'
            
            html += '</tbody></table>'
            return html
            
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            _logger.warning("Error formatting items as HTML table: %s", str(e))
            return ''
    
    @api.model
    def _escape_html(self, value):
        """
        Escape HTML special characters
        """
        if value is None:
            return ''
        value_str = str(value)
        return (value_str.replace('&', '&amp;')
                        .replace('<', '&lt;')
                        .replace('>', '&gt;')
                        .replace('"', '&quot;')
                        .replace("'", '&#x27;'))
    
    def create_crm_lead(self):
        """
        Create a CRM lead from the rejected service record
        """
        try:
            # Get UTM source for rejected services
            source = self.env['utm.source'].search([('id', '=',87)], limit=1)
            if not source:
                source = self.env['utm.source'].create({
                    'name': 'Missed Invoice'
                })
            # Search for branch using API branch value
            branch_record = False
            if self.branch:
                branch_record = self.env['clinizone.branch'].search([('name', 'ilike', self.branch)], limit=1)
                if not branch_record:
                    _logger.warning("Branch '%s' not found in clinizone.branch for invoice %s", self.branch, self.invoice_id)
            
            # Get or create campaign
            campaign = self.env['utm.campaign'].search([('name', '=', 'Rejected Services Follow-up')], limit=1)
            if not campaign:
                campaign = self.env['utm.campaign'].create({
                    'name': 'Rejected Services Follow-up'
                })
            
            # Find the "New" stage for opportunities
            new_stage = self.env['crm.stage'].search([
                ('name', '=', 'Untouched'),
                ('team_id', '=', False)
            ], limit=1)
            
            company_record = self.env.company
            if self.company_id:
                try:
                    company_candidate = self.env['res.company'].browse(int(self.company_id))
                    if company_candidate.exists():
                        company_record = company_candidate
                except (TypeError, ValueError):
                    _logger.warning("Invalid company_id %s on top.missed.invoice %s; falling back to current company",
                                    self.company_id, self.id)
            
            # Use HTML table directly from service_items (already formatted as HTML)
            services_details_html = self.service_items or ''

            # Get available fields from CRM lead model to avoid setting non-existent fields
            lead_model = self.env['crm.lead']
            available_fields = lead_model.fields_get()
            
            # Prepare lead data with only fields that exist in the model
            lead_data = {
                'name': self.patient_name,
                'partner_name': self.patient_name,
                'treating_doctor': self.consultant_name,
                'phone': self.mobile_no,
                'email_from': False,
                'type': 'opportunity',
                'topic':"Missed Invoices",
                'lead_source_id':87,
                'campaign_id': campaign.id if campaign else False,
                'stage_id': new_stage.id if new_stage else False,
                'expected_revenue': self.total or 0.0,
               # 'description': f"Rejected service for patient {self.patient_name} - Invoice: {self.invoice_id}\nConsultant: {self.consultant_name}\nDepartment: {self.department}\nBranch: {self.branch}",
                'description':services_details_html,
                'user_id': False,
                'team_id': False,  # No specific team
                'company_id':company_record.id,
                'service_detailes': services_details_html,
                'branch_id':  branch_record.id if branch_record else False,
            }
            
            
            # Create the lead inside a savepoint to prevent transaction abort
            try:
                with self.env.cr.savepoint():
                    lead = lead_model.create(lead_data)
                    _logger.info(f"Created CRM lead {lead.id} for rejected service {self.invoice_id}")
                    return lead
            except Exception as lead_error:
                _logger.exception("Error creating CRM lead for invoice %s: %s", self.invoice_id, str(lead_error))
                return False
            
        except Exception as e:
            _logger.exception("Error in create_crm_lead for invoice %s: %s", self.invoice_id, str(e))
            return False

    @api.model
    def cron_process_rejected_services(self):
        """
        Cron method to process rejected services
        Wrapped in savepoint to prevent transaction abort
        """
        # Wrap entire execution in savepoint to prevent transaction abort
        # This ensures Odoo can still update ir.cron.lastcall even if processing fails
        try:
            with self.env.cr.savepoint():
                # Get the date from the scheduled action context or use today
                from_date = datetime.now().strftime('%Y-%m-%d')
                
                _logger.info(f"Starting cron job for date: {from_date}")
                
                # Process with proper error handling
                # Errors are handled with savepoints in process_rejected_services
                result = self.process_rejected_services(from_date)
                
                if result and isinstance(result, dict):
                    _logger.info(f"Cron job completed: {result.get('records_created', 0)} records created, {result.get('leads_created', 0)} leads created")
                else:
                    _logger.info("Cron job completed with no results")
                
                return result
                
        except Exception as e:
            _logger.exception("Cron job failed: %s", str(e))
            # Don't re-raise the exception to avoid breaking the cron system
            # The savepoint ensures the transaction is not aborted
            return {
                'records_created': 0,
                'leads_created': 0,
                'error': str(e)
            }
    
    def test_cron_manually(self):
        """
        Manual test method for cron job - can be called from UI button
        """
        _logger.info("Manual cron test started")
        try:
            # Use self.env to get the model and call the cron method
            # self is the recordset from the button, but we need to call it as a model method
            result = self.env['top.missed.invoice'].cron_process_rejected_services()
            _logger.info(f"Manual cron test completed: {result}")
            
            # Return a user-friendly message
            if result and isinstance(result, dict):
                message = "Cron job completed successfully!\n"
                message += f"Records created: {result.get('records_created', 0)}\n"
                message += f"Leads created: {result.get('leads_created', 0)}"
                if result.get('error'):
                    message += f"\nError: {result.get('error')}"
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Cron Job Result',
                        'message': message,
                        'type': 'success' if not result.get('error') else 'warning',
                        'sticky': False,
                    }
                }
            return True
        except Exception as e:
            _logger.error(f"Manual cron test failed: {str(e)}", exc_info=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Cron Job Failed',
                    'message': f'Error: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }