// Copyright (c) 2026, BluChip Technologies and contributors
// For license information, please see license.txt

frappe.query_reports["Room Availability"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.add_days(frappe.datetime.get_today(), 1)
        },
        {
            fieldname: "room",
            label: "Room",
            fieldtype: "Link",
            options: "Room"
        },
        {
            fieldname: "room_type",
            label: "Room Type",
            fieldtype: "Link",
            options: "Room Type"
        }
    ]
};
