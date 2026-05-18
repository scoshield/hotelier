import frappe
from frappe.utils import getdate, add_days


def execute(filters=None):

    columns = get_columns()
    data = get_data(filters)

    return columns, data


# -------------------------
# COLUMNS
# -------------------------
def get_columns():

    return [
        {
            "label": "Date",
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": "Room",
            "fieldname": "room",
            "fieldtype": "Link",
            "options": "Room",
            "width": 280
        },
        {
            "label": "Room Type",
            "fieldname": "room_type",
            "fieldtype": "Data",
            "width": 280
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Guest",
            "fieldname": "guest",
            "fieldtype": "Data",
            "width": 180
        }
    ]


# -------------------------
# DATA
# -------------------------
def get_data(filters):

    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))

    room_filter = filters.get("room")
    room_type_filter = filters.get("room_type")

    # -------------------------
    # Build Room Filter
    # -------------------------
    room_conditions = []

    if room_filter:
        room_conditions.append(f"name = '{room_filter}'")

    if room_type_filter:
        room_conditions.append(f"room_type = '{room_type_filter}'")

    room_where = ""
    if room_conditions:
        room_where = "WHERE " + " AND ".join(room_conditions)

    # -------------------------
    # Fetch rooms (filtered)
    # -------------------------
    rooms = frappe.db.sql(f"""
        SELECT name, room_type, status
        FROM `tabRoom`
        {room_where}
    """, as_dict=True)

    results = []

    current_date = from_date

    # -------------------------
    # LOOP DATES
    # -------------------------
    while current_date <= to_date:

        for room in rooms:

            booking = frappe.db.sql("""
                SELECT
                    rr.guest_name

                FROM `tabHotel Room Pricing Package` hrpp

                INNER JOIN `tabRoom Reservation` rr
                    ON rr.name = hrpp.parent

                WHERE hrpp.room = %s
                AND %s BETWEEN hrpp.from_date AND hrpp.to_date
                AND rr.docstatus < 2

                LIMIT 1
            """, (room.name, current_date), as_dict=True)

            # -------------------------
            # STATUS LOGIC
            # -------------------------
            if room.status == "Maintenance":
                status = "Out of Order"
                guest = ""

            elif booking:
                status = "Occupied"
                guest = booking[0].guest_name

            else:
                status = "Vacant"
                guest = ""

            results.append({
                "date": current_date,
                "room": room.name,
                "room_type": room.room_type,
                "status": status,
                "guest": guest
            })

        current_date = add_days(current_date, 1)

    return results