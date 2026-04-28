# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from datetime import datetime, date, time
from odoo import models, api, _
from odoo.exceptions import UserError
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class AttendanceWizard(models.TransientModel):
    _name = 'attendance.calc.wizard'
    _description = 'attendance calc wizard'

    def calculate_attendance(self):
        """
        Process all attendance logs and add them to HR attendance report.
        If employee already has attendance for the same day, overwrite it.
        """
        try:
            minimal_attendance = self.env['ir.config_parameter'].sudo().get_param(
                'tis_hr_biometric_attendance.minimal_attendance')
            
            # Get all uncalculated logs, ordered by employee and time
            domain = [('is_calculated', '=', False)]
            attendance_logs = self.env['attendance.log'].search(domain, order='employee_id, punching_time')
            
            if not attendance_logs:
                _logger.info("No uncalculated attendance logs found")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Information'),
                        'message': _('No uncalculated attendance logs found. All logs have already been processed.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            _logger.info("Processing %d attendance logs", len(attendance_logs))
            
            if minimal_attendance:
                # Minimal attendance mode: One attendance record per day per employee
                self._process_minimal_attendance(attendance_logs)
            else:
                # Normal mode: Multiple check-in/check-out pairs per day
                self._process_normal_attendance(attendance_logs)
            
            # Mark all processed logs as calculated
            attendance_logs.write({'is_calculated': True})
            
            _logger.info("Successfully processed %d attendance logs", len(attendance_logs))
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Successfully processed %d attendance log(s) and updated employee attendance records.') % len(attendance_logs),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.exception("Error processing attendance logs: %s", str(e))
            raise UserError(_('Error processing attendance logs: %s') % str(e))

    def recalculate_all_attendance(self):
        """
        Reprocess ALL attendance logs (even if already calculated).
        This is useful when logs were marked as calculated but attendance records weren't created properly.
        """
        try:
            minimal_attendance = self.env['ir.config_parameter'].sudo().get_param(
                'tis_hr_biometric_attendance.minimal_attendance')
            
            # Get ALL logs (both calculated and uncalculated)
            attendance_logs = self.env['attendance.log'].search([], order='employee_id, punching_time')
            
            if not attendance_logs:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Information'),
                        'message': _('No attendance logs found.'),
                        'type': 'info',
                        'sticky': False,
                    }
                }
            
            _logger.info("Recalculating ALL %d attendance logs", len(attendance_logs))
            
            # Reset is_calculated flag
            attendance_logs.write({'is_calculated': False})
            
            if minimal_attendance:
                self._process_minimal_attendance(attendance_logs)
            else:
                self._process_normal_attendance(attendance_logs)
            
            # Mark all processed logs as calculated
            attendance_logs.write({'is_calculated': True})
            
            _logger.info("Successfully recalculated %d attendance logs", len(attendance_logs))
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Successfully recalculated %d attendance log(s) and updated employee attendance records.') % len(attendance_logs),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.exception("Error recalculating attendance logs: %s", str(e))
            raise UserError(_('Error recalculating attendance logs: %s') % str(e))

    def _process_minimal_attendance(self, logs):
        """Process logs in minimal attendance mode - one record per day per employee"""
        # Group logs by employee and date
        employee_date_logs = defaultdict(lambda: {'check_in': None, 'check_out': None})
        
        for log in logs:
            if not log.employee_id:
                _logger.warning("Skipping log without employee_id: %s", log.id)
                continue
                
            emp_id = log.employee_id.id
            log_date = log.punching_time.date()
            key = (emp_id, log_date)
            
            # Determine if this is check-in or check-out based on status
            is_check_in = log.status == '0' or (log.status == '2' and employee_date_logs[key]['check_in'] is None)
            is_check_out = log.status == '1'
            
            if is_check_in:
                # Use earliest check-in time
                if employee_date_logs[key]['check_in'] is None or log.punching_time < employee_date_logs[key]['check_in']:
                    employee_date_logs[key]['check_in'] = log.punching_time
            elif is_check_out:
                # Use latest check-out time
                if employee_date_logs[key]['check_out'] is None or log.punching_time > employee_date_logs[key]['check_out']:
                    employee_date_logs[key]['check_out'] = log.punching_time
            else:
                # Status '2' (Punched) - treat as check-in if no check-in yet, else check-out
                if employee_date_logs[key]['check_in'] is None:
                    employee_date_logs[key]['check_in'] = log.punching_time
                else:
                    if employee_date_logs[key]['check_out'] is None or log.punching_time > employee_date_logs[key]['check_out']:
                        employee_date_logs[key]['check_out'] = log.punching_time
        
        # Create or update attendance records
        created_count = 0
        updated_count = 0
        
        for (emp_id, log_date), times in employee_date_logs.items():
            if not times['check_in']:
                continue
            
            # Find existing attendance for this employee and date
            # Search by punch_date first, then by check_in date to catch all cases
            # This ensures we find attendances even if punch_date is not set
            date_start = datetime.combine(log_date, time.min)
            date_end = datetime.combine(log_date, time.max)
            existing_attendance = self.env['hr.attendance'].search([
                ('employee_id', '=', emp_id),
                '|',
                ('punch_date', '=', log_date),
                '&',
                ('check_in', '>=', date_start),
                ('check_in', '<=', date_end)
            ], limit=1)
            
            vals = {
                'employee_id': emp_id,
                'check_in': times['check_in'],
                'punch_date': log_date,
            }
            
            if times['check_out']:
                vals['check_out'] = times['check_out']
            else:
                # If no check-out, ensure check_out is False (not set)
                vals['check_out'] = False
            
            if existing_attendance:
                # Overwrite existing attendance with biometric log times
                # This ensures biometric log (e.g., 09:00) overwrites existing (e.g., 09:10)
                existing_attendance.write(vals)
                updated_count += 1
                _logger.info("Overwritten attendance for employee %s on %s: Biometric time %s replaced existing time %s", 
                           emp_id, log_date, times['check_in'], existing_attendance.check_in)
            else:
                # Create new attendance
                self.env['hr.attendance'].create(vals)
                created_count += 1
                _logger.debug("Created attendance for employee %s on %s", emp_id, log_date)
        
        _logger.info("Minimal attendance mode: Created %d, Updated %d attendance records", created_count, updated_count)

    def _process_normal_attendance(self, logs):
        """Process logs in normal mode - multiple check-in/check-out pairs per day"""
        # Group logs by employee and date
        employee_date_logs = defaultdict(lambda: defaultdict(list))
        
        for log in logs:
            if not log.employee_id:
                continue
            emp_id = log.employee_id.id
            log_date = log.punching_time.date()
            employee_date_logs[emp_id][log_date].append(log)
        
        # Process each employee-date combination
        for emp_id, date_logs in employee_date_logs.items():
            for log_date, day_logs in date_logs.items():
                # Delete ALL existing attendances for this employee and date (overwrite)
                # Search by punch_date first, then by check_in date to catch all cases
                # This ensures we find attendances even if punch_date is not set
                date_start = datetime.combine(log_date, time.min)
                date_end = datetime.combine(log_date, time.max)
                existing_attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', emp_id),
                    '|',
                    ('punch_date', '=', log_date),
                    '&',
                    ('check_in', '>=', date_start),
                    ('check_in', '<=', date_end)
                ])
                if existing_attendances:
                    _logger.info("Deleting %d existing attendance(s) for employee %s on %s to overwrite with biometric logs", 
                               len(existing_attendances), emp_id, log_date)
                    existing_attendances.unlink()
                
                # Sort logs by time
                day_logs.sort(key=lambda x: x.punching_time)
                
                # Process logs chronologically to create check-in/check-out pairs
                current_check_in = None
                current_attendance = None
                
                for log in day_logs:
                    # Determine action based on status
                    is_check_in = log.status == '0'
                    is_check_out = log.status == '1'
                    
                    if is_check_in or (log.status == '2' and current_check_in is None):
                        # New check-in
                        # If there's an open attendance, close it first
                        if current_attendance and not current_attendance.check_out:
                            # Set check-out to the check-in time (same time) if no check-out found
                            current_attendance.write({'check_out': current_attendance.check_in})
                        
                        # Create new attendance with check-in
                        current_attendance = self.env['hr.attendance'].create({
                            'employee_id': emp_id,
                            'check_in': log.punching_time,
                            'punch_date': log_date
                        })
                        current_check_in = log.punching_time
                        
                    elif is_check_out or (log.status == '2' and current_check_in is not None):
                        # Check-out
                        if current_attendance:
                            # Update current attendance with check-out
                            current_attendance.write({'check_out': log.punching_time})
                            current_attendance = None
                            current_check_in = None
                        else:
                            # No open attendance, create one with same time for check-in and check-out
                            self.env['hr.attendance'].create({
                                'employee_id': emp_id,
                                'check_in': log.punching_time,
                                'check_out': log.punching_time,
                                'punch_date': log_date
                            })
                
                # Close any remaining open attendance
                if current_attendance and not current_attendance.check_out:
                    # Set check-out to end of day if still open
                    end_of_day = current_attendance.check_in.replace(hour=23, minute=59, second=59)
                    current_attendance.write({'check_out': end_of_day})
        
        _logger.info("Normal attendance mode: Processed attendances for %d employee-date combinations", 
                     sum(len(date_logs) for date_logs in employee_date_logs.values()))
