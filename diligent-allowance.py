# เบี้ยขยัน / Diligent Allowance (DALOW) - per month
# Rules:
# - Eligible if: No late AND no non-annual leave during payslip period
# - Probation (before Permanent Date): pay fixed 300 if eligible
# - After probation: pay by step (employee.x_studio_open_diligence_allowance) using step_amounts
# Notes:
# - This rule only CALCULATES the allowance. Do NOT update step here.

step_amounts = {
    1: 300.0, 2: 400.0, 3: 500.0, 4: 600.0, 5: 700.0, 6: 800.0,
    7: 900.0, 8: 1000.0, 9: 1000.0, 10: 1000.0, 11: 1000.0, 12: 1000.0,
}

# ---- STEP from employee (Studio field) ----
step = int((employee.x_studio_open_diligence_allowance or 1))
if step < 1:
    step = 1
if step > 12:
    step = 12

date_from = payslip.date_from
date_to = payslip.date_to

# ---- 1) LATE (Input line code) ----
late = 0.0
for inp in payslip.input_line_ids:
    if inp.code == "LATEDEDUCTION":
        late = (inp.amount or 0.0)
        break
has_late = late > 0.0

# ---- 2) LEAVE (exclude Annual Leave by type id) ----
Leave = env["hr.leave"]
domain = [
    ("employee_id", "=", employee.id),
    ("state", "=", "validate"),
    ("request_date_from", "<=", date_to),
    ("request_date_to", ">=", date_from),
]
leaves = Leave.search(domain)

ANNUAL_TYPE_ID = 123  # <-- PUT YOUR REAL "Annual Leave (ลาพักผ่อน)" hr.leave.type ID HERE

has_blocking_leave = False
for lv in leaves:
    # blocking if NOT annual
    if lv.holiday_status_id.id != ANNUAL_TYPE_ID:
        has_blocking_leave = True
        break

eligible = (not has_late) and (not has_blocking_leave)

# ---- 3) Probation using Permanent Date on contract ----
permanent_date = contract.x_studio_permanent_date  # your field name
in_probation = bool(permanent_date and (date_to < permanent_date))  # before permanent date = probation

# ---- RESULT ----
if not eligible:
    result = 0.0
else:
    if in_probation:
        result = 300.0
    else:
        result = step_amounts.get(step, 300.0)
