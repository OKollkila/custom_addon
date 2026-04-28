# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models, _
from collections import defaultdict
from odoo.addons.base.models.res_partner import _tz_get
import pytz
from datetime import datetime
from ..zk import ZK
from odoo.exceptions import UserError, ValidationError
import re
import logging
_logger = logging.getLogger(__name__)

class BiometricDeviceConfig(models.Model):
    _name = 'biometric.config'
    _description = 'biometric config'

    name = fields.Char(string='Name', required=True)
    device_ip = fields.Char(string='Device IP', required=True)
    port = fields.Integer(string='Port', required=True)
    is_password_set = fields.Boolean(string='Is Password Set', default=False)
    device_password = fields.Char(string='Device Password', blank=True)
    time_zone = fields.Selection(_tz_get, string='Timezone', default=lambda self: self.env.user.tz or 'GMT')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, readonly=True)

    @api.onchange('is_password_set')
    def on_is_password_set_change(self):
        if not self.is_password_set:
            self.device_password = ''

    @api.onchange('device_password')
    def _check_password(self):
        if self.device_password and not self.device_password.isdigit():
            raise UserError(_("Device password should only contain numeric characters."))

    def test_device_connection(self):
        ip = self.device_ip
        port = self.port
        password = self.device_password
        _logger.info("/////////////////////////////33333333333333333333333333",) 
        # zk = ZK(ip, port, password=password,force_udp=True)
        zk = ZK(ip, port, password=password)
        _logger.info("///////////////////////////", zk)
        try:
            conn = zk.connect()
            if conn:
                raise UserError(_("Connection Success"))
            else:
                raise ValidationError(_("Connection Failed"))
        except Exception as e:
            raise UserError(_(str(e)))

    def sync_employees(self):
        uid = 0
        employees = self.env['hr.employee'].search([])
        next_user_id = 1
        uid_list = []
        user_id_list = []
        ip = self.device_ip
        port = self.port
        password = self.device_password
        zk = ZK(ip, port, password=password)
        try:
            conn = zk.connect()
            if conn:
                users = zk.get_users()
                def create_next_user_id(user_id):
                    pattern = r'(\d+)'

                    # Find the number and increment it by a specific value
                    def increment(match):
                        number = match.group(0)
                        incremented_number = str(int(number) + 1)  # Increment by 20
                        return incremented_number

                    # Replace the number in the original string
                    c_user_id = re.sub(pattern, increment, user_id)
                    return c_user_id

                if users:
                    for user in users:
                        uid_list.append(user.uid)
                        user_id_list.append(user.user_id)
                    uid_list.sort()
                    user_id_list.sort()
                    uid = uid_list[-1]
                    user_id = str(user_id_list[-1])
                    next_user_id = create_next_user_id(user_id)
                    num = 2
                    while 1:
                        if next_user_id in user_id_list:
                            user_id = str(user_id_list[-1 * num])
                            next_user_id = create_next_user_id(user_id)
                            num += 1
                        else:
                            for i in range(len(employees)):
                                test_user_id = create_next_user_id(next_user_id)
                                if test_user_id in user_id_list:
                                    next_user_id = test_user_id
                                    continue
                            break
                for employee in employees:
                    biometric_device = employee.biometric_device_ids.search(
                        [('employee_id', '=', employee.id), ('device_id', '=', self.id)])
                    if not biometric_device:
                        uid += 1
                        employee.biometric_device_ids = [(0, 0, {
                            'employee_id': employee.id,
                            'biometric_attendance_id': next_user_id,
                            'device_id': self.id,
                        })]
                        zk.set_user(uid, employee.name, 0, '', '', str(next_user_id),card=employee.pin)
                        next_user_id = create_next_user_id(next_user_id)
                return {'name': 'Success Message',
                        'type': 'ir.actions.act_window',
                        'res_model': 'employee.sync.wizard',
                        'view_mode': 'form',
                        'target': 'new'}
            else:
                raise ValidationError("Connection Failed")
        except Exception as e:
            raise UserError(_(str(e)))

    def download_attendance_log(self):
        attend_obj = self.env['attendance.log']
        ip = self.device_ip
        port = self.port
        password = self.device_password
        zk = ZK(ip, port, password=password)
        try:
            conn = zk.connect()
            if conn:
                attendances = zk.get_attendance()
                print("attendences",attendances)
                device = self.name
                company_id = self.company_id
                if attendances:
                    attendence_list = []
                    for attendance in attendances:
                        # attendence_dict = {}
                        atten_time = attendance.timestamp
                        atten_time = datetime.strptime(
                            atten_time.strftime('%Y-%m-%d %H:%M:%S'),
                            '%Y-%m-%d %H:%M:%S')
                        local_tz = pytz.timezone(self.time_zone or 'GMT')
                        local_dt = local_tz.localize(atten_time, is_dst=None)
                        utc_dt = local_dt.astimezone(pytz.utc)
                        utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                        atten_time = datetime.strptime(utc_dt,
                                                       "%Y-%m-%d %H:%M:%S")
                        atten_time = fields.Datetime.to_string(atten_time)
                        employees = self.env[
                            'biometric.attendance.devices'].search(
                            [('biometric_attendance_id', '=',
                              attendance.user_id),
                             ('device_id', '=', self.id)])
                        if len(employees) > 1:
                            employee_id = employees.mapped('employee_id')
                            employee_name = employee_id.mapped('name')
                            raise UserError(
                                _("Two Users have same Biometric User ID %s ") % employee_name)
                        if employees:
                            attendence_dict = {
                                'user_id': attendance.user_id,
                                'atten_time': atten_time,
                                'employee_id': employees.employee_id.id
                            }
                            attendence_list.append(attendence_dict)
                    employee_status = defaultdict(list)
                    sorted_attendance = sorted(attendence_list, key=lambda x: (x['user_id'], x['atten_time']))
                    for entry in sorted_attendance:
                        user_id = entry['user_id']
                        employee_id = entry['employee_id']
                        entry_time = entry['atten_time']
                        atten_time = datetime.strptime(entry['atten_time'],
                                                       '%Y-%m-%d %H:%M:%S')
                        if not employee_status[user_id]:
                            employee_status[user_id].append(
                                {'status': 'Check-in', 'time': atten_time,
                                 'employee_id': employee_id,
                                 'entry_time': entry_time
                                 })
                            entry['status'] = 'Check-in'
                        else:
                            if atten_time > employee_status[user_id][-1]['time']:
                                current_status = 'Check-out' if employee_status[user_id][-1]['status'] == 'Check-in' else 'Check-in'
                                employee_status[user_id].append(
                                    {'status': current_status, 'time': atten_time,'employee_id': employee_id,
                                 'entry_time': entry_time})
                                entry['status'] = current_status
                        existing_log = attend_obj.search(
                            [('employee_id', '=', employee_id),
                             ('punching_time', '=', entry_time)])
                        if existing_log:
                            for log in existing_log:
                                if log.is_calculated == True:
                                    if entry['status'] == 'Check-in':
                                        attendance_status = '0'
                                    elif entry['status'] == 'Check-out':
                                        attendance_status = '1'
                                    vals = {
                                        'employee_id': employee_id,
                                        'punching_time': entry_time,
                                        'status': attendance_status,
                                        'device': str(device),
                                        'company_id': company_id.id,
                                        'is_calculated': True}
                                else:
                                    if entry['status'] == 'Check-in':
                                        attendance_status = '0'
                                    elif entry['status'] == 'Check-out':
                                        attendance_status = '1'
                                    vals = {
                                        'employee_id': employee_id,
                                        'punching_time': atten_time,
                                        'status': attendance_status,
                                        'device': str(device),
                                        'company_id': company_id.id,
                                        'is_calculated': False}
                                existing_log.write(vals)
                        else:
                            if entry['status'] == 'Check-in':
                                attendance_status = '0'
                            elif entry['status'] == 'Check-out':
                                attendance_status = '1'
                            vals = {'employee_id': employee_id,
                                    'punching_time': atten_time,
                                    'status': attendance_status,
                                    'device': str(device),
                                    'company_id': company_id.id,
                                    'is_calculated': False}
                            attend_obj.create(vals)
                    return {'name': 'Success Message',
                            'type': 'ir.actions.act_window',
                            'res_model': 'success.wizard',
                            'view_mode': 'form',
                            'target': 'new'}
            else:
                raise ValidationError("Connection failed")
        except Exception as e:
            raise UserError(_(str(e)))

    def download_attendance_log_new(self):
        devices = self.env["biometric.config"].search([])
        for device in devices:
            device.download_attendance_log()
