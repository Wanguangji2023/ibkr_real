# inspect_positions.py
from ib_insync import IB
from config import Config

ib = IB()
ib.connect(Config.IBKR_HOST, Config.IBKR_PORT,
           clientId=Config.IBKR_CLIENT_ID)

print(f"{'symbol':<10} {'secType':<8} {'currency':<8} "
      f"{'primaryExch':<12} {'exchange':<10} {'qty':<12} {'avgCost'}")
print("-" * 90)

for p in ib.positions():
    c = p.contract
    print(f"{c.symbol:<10} {c.secType:<8} {c.currency:<8} "
          f"{str(c.primaryExchange):<12} {str(c.exchange):<10} "
          f"{p.position:<12} {p.avgCost}")

ib.disconnect()