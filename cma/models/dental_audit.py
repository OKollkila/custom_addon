from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError


# noinspection SpellCheckingInspection
class DentalAudit(models.Model):
    _name = 'clinizone.dental_audit'
    _description = 'clinizone.dental_audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    treatment_doctor = fields.Char("Treatment Doctor", required=True, tracking=True)
    mdr = fields.Char("MDR", required=True, tracking=True)
    patient_name = fields.Char("Patient Name", required=True, tracking=True)
    mobile = fields.Char("Mobile", required=True, tracking=True)
    ortho = fields.Char("Ortho", tracking=True)
    bleaching = fields.Char("Bleaching", tracking=True)
    scaling = fields.Char("Scaling", tracking=True)
    cf = fields.Char("CF", tracking=True)
    fixed = fields.Char("Fixed", tracking=True)
    rct = fields.Char("RCT", tracking=True)
    rerct = fields.Char("ReRCT", tracking=True)
    pedo = fields.Char('Pedo', tracking=True)
    ex = fields.Char("EX", tracking=True)
    surgical_ex = fields.Char("Surgical EX", tracking=True)
    surgery = fields.Char("Surgery", tracking=True)
    impaction = fields.Char("Impaction", tracking=True)
    apicectomy = fields.Char("Apicectomy", tracking=True)
    gingivectomy = fields.Char("Gingivectomy", tracking=True)
    cr_lenthening = fields.Char("CR Lenthening", tracking=True)
    denture = fields.Char("Denture", tracking=True)
    implant = fields.Char("Implant", tracking=True)
    ga = fields.Char("GA", tracking=True)
    perio = fields.Char("Perio", tracking=True)
    x_ray = fields.Char("X-Ray", tracking=True)
    tmj = fields.Char("TMJ", tracking=True)
    night_guard = fields.Char("Night Guard", tracking=True)
    fixed2 = fields.Char("(Fixed)", tracking=True)
    implant2 = fields.Char("(Implant)", tracking=True)
    maxillofacial = fields.Char("Maxillofacial", tracking=True)
    next_visit = fields.Date("Next Visit", tracking=True)
    branch_id = fields.Many2one("clinizone.branch", "Branch", required=False, tracking=True)
    prime_care_branch_id = fields.Many2one("clinizone.prime_care_branch", "PrimeCare Branch", required=False, tracking=True)
    clinic = fields.Char("Clinic", tracking=True)
    notes = fields.Text("Notes", tracking=True)
    lead_source = fields.Char("Lead Source", tracking=True)
    campaign = fields.Char("Campaign", tracking=True)

    lead_id = fields.Many2one("crm.lead", "Lead", tracking=True)

    def create(self, vals):
        if 'branch_id' not in vals and 'prime_care_branch_id' not in vals:
            raise ValidationError("Branch or PrimeCare Branch is required")

        branch = False
        prime_care_branch = False
        if 'branch_id' in vals:
            branch = self.env['clinizone.branch'].browse(vals['branch_id'])
        if 'prime_care_branch_id' in vals:
            prime_care_branch = self.env['clinizone.prime_care_branch'].browse(vals['prime_care_branch_id'])

        if branch and prime_care_branch and branch.id != prime_care_branch.branch_id.id:
            raise ValidationError("Conflict between Branch and PrimeCare Branch")

        if 'prime_care_branch_id' not in vals: # Branch is set, Get PrimeCare Branch from Branch
            vals['prime_care_branch_id'] = self.env['clinizone.prime_care_branch'].search([('branch_id', '=', branch.id)], limit=1).id

        if 'branch_id' not in vals: # PrimeCare Branch is set, Get Branch from PrimeCare Branch
            vals['branch_id'] = prime_care_branch.branch_id.id

        return super(DentalAudit, self).create(vals)

    def write(self, vals):
        if 'branch_id' in vals or 'prime_care_branch_id' in vals:
            branch = False
            prime_care_branch = False
            if 'branch_id' in vals:
                branch = self.env['clinizone.branch'].browse(vals['branch_id'])
            if 'prime_care_branch_id' in vals:
                prime_care_branch = self.env['clinizone.prime_care_branch'].browse(vals['prime_care_branch_id'])

            if branch and prime_care_branch and branch.id != prime_care_branch.branch_id.id:
                raise ValidationError("Conflict between Branch and PrimeCare Branch")

            if 'prime_care_branch_id' not in vals:
                vals['prime_care_branch_id'] = self.env['clinizone.prime_care_branch'].search([('branch_id', '=', branch.id)], limit=1).id

            if 'branch_id' not in vals:
                vals['prime_care_branch_id'] = prime_care_branch
        return super(DentalAudit, self).write(vals)

    def _create_leads(self):
        records = self.env['clinizone.dental_audit'].search([('lead_id', '=', False), ('next_visit', '=' , fields.Date.today())])
        for record in records:
            record._do_create_lead()

    def _do_create_lead(self):
        record = self
        lead = self.env['crm.lead'].create({
            'company_id': record.branch_id.company_id.id,
            'type': 'opportunity',
            'user_id': False,
            'treating_doctor': record.treatment_doctor,
            'patient_id': record.mdr,
            'name': record.patient_name,
            'contact_name': record.patient_name,
            'phone': record.mobile,
            'ads': record.next_visit,
            'branch_id': record.branch_id.id,
            'city': record.branch_id.city_id.name,
            'topic': record.clinic,
            'notes': record.notes,
            'source_id': self.env.ref('ramcrm.UTM_SOURCE_DENTAL_AUDIT').id,
            'lead_source_id': 15,
            'campaign': record.campaign if (record.campaign and len(record.campaign)) >= 3 else 'Dental Audit',
        })
        record.write({'lead_id': lead.id})

    @api.constrains('treatment_doctor', 'mdr' , 'patient_name', 'clinic', 'create_date')
    def validate_no_duplicates_within_x_days(self):
        for record in self:
            records = self.env['clinizone.dental_audit'].search_count([
                ('treatment_doctor', '=', record.treatment_doctor),
                ('mdr', '=', record.mdr),
                ('patient_name', '=', record.patient_name),
                ('clinic', '=', record.clinic),
                ('create_date', '>=', self.env.cr.now() - timedelta(days=3))
            ])
            if records > 1:
                raise ValidationError(f"Duplicate record found within 3 days: Patient Name: {record.patient_name}, MDR: {record.mdr}, Treatment Doctor: {record.treatment_doctor}, Clinic: {record.clinic}")