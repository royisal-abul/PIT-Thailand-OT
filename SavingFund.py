RULE_CODE = 'GRANTEE'  # Must match this salary rule code

# 0) If employee not enrolled in saving fund → no deduction
if not employee.x_studio_saving_fund:
    result = 0.0

# 1) Skip first pay period (monthly logic)
elif contract.date_start and (
    payslip.date_from.year == contract.date_start.year and
    payslip.date_from.month == contract.date_start.month
):
    result = 0.0

else:
    wage = float(contract.wage or 0.0)

    # 2) Determine target by salary tier
    if wage <= 15000:
        target = 5000.0
    elif wage <= 30000:
        target = 9000.0
    else:
        target = 12000.0

    # 3) Sum already deducted from previous payslips
    previous_slips = payslip.env['hr.payslip'].search([
        ('employee_id', '=', employee.id),
        ('state', 'in', ('done', 'paid')),
        ('date_to', '<', payslip.date_from),
    ])

    paid_so_far = 0.0
    for ps in previous_slips:
        for line in ps.line_ids:
            if line.code == RULE_CODE:
                paid_so_far += abs(line.total or 0.0)

    # 4) Add manually collected/open deposit
    open_paid = float(employee.x_studio_open_security_deposit or 0.0)

    remaining = target - paid_so_far - open_paid

    if remaining <= 0:
        result = 0.0
    else:
        monthly = wage * 0.05
        monthly = min(monthly, 750.0)   # monthly cap
        monthly = min(monthly, remaining)

        result = -monthly
