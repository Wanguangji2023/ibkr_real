# check_all_positions.py
from broker.ibkr_client import IBKRClient

client = IBKRClient()
client.connect()

print("=== 全部持仓（含非美股）===")
for p in client.ib.positions():
    c = p.contract
    print(f"  {c.symbol:10s} secType={c.secType} ccy={c.currency} "
          f"qty={p.position} cost={p.avgCost}")

client.disconnect()