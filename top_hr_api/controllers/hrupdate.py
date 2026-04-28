import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.osv.expression import OR
import base64
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)


def J(payload, status=200):
    return Response(json.dumps(payload, default=str),
                    status=status,
                    content_type="application/json; charset=utf-8")
class HrEmployeeAPI(http.Controller):
    def _json_response(self, payload, status=200):
        return Response(
            json.dumps(payload, default=str),
            status=status,
            content_type="application/json; charset=utf-8",
        )
    
    def _get_full_day_working_hours(self, calendar, target_date):
        """
        Get full day working hours from resource calendar, combining all periods (morning, break, afternoon).
        Returns the earliest start time, latest end time, total hours, and all periods.
        """
        from datetime import datetime, date, timedelta
        
        try:
            # Method 1: Try to get work intervals for the specific day
            work_intervals = calendar._get_work_intervals_of_day(
                start_dt=datetime.combine(target_date, datetime.min.time()),
                end_dt=datetime.combine(target_date, datetime.max.time()),
                compute_leaves=False
            )
            
            if work_intervals:
                return self._process_work_intervals(work_intervals, target_date)
            
        except Exception as e1:
            _logger.info(f"Method 1 failed: {str(e1)}")
            
            # Method 2: Try to get work intervals for the week and find the target day
            try:
                week_start = target_date - timedelta(days=target_date.weekday())
                week_end = week_start + timedelta(days=6)
                
                work_intervals = calendar._get_work_intervals(
                    start_dt=datetime.combine(week_start, datetime.min.time()),
                    end_dt=datetime.combine(week_end, datetime.max.time()),
                    compute_leaves=False
                )
                
                # Filter intervals for the target date
                target_intervals = []
                for interval in work_intervals:
                    if interval[0].date() == target_date:
                        target_intervals.append(interval)
                
                if target_intervals:
                    return self._process_work_intervals(target_intervals, target_date)
                    
            except Exception as e2:
                _logger.info(f"Method 2 failed: {str(e2)}")
                
                # Method 3: Fallback to calendar attendance records
                try:
                    if calendar.attendance_ids:
                        # Get attendance records for the target day of week
                        day_of_week = target_date.weekday()  # 0=Monday, 6=Sunday
                        day_attendances = calendar.attendance_ids.filtered(
                            lambda x: x.dayofweek == str(day_of_week)
                        )
                        
                        if day_attendances:
                            return self._process_attendance_records(day_attendances, target_date)
                            
                except Exception as e3:
                    _logger.info(f"Method 3 failed: {str(e3)}")
        
        # No working schedule found
        return {
            "work_from": None,
            "work_to": None,
            "date": target_date.isoformat(),
            "has_schedule": False,
            "total_hours": 0,
            "periods": []
        }
    
    def _process_work_intervals(self, work_intervals, target_date):
        """Process work intervals to get full day working hours."""
        from datetime import datetime
        
        periods = []
        total_hours = 0
        earliest_start = None
        latest_end = None
        
        for interval in work_intervals:
            start_time = interval[0]
            end_time = interval[1]
            
            # Calculate duration in hours
            duration = (end_time - start_time).total_seconds() / 3600
            total_hours += duration
            
            # Track earliest start and latest end
            if earliest_start is None or start_time < earliest_start:
                earliest_start = start_time
            if latest_end is None or end_time > latest_end:
                latest_end = end_time
            
            # Store period details
            periods.append({
                "start": start_time.strftime('%H:%M'),
                "end": end_time.strftime('%H:%M'),
                "duration_hours": round(duration, 2),
                "start_datetime": start_time.isoformat(),
                "end_datetime": end_time.isoformat()
            })
        
        return {
            "work_from": earliest_start.strftime('%H:%M') if earliest_start else None,
            "work_to": latest_end.strftime('%H:%M') if latest_end else None,
            "date": target_date.isoformat(),
            "has_schedule": len(periods) > 0,
            "total_hours": round(total_hours, 2),
            "periods": periods
        }
    
    def _process_attendance_records(self, attendances, target_date):
        """Process attendance records to get full day working hours."""
        from datetime import datetime
        
        periods = []
        total_hours = 0
        earliest_start = None
        latest_end = None
        
        for attendance in attendances:
            # Convert decimal hours to time
            start_hours = int(attendance.hour_from)
            start_minutes = int((attendance.hour_from - start_hours) * 60)
            end_hours = int(attendance.hour_to)
            end_minutes = int((attendance.hour_to - end_hours) * 60)
            
            # Create datetime objects for the target date
            start_time = datetime.combine(target_date, datetime.min.time().replace(
                hour=start_hours, minute=start_minutes
            ))
            end_time = datetime.combine(target_date, datetime.min.time().replace(
                hour=end_hours, minute=end_minutes
            ))
            
            # Calculate duration
            duration = (end_time - start_time).total_seconds() / 3600
            total_hours += duration
            
            # Track earliest start and latest end
            if earliest_start is None or start_time < earliest_start:
                earliest_start = start_time
            if latest_end is None or end_time > latest_end:
                latest_end = end_time
            
            # Store period details
            periods.append({
                "start": start_time.strftime('%H:%M'),
                "end": end_time.strftime('%H:%M'),
                "duration_hours": round(duration, 2),
                "start_datetime": start_time.isoformat(),
                "end_datetime": end_time.isoformat()
            })
        
        return {
            "work_from": earliest_start.strftime('%H:%M') if earliest_start else None,
            "work_to": latest_end.strftime('%H:%M') if latest_end else None,
            "date": target_date.isoformat(),
            "has_schedule": len(periods) > 0,
            "total_hours": round(total_hours, 2),
            "periods": periods
        }

    # GET /api/hr/employee?pin=...&barcode=...&fields=...&include_inactive=0&limit=0&offset=0
    # @http.route(
    #     "/api/hr/employee",
    #     type="http",
    #     auth="user",
    #     methods=["GET"],
    #     csrf=False,
    # )
    # def get_employee_by_pin_barcode(self, **kwargs):
    #     try:
    #         pin = kwargs.get("pin")
    #         id = kwargs.get("id")
    #         barcode = kwargs.get("barcode")
    #         fields_param = kwargs.get("fields")
    #         include_inactive = str(kwargs.get("include_inactive", "0")).strip() in ("1", "true", "True")
    #         limit = int(kwargs.get("limit") or 0)
    #         offset = int(kwargs.get("offset") or 0)
    #
    #         if fields_param:
    #             fields = [f.strip() for f in fields_param.split(",") if f.strip()]
    #         else:
    #             fields = [
    #                 "id", "name", "pin", "barcode", "active",
    #                 "work_email", "work_phone", "mobile_phone",
    #                 "identification_id", "job_id", "job_title",
    #                 "department_id", "company_id", "parent_id", "coach_id",
    #                 "work_location_id", "address_id",
    #                 "category_ids", "resource_calendar_id","work_location_name","user_partner_id", "user_id",
    #             ]
    #
    #         domain = []
    #         ors = []
    #         if pin:
    #             ors.append(("pin", "=", pin))
    #         if barcode:
    #             ors.append(("barcode", "=", barcode))
    #         if barcode:
    #            ors.append(("id", "=", id))
    #         if ors:
    #             domain = ["|", ors[0], ors[1]] if len(ors) == 2 else [ors[0]]
    #
    #         if not include_inactive:
    #             domain.append(("active", "=", True))
    #
    #         Employee = request.env["hr.employee"].sudo().with_context(active_test=not include_inactive)
    #         recs = Employee.search(domain, limit=limit or None, offset=offset or 0)
    #         data = recs.read(fields)
    #
    #         return self._json_response({
    #             "ok": True,
    #             "count": len(recs),
    #             "records": data,
    #         })
    #     except Exception as e:
    #         request.env.cr.rollback()
    #         return self._json_response({"ok": False, "error": str(e)}, status=500)
    @http.route(
        "/api/hr/employee",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def get_employee(self, **kwargs):
        try:
            # Inputs
            pin = (kwargs.get("pin") or "").strip()
            barcode = (kwargs.get("barcode") or "").strip()
            emp_id_raw = kwargs.get("id")
            emp_id = None
            if emp_id_raw not in (None, "", "false", "False"):
                try:
                    emp_id = int(emp_id_raw)
                except Exception:
                    return self._json_response(
                        {"ok": False, "error": "id must be an integer"},
                        status=400,
                    )

            fields_param = kwargs.get("fields")
            include_inactive = str(kwargs.get("include_inactive", "0")).strip().lower() in ("1", "true")
            limit_raw = kwargs.get("limit")
            limit = int(limit_raw) if limit_raw not in (None, "") else None
            # Treat 0 or negative as no limit
            if limit is not None and limit <= 0:
                limit = None
            offset = int(kwargs.get("offset") or 0)

            # Fields
            if fields_param:
                fields = [f.strip() for f in fields_param.split(",") if f.strip()]
            else:
                fields = [
                    "id", "name", "pin", "barcode", "active",
                    "work_email", "work_phone", "mobile_phone",
                    "identification_id", "job_id", "job_title",
                    "department_id", "company_id", "parent_id", "coach_id",
                    "work_location_id", "address_id", "geolocation_accuracy_distance",
                    "category_ids", "resource_calendar_id", "user_partner_id", "user_id",
                    # Keep custom fields here only if they exist in the database
                    # "work_location_name",
                ]

            # Domain: AND(pin==x, barcode==y) OR id==z
            domain = []
            if pin and barcode:
                # Both PIN and barcode must match
                domain = [("pin", "=", pin), ("barcode", "=", barcode)]
            elif emp_id is not None:
                # Search by ID only
                domain = [("id", "=", emp_id)]
            else:
                # If only one of pin/barcode is provided, return error
                if pin or barcode:
                    return self._json_response(
                        {"ok": False, "error": "Both pin and barcode are required for employee search"},
                        status=400,
                    )
                else:
                    return self._json_response(
                        {"ok": False, "error": "Provide either both pin and barcode, or id"},
                        status=400,
                    )

            if not include_inactive:
                domain.append(("active", "=", True))

            # Query
            Employee = request.env["hr.employee"].sudo().with_context(active_test=not include_inactive)
            recs = Employee.search(domain, limit=limit, offset=offset)
            data = recs.read(fields)

            # Process data to handle address_id based on allow_multi_attendance_location
            for record in data:
                # Check if allow_multi_attendance_location is false
                if hasattr(recs, 'allow_multi_attendance_location'):
                    employee = recs.filtered(lambda r: r.id == record['id'])
                    if employee and not employee.allow_multi_attendance_location:
                        # Return address_id as simple ID only
                        if record.get('address_id') and isinstance(record['address_id'], (list, tuple)):
                            record['address_id'] = record['address_id'][0] if record['address_id'] else None

            return self._json_response({
                "ok": True,
                "count": len(recs),
                "records": data,
            })
        except Exception as e:
            request.env.cr.rollback()
            return self._json_response({"ok": False, "error": str(e)}, status=500)

    # POST /api/hr/employees/by-pin-barcode
    # Body JSON:
    # {
    #   "pins": ["1001","1002"] | "1001,1002",
    #   "barcodes": ["EMP-01","EMP-02"] | "EMP-01,EMP-02",
    #   "fields": ["id","name","pin","barcode"],
    #   "include_inactive": false,
    #   "limit": 0,
    #   "offset": 0
    # }
    @http.route(
        "/api/hr/employees/by-pin-barcode",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def employees_by_pin_barcode(self, **kwargs):
        try:
            pins = kwargs.get("pins")
            barcodes = kwargs.get("barcodes")
            fields = kwargs.get("fields")
            include_inactive = bool(kwargs.get("include_inactive", False))
            limit = int(kwargs.get("limit") or 0)
            offset = int(kwargs.get("offset") or 0)

            if isinstance(pins, str):
                pins = [p.strip() for p in pins.split(",") if p.strip()]
            if isinstance(barcodes, str):
                barcodes = [b.strip() for b in barcodes.split(",") if b.strip()]

            if not fields:
                fields = [
                    "id", "name", "pin", "barcode", "active",
                    "work_email", "work_phone", "mobile_phone",
                    "identification_id", "job_id", "job_title",
                    "department_id", "company_id", "parent_id", "coach_id",
                    "work_location", "address_id", "work_address_id",
                    "category_ids", "resource_calendar_id", "user_id",
                ]

            domain = []
            ors = []
            if pins:
                ors.append(("pin", "in", pins))
            if barcodes:
                ors.append(("barcode", "in", barcodes))
            if ors:
                domain = ["|", ors[0], ors[1]] if len(ors) == 2 else [ors[0]]

            if not include_inactive:
                domain.append(("active", "=", True))

            Employee = request.env["hr.employee"].sudo().with_context(active_test=not include_inactive)
            recs = Employee.search(domain, limit=limit or None, offset=offset or 0)
            data = recs.read(fields)

            return {
                "ok": True,
                "count": len(recs),
                "records": data,
            }
        except Exception as e:
            request.env.cr.rollback()
            return {"ok": False, "error": str(e)}
#===================================================================================================
    # GET /api/hr/employees?id=&pin=&barcode=&fields=&active=1&limit=&offset=
    # Auth: api_key (use auth="user" if you prefer session auth)
    @http.route("/api/hr/employees", type="http", auth="user", methods=["GET"], csrf=False)
    def get_employees(self, **kw):
        try:
            env = request.env
            Employee = env["hr.employee"].sudo()

            # ---- domain ----
            dom = []
            if kw.get("id"):
                try:
                    dom.append(("id", "=", int(kw["id"])))
                except Exception:
                    return J({"ok": False, "error": "id must be integer"}, 400)
            if kw.get("pin"):
                dom.append(("pin", "=", kw["pin"]))
            if kw.get("barcode"):
                dom.append(("barcode", "=", kw["barcode"]))

            # ---- context: active flag ----
            ctx = dict(request.context or {})
            if str(kw.get("active", "1")).lower() in {"0", "false", "no"}:
                ctx["active_test"] = False

            # ---- fields ----
            req_fields = [f.strip() for f in (kw.get("fields") or "").split(",") if f.strip()]
            default_dotted = ["address_id.partner_latitude", "address_id.partner_longitude"]
            default_base = [
                "id", "name", "work_email", "work_phone", "mobile_phone",
                "pin", "barcode", "company_id", "address_id", "job_title",
                "active", "image_1920", "allow_multi_attendance_location", "resource_calendar_id"  # include photo, multi location flag, and calendar
            ]

            if req_fields:
                dotted = [f for f in req_fields if "." in f]
                base = [f for f in req_fields if "." not in f]
                for df in dotted:
                    first = df.split(".")[0]
                    if first not in base:
                        base.append(first)
                if "id" not in base:
                    base.insert(0, "id")
                for df in default_dotted:
                    if df not in dotted:
                        dotted.append(df)
                if "image_1920" not in base:
                    base.append("image_1920")
                # Always include required fields for partner assignment and work schedule logic
                if "allow_multi_attendance_location" not in base:
                    base.append("allow_multi_attendance_location")
                if "resource_calendar_id" not in base:
                    base.append("resource_calendar_id")
            else:
                base = default_base
                dotted = default_dotted

            # ---- pagination ----
            try:
                limit = int(kw.get("limit") or 80)
                offset = int(kw.get("offset") or 0)
            except Exception:
                return J({"ok": False, "error": "limit/offset must be integers"}, 400)

            recs = Employee.with_context(ctx).search(dom, limit=limit, offset=offset, order="id")

            # ---- serialize ----
            out = []
            if recs:
                base_vals = recs.read(base)
                by_id = {v["id"]: v for v in base_vals}
                for r in recs:
                    data = by_id[r.id]
                    # resolve dotted fields
                    for df in dotted:
                        cur = r
                        for i, p in enumerate(df.split(".")):
                            cur = getattr(cur, p, False)
                            if not cur:
                                data[df] = False
                                break
                            if i == len(df.split(".")) - 1:
                                data[df] = cur.ids if getattr(cur, "ids", None) else cur
                    # flat aliases
                    data["partner_latitude"] = data.get("address_id.partner_latitude")
                    data["partner_longitude"] = data.get("address_id.partner_longitude")
                    # employee image URL
                    data["image_url"] = f"/web/image/hr.employee/{r.id}/image_1920" if r.image_1920 else False
                    
                    # Add working hours for current day
                    try:
                        from datetime import datetime, date, timedelta
                        today = date.today()
                        
                        # Get employee's resource calendar
                        calendar = r.resource_calendar_id
                        _logger.info(f"Employee {r.id}: Calendar ID = {calendar.id if calendar else 'None'}, Calendar Name = {calendar.name if calendar else 'None'}")
                        if calendar:
                            # Get full day working hours (combining all periods)
                            work_schedule_data = self._get_full_day_working_hours(calendar, today)
                            
                            data["work_schedule"] = work_schedule_data
                            _logger.info(f"Employee {r.id}: Full day work schedule = {work_schedule_data}")
                        else:
                            # No calendar assigned
                            data["work_schedule"] = {
                                "work_from": None,
                                "work_to": None,
                                "date": today.isoformat(),
                                "has_schedule": False,
                                "total_hours": 0,
                                "periods": []
                            }
                    except Exception as e:
                        _logger.warning(f"Error getting work schedule for employee {r.id}: {str(e)}")
                        data["work_schedule"] = {
                            "work_from": None,
                            "work_to": None,
                            "date": date.today().isoformat(),
                            "has_schedule": False,
                            "total_hours": 0,
                            "periods": []
                        }
                    
                    # Add Partner Assignment data based on allow_multi_attendance_location setting
                    address_id_raw = data.get("address_id")
                    # Extract ID from tuple format [id, display_name] that Odoo returns for Many2one fields
                    address_id = address_id_raw[0] if isinstance(address_id_raw, (list, tuple)) and len(address_id_raw) > 0 else address_id_raw
                    allow_multi = getattr(r, 'allow_multi_attendance_location', False)
                    
                    # Debug: Log the extracted values
                    _logger.info(f"Employee {r.id}: address_id_raw={address_id_raw}, extracted_address_id={address_id}, allow_multi={allow_multi}")
                    
                    if address_id:
                        try:
                            # Validate parent partner exists (same as partner_assignment.py)
                            parent_partner = env["res.partner"].browse(address_id)
                            if not parent_partner.exists():
                                data["partner_assignments"] = []
                                data["partner_assignments_count"] = 0
                            else:
                                if allow_multi:
                                    # Multi location enabled: Get all partner assignments under the address_id (parent partner)
                                    partner_assignments = env["res.partner"].search([
                                        ("parent_id", "=", address_id),
                                        ("is_company", "=", False)  # Only contacts, not companies
                                    ])
                                else:
                                    # Multi location disabled: Get only the address_id partner itself (default assignment)
                                    partner_assignments = env["res.partner"].search([
                                        ("id", "=", address_id)
                                    ])
                                
                                # Prepare response data (same structure as partner_assignment.py)
                                assignments_data = []
                                for partner in partner_assignments:
                                    assignment_data = {
                                        "id": partner.id,
                                        "name": partner.name,
                                        "email": partner.email or "",
                                        "phone": partner.phone or "",
                                        "mobile": partner.mobile or "",
                                        "title": partner.title.name if partner.title else "",
                                        "function": partner.function or "",
                                        "parent_partner_id": address_id,
                                        "parent_partner_name": parent_partner.name,
                                        "geolocation": {
                                            "latitude": partner.partner_latitude or 0.0,
                                            "longitude": partner.partner_longitude or 0.0,
                                            "accuracy_distance": partner.geolocation_accuracy_distance or 0.0,
                                            "has_geolocation": bool(partner.partner_latitude and partner.partner_longitude)
                                        },
                                        "address": {
                                            "street": partner.street or "",
                                            "street2": partner.street2 or "",
                                            "city": partner.city or "",
                                            "state": partner.state_id.name if partner.state_id else "",
                                            "zip": partner.zip or "",
                                            "country": partner.country_id.name if partner.country_id else ""
                                        },
                                        "active": partner.active,
                                        "is_default_assignment": not allow_multi,  # True when multi location is disabled
                                        "create_date": partner.create_date.isoformat() if partner.create_date else "",
                                        "write_date": partner.write_date.isoformat() if partner.write_date else ""
                                    }
                                    assignments_data.append(assignment_data)
                                
                                data["partner_assignments"] = assignments_data
                                data["partner_assignments_count"] = len(assignments_data)
                                data["has_geolocation_count"] = len([p for p in partner_assignments if p.partner_latitude and p.partner_longitude])
                            
                        except Exception as e:
                            _logger.warning(f"Error getting partner assignments for employee {r.id}: {str(e)}")
                            data["partner_assignments"] = []
                            data["partner_assignments_count"] = 0
                            data["has_geolocation_count"] = 0
                    else:
                        data["partner_assignments"] = []
                        data["partner_assignments_count"] = 0
                        data["has_geolocation_count"] = 0
                    
                    out.append(data)

            if kw.get("id"):
                if not out:
                    return J({"ok": False, "error": "Employee not found"}, 404)
                return J({"ok": True, "record": out[0]})

            return J({"ok": True, "count": len(out), "records": out})
        except Exception as e:
            return J({"ok": False, "error": str(e)}, 500)