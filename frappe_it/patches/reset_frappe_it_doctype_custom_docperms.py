"""One-time cleanup: delete every Custom DocPerm row for a doctype this app
owns (module == "Frappe IT"), on every site - prod included.

These rows had drifted from this app's own DocType JSON permissions, and
Custom DocPerm always takes precedence over the DocType's own "permissions"
array once it exists for a role - so the live site was never actually
running what this app's own source said it should. The doctype JSON files
have now been corrected to match what the stale Custom DocPerm rows actually
granted, so the Custom DocPerm rows are now pure liability - they'd keep
shadowing the correct, git-tracked permissions on every site that already
has them.

Runs pre-model-sync, before fixture import would otherwise try to recreate
the (now intentionally removed) entries in
frappe_it/fixtures/custom_docperm.json. Any OTHER app's legitimate Custom
DocPerm rows on a Frappe IT-owned doctype (if any exist) will be restored
right after by that app's own fixture sync, later in the same migrate run -
Custom DocPerm rows are owned by the app that created them for its own
roles, not by the app that owns the doctype.

Standard one-time patch - Frappe's Patch Log ensures this never runs twice
on the same site.
"""

import frappe


def execute():
    owned_doctypes = frappe.get_all("DocType", filters={"module": "Frappe IT"}, pluck="name")
    if not owned_doctypes:
        return

    frappe.db.delete("Custom DocPerm", {"parent": ["in", owned_doctypes]})
    frappe.clear_cache()
