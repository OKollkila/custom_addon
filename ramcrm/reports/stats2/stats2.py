from odoo import fields, models, api, _

class ReportStats2Report(models.AbstractModel):
    _name = 'report.ramcrm.template_stats2_report'
    _description = 'Stats2 Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        from_date = data.get('from_date')
        to_date = data.get('to_date')
        company_ids = self.env.context.get('allowed_company_ids', self.env.user.company_ids.ids)

        # فلترة الـ leads باستخدام ORM فقط
        leads = self.env['crm.lead'].search([
            ('company_id', 'in', company_ids),
            ('create_date', '>=', from_date),
            ('create_date', '<=', to_date),
        ])

        details, cities, lead_sources, row_sums, column_sums = self.compute_details(leads)

        return {
            'doc_ids': docids,
            'doc_model': 'crm.lead',
            'docs': leads,
            'data': data,
            'details': details,
            'cities': cities,
            'lead_sources': lead_sources,
            'row_sums': row_sums,
            'column_sums': column_sums,
            'total_sum': sum(row_sums.values()),
            'from_date': from_date,
            'to_date': to_date,
        }

    def compute_details(self, leads):
        details = {}
        cities = set()
        lead_sources = set()
        row_sums = {}
        column_sums = {}

        for lead in leads:
            c = lead.city or 'Unknown'
            s = lead.lead_source or 'Unknown'

            cities.add(c)
            lead_sources.add(s)

            if c not in details:
                details[c] = {}
            if s not in details[c]:
                details[c][s] = 0
            details[c][s] += 1

            row_sums[c] = row_sums.get(c, 0) + 1
            column_sums[s] = column_sums.get(s, 0) + 1

        return details, cities, lead_sources, row_sums, column_sums
