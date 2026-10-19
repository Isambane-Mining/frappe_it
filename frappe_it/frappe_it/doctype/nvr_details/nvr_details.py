# Copyright (c) 2026, BuFf0k
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import escape_html, get_url_to_form

from frappe_it.frappe_it.utils import device_url_for


class NVRDetails(Document):
    def validate(self):
        self.ip_address = (self.ip_address or "").strip()
        self.device_url = device_url_for(self.ip_address)


@frappe.whitelist()
def get_linked_cameras_html(nvr_details_name: str) -> str:
    """
    Render the linked IP Camera Details as a table (list view with columns),
    replacing the old virtual child table implementation. Credentials are
    never rendered - open the camera record to see them.
    """
    if not nvr_details_name or nvr_details_name.startswith("new-"):
        return """
        <div class="it-linked-panel">
          <div class="it-linked-panel__empty">
            Linked cameras will appear here once the record is saved.
          </div>
        </div>
        """

    frappe.has_permission("NVR Details", "read", doc=nvr_details_name, throw=True)

    cameras = frappe.get_list(
        "IP Camera Details",
        filters={"linked_to_nvr": nvr_details_name},
        fields=["name", "ip_address", "location", "camera_link"],
        order_by="modified desc",
    ) or []

    if not cameras:
        return """
        <div class="it-linked-panel">
          <div class="it-linked-panel__empty">No linked cameras found.</div>
        </div>
        """

    rows_html = []
    for c in cameras:
        doc_url = get_url_to_form("IP Camera Details", c.name)

        camera_link_html = ""
        if c.camera_link:
            camera_link_html = f"""
              <a class="it-linked-panel__link" href="{escape_html(c.camera_link)}" target="_blank" rel="noopener">
                Open
              </a>
            """

        rows_html.append(
            f"""
            <tr>
              <td>
                <a class="it-linked-panel__link" href="{escape_html(doc_url)}" target="_blank" rel="noopener">
                  {escape_html(c.name)}
                </a>
              </td>
              <td class="it-linked-panel__mono">{escape_html(c.ip_address or "")}</td>
              <td class="it-linked-panel__truncate" title="{escape_html(c.location or "")}">
                {escape_html(c.location or "")}
              </td>
              <td>{camera_link_html}</td>
            </tr>
            """
        )

    return f"""
    <div class="it-linked-panel">
      <div class="it-linked-panel__header">
        <div class="it-linked-panel__title">Linked Cameras</div>
        <div class="it-linked-panel__count">{len(cameras)}</div>
      </div>

      <div class="it-linked-panel__table-wrap">
        <table class="table table-bordered table-hover">
          <thead>
            <tr>
              <th>Camera</th>
              <th>IP Address</th>
              <th>Location</th>
              <th>Camera Link</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows_html)}
          </tbody>
        </table>
      </div>
    </div>
    """
