from ib_insync import IB, Stock, LimitOrder, util

# 配置连接参数（基于你实盘 API 4001 端口）
IB_HOST = '127.0.0.1'       # 本机网关
IB_PORT = 4001              # 实盘 IB Gateway 端口
CLIENT_ID = 10              # 客户端 ID，需唯一
SYMBOL = 'WETO'             # 股票代码
TOTAL_QTY = 92              # 卖出数量
LIMIT_PRICE = 2.43          # 挂单价格：参考买一价，成交概率高

def main():
    # 启动事件循环
    util.startLoop()

    # 1. 连接 IB 网关
    ib = IB()
    ib.connect(IB_HOST, IB_PORT, clientId=CLIENT_ID)
    print(f"已连接：{ib.isConnected()}")

    # 2. 定义合约（关键：exchange 设为 OVERNIGHT）
    contract = Stock(SYMBOL, 'OVERNIGHT', 'USD')

    # 3. 定义限价单（关键：tif 设为 OVERNIGHT）
    order = LimitOrder(
        action='SELL',
        totalQuantity=TOTAL_QTY,
        lmtPrice=LIMIT_PRICE,
        tif='OVERNIGHT'
    )

    # 4. 提交订单
    trade = ib.placeOrder(contract, order)
    print(f"夜盘订单已提交：{trade}")

    # 5. 等待委托状态更新（建议等待几秒以观察状态）
    ib.sleep(3)
    print(f"当前状态：{trade.orderStatus.status}")

    # 6. 断开连接（如需要保持监控可暂不执行）
    ib.disconnect()

if __name__ == '__main__':
    main()