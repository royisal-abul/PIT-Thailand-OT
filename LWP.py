cr = payslip.env.cr

date_from = payslip.date_from
date_to = payslip.date_to

employee_id = employee.id
hours_per_day = contract.resource_calendar_id.hours_per_day or 9.0

sql = """
SELECT COALESCE(SUM(l.number_of_hours), 0)
FROM hr_leave l
WHERE l.employee_id = %s
  --AND l.state = 'validate'
  -- overlap with payslip period (local +7h)
  AND (l.date_from + INTERVAL '7 hours') < (%s::date + INTERVAL '1 day')
  AND (l.date_to   + INTERVAL '7 hours') >= %s
"""
cr.execute(sql, (employee_id, date_to, date_from))
lwp_hours = cr.fetchone()[0] or 0.0

hour_rate = float(contract.wage or 0.0) / 30.0 / hours_per_day
result = -(lwp_hours * hour_rate)
