# test_buy_order.py
from broker.ibkr_client import IBKRClient
from strategy.buy_strategy import BuyState, evaluate_buy
from state_store import append_executed_buy

client = IBKRClient()
client.connect()

# 模拟：ORGO 次2价 1.50，现价 1.44（<1.50 → 激活）
info = {"buy_price": 1.50, "range": "128-256"}
st = BuyState("ORGO")

# 1. 激活 + 记录 min_price
action, reason = evaluate_buy("ORGO", info, 1.44, st, {}, 100000, set(), set())
print(f"1) 现价1.44: {action} | {reason}")

# 2. 跌到 1.40，刷新 min_price
action, reason = evaluate_buy("ORGO", info, 1.40, st, {}, 100000, set(), set())
print(f"2) 现价1.40: {action} | {reason}")

# 3. 回弹到 1.42（>1.40×1.01=1.414）→ 触发
action, reason = evaluate_buy("ORGO", info, 1.42, st, {}, 100000, set(), set())
print(f"3) 现价1.42: {action} | {reason}")

if action == "buy":
    print(f"\n→ 执行买入: 金额={reason['amount']} 价格=1.42")
    trade = client.buy("ORGO", reason["amount"], 1.42)
    if trade:
        print(f"订单状态: {trade.orderStatus.status}")
        append_executed_buy(
            "ORGO", "ORGO", 1.42,
            int(reason["amount"] // 1.42),
            reason["amount"],
            trade.orderStatus.status
        )
        print("已写入 executed_buys.xlsx")
    else:
        print("下单失败")
else:
    print(f"\n未触发买入: {reason}")

client.disconnect()