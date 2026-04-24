import frappe
from frappe.utils import now_datetime, flt


def add_invoice_to_folio(doc):
    # 1. Find Open Folio
    folio_name = frappe.db.get_value(
        "Folio",
        {
            "guest": doc.customer,
            "status": "Open"
        },
        "name"
    )

    if not folio_name:
        frappe.throw(f"No Open Folio found for customer {doc.customer}")

    folio = frappe.get_doc("Folio", folio_name)

    # 2. Loop Invoice Items
    for item in doc.items:
        folio_item = frappe.get_doc({
            "doctype": "Folio Item",
            "folio": folio_name,
            "reference_doctype": "Sales Invoice",
            "reference_name": doc.name,
            "item_type": get_item_type(item),
            "description": item.item_name,
            "quantity": item.qty,
            "rate": item.rate,
            "amount": item.amount,
            "date": now_datetime(),
        })

        folio_item.insert(ignore_permissions=True)
        
    update_folio_total(folio_name, doc)
    
def update_folio_total(folio_name, doc):
    # 1. Total from ledger (SOURCE OF TRUTH)
    total = flt(frappe.db.sql("""
        SELECT SUM(amount)
        FROM `tabFolio Item`
        WHERE folio = %s
    """, folio_name)[0][0] or 0)
    
    if doc.paid_amount:
        current_paid = frappe.db.get_value("Folio", folio_name, "amount_paid") or 0

        frappe.db.set_value("Folio", folio_name, {
            "amount_paid": current_paid + doc.paid_amount
        })

    # 2. Paid amount (from payments or manual updates)
    amount_paid = flt(frappe.db.get_value(
        "Folio",
        folio_name,
        "amount_paid"
    ) or 0)

    # 3. Balance
    balance = total - amount_paid

    # 4. Update Folio
    frappe.db.set_value("Folio", folio_name, {
        "total": total,
        "amount_paid": amount_paid,
        "balance": balance
    })
    
    
def get_item_type(item):
    if item.item_group:
        return "Restaurant"    
    else:
        return "Other"


def add_charge_to_folio(
    guest,
    amount,
    reference_doctype,
    reference_name,
    description=None,
    posting_date=None,
    item_type="Other"
):
    # 🔹 Step 1: Find active folio using 'guest' field
    folio_name = frappe.get_value("Folio", {
        "guest": guest,
        "docstatus": 1
    })

    if not folio_name:
        frappe.log_error(f"No active folio for guest {guest}", "Folio Missing")
        return

    folio = frappe.get_doc("Folio", folio_name)

    # 🔹 Step 2: Prevent duplicates
    exists = frappe.db.exists("Folio Item", {
        "reference_doctype": reference_doctype,
        "reference_name": reference_name
    })

    if exists:
        return

    # 🔹 Step 3: Append item safely
    folio.append("items", {
        "item_type": item_type,
        "description": description,
        "amount": amount,
        "reference_doctype": reference_doctype,
        "reference_name": reference_name,
        "date": posting_date
    })

    # 🔹 Step 4: Save
    folio.save(ignore_permissions=True)