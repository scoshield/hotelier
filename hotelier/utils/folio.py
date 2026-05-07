import frappe
from frappe.utils import now_datetime, flt


def add_invoice_to_folio(doc):
    # 1. Check if the guest has an open reservation
    guest = frappe.db.get_value(
        "Room Reservation", {"guest_name": doc.customer, "docstatus": 0}, "name"
    )

    if not guest:
        return

    # 2. Find Open Folio
    folio_name = frappe.db.get_value(
        "Folio", {"guest": doc.customer, "docstatus": 0}, "name"
    )

    if not folio_name:
        # frappe.throw(f"No Open Folio found for customer {doc.customer}")
        # return
        folio = frappe.get_doc(
            {
                "doctype": "Folio",
                "guest": doc.customer,
                "reservation": guest,
                "total": doc.grand_total,
                "amount_paid": doc.paid_amount,
                "balance": doc.outstanding_amount,
                "status": "Open",
                "folio_type": "Guest",
            }
        )
        folio.insert()
        folio_name = folio.name

    folio = frappe.get_doc("Folio", folio_name)

    # 3. Loop Invoice Items
    for item in doc.items:
        folio_item = frappe.get_doc(
            {
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
            }
        )

        folio_item.insert(ignore_permissions=True)

    update_folio_total(folio_name)


# def get_or_create_folio(doc):
#     """Return an existing open Folio for the guest or create a new one"""
#     folio_name = frappe.db.get_value(
#         "Folio",
#         filters={"guest": doc.guest_name, "docstatus": 0},
#         fieldname="name",
#     )
#     if folio_name:
#         return folio_name

#     folio = frappe.get_doc(
#         {
#             "doctype": "Folio",
#             "guest": doc.guest_name,
#             "reservation": doc.name,
#             "total": doc.net_total,
#             "amount_paid": doc.amount_paid,
#             "balance": doc.balance,
#             "status": "Open",
#             "folio_type": "Guest",
#         }
#     )
#     folio.insert()
#     return folio.name


def update_folio_total(folio_name):
    """
    Recalculate Folio totals safely from source records.
    """

    if not folio_name:
        return

    # ---------------------------------------------------
    # 1. Calculate Folio Total from Folio Items
    # ---------------------------------------------------

    total = flt(
        frappe.db.sql(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM `tabFolio Item`
            WHERE folio = %s
            """,
            (folio_name,),
        )[0][0]
    )

    # ---------------------------------------------------
    # 2. Calculate Total Paid from Payment Entries
    #    (SOURCE OF TRUTH FOR PAYMENTS)
    # ---------------------------------------------------

    amount_paid = flt(frappe.db.get_value("Folio", folio_name, "amount_paid") or 0)

    # ---------------------------------------------------
    # 3. Calculate Balance
    # ---------------------------------------------------

    balance = total - amount_paid

    # Prevent negative balance if overpaid
    if balance < 0:
        balance = 0

    # ---------------------------------------------------
    # 4. Update Folio
    # ---------------------------------------------------

    frappe.db.set_value(
        "Folio",
        folio_name,
        {
            "total": total,
            "amount_paid": amount_paid,
            "balance": balance,
        },
        update_modified=False,
    )


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
    item_type="Other",
):
    # 🔹 Step 1: Find active folio using 'guest' field
    folio_name = frappe.get_value("Folio", {"guest": guest, "docstatus": 0})

    if not folio_name:
        frappe.log_error(f"No active folio for guest {guest}", "Folio Missing")
        return

    folio = frappe.get_doc("Folio", folio_name)

    # 🔹 Step 2: Prevent duplicates
    exists = frappe.db.exists(
        "Folio Item",
        {"reference_doctype": reference_doctype, "reference_name": reference_name},
    )

    if exists:
        return

    # 🔹 Step 3: Append item safely
    folio.append(
        "items",
        {
            "item_type": item_type,
            "description": description,
            "amount": amount,
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "date": posting_date,
        },
    )

    # 🔹 Step 4: Save
    folio.save(ignore_permissions=True)
