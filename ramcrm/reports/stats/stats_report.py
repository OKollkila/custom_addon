from odoo import fields, models, api, _

class ReportStatsReport(models.AbstractModel):
    _name = 'report.ramcrm.template_stats_report'
    _description = 'Stats Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        from_date = data['from_date']
        to_date = data['to_date']
        details, cities, lead_sources, row_sums, column_sums = self.detailed_table_1(from_date, to_date)
        return {
            'doc_ids': docids,
            'doc_model': 'crm.lead',
            'docs': self.env['crm.lead'].search([]),
            'data': data,
            'Stages': self.stage_details(from_date, to_date),
            'detailed_stages': self.detailed_stage_details(from_date, to_date),
            'details': details,
            'cities': cities,
            'lead_sources': lead_sources,
            'row_sums': row_sums,
            'column_sums': column_sums,
            'total_sum': sum(row_sums.values()),
        }

    def stage_details(self, from_date, to_date):
        untouched_id = self.env['crm.stage'].sudo().search([('name', '=', 'Untouched')], limit=1).id
        booked_id = self.env['crm.stage'].sudo().search([('name', '=', 'Booked')], limit=1).id
        rescheduled_id = self.env['crm.stage'].sudo().search([('name', '=', 'Rescheduled')], limit=1).id
        touched_active = self.env['crm.lead'].sudo().search_count([('create_date', '>=', from_date), ('create_date', '<=', to_date), ('stage_id', '!=', untouched_id), ('create_uid', '=', 6)])
        touched_archived = self.env['crm.lead'].sudo().search_count([('create_date', '>=', from_date), ('create_date', '<=', to_date), ('active', '=', False), ('create_uid', '=', 6)])
        untouched = self.env['crm.lead'].sudo().search_count([('create_date', '>=', from_date), ('create_date', '<=', to_date), ('stage_id', '=', untouched_id), ('create_uid', '=', 6)])
        booked = self.env['crm.lead'].sudo().search_count([('create_date', '>=', from_date), ('create_date', '<=', to_date), ('stage_id', 'in', [booked_id, rescheduled_id]), ('create_uid', '=', 6)])

        return [
            {
                'stage': 'Touched',
                'count': touched_active + touched_archived
            },
            # {
            #     'stage': 'Untouched',
            #     'count': untouched
            # },
            {
                'stage': 'Booked',
                'count': booked
            }
        ]

    def detailed_table_1(self, from_date, to_date):
        sql = (f"select city, lead_source, count(id) from crm_lead"
               f" where create_uid = 6"
               f" and create_date::date >= '{from_date}'"
               f" and create_date::date <= '{to_date}'"
               f" group by city, lead_source;"
               )
        self.env.cr.execute(sql)

        details = {}
        data = self.env.cr.fetchall()
        cities = set(tup[0] for tup in data)
        lead_sources = set(tup[1] for tup in data)

        row_sums = {}
        column_sums = {}
        for row, col, value in data:
            if row in row_sums:
                row_sums[row] += value
            else:
                row_sums[row] = value

            if col in column_sums:
                column_sums[col] += value
            else:
                column_sums[col] = value

        for el in data:
            if el[0] not in details.keys():
                details[el[0]] = {}
            details[el[0]][el[1]] = {
                'total': el[2],
                'booked': 0,
                'cr': 0,
            }

        sql = (f"select city, lead_source, count(id) from crm_lead"
               f" where create_uid = 6"
               f" and create_date::date >= '{from_date}'"
               f" and create_date::date <= '{to_date}'"
               f" and stage_id in (select id from crm_stage where name in ('Booked', 'Rescheduled'))"
               f" group by city, lead_source;"
               )
        self.env.cr.execute(sql)

        data = self.env.cr.fetchall()
        for el in data:
            details[el[0]][el[1]]['booked'] = el[2]
            details[el[0]][el[1]]['cr'] = round(100 * details[el[0]][el[1]]['booked'] / details[el[0]][el[1]]['total'])

        return details, cities, lead_sources, row_sums, column_sums

    def detailed_stage_details(self, from_date, to_date):
        ret = []

        untouched_id = self.env['crm.stage'].sudo().search([('name', '=', 'Untouched')], limit=1).id

        active_lead_stages = self.env['crm.lead'].sudo().read_group(
            [('create_date', '>=', from_date), ('create_date', '<=', to_date), ('create_uid', '=', 6)],
            ['stage_id', 'id:array_agg'], ['stage_id'],
        )
        for stage in active_lead_stages:
            if stage['stage_id'] and stage['stage_id'][0] == untouched_id:
                continue
            count = stage['stage_id_count']
            state = stage['stage_id'][1] if stage['stage_id'] else 'Undefined (Active or Won)'
            ret.append({'stage': state, 'count': count})

        inactive_lead_stages = self.env['crm.lead'].sudo().read_group(
            [('create_date', '>=', from_date), ('create_date', '<=', to_date), ('active', '=', False), ('create_uid', '=', 6)],
            ['lost_reason_id', 'id:array_agg'], ['lost_reason_id'],
        )
        for stage in inactive_lead_stages:
            count = stage['lost_reason_count']
            state = stage['lost_reason_id'][1] if stage['lost_reason_id'] else 'Undefined (Lost)'
            ret.append({'stage': state, 'count': count})


        return ret

