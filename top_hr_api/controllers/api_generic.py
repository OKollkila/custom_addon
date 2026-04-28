import json
import base64
from odoo import http
from odoo.http import request, Response

# ---- SECURITY: allow all or restrict to selected models ----
ALLOW_ALL_MODELS = True
ALLOWED_MODELS = {
    "crm.lead",
    "helpdesk.ticket",
    "res.partner",
    "clinizone.branch"
}

# Binary fields you may want to exclude by default
DEFAULT_BINARY_FIELD_BLOCKLIST = {
    "image_1920", "image_1024", "image_512", "image_256", "image_128",
}

def _json(payload, status=200):
    return Response(
        json.dumps(payload, default=str),
        status=status,
        content_type="application/json; charset=utf-8",
    )

def _normalize_model_name(name):
    """Accept 'crm.lead', 'crm_lead', 'crm/lead' and return a valid model name."""
    if not name:
        return None
    variants = {name, name.replace("/", "."), name.replace("_", ".")}
    for cand in variants:
        if cand in request.env:
            return cand
    return name if name in request.env else None

def _get_model(model_name):
    m = _normalize_model_name(model_name)
    if not m:
        raise ValueError(f"Unknown model: {model_name}")
    if not (ALLOW_ALL_MODELS or m in ALLOWED_MODELS):
        raise ValueError(f"Access to model '{m}' is not allowed")
    return request.env[m].sudo(), m

def _looks_base64(s):
    if not isinstance(s, str):
        return False
    try:
        base64.b64decode(s, validate=True)
        return True
    except Exception:
        return False

def _handle_attachments(attachments, res_model, res_id, mode="append"):
    if not attachments:
        return
    Attach = request.env["ir.attachment"].sudo()
    if mode == "replace":
        old = Attach.search([("res_model", "=", res_model), ("res_id", "=", res_id)])
        if old:
            old.unlink()
    for att in attachments:
        name = att.get("name") or "attachment"
        mimetype = att.get("mimetype") or "application/octet-stream"
        data = att.get("data")
        if not data:
            continue
        datas = data if _looks_base64(data) else base64.b64encode(str(data).encode()).decode()
        Attach.create({
            "name": name,
            "mimetype": mimetype,
            "datas": datas,
            "res_model": res_model,
            "res_id": res_id,
        })

def _coerce_relational(Record, field_name, raw):
    """Coerce many2one/many2many/one2many values from flexible JSON forms."""
    f = Record._fields[field_name]
    if f.type == "many2one":
        M = request.env[f.comodel_name].sudo()
        if isinstance(raw, int):
            return raw
        if isinstance(raw, dict) and raw.get("id"):
            return int(raw["id"])
        if isinstance(raw, dict) and isinstance(raw.get("domain"), list):
            rec = M.search(raw["domain"], limit=1)
            return rec.id or False
        if isinstance(raw, dict) and raw.get("name"):
            rec = M.search([("name", "=", raw["name"])], limit=1)
            return rec.id or False
        if isinstance(raw, dict) and raw.get("value") is not None:
            lookup = raw.get("lookup") or "name"
            rec = M.search([(lookup, "=", raw["value"])], limit=1)
            return rec.id or False
        if isinstance(raw, dict) and raw.get("create"):
            vals = {k: v for k, v in raw["create"].items() if k in M._fields}
            return M.create(vals).id
        if isinstance(raw, str):
            rec = M.search([("name", "=", raw)], limit=1)
            return rec.id or False
        return False

    if f.type == "many2many":
        M = request.env[f.comodel_name].sudo()
        ids = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, int):
                    ids.append(item)
                elif isinstance(item, dict):
                    if item.get("id"):
                        ids.append(int(item["id"]))
                    elif item.get("name"):
                        rec = M.search([("name", "=", item["name"])], limit=1)
                        if rec:
                            ids.append(rec.id)
                    elif item.get("domain"):
                        recs = M.search(item["domain"])
                        ids += recs.ids
                    elif item.get("create"):
                        vals = {k: v for k, v in item["create"].items() if k in M._fields}
                        ids.append(M.create(vals).id)
                elif isinstance(item, str):
                    rec = M.search([("name", "=", item)], limit=1)
                    if rec:
                        ids.append(rec.id)
        return [(6, 0, list(set(map(int, ids))))]

    if f.type == "one2many":
        if isinstance(raw, list):
            cmds = []
            for item in raw:
                if isinstance(item, (list, tuple)):
                    cmds.append(item)
                    continue
                if isinstance(item, dict):
                    if "create" in item:
                        vals = item["create"]
                        cmds.append([0, 0, vals])
                    elif "link" in item:
                        cmds.append([4, int(item["link"]), 0])
                    elif "unlink" in item:
                        cmds.append([3, int(item["unlink"]), 0])
                    elif "delete" in item:
                        cmds.append([2, int(item["delete"]), 0])
                    elif "replace" in item and isinstance(item["replace"], list):
                        cmds.append([6, 0, list(map(int, item["replace"]))])
                    elif "update" in item and isinstance(item["update"], dict):
                        _id = int(item["update"].get("id"))
                        _vals = item["update"].get("vals") or {}
                        cmds.append([1, _id, _vals])
            return cmds
        return False

    return False

def _build_vals(Model, payload):
    """Build create/write vals from payload (ignores unknown keys)."""
    fields_map = Model._fields
    vals = {}
    for k, v in payload.items():
        if k in ("defaults", "attachments", "attachments_mode"):
            continue
        if k not in fields_map:
            continue
        f = fields_map[k]
        if f.type in ("char", "text", "html", "float", "integer", "boolean",
                      "selection", "date", "datetime", "monetary", "binary"):
            vals[k] = v
        elif f.type in ("many2one", "many2many", "one2many"):
            coerced = _coerce_relational(Model, k, v)
            if coerced not in (False, None):
                vals[k] = coerced
    return vals

def _parse_body(kwargs):
    """
    Robust JSON body parser for type='http' routes.
    - If Content-Type is application/json: read raw body and json.loads it.
    - Else: fall back to kwargs (for form-data / x-www-form-urlencoded).
    """
    try:
        httpreq = request.httprequest  # Werkzeug request
        if (httpreq.mimetype or "").lower() == "application/json":
            raw = httpreq.get_data(cache=False, as_text=True)
            if raw:
                return json.loads(raw)
    except Exception:
        pass
    return kwargs or {}
def _prepare_fields_for_output(Model, requested_fields):
    """Determine which fields to output and avoid heavy binaries by default."""
    if requested_fields:
        fields_list = [f for f in requested_fields if f in Model._fields]
    else:
        # default to stored non-binary fields (skip common image blobs)
        fields_list = [
            n for n, f in Model._fields.items()
            if getattr(f, "store", False)
            and not (f.type == "binary" and n in DEFAULT_BINARY_FIELD_BLOCKLIST)
        ]
    return fields_list

def _serialize_record(rec, fields_list):
    row = {}
    for f in fields_list:
        if f not in rec._fields:
            continue
        field = rec._fields[f]
        val = rec[f]
        if field.type == "many2one":
            row[f] = {"id": val.id, "name": val.display_name} if val else None
        elif field.type in ("many2many", "one2many"):
            row[f] = [{"id": x.id, "name": x.display_name} for x in val]
        else:
            row[f] = val
    return row

class GenericAPI(http.Controller):

    @http.route("/api/<string:model>/fields", type="http", auth="bearer", methods=["GET"], csrf=False)
    def fields(self, model, **kwargs):
        try:
            Model, model_name = _get_model(model)
            meta = {}
            for name, f in Model._fields.items():
                meta[name] = {
                    "type": f.type,
                    "required": bool(getattr(f, "required", False)),
                    "relation": getattr(f, "comodel_name", None),
                    "store": bool(getattr(f, "store", False)),
                    "readonly": bool(getattr(f, "readonly", False)),
                }
            return _json({"ok": True, "model": model_name, "fields": meta})
        except Exception as e:
            return _json({"ok": False, "error": str(e)}, status=400)

    # ============================================================================================

    # @http.route("/api/<string:model>/create", type="http", auth="bearer", methods=["POST"], csrf=False)
    # def create(self, model, **kwargs):
    #     try:
    #         Model, model_name = _get_model(model)
    #         body = _parse_body(kwargs)
    #         defaults = body.get("defaults") or {}
    #         attachments = body.get("attachments") or []
    #         attachments_mode = (body.get("attachments_mode") or "append").lower()
    #
    #         vals = dict(defaults)
    #         vals.update(_build_vals(Model, body))
    #
    #         rec = Model.create(vals)
    #
    #         if attachments:
    #             _handle_attachments(attachments, model_name, rec.id, mode=attachments_mode)
    #
    #         return _json({"ok": True, "model": model_name, "id": rec.id})
    #     except Exception as e:
    #         return _json({"ok": False, "error": str(e)}, status=400)

    # ============================================================================================

    @http.route("/api/<string:model>/<int:rec_id>", type="http", auth="bearer", methods=["GET"], csrf=False)
    def read(self, model, rec_id, **kwargs):
        try:
            Model, model_name = _get_model(model)
            rec = Model.browse(rec_id)
            if not rec.exists():
                return _json({"ok": False, "error": "Record not found"}, status=404)

            fields_param = kwargs.get("fields")
            fields_list = _prepare_fields_for_output(Model, [f.strip() for f in fields_param.split(",")] if fields_param else [])

            data = _serialize_record(rec, fields_list)
            return _json({"ok": True, "model": model_name, "data": data})
        except Exception as e:
            return _json({"ok": False, "error": str(e)}, status=400)

    # ============================================================================================

    @http.route("/api/<string:model>/update/<int:rec_id>", type="http", auth="bearer", methods=["POST", "PUT", "PATCH"], csrf=False)
    def update(self, model, rec_id, **kwargs):
        try:
            Model, model_name = _get_model(model)
            rec = Model.browse(rec_id)
            if not rec.exists():
                return _json({"ok": False, "error": "Record not found"}, status=404)

            body = _parse_body(kwargs)
            attachments = body.get("attachments") or []
            attachments_mode = (body.get("attachments_mode") or "append").lower()

            vals = _build_vals(Model, body)
            if vals:
                rec.write(vals)

            if attachments:
                _handle_attachments(attachments, model_name, rec.id, mode=attachments_mode)

            return _json({"ok": True, "model": model_name, "id": rec.id})
        except Exception as e:
            return _json({"ok": False, "error": str(e)}, status=400)

    # ============================================================================================

    @http.route("/api/<string:model>/search_read", type="http", auth="bearer", methods=["POST"], csrf=False)
    def search_read(self, model, **kwargs):
        try:
            Model, model_name = _get_model(model)
            body = _parse_body(kwargs)

            domain = body.get("domain") or []
            requested_fields = body.get("fields") or []
            limit = int(body.get("limit") or 80)
            offset = int(body.get("offset") or 0)
            order = body.get("order") or "id desc"

            fields_list = _prepare_fields_for_output(Model, requested_fields)

            total = Model.search_count(domain)
            recs = Model.search(domain, limit=limit, offset=offset, order=order)

            data = [_serialize_record(r, fields_list) for r in recs]
            return _json({"ok": True, "model": model_name, "total": total, "returned": len(recs), "data": data})
        except Exception as e:
            return _json({"ok": False, "error": str(e)}, status=400)
   #============================================================================================
    @http.route("/api/<string:model>/delete/<int:rec_id>", type="http", auth="bearer", methods=["DELETE"], csrf=False)
    def delete(self, model, rec_id, **kwargs):
        try:
            Model, model_name = _get_model(model)
            rec = Model.browse(rec_id)
            if not rec.exists():
                return _json({"ok": False, "error": "Record not found"}, status=404)
            rec.unlink()
            return _json({"ok": True, "model": model_name, "deleted_id": rec_id})
        except Exception as e:
            return _json({"ok": False, "error": str(e)}, status=400)
