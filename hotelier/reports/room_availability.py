import frappe
from frappe.utils import getdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Room",
            "fieldname": "room",
            "fieldtype": "Link",
            "options": "Room",
            "width": 120
        },
        {
            "label": "Room Type",
            "fieldname": "room_type",
            "fieldtype": "Data",
            "width": 140
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Occupancy",
            "fieldname": "occupancy",
            "fieldtype": "Data",
            "width": 150
        }
    ]


def get_data(filters):
    date = getdate(filters.get("date"))

    rooms = frappe.db.get_all(
        "Room",
        fields=["name", "room_type", "status"]
    )

    results = []

    for room in rooms:

        booking = frappe.db.sql("""
            SELECT name, status
            FROM `tabReservation`
            WHERE room = %s
            AND %s BETWEEN check_in_date AND check_out_date
            AND status != 'Cancelled'
            LIMIT 1
        """, (room.name, date), as_dict=True)

        if room.status == "Maintenance":
            status = "Out of Order"
            occupancy = "N/A"

        elif booking:
            status = "Occupied" if booking[0].status == "Checked-in" else "Reserved"
            occupancy = booking[0].status

        else:
            status = "Available"
            occupancy = "Vacant"

        results.append({
            "room": room.name,
            "room_type": room.room_type,
            "status": status,
            "occupancy": occupancy
        })

    return results