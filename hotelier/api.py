import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime
from collections import defaultdict


@frappe.whitelist()
def auto_consume_ingredients(pos_closing_entry):

    # Guard against duplicate consumption entries
    # existing_entry = frappe.db.get_value(
    #     "Stock Entry",
    #     {
    #         "pos_closing_entry": pos_closing_entry,
    #         "docstatus": ["!=", 2],  # Not cancelled
    #     },
    #     "name",
    # )

    # if existing_entry:
    #     frappe.throw(
    #         _(
    #             "A Stock Entry ({0}) already exists for this closing entry. "
    #             "Cancel it first before regenerating.".format(existing_entry)
    #         )
    #     )
    """
    Called from POS Closing Entry via a custom button.
    Reads all POS Invoices for this closing session,
    looks up each item's active BOM, consolidates all
    ingredient quantities, and creates a single
    Material Issue Stock Entry.
    """

    # -----------------------------------------------
    # STEP 1 — Load the POS Closing Entry
    # -----------------------------------------------
    closing = frappe.get_doc("POS Closing Entry", pos_closing_entry)

    if closing.docstatus != 0:
        frappe.throw(
            _("Stock Entry can only be created for a Draft POS Closing Entry.")
        )

    pos_profile = closing.pos_profile
    period_start = closing.period_start_date
    period_end = closing.period_end_date

    # -----------------------------------------------
    # STEP 2 — Fetch all submitted POS Invoices
    #          for this profile within the shift window
    # -----------------------------------------------
    invoices = frappe.get_all(
        "POS Invoice",
        filters={
            "pos_profile": pos_profile,
            "docstatus": 1,  # Submitted only
            "posting_date": ["between", [period_start, period_end]],
        },
        fields=["name"],
    )

    if not invoices:
        frappe.throw(_("No submitted POS Invoices found for this closing period."))

    invoice_names = [inv["name"] for inv in invoices]

    # -----------------------------------------------
    # STEP 3 — Aggregate total qty sold per item
    # -----------------------------------------------
    # We query POS Invoice Item child table directly
    # to get item + qty across all invoices in one shot

    sold_items = frappe.get_all(
        "POS Invoice Item",
        filters={"parent": ["in", invoice_names]},
        fields=["item_code", "qty"],
    )

    # Sum quantities per item_code
    qty_sold = defaultdict(float)
    for row in sold_items:
        qty_sold[row["item_code"]] += row["qty"]

    if not qty_sold:
        frappe.throw(_("No items found in the invoices for this closing period."))

    # -----------------------------------------------
    # STEP 4 — For each item sold, look up its BOM
    #          and calculate ingredient consumption
    # -----------------------------------------------
    # consolidated_ingredients holds:
    # { (item_code, warehouse): total_qty_to_consume }

    consolidated_ingredients = defaultdict(float)
    items_without_bom = []

    for item_code, total_qty in qty_sold.items():

        # Fetch the default active BOM for this item
        bom_name = frappe.db.get_value(
            "BOM",
            {"item": item_code, "is_active": 1, "is_default": 1, "docstatus": 1},
            "name",
        )

        if not bom_name:
            # Item has no BOM — it is a raw stock item
            # (e.g. a whole bottle sold as-is)
            # Skip it — its stock was already deducted
            # directly by the POS invoice if it is a
            # stock item, or it needs no deduction if
            # it is a non-stock item with no BOM.
            items_without_bom.append(item_code)
            continue

        # Load the full BOM document
        bom = frappe.get_doc("BOM", bom_name)

        # BOM qty is the batch size the recipe is
        # written for (e.g. BOM qty = 1 means the
        # recipe makes 1 Mojito)
        bom_qty = bom.quantity or 1

        # Multiplier: if we sold 18 Mojitos and the
        # BOM is written for 1, multiplier = 18
        multiplier = total_qty / bom_qty

        for ingredient in bom.items:
            key = (ingredient.item_code, ingredient.source_warehouse or "Bar Store")
            consolidated_ingredients[key] += ingredient.qty * multiplier

    # -----------------------------------------------
    # STEP 5 — Build and insert the Stock Entry
    # -----------------------------------------------
    if not consolidated_ingredients:
        frappe.throw(
            _(
                "No BOM-based ingredients found to consume. "
                "Items without a BOM: {0}".format(", ".join(items_without_bom))
            )
        )

    # Determine the default expense account for
    # stock write-offs (used in Material Issue)
    company = frappe.db.get_value("POS Profile", pos_profile, "company")

    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Issue"
    se.company = company
    se.posting_date = nowdate()
    se.posting_time = now_datetime().strftime("%H:%M:%S")
    se.remarks = (
        "Auto ingredient consumption for POS Closing Entry: "
        "{0} | Profile: {1}".format(pos_closing_entry, pos_profile)
    )

    # Custom field — links this Stock Entry back to
    # the POS Closing Entry for traceability.
    # You must create this custom field manually:
    # Stock Entry → pos_closing_entry (Link → POS Closing Entry)
    se.pos_closing_entry = pos_closing_entry

    for (item_code, warehouse), qty in consolidated_ingredients.items():
        se.append(
            "items",
            {
                "item_code": item_code,
                "qty": round(qty, 4),
                "s_warehouse": warehouse,
            },
        )

    se.insert()

    # Return the Stock Entry name so the front-end
    # can show a success message and a direct link
    return {
        "stock_entry": se.name,
        "items_without_bom": items_without_bom,
        "total_ingredients": len(consolidated_ingredients),
    }
