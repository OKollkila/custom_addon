from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    prime_care_pending_invoice_login_url = fields.Char(string='Prime Care Missed Invoice Login URL')
    prime_care_pending_invoice_url = fields.Char(string='Prime Care Missed Invoice URL')
    prime_care_pending_invoice_company = fields.Char(string='Prime Care Missed Invoice Company')
    prime_care_pending_invoice_division = fields.Char(string='Prime Care Missed Invoice Division')
    prime_care_pending_invoice_username = fields.Char(string='Prime Care Missed Invoice Username')
    prime_care_pending_invoice_password = fields.Char(string='Prime Care Missed Invoice Password')
    prime_care_pending_invoice_token = fields.Char(string='Prime Care Missed Invoice Token')
    
    # Above Amount Invoice API Settings
    above_amount_invoice_url = fields.Char(
        string='Above Amount Invoice URL',
        help='API URL for invoices above amount (without date parameter)',
        default='http://15.184.10.121:8080/HISAdmin/api/invoice/invoicesAboveAnAmount'
    )
    above_amount_invoice_token = fields.Char(
        string='Above Amount Invoice Token',
        help='Bearer token for API authentication (optional)'
    )
    
    # Pending Referral API Settings
    pending_referral_url = fields.Char(
        string='Pending Referral URL',
        help='API URL for pending and rejected referrals (without date parameter)',
        default='http://15.184.10.121:8080/HISAdmin/api/referral/findPendingAndRejectedReferrals'
    )
    pending_referral_token = fields.Char(
        string='Pending Referral Token',
        help='Bearer token for API authentication (optional)'
    )
    
    # DNA Appointment API Settings
    dna_appointment_url = fields.Char(
        string='DNA Appointment URL',
        help='API URL for DNA (Did Not Attend) appointments (without date parameter)',
        default='http://15.184.10.121:8080/HISAdmin/api/appointment/findAllDNAAppointmentsByDateAndBranch'
    )
    dna_appointment_token = fields.Char(
        string='DNA Appointment Token',
        help='Bearer token for API authentication (optional)'
    )
    
    # Booked Appointment API Settings
    booked_appointment_url = fields.Char(
        string='Booked Appointment URL',
        help='API URL for booked appointments (without date parameter)',
        default='http://15.184.10.121:8080/HISAdmin/api/appointment/findAllBookedAppointmentsByDateAndBranch'
    )
    booked_appointment_token = fields.Char(
        string='Booked Appointment Token',
        help='Bearer token for API authentication (optional)'
    )