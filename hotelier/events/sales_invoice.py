import frappe
from hotelier.utils.folio import *


def on_submit(doc, method):
    customer = doc.customer

    if not customer:
        # return
        frappe.throw("Customer is required")

    add_invoice_to_folio(doc)


def on_cancel(doc, method):
    frappe.db.delete("Folio Item", {
        "reference_doctype": "Sales Invoice",
        "reference_name": doc.name
    })


def get_item_type(doc):
    for item in doc.items:
        if item.item_group == "Bar":
            return "Bar"
    return "Restaurant"