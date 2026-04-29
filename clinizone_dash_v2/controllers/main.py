# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import pytz
from datetime import datetime, time

class CZDashboardController(http.Controller):

    # ---------------------------------------------------------
    # 1. المساعدات (Helpers)
    # ---------------------------------------------------------
    def _is_privileged_user(self):
        """التحقق مما إذا كان المستخدم هو الحساب المختار لتخطي القيود"""
        return request.env.user.login == 'cz@clinizone.net'

    def _get_common_domain(self, company_ids, branch_ids, city_ids, date_from, date_to):
        domain = [('active', 'in', [True, False])]
        user_tz = request.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        
        # القفل الزمني: الداشبورد تبدأ من 2026 فقط
        min_allowed_date = datetime(2026, 1, 1, 0, 0, 0)
        
        if date_from:
            try:
                dt_from = datetime.strptime(date_from, '%Y-%m-%d')
                if dt_from < min_allowed_date:
                    dt_from = min_allowed_date
                utc_dt_from = local_tz.localize(datetime.combine(dt_from.date(), time.min)).astimezone(pytz.utc).replace(tzinfo=None)
                domain.append(('create_date', '>=', utc_dt_from))
            except: pass
        else:
            utc_min = local_tz.localize(min_allowed_date).astimezone(pytz.utc).replace(tzinfo=None)
            domain.append(('create_date', '>=', utc_min))

        if date_to:
            try:
                dt_to = datetime.strptime(date_to, '%Y-%m-%d')
                utc_dt_to = local_tz.localize(datetime.combine(dt_to, time.max)).astimezone(pytz.utc).replace(tzinfo=None)
                domain.append(('create_date', '<=', utc_dt_to))
            except: pass

        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        
        # استخدام sudo لجلب الفروع لو المستخدم هو المختار لضمان عدم فشل الدومين
        branch_env = request.env['clinizone.branch'].sudo() if self._is_privileged_user() else request.env['clinizone.branch']
        
        if branch_ids:
            domain.append(('branch_id', 'in', branch_ids))
        elif city_ids:
            rel_branches = branch_env.search([('city_id', 'in', city_ids)]).ids
            domain.append(('branch_id', 'in', rel_branches))
            
        return domain

    def _process_raw_stats(self, raw_data, company_id=None):
        """محرك حسابات الحالات مع معالجة استثناء الشركات (onlyBooked)"""
        untouched_names = ['Untouched', 'New']
        unreached_names = ['No Answer', 'Out of Service', 'Switched Off', 'Busy', 'Wrong Number', 'Duplicated', 'Hang up the phone']
        
        # قائمة الشركات التي تحسب Booked فقط وتلغي Already Booked
        onlyBooked_ids = [5, 8, 9]

        res = {'total': 0, 'untouched': 0, 'unreached': 0, 'reached': 0, 'booked': 0}
        
        for line in raw_data:
            count = line['__count']
            stage_name = line['stage_id'][1] if line['stage_id'] else ''
            lost_name = line['lost_reason_id'][1] if line['lost_reason_id'] else ''
            lost_id = line['lost_reason_id'][0] if line['lost_reason_id'] else False

            res['total'] += count
            if stage_name in untouched_names:
                res['untouched'] += count
            elif stage_name in unreached_names or lost_name in unreached_names:
                res['unreached'] += count
            else:
                res['reached'] += count
                if company_id in onlyBooked_ids:
                    if stage_name == 'Booked':
                        res['booked'] += count
                else:
                    booked_names = ['Booked', 'Already Booked']
                    if stage_name in booked_names or lost_name in booked_names or lost_id == 11:
                        res['booked'] += count
        
        res['cr'] = round((res['booked'] / res['reached'] * 100), 1) if res['reached'] > 0 else 0
        return res

    # ---------------------------------------------------------
    # 2. فلاتر لوحة التحكم (الديناميكية)
    # ---------------------------------------------------------
    @http.route('/web/czdboard/v2/filters', type='json', auth='user')
    def get_dashboard_filters(self):
        city_env = request.env['clinizone.city'].sudo() if self._is_privileged_user() else request.env['clinizone.city']
        cities = city_env.search([])
        return {'status': 'ok', 'data': {'cities': [{'id': c.id, 'name': c.name} for c in cities], 'companies': [], 'branches': []}}

    @http.route('/web/czdboard/v2/get_companies_by_cities', type='json', auth='user')
    def get_companies_by_cities(self, city_ids=None):
        branch_env = request.env['clinizone.branch'].sudo() if self._is_privileged_user() else request.env['clinizone.branch']
        comp_env = request.env['res.company'].sudo() if self._is_privileged_user() else request.env['res.company']
        
        domain = [('id', 'in', branch_env.search([('city_id', 'in', city_ids)]).mapped('company_id').ids)] if city_ids else []
        companies = comp_env.search(domain)
        return {'status': 'ok', 'data': [{'id': c.id, 'name': c.name} for c in companies]}

    @http.route('/web/czdboard/v2/get_branches_refined', type='json', auth='user')
    def get_branches_refined(self, city_ids=None, company_ids=None):
        branch_env = request.env['clinizone.branch'].sudo() if self._is_privileged_user() else request.env['clinizone.branch']
        domain = []
        if city_ids: domain.append(('city_id', 'in', city_ids))
        if company_ids: domain.append(('company_id', 'in', company_ids))
        branches = branch_env.search(domain)
        return {'status': 'ok', 'data': [{'id': b.id, 'name': b.name} for b in branches]}

    # ---------------------------------------------------------
    # 3. إحصائيات الإدارات العادية (CRM Stats)
    # ---------------------------------------------------------
    @http.route('/web/czdboard/v2/get_crm_stats', type='json', auth='user')
    def get_crm_stats(self, company_ids=None, branch_ids=None, city_ids=None, date_from=None, date_to=None):
        lead_env = request.env['crm.lead'].sudo() if self._is_privileged_user() else request.env['crm.lead']
        source_env = request.env['clinizone.lead_source'].sudo() if self._is_privileged_user() else request.env['clinizone.lead_source']
        
        base_domain = self._get_common_domain(company_ids, branch_ids, city_ids, date_from, date_to)
        department_ids = [11, 20, 70]
        sales_ids = [19, 20, 21, 26, 68]
        
        final_report = []
        for dept_id in department_ids:
            dept_rec = source_env.browse(dept_id)
            if not dept_rec.exists(): continue

            sources = source_env.search([
                '|', ('id', '=', dept_id), ('level_1_id', '=', dept_id),
                ('can_be_selected', '=', True), ('id', 'not in', sales_ids)
            ])
            
            dept_data = {'name': dept_rec.name, 'sources': []}
            raw_data = lead_env.read_group(
                domain=base_domain + [('lead_source_id', 'in', sources.ids)],
                fields=['lead_source_id', 'stage_id', 'lost_reason_id', 'company_id'],
                groupby=['lead_source_id', 'stage_id', 'lost_reason_id', 'company_id'], lazy=False
            )

            for src in sources:
                src_raw = [line for line in raw_data if line['lead_source_id'] and line['lead_source_id'][0] == src.id]
                c_id = src_raw[0].get('company_id')[0] if src_raw and src_raw[0].get('company_id') else None
                stats = self._process_raw_stats(src_raw, company_id=c_id)
                
                if stats.get('total', 0) > 0:
                    stats['name'] = src.name
                    dept_data['sources'].append(stats)
            
            if dept_data['sources']: 
                final_report.append(dept_data)
        
        return {'status': 'ok', 'data': final_report}

    # ---------------------------------------------------------
    # 4. إحصائيات قطاع المبيعات (Sales Stats)
    # ---------------------------------------------------------
    @http.route('/web/czdboard/v2/get_sales_stats', type='json', auth='user')
    def get_sales_stats(self, company_ids=None, branch_ids=None, city_ids=None, date_from=None, date_to=None):
        lead_env = request.env['crm.lead'].sudo() if self._is_privileged_user() else request.env['crm.lead']
        source_env = request.env['clinizone.lead_source'].sudo() if self._is_privileged_user() else request.env['clinizone.lead_source']
        
        base_domain = self._get_common_domain(company_ids, branch_ids, city_ids, date_from, date_to)
        sales_ids = [19, 20, 21, 26, 68]
        
        sales_raw_data = lead_env.read_group(
            domain=base_domain + ['|', ('lead_source_id', 'in', sales_ids), 
                                 '|', ('lead_source_id.level_1_id', 'in', sales_ids), 
                                      ('lead_source_id', '=', False)],
            fields=['lead_source_id', 'stage_id', 'lost_reason_id', 'company_id'],
            groupby=['lead_source_id', 'stage_id', 'lost_reason_id', 'company_id'], lazy=False
        )

        final_levels = []
        for dept_id in (sales_ids + [None]):
            sub_sources = source_env.search([
                '|', ('id', '=', dept_id), ('level_1_id', '=', dept_id), ('can_be_selected', '=', True)
            ]) if dept_id else request.env['clinizone.lead_source']
            
            dept_sources_list = []
            if not dept_id:
                none_raw = [l for l in sales_raw_data if not l['lead_source_id']]
                if none_raw:
                    c_id = none_raw[0].get('company_id')[0] if none_raw[0].get('company_id') else None
                    stats = self._process_raw_stats(none_raw, company_id=c_id)
                    if stats.get('total', 0) > 0:
                        stats['name'] = "No Source"
                        dept_sources_list.append(stats)
            else:
                for src in sub_sources:
                    src_raw = [l for l in sales_raw_data if l['lead_source_id'] and l['lead_source_id'][0] == src.id]
                    if src_raw:
                        c_id = src_raw[0].get('company_id')[0] if src_raw[0].get('company_id') else None
                        stats = self._process_raw_stats(src_raw, company_id=c_id)
                        if stats.get('total', 0) > 0:
                            stats['name'] = src.name
                            dept_sources_list.append(stats)

            if dept_sources_list:
                dept_name = source_env.browse(dept_id).name if dept_id else "None"
                t_reached = sum(s['reached'] for s in dept_sources_list)
                t_booked = sum(s['booked'] for s in dept_sources_list)
                final_levels.append({
                    'id': str(dept_id) if dept_id else 'none',
                    'name': dept_name,
                    'sources': dept_sources_list,
                    'total_count': sum(s['total'] for s in dept_sources_list),
                    'total_untouched': sum(s['untouched'] for s in dept_sources_list),
                    'total_reached': t_reached,
                    'total_booked': t_booked,
                    'avg_cr': round((t_booked / t_reached * 100), 1) if t_reached > 0 else 0
                })

        if final_levels:
            total_tab = {
                'id': 'all', 'name': 'Total Sales',
                'sources': [s for lvl in final_levels for s in lvl['sources']],
                'total_count': sum(l['total_count'] for l in final_levels),
                'total_untouched': sum(l['total_untouched'] for l in final_levels),
                'total_reached': sum(l['total_reached'] for l in final_levels),
                'total_booked': sum(l['total_booked'] for l in final_levels),
            }
            total_tab['avg_cr'] = round((total_tab['total_booked'] / total_tab['total_reached'] * 100), 1) if total_tab['total_reached'] > 0 else 0
            return {'status': 'ok', 'data': [total_tab] + final_levels}

        return {'status': 'ok', 'data': []}
    

    @http.route('/crmdb/api/login', type='json', auth='none', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        login = kwargs.get('login')
        password = kwargs.get('password')
        db = request.session.db

        try:
            uid = request.session.authenticate(db, login, password)

            if not uid:
                return {
                    'status': False,
                    'message': 'Wrong credentials'
                }

            user = request.env['res.users'].sudo().browse(uid)

            return {
                'status': True,
                'uid': uid,
                'name': user.name,
                'session_id': request.session.sid
            }

        except Exception as e:
            return {
                'status': False,
                'message': str(e)
            }