import json
import os
from config import Config
from logger import get_logger

log = get_logger("state_persist")

STATE_FILE = os.path.join(Config.DATA_DIR, "runtime_states.json")


def save_states(sell_states, buy_states):
    """保存运行时状态到 JSON"""
    data = {
        "sell": {},
        "buy": {},
    }
    for code, s in sell_states.items():
        data["sell"][code] = {
            "activated": s.activated,
            "max_price": s.max_price,
            "last_push_profit": s.last_push_profit,
            "is_loss_watch": s.is_loss_watch,
        }
    for code, s in buy_states.items():
        data["buy"][code] = {
            "activated": s.activated,
            "min_price": s.min_price,
        }
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log.error(f"保存状态失败: {e}")


def load_states(sell_states, buy_states, PositionState, BuyState):
    """从 JSON 恢复运行时状态"""
    if not os.path.exists(STATE_FILE):
        log.info("无状态文件，跳过恢复")
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log.warning(f"读取状态失败: {e}")
        return

    for code, s in data.get("sell", {}).items():
        st = PositionState(code)
        st.activated = s.get("activated", False)
        st.max_price = s.get("max_price", 0.0)
        st.last_push_profit = s.get("last_push_profit", 0)
        st.is_loss_watch = s.get("is_loss_watch", False)
        sell_states[code] = st

    for code, s in data.get("buy", {}).items():
        st = BuyState(code)
        st.activated = s.get("activated", False)
        st.min_price = s.get("min_price", float("inf"))
        buy_states[code] = st

    log.info(f"已恢复状态：sell={len(sell_states)} buy={len(buy_states)}")