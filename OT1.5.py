ot_hours = 0.0

date_from = payslip.date_from
date_to = payslip.date_to

# Get overtime records
ot_records = env['overtime_request'].search([
    ('employee_id', '=', employee.id),
    ('start_date', '>=', date_from),
    ('start_date', '<=', date_to),
    ('include_in_payroll', '=', True),
    ('state', '=', 'done'),
])

for rec in ot_records:
    dt = rec.start_date

    # weekend check (0=Mon, 6=Sun)
    weekend = dt.weekday() in (5, 6)

    # public holiday check
    calendar = contract.resource_calendar_id
    holiday = False
    if calendar:
        leave = env['resource.calendar.leaves'].search([
            ('calendar_id', '=', calendar.id),
            ('date_from', '<=', dt),
            ('date_to', '>=', dt),
        ], limit=1)
        if leave:
            holiday = True

    # Normal working day only
    if not weekend and not holiday:

        # After 18:01 → check hour manually
        if dt.hour > 18 or (dt.hour == 18 and dt.minute >= 1):
            ot_hours += rec.num_of_hours


# Hour rate
hours_per_day = contract.resource_calendar_id.hours_per_day or 8
hour_rate = float(contract.wage or 0.0) / 30 / hours_per_day

result = ot_hours * hour_rate * 1.5
