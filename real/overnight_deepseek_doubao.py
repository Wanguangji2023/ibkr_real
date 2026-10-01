from ib_insync import IB, Stock, LimitOrder, util
# 配置连接参数（基于你实盘 API 4001 端口）
IB_HOST = '127.0.0.1'
IB_PORT = 4001
CLIENT_ID = 10
SYMBOL = 'WETO'
TOTAL_QTY = 92
LIMIT_PRICE = 2.35

def main():
    util.startLoop()
    ib = IB()
    ib.connect(IB_HOST, IB_PORT, clientId=CLIENT_ID)
    print(f"✅已连接：{ib.isConnected()}")

    # 隔夜专用合约和订单
    contract = Stock(SYMBOL, 'OVERNIGHT', 'USD')
    order = LimitOrder(
        action='SELL',
        totalQuantity=TOTAL_QTY,
        lmtPrice=LIMIT_PRICE,
        tif='OVERNIGHT'
    )
    trade = ib.placeOrder(contract, order)
    print(f"📤隔夜订单已提交：{trade}")

    # 持续循环监听订单状态，直到成交/取消
    while not trade.isDone():
        ib.waitOnUpdate(0.5)
        print(f"当前状态：{trade.orderStatus.status} | 已成交：{trade.orderStatus.filled}")

    print("\n========订单最终结果========")
    print(f"订单状态: {trade.orderStatus.status}")
    print(f"委托数量: {TOTAL_QTY}")
    print(f"已成交数量: {trade.orderStatus.filled}")
    print(f"平均成交价: {trade.orderStatus.avgFillPrice}")

    ib.disconnect()
    print("🔌断开连接")

if __name__ == "__main__":
    main()
