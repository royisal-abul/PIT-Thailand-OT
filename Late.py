cr = payslip.env.cr

date_from = payslip.date_from
date_to = payslip.date_to

employee_id = employee.id
hours_per_day = contract.resource_calendar_id.hours_per_day or 9.0

sql = """
SELECT COALESCE(SUM(
    CASE
        -- Ignore special shift hour
        WHEN TO_CHAR(a.check_in + INTERVAL '7 hours', 'HH24') = '13' THEN 0

        -- Ignore if covered by leave (you commented state validation)
        WHEN EXISTS (
            SELECT 1
            FROM hr_leave l
            WHERE l.employee_id = a.employee_id
              AND (a.check_in + INTERVAL '7 hours')::date
                  BETWEEN (l.date_from + INTERVAL '7 hours')::date
                      AND (l.date_to   + INTERVAL '7 hours')::date
        ) THEN 0

        ELSE COALESCE(a.late_minutes, 0)
    END
), 0)
FROM hr_attendance a
WHERE a.employee_id = %s
  AND (a.check_in + INTERVAL '7 hours') >= %s
  AND (a.check_in + INTERVAL '7 hours') < (%s::date + INTERVAL '1 day')
  AND EXTRACT(DOW FROM (a.check_in + INTERVAL '7 hours')) BETWEEN 1 AND 5
"""

cr.execute(sql, (employee_id, date_from, date_to))
late_minutes = cr.fetchone()[0] or 0.0

# Manager grace rule: if late < 50 minutes, ignore
if employee.x_studio_job_classification == 'Manager' and late_minutes < 120:
    late_minutes = 0.0

minute_rate = float(contract.wage or 0.0) / 30.0 / hours_per_day / 60.0
result = -(late_minutes * minute_rate)
