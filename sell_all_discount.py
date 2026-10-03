# sell_all_discount.py
"""
以低于现价 10% 的限价单，清仓所有持仓（美股 + 非美股）
"""
from ib_insync import IB, Stock, LimitOrder
import time

DISCOUNT = 0.10          # 低于现价 10%
WAIT_SECONDS = 30        # 每笔等 30 秒


def main():
    ib = IB()
    ib.connect("127.0.0.1", 4002, clientId=99)
    ib.reqMarketDataType(3)
    ib.sleep(1)

    # 收集所有持仓（不再只 USD）
    positions = []
    for p in ib.positions():
        c = p.contract
        if c.secType != "STK":
            continue
        if int(p.position) <= 0:
            continue
        positions.append({
            "contract": c,
            "symbol": c.symbol,
            "qty": int(p.position),
            "currency": c.currency,
        })

    if not positions:
        print("无持仓")
        ib.disconnect()
        return

    print(f"\n=== 待清仓 {len(positions)} 支 ===")
    for pos in positions:
        print(f"  {pos['symbol']} ({pos['currency']}): {pos['qty']} 股")

    for pos in positions:
        symbol = pos["symbol"]
        qty = pos["qty"]
        contract = pos["contract"]

        # 拉现价
        try:
            ticker = ib.reqMktData(contract, "", False, False)
            ib.sleep(2)
            price = (ticker.marketPrice()
                     or ticker.last
                     or ticker.close
                     or ticker.bid)
        except Exception as e:
            print(f"{symbol}: 拉现价失败 - {e}")
            continue

        if not price or price != price or price <= 0:  # nan 检查
            print(f"{symbol}: 现价无效 ({price})，跳过")
            ib.cancelMktData(contract)
            continue

        # 限价 = 现价 × (1 - 10%)
        limit_price = round(price * (1 - DISCOUNT), 4)

        print(f"\n{symbol}: 现价 {price}, 限价 {limit_price}, 卖 {qty} 股")

        try:
            order = LimitOrder("SELL", qty, limit_price)
            order.tif = "DAY"
            order.outsideRth = True   # 允许盘前盘后
            trade = ib.placeOrder(contract, order)

            # 等 30 秒
            for _ in range(WAIT_SECONDS * 2):
                ib.sleep(0.5)
                if trade.orderStatus.status in (
                        "Filled", "Cancelled", "ApiCancelled", "Inactive"):
                    break

            s = trade.orderStatus
            print(f"  结果: {s.status} filled={s.filled} remaining={s.remaining}")

            # 没成交就取消
            if s.status not in ("Filled", "Cancelled") and s.filled < qty:
                print(f"  未完全成交，取消剩余 {s.remaining} 股")
                ib.cancelOrder(trade.order)
                ib.sleep(2)

        except Exception as e:
            print(f"  {symbol} 失败: {e}")

        ib.cancelMktData(contract)
        time.sleep(2)

    ib.disconnect()
    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()