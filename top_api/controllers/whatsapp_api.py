from odoo import http
from odoo.http import request


class WhatsappLeadController(http.Controller):

    @http.route('/api/whatsapp/lead', type='json', auth='public', methods=['POST'], csrf=False)
    def create_or_update_lead(self, **kwargs):
        # 1. التحقق من التوكن
        api_key = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')
        if api_key != '283bc7e6436d1dec75364ba4bbef4aabb401fc9b':
            return {"status": "error", "message": "Unauthorized"}

        # 2. تجهيز اليوزر
        api_user = request.env['res.users'].sudo().search([('name', '=', 'API')], limit=1)
        if not api_user:
            api_user = request.env.ref('base.user_admin')

        # 3. استلام البيانات
        lead_id = kwargs.get('lead_id')

        # تحديد الشركة (لو مبعوتة نستخدمها، لو لأ نستخدم 3 كافتراضي)
        req_company_id = kwargs.get('company_id')
        target_company_id = int(req_company_id) if req_company_id else 3

        # بيئة العمل
        CRMENV = request.env['crm.lead'].with_user(api_user).with_company(target_company_id).sudo()

        # 4. بناء قاموس التحديث بذكاء (Smart Vals Construction)
        # بنعمل قاموس فاضي، ونملأه بس باللي مبعوت
        vals = {}

        # الدوال دي للتأكد إننا مش بناخد قيم Null
        if kwargs.get('name'): vals['name'] = kwargs.get('name')
        if kwargs.get('email_from'): vals['email_from'] = kwargs.get('email_from')
        if kwargs.get('phone'): vals['phone'] = kwargs.get('phone')
        if kwargs.get('partner_name'): vals['contact_name'] = kwargs.get('partner_name')
        if kwargs.get('city'): vals['city'] = kwargs.get('city')
        if kwargs.get('internal_reference'): vals['description'] = kwargs.get(
            'internal_reference')  # ده اللي إنتي عايزاه

        # الحقول الرقمية
        if kwargs.get('team_id'): vals['team_id'] = int(kwargs.get('team_id'))
        if kwargs.get('company_id'): vals['company_id'] = int(kwargs.get('company_id'))
        if kwargs.get('branch_id'): vals['branch_id'] = int(kwargs.get('branch_id'))
        if kwargs.get('source_id'): vals['source_id'] = int(kwargs.get('source_id'))
        if kwargs.get('lead_source_id'): vals['lead_source_id'] = int(kwargs.get('lead_source_id'))
        # if kwargs.get('lead_source'): vals['lead_source'] = kwargs.get('lead_source')

        # 5. التنفيذ
        try:
            if lead_id:
                # --- حالة التحديث (Update) ---
                lead = CRMENV.browse(int(lead_id))
                if lead.exists():
                    # لو في بيانات للتحديث، نحدثها
                    if vals:
                        lead.write(vals)

                    return {
                        "status": "success",
                        "message": "Lead updated successfully",
                        "lead_id": lead.id
                    }
                else:
                    return {"status": "error", "message": "Lead ID not found"}
            else:
                # --- حالة الإنشاء (Create) ---
                # في الإنشاء، الاسم والتليفون إجباريين، لو مش في vals نرجع إيرور
                if 'name' not in vals or 'phone' not in vals:
                    return {"status": "error", "message": "Name and Phone are required for creation"}

                # إضافة اليوزر عند الإنشاء فقط
                vals['user_id'] = api_user.id

                # لو التيم مش مبعوت، نخليه فاضي عشان ميعملش مشاكل
                if 'team_id' not in vals:
                    vals['team_id'] = False

                new_lead = CRMENV.create(vals)
                return {
                    "status": "success",
                    "message": "Lead created successfully",
                    "lead_id": new_lead.id
                }

        except Exception as e:
            return {"status": "error", "message": str(e)}