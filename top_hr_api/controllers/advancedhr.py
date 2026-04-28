import json
import base64
import mimetypes
import magic
import logging
from odoo import http, fields, exceptions
from odoo.http import request, Response

from odoo.http import request
from datetime import datetime
from collections import defaultdict  # Make sure to import defaultdict
from odoo.http import request, Response
from odoo.exceptions import UserError
from markupsafe import Markup

_logger = logging.getLogger(__name__)

def error_response(error, msg):
    return {
        "jsonrpc": "2.0",
        "id": None,
        "error": {
            "code": 200,
            "message": msg,
            "data": {
                "name": str(error),
                "debug": "",
                "message": msg,
                "arguments": list(error.args),
                "exception_type": type(error).__name__
            }
        }
    }

def post_map_link(record, latitude, longitude, address):
        link = f"https://maps.google.com/maps?q={latitude},{longitude}&z=18"
        map_link = f'<a href="{link}" target="_blank" rel="noreferrer noopener">{link}   </a>'
        record.message_post(
            body=Markup(map_link),  # Directly using the map link without wrapping in any additional tags
            subtype_xmlid="mail.mt_note",
            message_type='comment'  # Ensuring the message is treated as a comment
        )  

def create_attachment(model_name, record_id, base64_content, original_filename=None):
    """
    Creates an attachment for a given model and record, using the original filename if available.

    :param model_name: The name of the model (e.g., 'account.payment')
    :param record_id: The ID of the record to which the attachment will be linked
    :param base64_content: The base64-encoded content of the attachment
    :param original_filename: (Optional) The original filename of the attachment
    :return: The created attachment record
    """
    # Check if the base64 content is provided
    if not base64_content:
        raise exceptions.ValidationError("No attachment content provided")

    # Decode the base64 content to ensure it is valid
    try:
        decoded_content = base64.b64decode(base64_content, validate=True)
    except Exception:
        raise exceptions.ValidationError("Invalid base64-encoded content")

    # Use `magic` to detect the file type and determine the extension
    file_type = magic.from_buffer(decoded_content, mime=True)
    extension = mimetypes.guess_extension(file_type)

    # Default to .bin if the extension is not found
    if not extension:
        extension = '.bin'

    # Use the original filename if provided; otherwise, generate a default name
    if original_filename:
        attachment_name_with_extension = original_filename
    else:
        attachment_name_with_extension = f'Attachment_{model_name}_{record_id}{extension}'

    # Create the attachment
    attachment = request.env['ir.attachment'].create({
        'name': attachment_name_with_extension,
        'type': 'binary',
        'datas': base64_content,  # Assuming this is the base64-encoded content
        'res_model': model_name,
        'res_id': record_id,
        'description': 'Attachment added programmatically',
        'mimetype': file_type,
    })

    # Post a message in Chatter with the attachment (optional, if applicable)
    record = request.env[model_name].browse(record_id)
    if record:
        record.message_post(
            body="An attachment has been added.",
            attachment_ids=[attachment.id],
        )

    return attachment



class AdvancedHR(http.Controller):

    @http.route('/knowledge/workspace_articles', type='http', auth='public', methods=['GET'], csrf=False)
    def get_workspace_articles(self, **kwargs):
        """
        Fetch all articles in the "workspace" category that are not marked for deletion, 
        including details like ID, name, creation date, and icon. Results are ordered by ID descending.

        :param kwargs: Optionally include 'limit' and 'offset' for pagination.
        :return: JSON response with article details or error message.
        """
        try:
            # Fetch pagination parameters from the request
            limit = int(kwargs.get('limit', 10))  # Default limit is 10
            offset = int(kwargs.get('offset', 0))  # Default offset is 0

            # Query to fetch articles matching the criteria
            articles = request.env['knowledge.article'].sudo().search(
                [("category", "=", "workspace"),("is_user_favorite", "=", True)],
                order='id desc',
                limit=limit,
                offset=offset
            )

            # Prepare the response data
            data = [
                {
                    'id': article.id,
                    'name': article.name or 'Unnamed Article',
                    'date': article.create_date.strftime('%Y-%m-%d %H:%M:%S') if article.create_date else None,
                    'icon': article.icon,
                    'is_article_item':article.is_article_item,
                    'category': article.category
                }
                for article in articles
            ]

            # Return JSON response
            return http.Response(
                json.dumps({"success": True, "articles": data}),
                content_type='application/json',
                status=200
            )

        except Exception as e:
            # Log the error for debugging purposes
            _logger.error(f"Error fetching workspace articles: {e}")

            # Return error response
            return http.Response(
                json.dumps({"error": f"An error occurred: {str(e)}"}),
                content_type='application/json',
                status=500
            )


    @http.route('/knowledge/article_detail', type='http', auth='public', methods=['GET'], csrf=False)
    def get_article_detail(self, **kwargs):
        """
        Fetch article details by the provided ID.
        :param article_id: ID of the article.
        :return: JSON response with article details.
        """
        # Extract article_id from the query string
        article_id = kwargs.get('article_id')

        # Check if article_id is provided
        if not article_id:
            return http.Response(
                json.dumps({"error": "Article ID is required"}),
                content_type="application/json",
                status=400
            )

        try:
            # Fetch the article by ID
            article = request.env['knowledge.article'].sudo().browse(int(article_id))

            # Check if the article exists
            if not article.exists():
                return http.Response(
                    json.dumps({"error": "Article not found"}),
                    content_type="application/json",
                    status=404
                )

            # Prepare response data
            data = {
                'id': article.id,
                'name': article.name,
                'content': article.body,  # Adjust to the actual field for content in your model
                'category': article.category,
                'created_date': article.create_date.strftime('%Y-%m-%d %H:%M:%S') if article.create_date else None,
                'create_user_name': article.create_user_name if hasattr(article, 'create_user_name') else "Unknown",
            }

            # Return success response
            return http.Response(
                json.dumps({"success": True, "article": data}),
                content_type="application/json",
                status=200
            )

        except Exception as e:
            # Return error response for unexpected errors
            return http.Response(
                json.dumps({"error": f"An error occurred: {str(e)}"}),
                content_type="application/json",
                status=500
            )
#####################################################################################################################            
    @http.route('/api/hr_excuse/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_hr_excuse(self):
        """
        API route to create a record in the hr.excuse model.
        """
        try:
            # Get the raw JSON payload
            raw_data = request.httprequest.get_data()
            data = json.loads(raw_data)

            # Log the received payload for debugging
            _logger.info(f"Received payload: {data}")

            # Extract parameters from the payload
            employee_id = data.get('employee_id')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            comment = data.get('comment')

            # Validate mandatory fields
            if not employee_id or not start_date or not end_date:
                return {
                    "success": False,
                    "message": "Missing required fields: 'employee_id', 'start_date', and 'end_date' are mandatory."
                }

            # Parse dates and format them to 'YYYY-MM-DD HH:MM:SS'
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d-%H-%M')
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d-%H-%M')

                # Convert to string format 'YYYY-MM-DD HH:MM:SS' for PostgreSQL
                formatted_start_date = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
                formatted_end_date = end_datetime.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid date format. Use 'YYYY-MM-DD-HH-MM'."
                }

            if start_datetime >= end_datetime:
                return {
                    "success": False,
                    "message": "End date must be after the start date."
                }

            # Calculate the period in hours
            period_in_hours = (end_datetime - start_datetime).total_seconds() / 3600

            # Create the record in the hr.excuse model
            excuse = request.env['hr.excuse'].sudo().create({
                'employee_id': employee_id,
                'start_date': formatted_start_date,
                'end_date': formatted_end_date,
                'comment': comment,
                'state': 'draft',  # Default value for state
                'period': period_in_hours,  # Automatically calculated
            })

            return {
                "success": True,
                "message": "Excuse record created successfully.",
                "data": {
                    "id": excuse.id,
                    "period": period_in_hours,
                },
            }
        except Exception as e:
            # Log the error for debugging
            _logger.error(f"Error creating hr.excuse record: {str(e)}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}",
            }

 
    @http.route('/api/hr_excuse/get_by_employee', type='http', auth='public', methods=['GET'], csrf=False)
    def get_excuses_by_employee(self, **kwargs):
        """
        API route to retrieve all Excuse records for a specific employee_id using query parameters.
        """
        try:
            # Extract employee_id from query parameters
            employee_id = kwargs.get('employee_id')

            # Validate input
            if not employee_id:
                return request.make_response(
                    json.dumps({
                        "success": False,
                        "message": "Missing required field: 'employee_id'."
                    }),
                    headers={'Content-Type': 'application/json'}
                )

            # Fetch records from hr.excuse model
            excuses = request.env['hr.excuse'].sudo().search([('employee_id', '=', int(employee_id))])

            # Prepare the result
            excuse_list = []
            for excuse in excuses:
                excuse_list.append({
                    'id': excuse.id,
                    'start_date': excuse.start_date.strftime('%Y-%m-%d %H:%M:%S') if excuse.start_date else None,
                    'end_date': excuse.end_date.strftime('%Y-%m-%d %H:%M:%S') if excuse.end_date else None,
                    'period': excuse.period,
                    'state': excuse.state,
                    'comment': excuse.comment,
                })

            return request.make_response(
                json.dumps({
                    "success": True,
                    "message": "Excuse records retrieved successfully.",
                    "data": excuse_list,
                }),
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            # Log the error for debugging
            _logger.error(f"Error retrieving excuses: {str(e)}")
            return request.make_response(
                json.dumps({
                    "success": False,
                    "message": f"An error occurred: {str(e)}",
                }),
                headers={'Content-Type': 'application/json'}
            )
            
#######################################loans####################################################

    @http.route('/api/hr_loan/create', type='http', auth='public', methods=['POST'], csrf=False)
    def create_loan(self, **kwargs):
        """
        API route to create a loan record in the hr.loan model.
        """
        try:
            # Parse the raw JSON payload
            raw_data = request.httprequest.get_data()
            data = json.loads(raw_data.decode('utf-8'))

            # Log the received payload for debugging
            _logger.info(f"Received payload: {data}")

            # Extract parameters
            employee_id = data.get('employee_id')
            amount = data.get('amount')
            date = data.get('date')  # Provided loan date
            start_date = data.get('start_date')  # New start_date field
            reason = data.get('reason')

            # Validate mandatory fields
            missing_fields = []
            if not employee_id:
                missing_fields.append("employee_id")
            if not amount:
                missing_fields.append("amount")
            if not date:
                missing_fields.append("date")
            if not start_date:
                missing_fields.append("start_date")
            if not reason:
                missing_fields.append("reason")

            if missing_fields:
                return request.make_response(
                    json.dumps({
                        "success": False,
                        "message": f"Missing required fields: {', '.join(missing_fields)}."
                    }),
                    headers={'Content-Type': 'application/json'}
                )

            # Parse and validate dates
            try:
                loan_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
                loan_start_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                return request.make_response(
                    json.dumps({
                        "success": False,
                        "message": "Invalid date format. Use 'YYYY-MM-DD'."
                    }),
                    headers={'Content-Type': 'application/json'}
                )

            # Create the record in the hr.loan model
            loan = request.env['hr.loan'].sudo().create({
                'employee_id': employee_id,
                'amount': amount,
                'date': loan_date,
                'start_date': loan_start_date,  # Include start_date
                'reason': reason,
            })

            return request.make_response(
                json.dumps({
                    "success": True,
                    "message": "Loan record created successfully.",
                    "data": {
                        "id": loan.id,
                        "employee_id": loan.employee_id.id,
                        "amount": loan.amount,
                        "date": loan.date.strftime('%Y-%m-%d') if loan.date else None,  # Convert date to string
                        "start_date": loan.start_date.strftime('%Y-%m-%d') if loan.start_date else None,  # Convert date to string
                        "reason": loan.reason,
                    },
                }),
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            _logger.error(f"Error creating hr.loan record: {str(e)}")
            return request.make_response(
                json.dumps({
                    "success": False,
                    "message": f"An error occurred: {str(e)}",
                }),
                headers={'Content-Type': 'application/json'}
            )
            
            ######################################################all loans #######################
    @http.route('/api/hr_loan/get_by_employee', type='http', auth='public', methods=['GET'], csrf=False)
    def get_loans_by_employee(self, **kwargs):
        """
        API route to retrieve all loans for a specific employee_id.
        """
        try:
            # Extract employee_id from query parameters
            employee_id = kwargs.get('employee_id')

            # Validate employee_id
            if not employee_id:
                return request.make_response(
                    json.dumps({
                        "success": False,
                        "message": "Missing required field: 'employee_id'."
                    }),
                    headers={'Content-Type': 'application/json'}
                )

            # Fetch all loans for the specified employee_id
            loans = request.env['hr.loan'].sudo().search([('employee_id', '=', int(employee_id))])

            # Prepare the response data
            loan_list = []
            for loan in loans:
                loan_list.append({
                    'id': loan.id,
                    'employee_id': loan.employee_id.id,
                    'amount': loan.amount,
                    'date': loan.date.strftime('%Y-%m-%d') if loan.date else None,
                    'start_date': loan.start_date.strftime('%Y-%m-%d') if loan.start_date else None,
                    'reason': loan.reason,
                    'state': loan.state  # Include state if applicable
                })

            return request.make_response(
                json.dumps({
                    "success": True,
                    "message": "Loans retrieved successfully.",
                    "data": loan_list,
                }),
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            _logger.error(f"Error retrieving loans: {str(e)}")
            return request.make_response(
                json.dumps({
                    "success": False,
                    "message": f"An error occurred: {str(e)}",
                }),
                headers={'Content-Type': 'application/json'}
            )
#######################################################################

    @http.route('/api/resignation_request/create', type='http', auth='public', methods=['POST'], csrf=False)
    def create_resignation_request(self, **kwargs):
        try:
            # Extract raw JSON payload
            raw_data = request.httprequest.get_data()
            data = json.loads(raw_data.decode('utf-8'))

            # Required fields
            employee_id = data.get('employee_id')
            last_working_date = data.get('last_working_date')
            resignation_type = data.get('resignation_type')
            transaction_date = data.get('transaction_date')
            resignation_reasons = data.get('resignation_reasons')

            # Map boolean exit_interview_required to selection options ('yes' or 'no')
            exit_interview_required = data.get('exit_interview_required', False)
            if isinstance(exit_interview_required, bool):
                exit_interview_required = 'yes' if exit_interview_required else 'no'

            # Optional field
            final_iqama = data.get('final_iqama', False)

            # Validate required fields
            missing_fields = []
            if not employee_id:
                missing_fields.append("employee_id")
            if not last_working_date:
                missing_fields.append("last_working_date")
            if not resignation_type:
                missing_fields.append("resignation_type")
            if not transaction_date:
                missing_fields.append("transaction_date")
            if not resignation_reasons:
                missing_fields.append("resignation_reasons")

            if missing_fields:
                return request.make_response(
                    json.dumps({
                        "success": False,
                        "message": f"Missing required fields: {', '.join(missing_fields)}."
                    }),
                    headers={'Content-Type': 'application/json'}
                )

            # Parse date fields
            try:
                parsed_last_working_date = datetime.strptime(last_working_date, '%Y-%m-%d').strftime('%Y-%m-%d')
                parsed_transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                return request.make_response(
                    json.dumps({
                        "success": False,
                        "message": "Invalid date format. Use 'YYYY-MM-DD'."
                    }),
                    headers={'Content-Type': 'application/json'}
                )

            # Create the resignation request record
            resignation_request = request.env['resignation.request'].sudo().create({
                'employee_id': employee_id,
                'last_working_date': parsed_last_working_date,
                'resignation_type': resignation_type,
                'transaction_date': parsed_transaction_date,
                'resignation_reasons': resignation_reasons,
                'exit_interview_required': exit_interview_required,
                'final_iqama': final_iqama,
            })

            # Convert datetime fields to string for JSON serialization
            resignation_data = {
                "id": resignation_request.id,
                "employee_id": resignation_request.employee_id.id,
                "last_working_date": str(resignation_request.last_working_date),  # Convert to string
                "resignation_type": resignation_request.resignation_type,
                "transaction_date": str(resignation_request.transaction_date),  # Convert to string
                "resignation_reasons": resignation_request.resignation_reasons,
                "exit_interview_required": resignation_request.exit_interview_required,
                "final_iqama": resignation_request.final_iqama,
            }

            # Return a success response
            return request.make_response(
                json.dumps({
                    "success": True,
                    "message": "Resignation request created successfully.",
                    "data": resignation_data,
                }),
                headers={'Content-Type': 'application/json'}
            )
        except Exception as e:
            _logger.error(f"Error creating resignation request: {str(e)}")
            return request.make_response(
                json.dumps({
                    "success": False,
                    "message": f"An error occurred: {str(e)}",
                }),
                headers={'Content-Type': 'application/json'}
            )
##############################################################detailes 
    @http.route('/api/resignation_request/<int:resignation_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_resignation_request(self, resignation_id, **kwargs):
        try:
            # Retrieve the resignation request by ID
            resignation_request = request.env['resignation.request'].sudo().browse(resignation_id)

            # Check if the resignation request exists
            if not resignation_request:
                return request.make_response(
                    json.dumps({
                        "success": False,
                        "message": f"Resignation request with ID {resignation_id} not found."
                    }),
                    headers={'Content-Type': 'application/json'}
                )

            # Convert date fields to string for JSON serialization
            resignation_data = {
                "id": resignation_request.id,
                "employee_id": resignation_request.employee_id.id,
                "last_working_date": str(resignation_request.last_working_date),  # Convert to string
                "resignation_type": resignation_request.resignation_type,
                "transaction_date": str(resignation_request.transaction_date),  # Convert to string
                "resignation_reasons": resignation_request.resignation_reasons,
                "exit_interview_required": resignation_request.exit_interview_required,
                "final_iqama": resignation_request.final_iqama,
                "state":resignation_request.state
            }

            # Return a success response with resignation data
            return request.make_response(
                json.dumps({
                    "success": True,
                    "message": "Resignation request details retrieved successfully.",
                    "data": resignation_data,
                }),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            _logger.error(f"Error retrieving resignation request: {str(e)}")
            return request.make_response(
                json.dumps({
                    "success": False,
                    "message": f"An error occurred: {str(e)}",
                }),
                headers={'Content-Type': 'application/json'}
            )
####################################business trip 

    @http.route('/api/business_trip_request/create', type='http', auth='public', methods=['POST'], csrf=False)
    def create_business_trip_request(self, **kwargs):
        try:
            # Extract raw JSON payload
            raw_data = request.httprequest.get_data()
            data = json.loads(raw_data.decode('utf-8'))

            # Required fields
            employee_id = data.get('employee_id')
            date_from = data.get('date_from')
            description = data.get('description')

            # Optional fields
            date_to = data.get('date_to')
            destination_from = data.get('destination_from')
            destination_to = data.get('destination_to')
            request_travel_air_ticket = data.get('request_travel_air_ticket', False)
            request_company_car = data.get('request_company_car', False)
            request_accommodation = data.get('request_accommodation', False)
            request_internal_transport = data.get('request_internal_transport', False)
            attachment = data.get('attachment', None)
            attachmentname = data.get('filename')

            # Validate required fields
            missing_fields = []
            if not employee_id:
                missing_fields.append("employee_id")
            if not date_from:
                missing_fields.append("date_from")
            if not description:
                missing_fields.append("description")

            if missing_fields:
                return request.make_response(
                    json.dumps({
                        "success": False,
                        "message": f"Missing required fields: {', '.join(missing_fields)}."
                    }),
                    headers={'Content-Type': 'application/json'}
                )

            # Parse date fields if they are present
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else None
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date() if date_to else None

            # Create the business trip request record
            business_trip_request = request.env['business.trip.request'].sudo().create({
                'employee_id': employee_id,
                'date_from': date_from,
                'date_to': date_to,
                'destination_from': destination_from,
                'destination_to': destination_to,
                'request_travel_air_ticket': request_travel_air_ticket,
                'request_company_car': request_company_car,
                'request_accommodation': request_accommodation,
                'request_internal_transport': request_internal_transport,
                'description': description,
            })

            # Handle attachment if provided
            if attachment:
               create_attachment('business.trip.request', business_trip_request.id, attachment, attachmentname)

            # Convert date fields to string format (YYYY-MM-DD)
            date_from_str = business_trip_request.date_from.strftime('%Y-%m-%d') if business_trip_request.date_from else None
            date_to_str = business_trip_request.date_to.strftime('%Y-%m-%d') if business_trip_request.date_to else None

            # Return a success response with the created data
            return request.make_response(
                json.dumps({
                    "success": True,
                    "message": "Business trip request created successfully.",
                    "data": {
                        "id": business_trip_request.id,
                        "employee_id": business_trip_request.employee_id.id,
                        "date_from": date_from_str,
                        "date_to": date_to_str,
                        "destination_from": business_trip_request.destination_from,
                        "destination_to": business_trip_request.destination_to,
                        "request_travel_air_ticket": business_trip_request.request_travel_air_ticket,
                        "request_company_car": business_trip_request.request_company_car,
                        "request_accommodation": business_trip_request.request_accommodation,
                        "request_internal_transport": business_trip_request.request_internal_transport,
                        "description": business_trip_request.description,
                    },
                }),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            _logger.error(f"Error creating business trip request: {str(e)}")
            return request.make_response(
                json.dumps({
                    "success": False,
                    "message": f"An error occurred: {str(e)}",
                }),
                headers={'Content-Type': 'application/json'}
            )

###################################all business trip

    @http.route('/api/business_trip_request/get_by_employee', type='http', auth='public', methods=['GET'], csrf=False)
    def get_business_trip_requests_by_employee(self, employee_id, **kwargs):
        try:
            # Retrieve the employee's business trip requests
            trip_requests = request.env['business.trip.request'].sudo().search([('employee_id', '=', int(employee_id))])

            if not trip_requests:
                return request.make_response(
                    json.dumps({
                        "success": False,
                        "message": "No business trip requests found for this employee.",
                    }),
                    headers={'Content-Type': 'application/json'}
                )

            # Prepare the response data
            trip_data = []
            for trip in trip_requests:
                trip_data.append({
                    "id": trip.id,
                    "employee_id": trip.employee_id.id,
                    "date_from": trip.date_from.strftime('%Y-%m-%d') if trip.date_from else None,
                    "date_to": trip.date_to.strftime('%Y-%m-%d') if trip.date_to else None,
                    "destination_from": trip.destination_from,
                    "destination_to": trip.destination_to,
                    "request_travel_air_ticket": trip.request_travel_air_ticket,
                    "request_company_car": trip.request_company_car,
                    "request_accommodation": trip.request_accommodation,
                    "request_internal_transport": trip.request_internal_transport,
                    "description": trip.description,
                    "state": trip.state,
                })

            return request.make_response(
                json.dumps({
                    "success": True,
                    "message": "Business trip requests retrieved successfully.",
                    "data": trip_data
                }),
                headers={'Content-Type': 'application/json'}
            )

        except Exception as e:
            return request.make_response(
                json.dumps({
                    "success": False,
                    "message": f"An error occurred: {str(e)}",
                }),
                headers={'Content-Type': 'application/json'}
            )
###################################################################################missed punch

    @http.route('/api/project/task/create', type='json', auth='user', methods=['POST'])
    def create_project_task(self, **kwargs):
        # Log the raw request data
        try:
            json_data = request.httprequest.get_json()  # Use get_json() to fetch the payload
            _logger.info("Received request data: %s", json_data)
        except Exception as e:
            _logger.error("Error reading request data: %s", e)
            return {"error": "Failed to read request data."}
        
        # Check if the request contains any data
        if not json_data:
            return {"error": "No data provided."}
        
        # Extract task details from the request payload
        title = json_data.get('title', None)
        description = json_data.get('description', '')
        user_ids = json_data.get('user_ids', [])
        stage_id = json_data.get('stage_id', None)
        deadline = json_data.get('deadline', None)
        attachment = json_data.get('attachment',None)
        attachmentname = json_data.get('attachment')

        # Validate if the required fields are present
        if not title:
            return {"error": "Title is required."}
        
        
        # Fetch the project to check if it is private

        try:
            # Create the task using the ORM
            task = request.env['project.task'].sudo().create({
                'name': title,
                'description': description,
                'user_ids': [(6, 0, user_ids)],  # Use 6, 0, user_ids to assign users
                'stage_id': stage_id,
                'date_deadline': deadline,
            })
            if attachment:
               create_attachment('project.task', task.id, attachment, attachmentname)

            return {
                "message": "Task created successfully in private project",
                "task_id": task.id,
                "task_name": task.name,
            }

        except Exception as e:
            _logger.error("Error creating task: %s", e)
            return {"error": str(e)}
#############################################################################################
    # @http.route('/api/project/tasks/by_user', type='http', auth='user', methods=['GET'])
    # def get_tasks_by_user(self, **kwargs):
    #     # Get user ID from the query parameters
    #     user_id = request.params.get('user_id')

    #     # Validate if user_id is provided
    #     if not user_id:
    #         return request.make_response(
    #             '{"error": "User ID is required."}', 
    #             headers={'Content-Type': 'application/json'}, 
    #             status=400
    #         )
        
    #     try:
    #         user_id = int(user_id)
    #     except ValueError:
    #         return request.make_response(
    #             '{"error": "User ID must be an integer."}', 
    #             headers={'Content-Type': 'application/json'}, 
    #             status=400
    #         )

    #     # Check if the user exists
    #     user = request.env['res.users'].sudo().browse(user_id)
    #     if not user.exists():
    #         return request.make_response(
    #             '{"error": "User not found."}', 
    #             headers={'Content-Type': 'application/json'}, 
    #             status=404
    #         )

    #     # Get all tasks assigned to the user
    #     tasks = request.env['project.task'].sudo().search([('user_ids', 'in', user_id)])

    #     # Prepare the response
    #     task_data = []
    #     for task in tasks:
    #         task_data.append({
    #             'task_id': task.id,
    #             'task_name': task.name,
    #             'description': task.description,
    #             'deadline': task.date_deadline.strftime('%Y-%m-%d %H:%M:%S') if task.date_deadline else None,  # Format datetime
    #             'stage_id':task.personal_stage_id.id,
    #             'stage_name': task.personal_stage_type_id.name,
    #             'state':task.state
    #         })

    #     response = {
    #         "message": "Tasks retrieved successfully",
    #         "tasks": task_data
    #     }

    #     return request.make_response(
    #         http.json.dumps(response), 
    #         headers={'Content-Type': 'application/json'}, 
    #         status=200
    #     )
    
    @http.route('/api/project/tasks/by_user', type='http', auth='user', methods=['GET'])
    def get_tasks_by_user(self, **kwargs):
        # Get user ID and state from the query parameters
        user_id = request.params.get('user_id')
        state = request.params.get('state')

        # Validate if user_id is provided
        if not user_id:
            return request.make_response(
                json.dumps({"error": "User ID is required."}), 
                headers={'Content-Type': 'application/json'}, 
                status=400
            )
        
        try:
            user_id = int(user_id)
        except ValueError:
            return request.make_response(
                json.dumps({"error": "User ID must be an integer."}), 
                headers={'Content-Type': 'application/json'}, 
                status=400
            )

        # Check if the user exists
        user = request.env['res.users'].sudo().browse(user_id)
        if not user.exists():
            return request.make_response(
                json.dumps({"error": "User not found."}), 
                headers={'Content-Type': 'application/json'}, 
                status=404
            )

        # Prepare the base domain for searching tasks
        domain = [('user_ids', 'in', user_id)]

        # If state is provided, add a filter for state to the domain
        if state:
            domain.append(('state', '=', state))

        # Get all tasks assigned to the user (and filtered by state if provided), ordered by id in descending order
        tasks = request.env['project.task'].sudo().search(domain, order='id desc')

        # Prepare the response
        task_data = []
        for task in tasks:
            task_data.append({
                'task_id': task.id,
                'task_name': task.name,
                'description': task.description,
                'deadline': task.date_deadline.strftime('%Y-%m-%d %H:%M:%S') if task.date_deadline else None,  # Format datetime
                'stage_id':task.personal_stage_id.id,
                'stage_name': task.personal_stage_type_id.name,
                'state':task.state
            })

        response = {
            "message": "Tasks retrieved successfully",
            "tasks": task_data
        }

        return request.make_response(
            json.dumps(response), 
            headers={'Content-Type': 'application/json'}, 
            status=200
        )

######################################################

    @http.route('/api/project/task/update_state', type='json', auth='user', methods=['PUT'])
    def update_task_state(self, **kwargs):
        # Log the incoming request data for debugging
        _logger.info("Received request data (kwargs): %s", kwargs)
        
        # Try reading the raw request body and log it
        try:
            raw_data = request.httprequest.data
            _logger.info("Raw request body: %s", raw_data)

            # Attempt to parse the raw data as JSON
            payload = json.loads(raw_data)
            _logger.info("Parsed JSON Payload: %s", payload)
        except Exception as e:
            _logger.error("Error reading or parsing JSON payload: %s", str(e))
            return {"error": "Unable to parse JSON payload."}

        # Get task ID, state, and stage_id from the parsed payload
        task_id = payload.get('task_id')
        stage_id = payload.get('stage_id')
        state = payload.get('state')
        attachment = payload.get('attachment',None)
        attachmentname = payload.get('attachment')

        # Validate if task_id is provided
        if not task_id:
            return {"error": "Task ID is required."}

        # Check if the task exists
        task = request.env['project.task'].sudo().browse(task_id)
        if attachment:
           create_attachment('project.task', task_id, attachment, attachmentname)

        if not task.exists():
            return {"error": "Task not found."}

        # Prepare the fields to update
        values_to_update = {}

        # If state is provided, add it to the update values
        if state:
            values_to_update['state'] = state

        # If stage_id is provided, add it to the update values
        if stage_id:
            # Check if the stage exists
            stage = request.env['project.task.type'].sudo().browse(stage_id)
            if not stage.exists():
                return {"error": "Stage not found."}
            values_to_update['stage_id'] = stage_id

        # Update the task with the new values
        if values_to_update:
            task.write(values_to_update)

        # Prepare the response
        return {
            "message": "Task state updated successfully",
            "task_id": task.id,
            "new_stage_id": task.stage_id.id if task.stage_id else None,
            "new_state": task.state  # Get the updated state value from the task
        }
