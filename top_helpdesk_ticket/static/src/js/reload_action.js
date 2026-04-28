/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardAction } from "@web/webclient/actions/action_service";

registry.category("actions").add("reload_filtered_helpdesk_action", standardAction.extend({
    async start(env, action) {
        const result = await env.services.orm.call(
            "helpdesk.ticket",
            "get_action_filtered_by_user",
            []
        );
        env.services.action.doAction(result);
        return Promise.resolve();
    },
}));
