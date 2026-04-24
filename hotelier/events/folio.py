import frappe
from frappe.utils import flt

def on_submit(doc, method):
    submit_folio_items(doc)
    
def submit_folio_items(doc):
    # Get all Folio Items linked to this Folio
    folio_items = frappe.get_all(
        "Folio Item",
        filters={"folio": doc.name, "docstatus": 0},
        pluck="name"
    )

    for item_name in folio_items:
        item = frappe.get_doc("Folio Item", item_name)
        item.submit()
        
def on_cancel(doc, method):
    folio_items = frappe.get_all(
        "Folio Item",
        filters={"folio": doc.name, "docstatus": 1},
        pluck="name"
    )

    for item_name in folio_items:
        item = frappe.get_doc("Folio Item", item_name)
        item.cancel()
        
def validate_folio_before_submit(doc, method):

    # 1. Recalculate TOTAL from ledger (source of truth)
    total = flt(frappe.db.sql("""
        SELECT SUM(amount)
        FROM `tabFolio Item`
        WHERE folio = %s
    """, doc.name)[0][0] or 0)

    # 2. Paid amount (from Folio or payment table)
    paid = flt(doc.amount_paid)

    # 3. Balance
    balance = total - paid

    # 4. Sync values BEFORE validation
    doc.total = total
    doc.balance = balance

    # 5. HARD BLOCK conditions
    if doc.status == "Open":
        frappe.throw("Cannot submit an open Folio. Change status to Paid")
        
    if balance > 0:
        frappe.throw(
            f"Cannot submit Folio {doc.name}. Outstanding balance: {balance}"
        )

    if total == 0:
        frappe.throw("Cannot submit an empty Folio")