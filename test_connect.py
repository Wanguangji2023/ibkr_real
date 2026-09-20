from ib_insync import IB
from config import Config

ib = IB()
ib.connect(Config.IBKR_HOST, Config.IBKR_PORT,
           clientId=Config.IBKR_CLIENT_ID)
print(f"已连接: {ib.isConnected()}")
print(f"账户: {ib.managedAccounts()}")

for v in ib.accountSummary():
    if v.tag in ("AvailableFunds", "NetLiquidation") and v.currency == "USD":
        print(f"{v.tag}: {v.value}")

for p in ib.positions():
    print(f"持仓: {p.contract.symbol} {p.position} @ {p.avgCost}")

ib.disconnect()