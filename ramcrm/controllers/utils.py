def find_matching_lead_source(env, lead_source):
    lead_source = lead_source.strip()
    original_lead_source = lead_source
    if not lead_source:
        return False
    lead_source = lead_source.split()[0]


    mapping = {
        'googlesearch': 'Google Search',
    }

    if lead_source in mapping:
        lead_source = mapping[lead_source]

    lead_source_id = env['clinizone.lead_source'].sudo().search([('name', 'ilike', lead_source)], limit=1)

    if not lead_source_id:
        if True: # TODO: Add a condition to check if we should create a new lead source
            lead_source_id = env['clinizone.lead_source'].sudo().create({'name': original_lead_source})

    return lead_source_id

def validate_service_id(env, the_service_id):
    if not the_service_id:
        return False

    service_id = env['clinizone.service'].search([('id', '=', the_service_id)], limit=1)
    if not service_id:
        return False

    return service_id