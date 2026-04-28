from . import models
from . import controllers

def post_init_hook(env):
    """
    Migration: Set workflow_level_id for existing tickets.
    - If old column workflow_level (char) exists, set workflow_level_id from workflow_level by code.
    - If workflow_level_id is null, set to first workflow level.
    Called with (env) on Odoo 16+; use env.cr for raw SQL.
    """
    cr = env.cr
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'helpdesk_ticket' AND column_name IN ('workflow_level', 'workflow_level_id')
    """)
    cols = {r[0] for r in cr.fetchall()}
    
    if 'workflow_level_id' in cols:
        if 'workflow_level' in cols:
            # Migrate from old workflow_level (char) to workflow_level_id
            cr.execute("""
                UPDATE helpdesk_ticket t
                SET workflow_level_id = w.id
                FROM workflow_level w
                WHERE w.code = t.workflow_level AND t.workflow_level IS NOT NULL AND t.workflow_level != ''
            """)
        # Set any remaining null to first level
        cr.execute("""
            UPDATE helpdesk_ticket t
            SET workflow_level_id = (SELECT id FROM workflow_level ORDER BY sequence LIMIT 1)
            WHERE t.workflow_level_id IS NULL
        """)
