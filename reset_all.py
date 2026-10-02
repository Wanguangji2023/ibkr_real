# reset_all.py
"""
一键清仓 + 重置数据
1. 卖出所有美股持仓
2. 删除 ibkr_data/*.xlsx 和 runtime_states.json
3. 重新初始化状态文件
"""
from ib_insync import IB, Stock, MarketOrder
import time
import os
import glob
from openpyxl import Workbook
from config import Config


def sell_all_positions():
    """卖出所有美股持仓"""
    ib = IB()
    ib.connect(Config.IBKR_HOST, Config.IBKR_PORT,
               clientId=99)
    ib.reqMarketDataType(3)
    ib.sleep(1)

    # 查所有美股持仓
    positions = []
    for p in ib.positions():
        c = p.contract
        if c.secType == "STK" and c.currency == "USD":
            positions.append({
                "symbol": c.symbol,
                "qty": int(p.position),
                "avgCost": p.avgCost,
            })

    if not positions:
        print("无美股持仓，跳过清仓")
        ib.disconnect()
        return

    print(f"\n=== 开始清仓 {len(positions)} 支 ===")
    for pos in positions:
        print(f"  {pos['symbol']}: {pos['qty']} 股 @ {pos['avgCost']}")

    for pos in positions:
        symbol = pos["symbol"]
        qty = pos["qty"]
        if qty <= 0:
            continue

        try:
            contract = Stock(symbol, "SMART", "USD")
            ib.qualifyContracts(contract)

            order = MarketOrder("SELL", qty)
            order.tif = "DAY"
            trade = ib.placeOrder(contract, order)

            # 等 15 秒
            for _ in range(30):
                ib.sleep(0.5)
                if trade.orderStatus.status in ("Filled", "Cancelled", "ApiCancelled", "Inactive"):
                    break

            s = trade.orderStatus
            print(f"  {symbol}: 卖 {qty} 股 -> {s.status} filled={s.filled}")

            # 部分成交，取消剩余
            if s.status not in ("Filled", "Cancelled") and s.filled < qty:
                ib.cancelOrder(trade.order)
                ib.sleep(2)
                print(f"    {symbol}: 取消剩余 {qty - int(s.filled)} 股")

        except Exception as e:
            print(f"  {symbol}: 卖出失败 - {e}")

        time.sleep(2)

    ib.disconnect()
    print("\n=== 清仓完成 ===")


def reset_data_files():
    """删除并重建所有 ibkr_data 文件"""
    data_dir = Config.DATA_DIR

    # 要删除的文件
    to_delete = [
        "executed_buys.xlsx",
        "silence_list.xlsx",
        "loss_watch.xlsx",
        "invalid_contracts.xlsx",
        "out_of_range_high.xlsx",
        "out_of_range_low.xlsx",
        "runtime_states.json",
        "portfolio.xlsx",
    ]

    print(f"\n=== 重置 {data_dir} ===")
    for fname in to_delete:
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"  已删除: {fname}")
            except Exception as e:
                print(f"  删除失败 {fname}: {e}")
        else:
            print(f"  不存在: {fname}")

    # 重建 xlsx 文件
    FILES = {
        "executed_buys.xlsx":     ["代码", "名称", "买入日期", "买入价", "数量", "金额", "状态"],
        "silence_list.xlsx":      ["代码", "卖出日期", "静默到期日", "备注"],
        "loss_watch.xlsx":        ["代码", "成本价", "最低价", "最大亏损%", "记录日期", "备注"],
        "invalid_contracts.xlsx": ["代码", "记录时间", "原因"],
        "out_of_range_high.xlsx": ["代码", "记录时间", "当前价", "区间最高", "备注"],
        "out_of_range_low.xlsx":  ["代码", "记录时间", "当前价", "区间最低", "备注"],
    }

    print("\n=== 重建状态文件 ===")
    for fname, headers in FILES.items():
        path = os.path.join(data_dir, fname)
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        wb.save(path)
        print(f"  已创建: {fname}")

    print("\n=== 重置完成 ===")


def main():
    print("=" * 50)
    print("一键清仓 + 重置数据")
    print("=" * 50)
    print()

    # 1. 清仓
    print("【步骤 1】清仓所有美股持仓")
    sell_all_positions()

    # 2. 重置数据
    print("\n【步骤 2】重置数据文件")
    reset_data_files()

    print("\n" + "=" * 50)
    print("✅ 完成！可以重启程序了")
    print("=" * 50)


if __name__ == "__main__":
    main()