# Thailand PIT – Monthly Based (No proration)

def _to_float(v):
    if not v:
        return 0.0
    try:
        s = str(v).strip().replace(",", "")
        if not s:
            return 0.0
        if s.endswith("%"):
            return float(s[:-1])
        return float(s)
    except:
        return 0.0

def _min(a, b):
    return a if a <= b else b

cr = payslip.env.cr

# -------------------------------------------------
# 1) Get active PIT configuration
# -------------------------------------------------
cr.execute("""
    SELECT id,
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
    (pit_id,
     personal_ded,
     spouse_ded,
     child_each,
     life_ins_limit,
     home_int_limit,
     donation_pct) = pit

    personal_ded = _to_float(personal_ded)
    spouse_ded = _to_float(spouse_ded)
    child_each = _to_float(child_each)
    life_ins_limit = _to_float(life_ins_limit)
    home_int_limit = _to_float(home_int_limit)
    donation_pct = _to_float(donation_pct)

    # -------------------------------------------------
    # 2) Get tax brackets
    # -------------------------------------------------
    cr.execute("""
        SELECT income_from, income_to, tax_rate
        FROM personal_income_tax_rate
        WHERE pit_id = %s
        ORDER BY income_from ASC
    """, (pit_id,))
    brackets = cr.fetchall() or []

    # -------------------------------------------------
    # 3) Annual income (Monthly wage × 12)
    # -------------------------------------------------
    monthly_wage = float(contract.wage or 0.0)
    annual_gross = monthly_wage * 12.0

    # Expense deduction: 50% capped at 100,000
    expense_ded = annual_gross * 0.5
    if expense_ded > 100000.0:
        expense_ded = 100000.0

    net_income = annual_gross - expense_ded
    if net_income < 0.0:
        net_income = 0.0

    # -------------------------------------------------
    # 4) Employee deductions
    # -------------------------------------------------
    spouse_input = _to_float(employee.x_studio_pit_spouse_input or 0.0)
    child_input = _to_float(employee.x_studio_pit_child_input or 0.0)
    child_count = _to_float(employee.x_studio_pit_child_count or 0.0)
    life_ins_paid = _to_float(employee.x_studio_pit_life_ins_paid or 0.0)
    home_int_paid = _to_float(employee.x_studio_pit_home_interest_paid or 0.0)
    donate_paid = _to_float(employee.x_studio_pit_donate_paid or 0.0)
    pfund_paid = _to_float(employee.x_studio_pit_pf_paid or 0.0)

    ded_personal = personal_ded

    # spouse rule:
    # 1 = use config amount
    # >1 = manual amount
    ded_spouse = 1.0
    if spouse_input:
        if spouse_input == 1.0:
            ded_spouse = spouse_ded
        else:
            ded_spouse = spouse_input

    ded_children = child_count * child_input if child_input else 0.0
    ded_life = _min(life_ins_paid, life_ins_limit) if life_ins_limit else life_ins_paid
    ded_home = _min(home_int_paid, home_int_limit) if home_int_limit else home_int_paid
    ded_pfund = pfund_paid

    other_ded = ded_personal + ded_spouse + ded_children + ded_life + ded_home + ded_pfund

    base_for_donation = net_income - other_ded
    if base_for_donation < 0.0:
        base_for_donation = 0.0

    donation_cap = base_for_donation * (donation_pct / 100.0) if donation_pct else 0.0
    ded_donation = donate_paid * 2.0
    if donation_cap:
        ded_donation = _min(ded_donation, donation_cap)

    taxable_income = net_income - (other_ded + ded_donation)
    if taxable_income < 0.0:
        taxable_income = 0.0

    # -------------------------------------------------
    # 5) Progressive tax
    # -------------------------------------------------
    annual_tax = 0.0

    for row in brackets:
        inc_from = _to_float(row[0])
        inc_to = _to_float(row[1])
        rate = _to_float(row[2]) / 100.0

        if taxable_income <= inc_from:
            continue

        upper = taxable_income if not inc_to else _min(taxable_income, inc_to)
        band = upper - inc_from

        if band > 0.0:
            annual_tax += band * rate

    # Monthly withholding (no proration)
    monthly_tax = annual_tax / 12.0

    result = -monthly_tax
    result_name = "Income Tax"
