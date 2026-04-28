import os

import xlrd
from odoo import models, fields
from odoo.exceptions import UserError


class Branch(models.Model):
    _name = 'clinizone.branch'
    _description = 'clinizone.branch'

    code = fields.Char("External Code")
    name = fields.Char("Name", required=True)
    city_id = fields.Many2one("clinizone.city", "City")
    company_id = fields.Many2one("res.company", "Company")
    helpdesk_team_id = fields.Many2one("helpdesk.team", "Helpdesk Team")
    medical_director_team_id = fields.Many2one("helpdesk.team", "Medical Director Team")
    can_be_selected = fields.Boolean("Can be selected", default=False)


    def _import_from_excel(self, filepath):
        path = os.path.join(os.path.dirname(__file__), filepath)
        workbook = xlrd.open_workbook(path)
        sheet = workbook.sheet_by_index(0)
        for row in range(2, 33):
            branch = sheet.row_values(row)
            branch_data = {
                'code': str(int(branch[0])),
                'name': branch[1],
                'mgr_names': branch[2].split('\n'),
                'mgr_emails': branch[3].split('\n'),
                'cs_names': branch[4].split('\n'),
                'cs_emails': branch[5].split('\n'),
                'md_names': branch[6].split('\n'),
                'md_emails': branch[7].split('\n'),
            }
            print(branch_data)

            existing_branch = self.env['clinizone.branch'].search([('id', '=', branch_data['code'])], limit=1)
            if not existing_branch:
                raise UserError('Branch with id ' + branch_data['code'] + ' does not exist')

            mgr_team = branch_data['name'] + ' Manager'
            cs_team = branch_data['name'] + ' CS'
            md_team = branch_data['name'] + ' Medical Director'

            mgr_team_id = self.env['helpdesk.team'].search([('name', '=', mgr_team)])
            if not mgr_team_id:
                print('Creating team ', mgr_team)
                mgr_team_id = self.env['helpdesk.team'].create({'name': mgr_team, 'privacy': 'invite', 'escalate_team_id': self.env['helpdesk.team'].search([('name', '=', 'Customer Care Center')], limit=1).id})
            else:
                mgr_team_id = mgr_team_id[0]

            cs_team_id = self.env['helpdesk.team'].search([('name', '=', cs_team)])
            if not cs_team_id:
                print('Creating team ', cs_team)
                cs_team_id = self.env['helpdesk.team'].create({'name': cs_team, 'privacy': 'invite', 'escalate_team_id': mgr_team_id.id})
            else:
                cs_team_id = cs_team_id[0]

            md_team_id = self.env['helpdesk.team'].search([('name', '=', md_team)])
            if not md_team_id:
                print('Creating team ', md_team)
                md_team_id = self.env['helpdesk.team'].create({'name': md_team, 'privacy': 'invite', 'escalate_team_id': mgr_team_id.id})
            else:
                md_team_id = md_team_id[0]

            existing_branch.helpdesk_team_id = cs_team_id.id
            existing_branch.medical_director_team_id = md_team_id.id

            print ('Now handling team members...')
            print('Managers...')
            for i in range(len(branch_data['mgr_names'])):
                mgr_email = branch_data['mgr_emails'][i]
                mgr_name = branch_data['mgr_names'][i]
                mgr_user_id = self.env['res.users'].search([('login', '=', mgr_email)])
                if not mgr_user_id:
                    print('Creating user ', mgr_name)
                    mgr_user_id = self.env['res.users'].create({
                        'name': mgr_name,
                        'login': mgr_email,
                        'groups_id': [(6, 0, [self.env.ref('helpdesk.group_helpdesk_user').id])],
                    })
                    print ('Setting as member for team ', mgr_team_id.name)
                    mgr_team_id.member_ids = [(4, mgr_user_id.id)]
                    mgr_team_id.visibility_member_ids = [(4, mgr_user_id.id)]
                    md_team_id.member_ids = [(4, mgr_user_id.id)]
                    md_team_id.visibility_member_ids = [(4, mgr_user_id.id)]
                    cs_team_id.member_ids = [(4, mgr_user_id.id)]
                    cs_team_id.visibility_member_ids = [(4, mgr_user_id.id)]
                else:
                    print('User already exists ', mgr_name)
                    print ('Setting as member for team ', mgr_team_id.name)
                    mgr_team_id.member_ids = [(4, mgr_user_id.id)]
                    mgr_team_id.visibility_member_ids = [(4, mgr_user_id.id)]

            print ('Customer Support...')
            for i in range(len(branch_data['cs_names'])):
                cs_email = branch_data['cs_emails'][i]
                cs_name = branch_data['cs_names'][i]
                cs_user_id = self.env['res.users'].search([('login', '=', cs_email)])
                if not cs_user_id:
                    print('Creating user ', cs_name)
                    cs_user_id = self.env['res.users'].create({
                        'name': cs_name,
                        'login': cs_email,
                        'groups_id': [(6, 0, [self.env.ref('helpdesk.group_helpdesk_user').id])],
                    })
                    print ('Setting as member for team ', cs_team_id.name)
                    cs_team_id.member_ids = [(4, cs_user_id.id)]
                    cs_team_id.visibility_member_ids = [(4, cs_user_id.id)]
                else:
                    print('User already exists ', cs_name)
                    print ('Setting as member for team ', cs_team_id.name)
                    cs_team_id.member_ids = [(4, cs_user_id.id)]
                    cs_team_id.visibility_member_ids = [(4, cs_user_id.id)]

            print('Medical Doctors...')
            for i in range(len(branch_data['md_names'])):
                md_email = branch_data['md_emails'][i]
                if md_email.strip() == '':
                    continue
                md_name = branch_data['md_names'][i]
                md_user_id = self.env['res.users'].search([('login', '=', md_email)])
                if not md_user_id:
                    print('Creating user ', md_name)
                    md_user_id = self.env['res.users'].create({
                        'name': md_name,
                        'login': md_email,
                        'groups_id': [(6, 0, [self.env.ref('helpdesk.group_helpdesk_user').id])],
                    })
                    print ('Setting as member for team ', md_team_id.name)
                    md_team_id.member_ids = [(4, md_user_id.id)]
                    md_team_id.visibility_member_ids = [(4, md_user_id.id)]
                else:
                    print('User already exists ', md_name)
                    print ('Setting as member for team ', md_team_id.name)
                    md_team_id.member_ids = [(4, md_user_id.id)]
                    md_team_id.visibility_member_ids = [(4, md_user_id.id)]