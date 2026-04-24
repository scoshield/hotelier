frappe.query_reports["Room Availability"] = {
    filters: [
        {
            fieldname: "date",
            label: "Date",
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "room_type",
            label: "Room Type",
            fieldtype: "Link",
            options: "Room Type"
        }
    ]
};