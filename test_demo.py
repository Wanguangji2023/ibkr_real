# test_demo.py
"""
模拟盘测试：验证卖出和买入策略的各种场景。
"""
from strategy.sell_strategy import PositionState, evaluate_sell
from strategy.buy_strategy import BuyState, evaluate_buy


def show(step, result):
    action, reason = result
    print(f"  {step:30s} -> {action:6s} | {reason}")


def test_sell():
    print("\n=== 卖出策略测试 ===")
    print("场景：成本 10.0，验证各阶段行为\n")

    st = PositionState("TEST")
    cost = 10.0

    # 1. 盈利 3%，未激活
    show("1) 现价10.3 (3%)", evaluate_sell("TEST", cost, 100, 10.3, st))

    # 2. 盈利 6%，激活但不执行
    show("2) 现价10.6 (6%)", evaluate_sell("TEST", cost, 100, 10.6, st))

    # 3. 涨到 10.8 (8%)，刷新最高价，但现价高于止盈价，持有
    show("3) 现价10.8 (8%)", evaluate_sell("TEST", cost, 100, 10.8, st))

    # 4. 回落到 10.7 (7%)，仍高于止盈价 10.6542，持有
    show("4) 现价10.7 (7%)", evaluate_sell("TEST", cost, 100, 10.7, st))

    # 5. 回落到 10.65 (6.5%)，低于止盈价 10.6542，触发清仓
    show("5) 现价10.65 (6.5%)", evaluate_sell("TEST", cost, 100, 10.65, st))

    print("\n--- 场景：涨到 12% 再回撤 ---\n")
    st2 = PositionState("TEST2")
    # 涨到 12%
    show("1) 现价11.2 (12%)", evaluate_sell("TEST2", cost, 100, 11.2, st2))
    # 12% 对应回撤 0.7%，止盈价 = 11.2 × 0.993 = 11.1216
    # 回撤到 11.1 (11%)，低于止盈价，触发
    show("2) 现价11.1 (11%)", evaluate_sell("TEST2", cost, 100, 11.1, st2))

    print("\n--- 场景：涨到 5.5%，回撤后盈利不足5%不执行 ---\n")
    st3 = PositionState("TEST3")
    # 涨到 5.5% (10.55)，激活但 <6.5%
    show("1) 现价10.55 (5.5%)", evaluate_sell("TEST3", cost, 100, 10.55, st3))
    # 跌到 5.0% (10.5)，仍 <6.5%，不查表
    show("2) 现价10.5 (5%)", evaluate_sell("TEST3", cost, 100, 10.5, st3))


def test_buy():
    print("\n=== 买入策略测试 ===")
    print("场景：次2价=5.0，账户余额1000\n")

    info = {"buy_price": 5.0, "range": "32-64"}
    st = BuyState("TEST")

    # 1. 价格 6.0，未激活
    show("1) 现价6.0 (未激活)", evaluate_buy("TEST", info, 6.0, st, {}, 1000, set(), set()))

    # 2. 价格 4.8，激活
    show("2) 现价4.8 (激活)", evaluate_buy("TEST", info, 4.8, st, {}, 1000, set(), set()))

    # 3. 跌到 4.5，刷新最低
    show("3) 现价4.5 (刷新最低)", evaluate_buy("TEST", info, 4.5, st, {}, 1000, set(), set()))

    # 4. 回弹到 4.54（4.5×1.01=4.545，未达到）
    show("4) 现价4.54 (未回弹到位)", evaluate_buy("TEST", info, 4.54, st, {}, 1000, set(), set()))

    # 5. 回弹到 4.55，触发
    show("5) 现价4.55 (回弹触发)", evaluate_buy("TEST", info, 4.55, st, {}, 1000, set(), set()))

    # 6. 已有持仓
    show("6) 已有持仓", evaluate_buy("TEST", info, 4.55, st, {"TEST": {}}, 1000, set(), set()))

    # 7. 黑名单
    show("7) 在黑名单", evaluate_buy("TEST", info, 4.55, st, {}, 1000, {"TEST"}, set()))

    # 8. 静默期
    show("8) 在静默期", evaluate_buy("TEST", info, 4.55, st, {}, 1000, set(), {"TEST"}))

    # 9. 余额不足
    show("9) 余额 150", evaluate_buy("TEST", info, 4.55, st, {}, 150, set(), set()))

    # 10. 余额 250，全部买入
    r = evaluate_buy("TEST", info, 4.55, st, {}, 250, set(), set())
    print(f"  10) 余额250 -> {r[0]} | amount={r[1].get('amount') if r[0]=='buy' else r[1]}")

    # 11. 余额 1000，买 300
    r = evaluate_buy("TEST", info, 4.55, st, {}, 1000, set(), set())
    print(f"  11) 余额1000 -> {r[0]} | amount={r[1].get('amount') if r[0]=='buy' else r[1]}")


if __name__ == "__main__":
    test_sell()
    test_buy()