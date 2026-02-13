#from decimal import Decimal, ROUND_HALF_UP

def _to_amount(v):
    try:
        return float(v.amount)
    except Exception:
        pass
    try:
        return float(v.get('amount', 0.00))
    except Exception:
        pass
    try:
        return float(v or 0.00)
    except Exception:
        return 0.00

df = payslip.date_from
dt = payslip.date_to

# Intersection of contract and payslip
start = max(df, contract.date_start or df)
end   = min(dt, contract.date_end or dt)

total_days = (dt - df).days + 1

if contract.date_start and df <= contract.date_start <= dt:
    total_days = 30

eligible = (end - start).days + 1 if end >= start else 0

wage = round(payslip.paid_amount * (eligible / total_days if total_days else 0.0))

late = _to_amount(inputs.get('LATEDEDUCTION'))
lwp  = _to_amount(inputs.get('LEAVEWITHOUT PAY'))
pvm = _to_amount(inputs.get('POSITIONVALUE'))
cagg = _to_amount(inputs.get('CAGG'))
othincome = _to_amount(inputs.get('OTHERINCOME'))
#wage = float(contract.wage or 0.0)


# Toggle this to True if you want exceptions with the values in logs
DEBUG = False
if DEBUG:
    raise Exception("DBG LWP=%.2f LATE=%.2f WAGE=%.2f PVM=%.2f CAGG=%.2f OTHERINCOME=2f" % (lwp, late, wage, pvm, cagg, othincome))

base_wage   = max(wage + lwp + late + pvm + cagg + othincome  , 0.0)
base_amount = round((base_wage * 0.05 + 0.05),0)
#base_amount  = (Decimal(base_wage) * Decimal('0.05')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
bounded_amount = max(min(base_amount, 875.0), 83.0)
result      = -bounded_amount

# Optional label while testing
# result_name = "Social Insurance (LWP=%.2f LD=%.2f)" % (lwp, late)           
