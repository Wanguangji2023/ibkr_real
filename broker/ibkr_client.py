import math
from ib_insync import IB, Stock, MarketOrder
from config import Config
from logger import get_logger
from state_store import load_invalid_contracts, append_invalid_contract
import time

log = get_logger("ibkr")

MDT_NAMES = {1: "Live", 2: "Frozen", 3: "Delayed", 4: "Delayed-Frozen"}
def prices_batch(self, codes):
    """批量拉行情，返回 {code: price}"""
    contracts = {}
    tickers = {}
    for code in codes:
        c = self._get_contract(code)
        if c is None:
            continue
        contracts[code] = c
        tickers[code] = self.ib.reqMktData(c, "", False, False)

    self.ib.sleep(3)   # 一次性等待所有行情

    result = {}
    for code, ticker in tickers.items():
        for attr in ("marketPrice", "last", "close", "bid", "ask"):
            try:
                val = getattr(ticker, attr)
                if callable(val):
                    val = val()
            except Exception:
                val = None
            if val is None:
                continue
            try:
                fval = float(val)
            except (ValueError, TypeError):
                continue
            if not math.isnan(fval) and fval > 0:
                result[code] = fval
                break   

    for c in contracts.values():
        self.ib.cancelMktData(c)

    return result

class IBKRClient:
    def __init__(self):
        self.ib = IB()
        self._qualified = {}
        self._invalid = load_invalid_contracts()   # ← 关键：加载黑名单
        # print(f"[DEBUG] IBKRClient init: _in    valid = {self._invalid}")
        log.info(f"IBKRClient 加载无效合            约 {len(self._invalid)} 条: {self._invalid}")

    def connect(self):
        self.ib.connect(Config.IBKR_HOST, Config.IBKR_PORT,
                        clientId=Config.IBKR_CLIENT_ID)
        log.info(f"已连接 IBKR {Config.IBKR_HOST}:{Config.IBKR_PORT} "
                 f"账户 {self.ib.managedAccounts()}")

        mdt = Config.MARKET_DATA_TYPE
        try:
            self.ib.reqMarketDataType(mdt)
            log.info(f"行情类型: {mdt} ({MDT_NAMES.get(mdt, '?')})")
        except Exception as e:
            log.warning(f"设置行情类型失败: {e}")

    def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()

    def get_invalid_codes(self):
        return self._invalid

    def account_balance(self):
        account = Config.ACCOUNT_ID or ""
        for v in self.ib.accountSummary(account):
            if v.tag == "AvailableFunds" and v.currency == "USD":
                try:
                    return float(v.value)
                except Exception:
                    return 0.0
        return 0.0

    @staticmethod
    def _is_us_stock(contract):
        return (contract.secType == "STK"
                and contract.currency == "USD")

    def positions(self):
        result = {}
        for p in self.ib.positions():
            if self._is_us_stock(p.contract):
                result[p.contract.symbol] = p.position
        return result

    def positions_detail(self):
        result = {}
        for p in self.ib.positions():
            if self._is_us_stock(p.contract):
                result[p.contract.symbol] = {
                    "qty": p.position,
                    "cost": p.avgCost,
                }
        return result

    def _get_contract(self, code):
        # 已知无效，直接返回 None，不做任何请求
        if code in self._invalid:
            return None

        # 缓存命中
        if code in self._qualified:
            return self._qualified[code]
        
        # 防止未连接时全部失败
        if not self.ib.isConnected():
            log.error("IBKR 未连接，无法 qualifyContracts")
            return None
        
        contract = Stock(code, "SMART", "USD")
        try:
            qualified = self.ib.qualifyContracts(contract)
            if not qualified:
                log.warning(f"{code} 合约无效，加入黑名单")
                self._invalid.add(code)
                append_invalid_contract(code, "No security definition")
                self._qualified[code] = None
                return None
            self._qualified[code] = qualified[0]
            return qualified[0]
        except Exception as e:
            log.warning(f"{code} qualifyContracts 失败: {e}")
            self._invalid.add(code)
            append_invalid_contract(code, str(e))
            self._qualified[code] = None
            return None

    def price(self, code, retry=2):
        contract = self._get_contract(code)
        if contract is None:
            return None 

        for attempt in range(retry):
            try:
                ticker = self.ib.reqMktData(contract, "", False, False)
                self.ib.sleep(2)
            except Exception as e:
                log.warning(f"{code} reqMktData 失败: {e}")
                continue

            for attr in ("marketPrice", "last", "close", "bid", "ask"):
                try:
                    val = getattr(ticker, attr)
                    if callable(val):
                        val = val()
                except Exception:
                    val = None
                if val is None:
                    continue
                try:
                    fval = float(val)
                except (ValueError, TypeError):
                    continue
                if not math.isnan(fval) and fval > 0:
                    self.ib.cancelMktData(contract)
                    return fval

            self.ib.cancelMktData(contract)
            log.debug(f"{code} 第 {attempt+1} 次未取到价格")

        log.warning(f"{code} 无有效价格")
        return None
    def prices_batch(self, codes):
        """
        批量拉行情，返回 {code: price}。
        一次性订阅所有代码，等 3 秒后统一取价，再取消订阅。
        """
        contracts = {}
        tickers = {}

        for code in codes:
            c = self._get_contract(code)
            if c is None:
                continue
            contracts[code] = c
            try:
                tickers[code] = self.ib.reqMktData(c, "", False, False)
            except Exception as e:
                log.warning(f"{code} reqMktData 失败: {e}")

        if not tickers:
            return {}

        self.ib.sleep(3)   # 一次性等所有行情返回

        result = {}
        for code, ticker in tickers.items():
            for attr in ("marketPrice", "last", "close", "bid", "ask"):
                try:
                    val = getattr(ticker, attr)
                    if callable(val):
                        val = val()
                except Exception:
                    val = None
                if val is None:
                    continue
                try:
                    fval = float(val)
                except (ValueError, TypeError):
                    continue
                if not math.isnan(fval) and fval > 0:
                    result[code] = fval
                    break

        # 取消订阅，避免行情泄漏
        for c in contracts.values():
            try:
                self.ib.cancelMktData(c)
            except Exception:
                pass

        return result    

    # def buy(self, code, amount_usd, price):
    #     qty = int(amount_usd    // price)   
    #     if qty <= 0:
    #         return None
    #     contract = self._get_contract(code)
    #     if contract is None:
    #         return None
    #     order = MarketOrder("BUY", qty)
    #     trade = self.ib.placeOrder(contract, order)
    #     self.ib.sleep(2)
    #     log.info(f"买入 {code} 数量 {qty} 状态 {trade.orderStatus.status}")
    #     return trade

    # def sell_all(self, code, qty):
    #     contract = self._get_contract(code)
    #     if contract is None:
    #         return None
    #     order = MarketOrder("SELL", int(qty))
    #     trade = self.ib.placeOrder(contract, order)
    #     self.ib.sleep(2)
    #     log.info(f"卖出 {code} 数量 {qty} 状态 {trade.orderStatus.status}")
    #     return trade
    def buy(self, code, amount_usd, price, wait_seconds=10):
        """按金额买入，等终态"""
        qty = int(amount_usd // price)
        if qty <= 0:
            log.warning(f"{code} 金额 {amount_usd} 不足买入 1 股")
            return None

        contract = self._get_contract(code)
        if contract is None:
            return None

        order = MarketOrder("BUY", qty)
        order.tif = "DAY"

        trade = self.ib.placeOrder(contract, order)

        # 等终态或超时
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            self.ib.sleep(0.5)
            status = trade.orderStatus.status
            if status in ("Filled", "Cancelled", "ApiCancelled", "Inactive"):
                break

        log.info(f"买入 {code} 数量 {qty} 最终状态 {trade.orderStatus.status} "
                 f"filled={trade.orderStatus.filled}")
        return trade

    def sell_all(self, code, qty, wait_seconds=10):
        """清仓卖出，等终态"""
        contract = self._get_contract(code)
        if contract is None:
            return None

        order = MarketOrder("SELL", int(qty))
        order.tif = "DAY"

        trade = self.ib.placeOrder(contract, order)

        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            self.ib.sleep(0.5)
            status = trade.orderStatus.status
            if status in ("Filled", "Cancelled", "ApiCancelled", "Inactive"):
                break

        log.info(f"卖出 {code} 数量 {qty} 最终状态 {trade.orderStatus.status} "
                 f"filled={trade.orderStatus.filled}")
        return trade    