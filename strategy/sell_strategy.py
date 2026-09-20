import csv
from config import Config
from logger import get_logger
import notifier
from state_store import append_silence, append_loss_watch, load_loss_watch

log = get_logger("sell")


def _load_tp_table():
    table = []
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            with open(Config.DYNAMIC_TP, encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    reader.fieldnames = [
                        (n or "").strip().lstrip("\ufeff")
                        for n in reader.fieldnames
                    ]
                for row in reader:
                    try:
                        table.append((float(row["profit"]),
                                      float(row["drawdown"])))
                    except (KeyError, ValueError, TypeError):
                        continue
            break
        except UnicodeDecodeError:
            continue
    if not table:
        raise RuntimeError(f"动态止盈表加载失败: {Config.DYNAMIC_TP}")
    table.sort()
    log.info(f"已加载动态止盈表 {len(table)} 行，"
             f"最低档 {table[0]} 最高档 {table[-1]}")
    return table


_TP_TABLE = _load_tp_table()


def _drawdown_for(profit_ratio):
    """
    返回当前盈利对应的回撤比例。
    若盈利 < 表中最低档，返回 None，表示动态止盈未生效。
    """
    if not _TP_TABLE:
        return None
    if profit_ratio < _TP_TABLE[0][0]:
        return None
    dd = _TP_TABLE[0][1]
    for p, d in _TP_TABLE:
        if profit_ratio >= p:
            dd = d
        else:
            break
    return dd


class PositionState:
    def __init__(self, code):
        self.code = code
        self.activated = False
        self.max_price = 0.0
        self.last_push_profit = 0
        self.is_loss_watch = False


def evaluate_sell(code, cost, qty, price, state: PositionState,
                  in_loss_watch=False):
    if cost is None or cost <= 0 or price is None or price <= 0:
        return "hold", "无效数据"

    profit_ratio = (price - cost) / cost

    # ---- 亏损 >5%：记录 ----
    if profit_ratio < -0.05 and not in_loss_watch:
        append_loss_watch(code, cost, price, profit_ratio)
        log.info(f"{code} 亏损 {profit_ratio:.2%}，已记录到 loss_watch")
        in_loss_watch = True
    state.is_loss_watch = in_loss_watch

    # ---- 亏损观察名单：回本（≥0%）即可清仓 ----
    if in_loss_watch and profit_ratio >= 0:
        return "sell", f"亏损回本清仓（盈利 {profit_ratio:.2%}）"

    # ---- 激活止盈 ----
    if not state.activated and profit_ratio >= 0.05:
        state.activated = True
        state.max_price = price
        notifier.push(
            f"【止盈激活】{code} 成本 {cost:.4f} 现价 {price:.4f} "
            f"盈利 {profit_ratio:.2%}",
            key=f"activate_{code}"
        )

    if not state.activated:
        return "hold", "未激活"

    # ---- 刷新最高价 ----
    if price > state.max_price:
        state.max_price = price

    # ---- 每 +1% 推送 ----
    cur_bucket = int(profit_ratio * 100)
    if cur_bucket >= state.last_push_profit + 1:
        state.last_push_profit = cur_bucket
        notifier.push(
            f"【盈利提醒】{code} 盈利 {profit_ratio:.2%} "
            f"最高价 {state.max_price:.4f}",
            key=f"profit_{code}_{cur_bucket}"
        )

    # ---- 动态止盈 ----
    # dd = _drawdown_for(profit_ratio)
    peak_profit = (state.max_price - cost) / cost
    dd = _drawdown_for(peak_profit)
    if dd is None:
        return "hold", f"盈利{profit_ratio:.2%}（<6.5%，动态止盈未生效）"

    stop_price = state.max_price * (1 - dd)
    profit_after_dd = (stop_price - cost) / cost

    if price <= stop_price:
        if profit_after_dd >= 0.05:
            return "sell", (f"动态止盈 回撤{dd:.2%} 止盈价{stop_price:.4f} "
                            f"回撤后盈利{profit_after_dd:.2%}")
        else:
            return "hold", (f"触价但回撤后盈利 {profit_after_dd:.2%} <5%，"
                            f"不执行")

    return "hold", f"持有 盈利{profit_ratio:.2%}"