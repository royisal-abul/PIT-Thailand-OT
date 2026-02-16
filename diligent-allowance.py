# เบี้ยขยัน / Diligent Allowance (per month)
# Business rules:
# - No late, No leave (except Annual Leave)
# - During probation: fixed 300 THB/month if eligible, else 0
# - After probation: step accumulation 300 -> 400 -> ... cap 1000
# - If current month has non-annual leave: reset step to 1 (300) and pay 0 for that month (or pay 300 only if you want)
#
# NOTE: This rule computes amount; step persistence should be updated by a scheduled job or end-of-payslip validation.

step_amounts = {
    1: 300.0, 2: 400.0, 3: 500.0, 4: 600.0, 5: 700.0, 6: 800.0,
    7: 900.0, 8: 1000.0, 9: 1000.0, 10: 1000.0, 11: 1000.0, 12: 1000.0,
}

# Helper: safe step
step = int(getattr(contract, "x_diligence_step", 1) or 1)
if step < 1:
    step = 1
if step > 12:
    step = 12

# Identify payslip period
date_from = payslip.date_from
date_to = payslip.date_to

# 1) Check LATE: depends on your attendance implementation.
# If you track late minutes via worked days input or custom worked days line, read it here.
# Example expects an Input with code 'LATE' (amount = late minutes or count)
late = 0.0
for inp in payslip.input_line_ids:
    if inp.code == "LATE":
        late = inp.amount or 0.0
        break
has_late = late > 0.0

# 2) Check LEAVE (except Annual Leave)
# We search validated leaves overlapping the payslip range, excluding Annual Leave.
Leave = env["hr.leave"]
domain = [
    ("employee_id", "=", employee.id),
    ("state", "=", "validate"),
    ("request_date_from", "<=", date_to),
    ("request_date_to", ">=", date_from),
]
leaves = Leave.search(domain)

# Define Annual Leave identification:
# Option A: by leave type code/name. Best: add a boolean on leave type like x_is_annual.
def is_annual(leave):
    lt = leave.holiday_status_id
    # try custom boolean first, fallback to name contains "Annual"
    return bool(getattr(lt, "x_is_annual", False)) or ("annual" in (lt.name or "").lower())

has_blocking_leave = any(not is_annual(lv) for lv in leaves)

eligible = (not has_late) and (not has_blocking_leave)

# 3) Probation logic
# Use contract.x_probation_end (date) OR adapt to your field.
prob_end = getattr(contract, "x_probation_end", False)
in_probation = bool(prob_end and date_to <= prob_end)

if not eligible:
    result = 0.0
else:
    if in_probation:
        result = 300.0
    else:
        result = step_amounts.get(step, 300.0)
