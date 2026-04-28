# -*- coding: utf-8 -*-
import json
from datetime import date, datetime
from odoo import models, fields, api
from odoo.exceptions import UserError
import requests

class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.model
    def _fields_meta(self):
        """Cache fields meta to validate types & relations."""
        return self.fields_get()

    @api.model
    def _resolve_m2o_by_name(self, field_name, display_name):
        """Find an M2O by its display name without creating it."""
        if not display_name:
            return False
        fields_meta = self._fields_meta()
        f = fields_meta.get(field_name)
        if not f or f.get('type') != 'many2one':
            return False
        rel_model = f.get('relation')
        if not rel_model:
            return False
        rec = self.env[rel_model].search([('name', 'ilike', display_name)], limit=1)
        return rec.id or False

    @api.model
    def _safe_set(self, vals, field_name, value):
        """Set only if field exists and value is compatible; otherwise skip."""
        fields_meta = self._fields_meta()
        f = fields_meta.get(field_name)
        if not f:
            return
        ftype = f.get('type')
        try:
            if value in (None, False, "", []):
                # still allow explicit False for some fields
                return
            if ftype in ('char', 'text', 'html', 'selection'):
                vals[field_name] = str(value)
            elif ftype in ('integer',):
                vals[field_name] = int(value)
            elif ftype in ('float', 'monetary'):
                vals[field_name] = float(value)
            elif ftype in ('boolean',):
                # convert common truthy strings
                if isinstance(value, str):
                    vals[field_name] = value.lower() in ('1', 'true', 'yes', 'y')
                else:
                    vals[field_name] = bool(value)
            elif ftype in ('date',):
                if isinstance(value, (list, tuple)) and len(value) >= 3:
                    vals[field_name] = date(int(value[0]), int(value[1]), int(value[2]))
                elif isinstance(value, str) and value:
                    vals[field_name] = fields.Date.to_date(value)
            elif ftype in ('datetime',):
                if isinstance(value, str) and value:
                    # try parse ISO
                    # Odoo will auto convert if format acceptable
                    vals[field_name] = fields.Datetime.to_datetime(value)
                elif isinstance(value, (list, tuple)) and len(value) >= 6:
                    vals[field_name] = datetime(
                        int(value[0]), int(value[1]), int(value[2]),
                        int(value[3]), int(value[4]), int(value[5])
                    )
            elif ftype in ('many2one',):
                # If user passes string → resolve by name
                if isinstance(value, (int,)) and value > 0:
                    vals[field_name] = value
                elif isinstance(value, str):
                    m2o_id = self._resolve_m2o_by_name(field_name, value)
                    if m2o_id:
                        vals[field_name] = m2o_id
        except Exception:
            # Silently skip incompatible assignment
            return

    @api.model
    def _build_description_table(self, data_dict, mapped_keys):
        """Add leftovers as HTML table in description."""
        rows = []
        for k, v in data_dict.items():
            if k in mapped_keys:
                continue
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False, default=str)
            rows.append(f"<tr><td><b>{k}</b></td><td>{(v or '')}</td></tr>")
        if not rows:
            return ""
        return (
            "<h4>HIS Extra Fields</h4>"
            "<table border='1' style='border-collapse:collapse;width:100%'>"
            "<thead><tr><th>Field</th><th>Value</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    @api.model
    def _compose_vals_from_his(self, rec):
        """
        Map HIS record → crm.lead vals.
        Tries to allocate fields intelligently, respecting your current CRM schema.
        """
        # Common base
        vals = {}
        mapped_keys = set()

        # Identify team & stage
        team_id = self.env['crm.team'].search([('name', 'ilike', 'Sales')], limit=1).id or False
        stage_id = self.env['crm.stage'].search([('name', 'ilike', 'Untouched')], limit=1).id or False

        # Primary name
        display_name = rec.get('patientName') or rec.get('mrno') or 'Appointment'
        name = f"{display_name}"
        if rec.get('department'):
            name += f" - {rec.get('department')}"
        if rec.get('visitType'):
            name += f" - {rec.get('visitType')}"
        vals['name'] = name
        mapped_keys.update({'patientName', 'mrno', 'department', 'visitType'})

        # Basic allocations
        vals['team_id'] = team_id
        vals['stage_id'] = stage_id
        vals['type'] = 'opportunity'

        # Phone, city (char) + city_id (m2o) if possible
        self._safe_set(vals, 'phone', rec.get('mobileNo')); mapped_keys.add('mobileNo')
        self._safe_set(vals, 'city', rec.get('city')); mapped_keys.add('city')

        # If you have city_id M2O, try to link
        if 'city_id' in self._fields_meta():
            city_id = self._resolve_m2o_by_name('city_id', rec.get('city'))
            if city_id:
                vals['city_id'] = city_id

        # Company (if same id exists)
        company_id = 3 # rec.get('companyId')
        if isinstance(company_id, int) and company_id > 0 and 'company_id' in self._fields_meta():
            # Ensure company exists, otherwise skip to avoid access errors
            if self.env['res.company'].browse(company_id).exists():
                vals['company_id'] = company_id
        mapped_keys.add('companyId')

        # Lead source mapping
        # Example in your DB shows lead_source_id = "Mobile App", lead_source_level_1 = "Digital"
        booked_from = rec.get('bookedFrom')  # e.g., "PrimeCare Mobile App"
        lead_source_name = "Mobile App" if (booked_from and "mobile" in booked_from.lower()) else (booked_from or "")
        if lead_source_name:
            # Many2one: lead_source_id / lead_source_level_1_id / lead_source_level_2_id
            if 'lead_source_id' in self._fields_meta():
                src_id = self._resolve_m2o_by_name('lead_source_id', lead_source_name)
                if src_id:
                    vals['lead_source_id'] = src_id
            if 'lead_source_level_1_id' in self._fields_meta():
                lvl1_id = self._resolve_m2o_by_name('lead_source_level_1_id', 'Digital')
                if lvl1_id:
                    vals['lead_source_level_1_id'] = lvl1_id
            if 'lead_source_level_2_id' in self._fields_meta():
                lvl2_id = self._resolve_m2o_by_name('lead_source_level_2_id', 'Digital')
                if lvl2_id:
                    vals['lead_source_level_2_id'] = lvl2_id
        mapped_keys.add('bookedFrom')

        # Department / Service / Branch / Speciality
        if 'department_id' in self._fields_meta():
            dep_id = self._resolve_m2o_by_name('department_id', rec.get('department'))
            if dep_id:
                vals['department_id'] = dep_id
        mapped_keys.add('department')

        # Prefer serviceName, fallback to machineInfo.newName
        service_name = rec.get('serviceName') or (rec.get('machineInfo') or {}).get('newName')
        if 'service_id' in self._fields_meta() and service_name:
            srv_id = self._resolve_m2o_by_name('service_id', service_name)
            if srv_id:
                vals['service_id'] = srv_id
        mapped_keys.update({'serviceName', 'machineInfo'})

        if 'branch_id' in self._fields_meta():
            br_id = self._resolve_m2o_by_name('branch_id', rec.get('branchName'))
            if br_id:
                vals['branch_id'] = br_id
        mapped_keys.add('branchName')

        # People / medical details
        self._safe_set(vals, 'topic', rec.get('patientName')); mapped_keys.add('patientName')
        self._safe_set(vals, 'treating_doctor', rec.get('practitionerName')); mapped_keys.add('practitionerName')
        self._safe_set(vals, 'speciality', rec.get('speciality')); mapped_keys.add('speciality')

        # Patient identifiers
        # If patient_id field exists and is text/integer, store HIS patientId
        if 'patient_id' in self._fields_meta():
            self._safe_set(vals, 'patient_id', rec.get('patientId'))
        mapped_keys.add('patientId')

        # Doctor reservation / MRN if you have a field like doctor_reservation_no
        if 'doctor_reservation_no' in self._fields_meta():
            self._safe_set(vals, 'doctor_reservation_no', rec.get('mrno'))
        mapped_keys.add('mrno')

        # Campaign (store the source system)
        if 'campaign' in self._fields_meta():
            self._safe_set(vals, 'campaign', rec.get('bookedFrom'))

        # Status / HIS Status → if you have status_id (m2o) try map by name; else dump to description
        if 'status_id' in self._fields_meta():
            status_name = rec.get('hisStatus') or rec.get('status')
            if status_name:
                st_id = self._resolve_m2o_by_name('status_id', status_name)
                if st_id:
                    vals['status_id'] = st_id
        mapped_keys.update({'status', 'hisStatus'})

        # Dates
        # created_date (if exists)
        if 'created_date' in self._fields_meta():
            self._safe_set(vals, 'created_date', rec.get('createdDate'))
        mapped_keys.add('createdDate')

        # preferred_time (if datetime field exists, set startTime; or store as string for char/text)
        if 'preferred_time' in self._fields_meta():
            self._safe_set(vals, 'preferred_time', rec.get('startTime'))
        mapped_keys.add('startTime')
        mapped_keys.add('endTime')
        mapped_keys.add('appointmentDate')

        # Gender / age / nationality to best-effort fields if present
        if 'notes' in self._fields_meta():
            base_notes = f"Gender: {rec.get('gender') or ''}, Age: {rec.get('age') or ''}, Nationality: {rec.get('nationality') or ''}".strip().strip(',')
            if base_notes:
                existing = vals.get('notes') or ""
                vals['notes'] = (existing + ("\n" if existing else "") + base_notes).strip()
        mapped_keys.update({'gender', 'age', 'nationality'})

        # Free text fields
        for k in ('campaign_activity', 'reason', 'service_detailes', 'referred'):
            if k in self._fields_meta():
                # optionally fill service_detailes with a short machine summary
                if k == 'service_detailes':
                    mi = rec.get('machineInfo') or {}
                    if mi:
                        brief = f"{mi.get('newName') or mi.get('name') or ''} ({mi.get('machineCode') or ''})"
                        if brief.strip():
                            self._safe_set(vals, 'service_detailes', brief)
                else:
                    # leave empty or derive if you have a rule
                    pass

        # Build HTML description with leftovers (including machineInfo full JSON)
        desc_html = self._build_description_table(rec, mapped_keys)
        if desc_html:
            # merge with existing description if present
            existing_desc = vals.get('description') or ""
            vals['description'] = (existing_desc + ("\n" if existing_desc else "") + desc_html).strip()

        return vals

    @api.model
    def _already_imported_domain(self, rec):
        """Define duplicate criteria: same patientId + startTime."""
        patient_id = rec.get('patientId') or ''
        start_time = rec.get('startTime') or ''
        return [
            ('patient_id', '=', patient_id),
            ('preferred_time', '=', start_time),
        ]

    @api.model
    def cron_fetch_mobile_appointments(self):
        """Daily: fetch today's appointments and create CRM leads. """
        today = date.today().strftime("%Y-%m-%d")
        url = f"https://ramprimecare.com/HISAdmin/api/appointment/findMobileAppointmentByDate?fromDate={today}"

        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json() or []
            if not isinstance(data, list):
                raise UserError("Unexpected response format: expected a list of objects.")
        except Exception as e:
            raise UserError(f"HIS API fetch failed: {e}")

        created, skipped = 0, 0
        for rec in data:
            # Skip clearly malformed items
            if not isinstance(rec, dict):
                continue

            # Dedup
            dom = self._already_imported_domain(rec)
            exists = self.search(dom, limit=1)
            if exists:
                skipped += 1
                continue

            vals = self._compose_vals_from_his(rec)

            # Fallbacks to avoid required-field errors
            if not vals.get('name'):
                vals['name'] = rec.get('patientName') or rec.get('mrno') or 'Appointment'
            if not vals.get('team_id'):
                vals['team_id'] = self.env['crm.team'].search([], limit=1).id
            if not vals.get('stage_id'):
                vals['stage_id'] = self.env['crm.stage'].search([], limit=1).id

            self.create(vals)
            created += 1

        return {"created": created, "skipped": skipped, "date": today}
