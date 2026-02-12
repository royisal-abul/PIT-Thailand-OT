cr = payslip.env.cr

date_from = payslip.date_from
date_to = payslip.date_to

employee_id = employee.id
hours_per_day = contract.resource_calendar_id.hours_per_day or 9.0

# -------------------------------------------------
# Overtime from overtime_request
# -------------------------------------------------
sql_request = """
    SELECT COALESCE(
        SUM(
            EXTRACT(EPOCH FROM (
                (r.end_date   + INTERVAL '7 hours')
                -
                (r.start_date + INTERVAL '7 hours')
            )) / 3600.0
        ),
    0)
    FROM overtime_request r
    WHERE r.employee_id = %s
      AND (r.start_date + INTERVAL '7 hours') >= %s
      --AND (r.start_date + INTERVAL '7 hours') <= %s
      AND r.include_in_payroll = TRUE
      AND r.state = 'done'
      AND EXTRACT(DOW FROM (r.start_date + INTERVAL '7 hours')) BETWEEN 6 AND 7
      AND (r.end_date + INTERVAL '7 hours') >
          DATE_TRUNC('day', (r.start_date + INTERVAL '7 hours'))
          + INTERVAL '18 hours 1 minute'
"""

cr.execute(sql_request, (employee_id, date_from, date_to))
ot_hours_request = cr.fetchone()[0] or 0.0

# -------------------------------------------------
# Overtime from hr_attendance (only days that have an overtime_request)
# -------------------------------------------------
sql_attendance = """
    SELECT COALESCE(
        SUM(
            GREATEST(
                EXTRACT(EPOCH FROM (
                    LEAST(
                        (a.check_out + INTERVAL '7 hours'),
                        DATE_TRUNC('day', (a.check_in + INTERVAL '7 hours')) + INTERVAL '1 day'
                    )
                    -
                    GREATEST(
                        (a.check_in + INTERVAL '7 hours'),
                        DATE_TRUNC('day', (a.check_in + INTERVAL '7 hours'))
                        + INTERVAL '18 hours 1 minute'
                    )
                )) / 3600.0,
            0.0)
        ),
    0.0)
    FROM hr_attendance a
    WHERE a.employee_id = %s
      AND (a.check_in + INTERVAL '7 hours') >= %s
      --AND (a.check_in + INTERVAL '7 hours') <= %s
      AND a.check_out IS NOT NULL
      AND EXTRACT(DOW FROM (a.check_in + INTERVAL '7 hours')) BETWEEN 1 AND 5
      AND (a.check_out + INTERVAL '7 hours') >
          DATE_TRUNC('day', (a.check_in + INTERVAL '7 hours'))
          + INTERVAL '18 hours 1 minute'
      AND to_char(a.check_in, 'yyyymmdd') IN (
            SELECT to_char(r.start_date, 'yyyymmdd')
            FROM overtime_request r
            WHERE r.employee_id = %s
              AND (r.start_date + INTERVAL '7 hours') >= %s
             -- AND (r.start_date + INTERVAL '7 hours') <= %s
              AND r.include_in_payroll = TRUE
              AND r.state = 'done'
        )
"""

cr.execute(
    sql_attendance,
    (employee_id, date_from, date_to, employee_id, date_from, date_to),
)
ot_hours = cr.fetchone()[0] or 0.0

# -------------------------------------------------
# Compare request vs attendance
# (Your current logic effectively always uses attendance hours.)
# If you want: pay the smaller of the two:
# ot_hours = min(ot_hours, ot_hours_request)
# -------------------------------------------------
ot_hours = ot_hours if ot_hours_request >= ot_hours else ot_hours  # same outcome

# -------------------------------------------------
# Hour rate + result
# -------------------------------------------------
hour_rate = float(contract.wage or 0.0) / 30.0 / hours_per_day
result = ot_hours * hour_rate * 3
