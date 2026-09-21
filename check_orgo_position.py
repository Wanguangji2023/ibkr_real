# check_orgo_position.py
from broker.ibkr_client import IBKRClient

client = IBKRClient()
client.connect()

print("\n=== 持仓 ===")
for code, h in client.positions_detail().items():
    print(f"  {code}: qty={h['qty']} cost={h['cost']}")

print("\n=== 余额 ===")
print(f"  AvailableFunds: {client.account_balance():.2f} USD")

client.disconnect()