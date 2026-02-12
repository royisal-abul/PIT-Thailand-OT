# Income Tax (PIT) - Thailand style progressive tax (Thailand)
# Reads PIT config + brackets from DB tables:
#   personal_income_tax (header)
#   personal_income_tax_rate (lines)
#
# Employee PIT inputs read from hr_employee:
#   x_studio_pit_spouse_input
#   x_studio_pit_child_input
#   x_studio_pit_life_ins_paid
#   x_studio_pit_home_interest_paid
#   x_studio_pit_donate_paid
#   x_studio_pit_pf_paid

def _to_float(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return 0.0
    s = s.replace(",", "")
    if s.endswith("%"):
        try:
            return float(s[:-1])
        except Exception:
            return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0

cr = payslip.env.cr  # IMPORTANT: 'env' may not exist in salary rule context

# -------------------------
# 1) Get active PIT config (latest by effective_date)
# -------------------------
cr.execute("""
    SELECT id,
           calendar_year,
           effective_date,
           x_studio_personal_deduction,
           x_studio_spouse_no_income,
           x_studio_children_each,
           x_studio_life_insurance_premiums,
           x_studio_homeowner_interest,
           x_studio_donations_
    FROM personal_income_tax
    WHERE active = TRUE
    ORDER BY effective_date DESC, id DESC
    LIMIT 1
""")
pit = cr.fetchone()

if not pit:
    result = 0.0
else:
    (pit_id, calendar_year, effective_date,
     personal_ded, spouse_ded, child_each,
     life_ins_limit, home_int_limit, donation_pct) = pit

    personal_ded = _to_float(personal_ded)
    spouse_ded = _to_float(spouse_ded)
    child_each = _to_float(child_each)
    life_ins_limit = _to_float(life_ins_limit)
    home_int_limit = _to_float(home_int_limit)
    donation_pct = _to_float(donation_pct)  # e.g. "10%" -> 10.0

    # -------------------------
    # 2) Get tax brackets
    # -------------------------
    cr.execute("""
        SELECT income_from, income_to, tax_rate
        FROM personal_income_tax_rate
        WHERE pit_id = %s
        ORDER BY income_from ASC
    """, (pit_id,))
    brackets = cr.fetchall() or []

    # -------------------------
    # 3) Build annual income base
    # -------------------------
    gross_period = categories.GROSS or 0.0

    date_from = payslip.date_from
    date_to = payslip.date_to
    days = (date_to - date_from).days + 1
    period_month_factor = days / 30.0 if days > 0 else 1.0  # approx

    annual_gross = gross_period * (12.0 / period_month_factor) if period_month_factor > 0 else gross_period * 12.0

    # Salary expense deduction: 50% capped at 100,000
    expense_ded = min(annual_gross * 0.5, 100000.0)

    net_income = annual_gross - expense_ded
    if net_income < 0:
        net_income = 0.0

    # -------------------------
    # 4) Other deductions (from employee fields)
    # -------------------------
    emp = employee

    spouse_input = _to_float(getattr(emp, "x_studio_pit_spouse_input", 0.0))
    child_count = _to_float(getattr(emp, "x_studio_pit_child_input", 0.0))
    life_ins_paid = _to_float(getattr(emp, "x_studio_pit_life_ins_paid", 0.0))
    home_int_paid = _to_float(getattr(emp, "x_studio_pit_home_interest_paid", 0.0))
    donate_paid = _to_float(getattr(emp, "x_studio_pit_donate_paid", 0.0))
    pfund_paid = _to_float(getattr(emp, "x_studio_pit_pf_paid", 0.0))

    ded_personal = personal_ded

    # spouse:
    # - spouse_input == 1 => apply configured spouse deduction
    # - spouse_input > 1  => treat as manual amount
    ded_spouse = 0.0
    if spouse_input:
        ded_spouse = spouse_ded if spouse_input == 1.0 else spouse_input

    # children:
    ded_children = child_count * child_each if child_count else 0.0

    ded_life_ins = min(life_ins_paid, life_ins_limit) if life_ins_limit else life_ins_paid
    ded_home_int = min(home_int_paid, home_int_limit) if home_int_limit else home_int_paid

    # provident fund (cap if you want)
    ded_pfund = pfund_paid

    other_deductions = ded_personal + ded_spouse + ded_children + ded_life_ins + ded_home_int + ded_pfund

    # donation cap: X% of (net income - other deductions), donation double deduction
    base_for_donation_cap = net_income - other_deductions
    if base_for_donation_cap < 0:
        base_for_donation_cap = 0.0

    donation_cap = base_for_donation_cap * (donation_pct / 100.0) if donation_pct else 0.0

    ded_donation = donate_paid * 2.0
    if donation_cap:
        ded_donation = min(ded_donation, donation_cap)

    taxable_income = net_income - (other_deductions + ded_donation)
    if taxable_income < 0:
        taxable_income = 0.0

    # -------------------------
    # 5) Progressive tax calculation
    # -------------------------
    annual_tax = 0.0
    for inc_from, inc_to, rate in brackets:
        inc_from = _to_float(inc_from)
        inc_to = _to_float(inc_to)  # if 0/NULL => no upper limit
        rate = _to_float(rate) / 100.0

        if taxable_income <= inc_from:
            continue

        upper_limit = taxable_income if not inc_to else min(taxable_income, inc_to)
        band = upper_limit - inc_from
        if band > 0:
            annual_tax += band * rate

    # Withhold for this payslip period
    tax_period = (annual_tax / 12.0) * period_month_factor if period_month_factor > 0 else 0.0

    # Salary rule result: deduction should be negative
    result = -tax_period
    result_name = "Income Tax"
