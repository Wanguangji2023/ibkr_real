# test_positions.py
from broker.ibkr_client import IBKRClient

client = IBKRClient()
client.connect()
print("美股持仓:", client.positions_detail())
client.disconnect()