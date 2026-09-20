from config import Config
from logger import get_logger
import notifier
from state_store import (load_executed_buys, load_silence,
                         append_executed_buy)

log = get_logger("buy")


class BuyState:
    """每支候选股的运行状态"""
    def __init__(self, code):
        self.code = code
        self.activated = False
        self.min_price = float("inf")


def evaluate_buy(code, info, price, state: BuyState,
                 holdings, balance, executed, silence):
    """
    返回 (action, reason)
    action: 'buy' / 'hold'
    """
    buy_price_ref = info["buy_price"]  # 次2价

    # ---- 激活监听 ----
    if price < buy_price_ref:
        state.activated = True
        if price < state.min_price:
            state.min_price = price
    else:
        return "hold", "未激活"

    # ---- 刷新最低价 ----
    if price < state.min_price:
        state.min_price = price

    # ---- 回弹 1% ----
    rebound_price = state.min_price * 1.01
    if not (price >= rebound_price and price < buy_price_ref):
        return "hold", "未满足回弹"

    # ---- 6 项检查 ----
    if code in holdings:
        return "hold", "已有持仓"
    if code in executed:
        return "hold", "已在黑名单"
    if code in silence:
        return "hold", "在静默期"
    if balance < Config.MIN_BALANCE_USD:
        return "hold", f"余额不足 {balance:.2f}"
    # 持仓上限（仅实盘）
    if Config.MODE == "live" and len(holdings) >= Config.MAX_HOLDINGS:
        return "hold", "持仓上限"

    # ---- 买入金额 ----
    if balance < Config.BUY_AMOUNT_USD:
        amount = balance
    else:
        amount = Config.BUY_AMOUNT_USD

    return "buy", {
        "amount": amount,
        "price": price,
        "min_price": state.min_price,
        "ref": buy_price_ref,
    }