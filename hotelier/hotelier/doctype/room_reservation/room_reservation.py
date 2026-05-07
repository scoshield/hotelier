# Copyright (c) 2026, BluChip Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


class RoomReservation(Document):
    def on_submit(self):
        """
        On submitting a Room Reservation:
        1. Create a Folio for the guest if not already open
        2. Create Folio Item entries for each booked item
        """
        folio_name = self.get_or_create_folio()

        # Loop through items (rooms or other bookings)
        for item in getattr(self, "items", []):  # services child table is 'items'
            self.create_folio_item(folio_name, item)

            # Optionally update the total in the folio
            # self.update_folio_total(folio_name, item)

        for item in getattr(
            self, "room_reservation", []
        ):  # room reservation child table is 'items'
            self.create_folio_reservation(folio_name, item)

        # Optionally update the total in the folio
        # self.update_folio_total(folio_name, item)

    def get_or_create_folio(self):
        """Return an existing open Folio for the guest or create a new one"""
        folio_name = frappe.db.get_value(
            "Folio",
            filters={"guest": self.guest_name, "docstatus": 0},
            fieldname="name",
        )
        if folio_name:
            return folio_name

        folio = frappe.get_doc(
            {
                "doctype": "Folio",
                "guest": self.guest_name,
                "reservation": self.name,
                "total": self.net_total,
                "amount_paid": self.amount_paid,
                "balance": self.balance,
                "status": "Open",
                "folio_type": "Guest",
            }
        )
        folio.insert()
        return folio.name

    def create_folio_item(self, folio_name, item):
        """Create a Folio Item linked to the Folio"""
        # Determine quantity: for rooms, use period; for other items, quantity field
        quantity = flt(getattr(item, "quantity", 0)) or flt(
            getattr(item, "qty", 1)
        )
        rate = flt(getattr(item, "rate", 0))
        amount = rate * quantity

        folio_item = frappe.get_doc(
            {
                "doctype": "Folio Item",
                "folio": folio_name,
                "reference_doctype": "Room Service",
                "reference_name": self.name,
                "item_type": getattr(
                    item, "item_type", "Room"
                ),  # e.g., Room, Restaurant
                "description": getattr(item, "description", ""),
                "quantity": quantity,
                "rate": rate,
                "amount": amount,
                "date": now_datetime(),
            }
        )
        folio_item.insert()

    def create_folio_reservation(self, folio_name, item):
        """Create a Folio Item linked to the Folio"""
        # Determine quantity: for rooms, use period; for other items, quantity field
        quantity = flt(getattr(item, "period_of_stay", 0)) or flt(
            getattr(item, "qty", 1)
        )
        rate = flt(getattr(item, "rate", 0))
        amount = rate * quantity

        folio_item = frappe.get_doc(
            {
                "doctype": "Folio Item",
                "folio": folio_name,
                "reference_doctype": "Room Reservation",
                "reference_name": self.name,
                "item_type": getattr(
                    item, "item_type", "Room"
                ),  # e.g., Room, Restaurant
                "description": getattr(item, "description", ""),
                "quantity": quantity,
                "rate": rate,
                "amount": amount,
                "date": now_datetime(),
            }
        )
        folio_item.insert()

    def update_folio_total(self, folio_name, item):
        """Update the total field in Folio based on all linked Folio Items"""
        total = flt(
            frappe.db.sql(
                """
            SELECT SUM(amount) FROM `tabFolio Item`
            WHERE folio=%s
        """,
                folio_name,
            )[0][0]
            or 0
        )

        frappe.db.set_value(
            "Folio",
            folio_name,
            {
                "total": self.net_total,
                "amount_paid": self.amount_paid,
                "balance": self.balance,
            },
        )
        """Create a Folio Item for each room or service"""
        # Calculate quantity: for rooms, it's the period (number of nights)
        quantity = (
            flt(item.period_of_stay)
            if hasattr(item, "period_of_stay")
            else flt(item.quantity or 1)
        )
        rate = flt(item.rate or 0)
        total = quantity * rate

        # folio_item = frappe.get_doc({
        #     "doctype": "Folio Item",
        #     "folio": folio_name,
        #     "reference_doctype": "Room",
        #     "reference_name": self.name,
        #     "item": item.item,
        #     "description": getattr(item, "description", ""),
        #     "rate": rate,
        #     "quantity": quantity,
        #     "total": total
        # })
        # folio_item.insert()
