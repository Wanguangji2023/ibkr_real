import time
from datetime import datetime
from portfolio import save_portfolio
from config import Config, check_files, print_runtime_info
from logger import get_logger
import market_time
import notifier
from data_loader import load_holding_csv, load_buy_pool
# from state_store import (load_executed_buys, load_silence,
#                          append_executed_buy, append_silence,
#                          append_out_of_range)   # ★ 新增
from state_store import (load_executed_buys, load_silence,
                         append_executed_buy, append_silence,
                         append_out_of_range, update_executed_status)
from strategy.sell_strategy import PositionState, evaluate_sell
from strategy.buy_strategy import BuyState, evaluate_buy
from broker.ibkr_client import IBKRClient

from state_persist import save_states, load_states

log = get_logger("main")

# 已推送过"超出区间"的代码（避免重复推送）
_pushed_oor_high = set()
_pushed_oor_low = set()

# ibkr_real.py 顶部，跟 sell_states 一起
_consecutive_no_data = 0

# 运行状态
sell_states = {}   # {code: PositionState}
buy_states = {}    # {code: BuyState}       
  

# 缓存  
holdings = {}      # {code: {"qty":, "cost":}}
buy_pool = {}
executed = set()
silence = set()


# def refresh_static(client=None, load_xlsx=True):
#     global buy_pool, executed, silence

#     if load_xlsx:
#         buy_pool = load_buy_pool()

#         # 只在重载 xlsx 时校验合约
#         if client is not None and buy_pool:
#             invalid = client.get_invalid_codes()
#             valid_pool = {}
#             for code, info in buy_pool.items():
#                 if code in invalid:
#                     continue
#                 contract = client._get_contract(code)
#                 if contract is None:
#                     continue
#                 valid_pool[code] = info
#             buy_pool = valid_pool

#     executed = load_executed_buys()
#     silence = load_silence()

#     log.info(f"股票池 {len(buy_pool)} 支；黑名单 {len(executed)}；"
#              f"静默期 {len(silence)}")
# def refresh_static(client=None):
#     """刷新静态数据
#     - buy_pool 只在首次（空）时加载 xlsx
#     - executed / silence 每轮刷新
#     """
#     global buy_pool, executed, silence

#     # ★ 只在首次加载 xlsx（buy_pool 为空）
#     if not buy_pool:
#         buy_pool = load_buy_pool()

#         # 首次校验合约
#         if client is not None and buy_pool:
#             invalid = client.get_invalid_codes()
#             valid_pool = {}
#             for code, info in buy_pool.items():
#                 if code in invalid:
#                     continue
#                 contract = client._get_contract(code)
#                 if contract is None:
#                     continue
#                 valid_pool[code] = info
#             buy_pool = valid_pool

#     # 每轮刷新黑名单/静默期
#     executed = load_executed_buys()
# #     silence = load_silence()

#     log.info(f"股票池 {len(buy_pool)} 支；黑名单 {len(executed)}；"
#              f"静默期 {len(silence)}")
def refresh_static(client=None):
    """刷新静态数据
    - buy_pool 只在首次（空）时加载
    - executed / silence 每轮刷新
    """
    global buy_pool, executed, silence

    # ★ 只在首次加载 xlsx
    if not buy_pool:
        buy_pool = load_buy_pool()

        if client is not None and buy_pool:
            invalid = client.get_invalid_codes()
            valid_pool = {}
            for code, info in buy_pool.items():
                if code in invalid:
                    continue
                contract = client._get_contract(code)
                if contract is None:
                    continue
                valid_pool[code] = info
            buy_pool = valid_pool

    # 每轮刷新黑名单/静默期
    executed = load_executed_buys()
    silence = load_silence()

    log.info(f"股票池 {len(buy_pool)} 支；黑名单 {len(executed)}；"
             f"静默期 {len(silence)}")
def refresh_holdings(client):
    global holdings
    if Config.MODE in ("live", "demo"):
        holdings = client.positions_detail()
    else:
        holdings = load_holding_csv()
    log.info(f"美股持仓 {len(holdings)} 支: {list(holdings.keys())}")

def run_sell(client):
    if not holdings:
        log.info("无持仓")  
        return
    # 批量拉所有持仓的行情  
    codes = list(holdings.keys())
    prices = client.prices_batch(codes)
    log.info(f"持仓行情: {len(prices)}/{len(codes)} 支成功")
    # ★ 保存持仓盈亏
    try:
        save_portfolio(holdings, prices)
    except Exception as e:
        log.error(f"保存 portfolio 失败: {e}")

    for code, h in list(holdings.items()):
        qty = h.get("qty")
        cost = h.get("cost")
        if not qty or not cost:
            continue
        try:
            price = prices.get(code) #client.price(code)

        except Exception as e:
            log.error(f"{code} 行情获取失败: {e}")
            continue
        if not price:
            log.warning(f"{code} 行情为空")
            continue

        st = sell_states.setdefault(code, PositionState(code))
        action, reason = evaluate_sell(code, cost, qty, price, st,
                                       in_loss_watch=st.is_loss_watch)
        log.info(f"[SELL] {code} 现价{price:.4f} -> {action} ({reason})")

        # if action == "sell":
        #     if Config.AUTO_SELL:    
        #         try:
        #             client.sell_all(code, qty)
        #             append_silence(code, reason)
        #             sell_states.pop(code, None)
        #             notifier.push(f"【已清仓】{code} {reason}",
        #                           key=f"sell_{code}")
        #         except Exception as e:
        #             log.error(f"{code} 清仓失败: {e}")
        #     else:
        #         log.info(f"[SELL-DRY] {code} 信号触发，但 AUTO_SELL=false")
        #         notifier.push(f"【卖出信号-未执行】{code} {reason}",
        #                       key=f"sell_sig_{code}")
        # if action == "sell":
        #     if Config.AUTO_SELL:
        #         # ★ 检查是否 RTH
        #         if not market_time.is_trading_now(pre_post=False):
        #             log.warning(f"{code} 卖出信号，但当前非 RTH，跳过下单")
        #             notifier.push(
        #                 f"【卖出信号-RTH外】{code} {reason}",
        #                 key=f"sell_rth_out_{code}_{int(time.time()//60)}"
        #             )
        #             continue
        if action == "sell":
            if Config.AUTO_SELL:
                # ★ 检查是否可交易
                if not market_time.is_tradable():
                    log.warning(f"{code} 卖出信号，但当前不可交易"
                                f"（TRADING_HOURS={Config.TRADING_HOURS}），跳过")
                    notifier.push(
                        f"【卖出信号-非交易时段】{code} {reason}",
                        key=f"sell_non_tradable_{code}_{int(time.time()//60)}"
                    )
                    continue


                # RTH 内下单
                try:
                    client.sell_all(code, qty)
                    append_silence(code, reason)
                    sell_states.pop(code, None)
                    save_states(sell_states, buy_states)
                    notifier.push(
                        f"【已清仓】{code} {reason}",
                        key=f"sell_{code}"
                    )
                except Exception as e:
                    log.error(f"{code} 清仓失败: {e}")
            else:
                log.info(f"[SELL-DRY] {code} 信号触发，但 AUTO_SELL=false")
                notifier.push(
                    f"【卖出信号-未执行】{code} {reason}",
                    key=f"sell_sig_{code}"
                )
        
                
    # 清理已不在持仓里的 sell_states
    for code in list(sell_states.keys()):
        if code not in holdings:
            log.info(f"清理已清仓状态: {code}")
            sell_states.pop(code, None)



def run_buy(client):
    global _consecutive_no_data

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

    # ★ 行情告警判断
    if len(prices) == 0:
        _consecutive_no_data += 1
        log.warning(f"连续 {_consecutive_no_data} 轮    无行情")
        if _consecutive_no_data == 5:
            notifier.push(
                "⚠️ 【行情告警】连续 5 轮无行情\n"
                "可能原因：\n"
                "1. Web 端 / 手机 App 同时登录\n"
                "2. IB Gateway 状态异常\n"
                "3. 订阅问题",
                key="no_data_warning"
            )
    else:
        _consecutive_no_data = 0

    # 逐支判断
    for code, info in candidates.items():
        price = prices.get(code)
        if price is None:
            log.warning(f"{code} 行情为空")
            continue

        range_high = info.get("range_high")
        range_low = info.get("range_low")

        if range_high is not None and price > range_high:
            if code not in _pushed_oor_high:
                _pushed_oor_high.add(code)
                append_out_of_range(code, "high", price, range_high,
                                    f"现价{price} > 最高{range_high}")
                notifier.push(
                    f"⚠️ 【超出区间高】{code}\n"
                    f"现价 {price} > 区间最高 {range_high}\n"
                    f"已从买入队列剔除",
                    key=f"oor_high_{code}"
                )
                log.warning(f"{code} 超出区间高 {price} > {range_high}")
            continue

        if range_low is not None and price < range_low:
            if code not in _pushed_oor_low:
                _pushed_oor_low.add(code)
                append_out_of_range(code, "low", price, range_low,
                                    f"现价{price} < 最低{range_low}")
                notifier.push(
                    f"⚠️ 【超出区间低】{code}\n"
                    f"现价 {price} < 区间最低 {range_low}\n"
                    f"已从买入队列剔除",
                    key=f"oor_low_{code}"
                )
                log.warning(f"{code} 超出区间低 {price} < {range_low}")
            continue

        # 价格回到区间内，清理推送标记
        if range_high is not None and code in _pushed_oor_high and price <= range_high:
            _pushed_oor_high.discard(code)
        if range_low is not None and code in _pushed_oor_low and price >= range_low:
            _pushed_oor_low.discard(code)   

        st = buy_states.setdefault(code, BuyState(code))
        action, reason = evaluate_buy(code, info, price, st,
                                      holdings, balance, executed, silence)
        # log.info(f"[BUY] {code} 现价{price:.4f} -> {action} ({reason})")
        # 只打印 buy 或已激活的，减少日志
        if action == "buy":
            log.info(f"[BUY] {code} 现价{price:.4f} -> buy")
        elif st.activated:
            log.info(f"[BUY] {code} 现价{price:.4f} -> hold ({reason})")
        # 未激活的不打印

      
        if action == "buy":
            if Config.AUTO_BUY:
                # 检查黑名单
                if code in executed:
                    log.warning(f"{code} 已在黑名单，跳过")
                    continue

                # RTH 检查
                if not market_time.is_tradable():
                    log.warning(f"{code} 买入信号，但当前不可交易"
                                f"（TRADING_HOURS={Config.TRADING_HOURS}），跳过下单")
                    notifier.push(
                        f"【买入信号-非交易时段】{code} 金额{reason['amount']:.2f} 价格{price:.4f}",
                        key=f"buy_non_tradable_{code}_{int(time.time()//60)}"
                    )
                    continue

                # ★ 下单前先写文件（Pending），失败则不买
                try:
                    append_executed_buy(code, code, price,
                                        int(reason["amount"] // price),
                                        reason["amount"], "Pending")
                    executed.add(code)   # 内存也加
                except Exception as e:
                    log.error(f"{code} 写入 executed_buys 失败: {e}，跳过下单")
                    continue

                # ★ 下单
                try:
                    trade = client.buy(code, reason["amount"], price)
                    status = trade.orderStatus.status if trade else "失败"
                    log.info(f"{code} 下单结果: {status}")
                    # ★ 更新状态（Pending → Filled / 其他）
                    try:
                        from state_store import update_executed_status
                        update_executed_status(code, status)
                    except Exception as e:
                        log.warning(f"{code} 更新状态失败: {e}")

                    notifier.push(
                        f"【已买入】{code} 金额{reason['amount']:.2f} 价格{price:.4f}",
                        key=f"buy_{code}"
                    )
                except Exception as e:
                    log.error(f"{code} 买入异常: {e}")
            else:
                log.info(f"[BUY-DRY] {code} 信号触发，但 AUTO_BUY=false")
                notifier.push(
                    f"【买入信号-未执行】{code} 金额{reason['amount']:.2f} 价格{price:.4f}",
                    key=f"buy_sig_{code}"
                )        
                
    # 清理已不在候选池的 buy_states（可选）
    for code in list(buy_states.keys()):
        if code not in buy_pool:
            buy_states.pop(code, None)

            

def check_market_data(client):
    """启动时检查行情是否可用"""
    price = client.price("AAPL")
    if price is None:
        log.error("❌ 行情不可用！")
        notifier.push(
            "⚠️ 【行情告警】IBKR 行情不可用\n"
            "可能原因：\n"
            "1. Web 端 / 手机 App 同时登录\n"
            "2. 订阅过期\n"
            "3. IB Gateway 状态异常\n"
            "建议：关闭其他 IBKR 登录，重启 Gateway",
            key="market_data_warning"
        )
        return False
    log.info(f"✅ 行情自检通过：AAPL = {price}")
    return True


def main():
    check_files()
    print_runtime_info()
    log.info("=== IBKR 自动交易程序启动 ===")

    client = IBKRClient()
    client.connect()

    if not check_market_data(client):
        log.error("行情不可用，退出")
        return

    load_states(sell_states, buy_states, PositionState, BuyState)
    refresh_static(client)

    try:
        loop_count = 0
        while True:
            if not client.ib.isConnected():
                log.warning("IBKR 断线，尝试重连...")
                if not client.reconnect():
                    notifier.push(
                        "⚠️ 【IBKR 断线】重连失败，程序退出",
                        key=f"reconnect_fail_{int(time.time())}"
                    )
                    break
                log.info("重连成功，继续运行")

            if Config.TRADE_ONLY_MARKET_HOURS and \
               not market_time.is_trading_now(Config.PRE_POST_MARKET):
                log.info("非交易时段，休眠到下一个开盘")
                market_time.sleep_until_next_open()
                continue

            try:
                # ★ 每 10 轮刷新 xlsx
                # load_xlsx = (loop_count % 10 == 0)                
                refresh_static(client)
                refresh_holdings(client)
                run_sell(client)
                run_buy(client)
                save_states(sell_states, buy_states)
                # loop_count += 1
            except ConnectionError as e:
                log.warning(f"连接异常: {e}，下一轮重连")
                time.sleep(5)
                continue
            except Exception as e:
                log.exception(f"循环异常: {e}")
                notifier.push(
                    f"【循环异常】{e}",
                    key=f"loop_err_{int(time.time() // 60)}"
                )
                time.sleep(30)
                continue

            time.sleep(Config.LOOP_INTERVAL)

    except KeyboardInterrupt:
        log.info("收到 Ctrl+C，退出")
    except Exception as e:
        log.exception(f"主循环异常: {e}")
        try:
            notifier.push(
                f"【程序异常】{e}",
                key=f"fatal_{int(time.time())}"
            )
        except Exception:
            pass
    finally:
        if client.ib.isConnected():
            try:
                client.disconnect()
            except Exception:
                pass
        log.info("程序退出")


if __name__ == "__main__":
    main()