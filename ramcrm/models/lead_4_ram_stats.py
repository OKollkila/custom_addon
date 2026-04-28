from odoo import models, fields, tools


class Lead4RamStats(models.Model):
    _name = 'clinizone.lead_4_ram_stats'
    _auto = False
    _description = 'Anonymized Lead for RAM Stats'
    _rec_name = 'id'

    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    lead_source_id = fields.Many2one('clinizone.lead_source', string='Lead Source', readonly=True)
    lead_source_level_1_id = fields.Many2one('clinizone.lead_source', string='Lead Source Level 1', readonly=True)
    lead_source_level_2_id = fields.Many2one('clinizone.lead_source', string='Lead Source Level 2', readonly=True)
    stage2 = fields.Selection([('untouched', 'Untouched'), ('touched', 'Touched'), ('booked', 'Booked'), ('lost', 'Lost')], index=True, string='Stage 2', readonly=True)
    stage3 = fields.Selection([('untouched', 'Untouched'), ('reached', 'Reached'), ('unreached', 'Unreached'), ('booked', 'Booked')], index=True, string='Stage 3', readonly=True)
    stage4_id = fields.Many2one('cz.lead.stage4', string='Stage4')
    status_id = fields.Many2one('cz.lead.status', string='Status')
    lost_won = fields.Selection([('lost', 'Lost'), ('won', 'Active')], readonly=True, index=True, string='Lost/Active')
    campaign = fields.Char(string='Campaign', readonly=True)
    topic = fields.Char(string='Topic', readonly=True)
    city_id = fields.Many2one('clinizone.city', string='City', readonly=True)
    branch_id = fields.Many2one('clinizone.branch', string='Branch', readonly=True)
    department_id = fields.Many2one('clinizone.department', string='Department', readonly=True)
    service_id = fields.Many2one('clinizone.service', string='Service', readonly=True)
    ads = fields.Boolean(string='Ads', readonly=True)
    create_uid = fields.Many2one('res.users', string='Created by', readonly=True)
    create_date = fields.Datetime(string='Create Date', readonly=True)
    notes = fields.Char(string='Notes', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                select l.id,
                       lead_source_id,
                       (select level_1_id from clinizone_lead_source s where s.id = lead_source_id) as lead_source_level_1_id,
                       (select level_2_id from clinizone_lead_source s where s.id = lead_source_id) as lead_source_level_2_id,
                       stage2,
                       stage3,
                       stage4_id,
                       status_id,
                       campaign,
                       topic,
                       b.city_id,
                       branch_id,
                       department_id,
                       service_id,
                       ads,
                       l.create_uid,
                       l.notes,
                       l.create_date,
                       CASE WHEN active IS NOT NULL AND active = FALSE THEN 'lost' ELSE 'won' END as lost_won,
                       l.company_id
                from crm_lead l left join clinizone_branch b on l.branch_id = b.id
                where lead_source_id not in (select id from clinizone_lead_source where name ilike '%s')
            )
        """ % (self._table, '%audit%'))