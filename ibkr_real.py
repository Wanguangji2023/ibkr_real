import time
from datetime import datetime

from config import Config, check_files, print_runtime_info
from logger import get_logger
import market_time
import notifier
from data_loader import load_holding_csv, load_buy_pool
from state_store import (load_executed_buys, load_silence,
                         append_executed_buy, append_silence)
from strategy.sell_strategy import PositionState, evaluate_sell
from strategy.buy_strategy import BuyState, evaluate_buy
from broker.ibkr_client import IBKRClient

from state_persist import save_states, load_states

log = get_logger("main")

# 运行状态
sell_states = {}   # {code: PositionState}
buy_states = {}    # {code: BuyState}

# 缓存
holdings = {}      # {code: {"qty":, "cost":}}
buy_pool = {}
executed = set()
silence = set()


# def refresh_static():
#     """每次循环前刷新静态数据"""
#     global buy_pool, executed, silence
#     buy_pool = load_buy_pool()
#     executed = load_executed_buys()
#     silence = load_silence()
#     log.info(f"股票池 {len(buy_pool)} 支；黑名单 {len(executed)}；"
#              f"静默期 {len(silence)}")
def refresh_static(client=None):
    """
    每次循环刷新静态数据：
    - 股票池（买入候选）
    - 已执行买入黑名单
    - 静默期
    - 无效合约黑名单（持久化）
    """
    global buy_pool, executed, silence
    buy_pool = load_buy_pool()
    executed = load_executed_buys()
    silence = load_silence()
    # print(f"[DEBUG] refresh_static: client={client is not None}, "
    #     f"buy_pool={len(buy_pool)}")

    invalid_count = 0
    if client is not None and buy_pool:
        invalid = client.get_invalid_codes()
        # print(f"[DEBUG] refresh _static: invalid = {invalid}")
        invalid_count = len(invalid)
        valid_pool = {}
        for code, info in buy_pool.items():
            # 已知无效，直接跳过
            if code in invalid:
                continue
            # 第一次见到的代码，做一次 qualifyContracts
            contract = client._get_contract(code)
            if contract is None:
                continue
            valid_pool[code] = info 
        buy_pool = valid_pool

    log.info(f"股票池 {len(buy_pool)} 支；黑名单 {len(executed)}；"
             f"静默期 {len(silence)}；无效合约 {invalid_count}")
    if buy_pool:
        log.info(f"股票池示例: {list(buy_pool.keys())[:5]}")

# def refresh_holdings(client):
#     """实盘从 IBKR 取持仓；模拟盘用 CSV + 成本""" 
#     global holdings
#     if Config.MODE == "live":
#         pos = client.positions()
#         csv_data = load_holding_csv()
#         holdings = {}
#         for code, qty in pos.items():
#             cost = csv_data.get(code, {}).get("cost")
#             holdings[code] = {"qty": qty, "cost": cost}
#     else:
#         holdings = load_holding_csv()
def refresh_holdings(client):
    global holdings
    if Config.MODE in ("live", "demo"):
        holdings = client.positions_detail()
    else:
        holdings = load_holding_csv()
    log.info(f"美股持仓 {len(holdings)} 支: {list(holdings.keys())}")


# def run_sell(client):
#     if not Config.AUTO_SELL:
#         log.info("卖出开关关闭")
#         return
#     for code, h in list(holdings.items()):
#         qty = h.get("qty")
#         cost = h.get("cost")
#         if not qty or not cost:
#             continue
#         try:
#             price = client.price(code)
#         except Exception as e:
#             log.error(f"{code} 行情获取失败: {e}")
#             continue
#         if not price:
#             continue

#         st = sell_states.setdefault(code, PositionState(code))
#         action, reason = evaluate_sell(code, cost, qty, price, st,
#                                        in_loss_watch=False)
#         log.info(f"[SELL] {code} 现价{price:.4f} -> {action} ({reason})")
#         if action == "sell":
#             try:
#                 client.sell_all(code, qty)
#                 append_silence(code, reason)
#                 sell_states.pop(code, None)
#                 notifier.push(f"【已清仓】{code} {reason}", key=f"sell_{code}")
#             except Exception as e:
#                 log.error(f"{code} 清仓失败: {e}")


# def run_buy(client):
#     if not Config.AUTO_BUY:
#         log.info("买入开关关闭")
#         return
#     if not buy_pool:
#         return

#     balance = client.account_balance()
#     log.info(f"账户余额 {balance:.2f} USD")

#     for code, info in buy_pool.items():
#         if code in holdings:
#             continue
#         if code in executed:
#             continue
#         if code in silence:
#             continue

#         try:
#             price = client.price(code)
#         except Exception as e:
#             log.error(f"{code} 行情获取失败: {e}")
#             continue
#         if not price:
#             continue

#         st = buy_states.setdefault(code, BuyState(code))
#         action, reason = evaluate_buy(code, info, price, st,
#                                       holdings, balance, executed, silence)
#         log.info(f"[BUY] {code} 现价{price:.4f} -> {action} ({reason})")
#         if action == "buy":
#             try:
#                 trade = client.buy(code, reason["amount"], price)
#                 status = trade.orderStatus.status if trade else "失败"
#                 append_executed_buy(code, code, price,
#                                     int(reason["amount"] // price),
#                                     reason["amount"], status)
#                 executed.add(code)
#                 notifier.push(
#                     f"【已买入】{code} 金额{reason['amount']:.2f} "
#                     f"价格{price:.4f}",
#                     key=f"buy_{code}"
#                 )
#             except Exception as e:
#                 log.error(f"{code} 买入失败: {e}")
#                 append_executed_buy(code, code, price, 0, 0, f"ERROR:{e}")

def run_sell(client):
    if not holdings:
        log.info("无持仓")  
        return
    # 批量拉所有持仓的行情  
    codes = list(holdings.keys())
    prices = client.prices_batch(codes)
    log.info(f"持仓行情: {len(prices)}/{len(codes)} 支成功")

    for code, h in list(holdings.items()):
        qty = h.get("qty")
        cost = h.get("cost")
        if not qty or not cost:
            continue
        try:
            price = client.price(code)
        except Exception as e:
            log.error(f"{code} 行情获取失败: {e}")
            continue
        if not price:
            log.warning(f"{code} 行情为空")
            continue

        st = sell_states.setdefault(code, PositionState(code))
        action, reason = evaluate_sell(code, cost, qty, price, st,
                                       in_loss_watch=False)
        log.info(f"[SELL] {code} 现价{price:.4f} -> {action} ({reason})")

        if action == "sell":
            if Config.AUTO_SELL:
                try:
                    client.sell_all(code, qty)
                    append_silence(code, reason)
                    sell_states.pop(code, None)
                    notifier.push(f"【已清仓】{code} {reason}",
                                  key=f"sell_{code}")
                except Exception as e:
                    log.error(f"{code} 清仓失败: {e}")
            else:
                log.info(f"[SELL-DRY] {code} 信号触发，但 AUTO_SELL=false")
                notifier.push(f"【卖出信号-未执行】{code} {reason}",
                              key=f"sell_sig_{code}")
                
    # 清理已不在持仓里的 sell_states
    for code in list(sell_states.keys()):
        if code not in holdings:
            log.info(f"清理已清仓状态: {code}")
            sell_states.pop(code, None)


# def run_buy(client):
#     if not buy_pool:
#         log.info("股票池为空")
#         return

#     balance = client.account_balance()
#     log.info(f"账户余额 {balance:.2f} USD")
#     #aaa
#     # 过滤候选
#     candidates = {}

#     for code, info in buy_pool.items():
#         if code in holdings:
#             continue
#         if code in executed:
#             continue
#         if code in silence:
#             continue

#         candidates[code] = info
#         if not candidates:
#             return
#          # 批量拉行情
#         prices = client.prices_batch(list(candidates.keys()))
#         log.info(f"批量拉行情: {len(prices)}/{len(candidates)} 支成功")
#         for code, info in candidates.items():
#             price = prices.get(code)
#             if price is None:
#                 continue

#         try:
#             price = client.price(code)
#         except Exception as e:  
#             log.error(f"{code} 行情获取失败: {e}")
#             continue
#         if not price:
#             log.warning(f"{code} 行情为空")
#             continue

#         st = buy_states.setdefault(code, BuyState(code))
#         action, reason = evaluate_buy(code, info, price, st,
#                                       holdings, balance, executed, silence)
#         log.info(f"[BUY] {code} 现价{price:.4f} -> {action} ({reason})")

#         if action == "buy":
#             if Config.AUTO_BUY:
#                 try:
#                     trade = client.buy(code, reason["amount"], price)
#                     status = trade.orderStatus.status if trade else "失败"
#                     append_executed_buy(code, code, price,
#                                         int(reason["amount"] // price),
#                                         reason["amount"], status)
#                     executed.add(code)
#                     notifier.push(
#                         f"【已买入】{code} 金额{reason['amount']:.2f} "
#                         f"价格{price:.4f}",
#                         key=f"buy_{code}"
#                     )
#                 except Exception as e:
#                     log.error(f"{code} 买入失败: {e}")
#                     append_executed_buy(code, code, price, 0, 0, f"ERROR:{e}")
#             else:
#                 log.info(f"[BUY-DRY] {code} 信号触发，但 AUTO_BUY=false")
#                 notifier.push(f"【买入信号-未执行】{code} "
#                               f"金额{reason['amount']:.2f} 价格{price:.4f}",
#                               key=f"buy_sig_{code}")
def run_buy(client):
    if not buy_pool:
        log.info("股票池为空")
        return

    balance = client.account_balance()
    log.info(f"账户余额 {balance:.2f} USD")

    # 过滤候选
    candidates = {}
    for code, info in buy_pool.items():
        if code in holdings or code in executed or code in silence:
            continue
        candidates[code] = info

    if not candidates:
        log.info("无候选股票")
        return

    # ★ 批量拉行情（循环外，一次拉完）
    prices = client.prices_batch(list(candidates.keys()))
    log.info(f"批量拉行情: {len(prices)}/{len(candidates)} 支成功")

    # 逐支判断
    for code, info in candidates.items():
        price = prices.get(code)
        if price is None:
            log.warning(f"{code} 行情为空")
            continue

        st = buy_states.setdefault(code, BuyState(code))
        action, reason = evaluate_buy(code, info, price, st,
                                      holdings, balance, executed, silence)
        log.info(f"[BUY] {code} 现价{price:.4f} -> {action} ({reason})")

        if action == "buy":
            if Config.AUTO_BUY:
                try:
                    trade = client.buy(code, reason["amount"], price)
                    status = trade.orderStatus.status if trade else "失败"
                    append_executed_buy(code, code, price,
                                        int(reason["amount"] // price),
                                        reason["amount"], status)
                    executed.add(code)
                    notifier.push(
                        f"【已买入】{code} 金额{reason['amount']:.2f} "
                        f"价格{price:.4f}",
                        key=f"buy_{code}"
                    )
                except Exception as e:
                    log.error(f"{code} 买入失败: {e}")
                    append_executed_buy(code, code, price, 0, 0, f"ERROR:{e}")
            else:
                log.info(f"[BUY-DRY] {code} 信号触发，但 AUTO_BUY=false")
                notifier.push(f"【买入信号-未执行】{code} "
                              f"金额{reason['amount']:.2f} 价格{price:.4f}",
                              key=f"buy_sig_{code}")

                
    # 清理已不在候选池的 buy_states（可选）
    for code in list(buy_states.keys()):
        if code not in buy_pool:
            buy_states.pop(code, None)

            
def main():
    check_files()
    log.info("=== IBKR 自动交易程序启动 ===")
    # refresh_static()
   
    client = IBKRClient()
    client.connect()

    # 恢复状态
    load_states(sell_states, buy_states, PositionState, BuyState)   

    refresh_static(client) 

    try:
        while True:
            if Config.TRADE_ONLY_MARKET_HOURS and \
               not market_time.is_trading_now(Config.PRE_POST_MARKET):
                log.info("非交易时段，休眠到下一个开盘")
                market_time.sleep_until_next_open()
                continue

            # refresh_static()
            refresh_static(client) 
            refresh_holdings(client)

            run_sell(client)
            run_buy(client)

            # 保存状态
            save_states(sell_states, buy_states)

            time.sleep(30)
    except KeyboardInterrupt:
        log.info("收到 Ctrl+C，退出")
    except Exception as e:
        log.exception(f"主循环异常: {e}")
        notifier.push(f"【程序异常】{e}", key="fatal") # key 固定，但只推一次
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()