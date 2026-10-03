# broker/ibkr_client.py
import math
import time
from ib_insync import IB, Stock, MarketOrder, LimitOrder
from config import Config
from logger import get_logger
from state_store import load_invalid_contracts, append_invalid_contract

log = get_logger("ibkr")

MDT_NAMES = {1: "Live", 2: "Frozen", 3: "Delayed", 4: "Delayed-Frozen"}


class IBKRClient:
    def __init__(self):
        self.ib = IB()
        self._qualified = {}
        self._invalid = load_invalid_contracts()

    def connect(self):
        self.ib.connect(Config.IBKR_HOST, Config.IBKR_PORT,
                        clientId=Config.IBKR_CLIENT_ID)
        log.info(f"已连接 IBKR {Config.IBKR_HOST}:{Config.IBKR_PORT} "
                 f"账户 {self.ib.managedAccounts()}")

        # 注册错误处理
        self.ib.errorEvent += self._on_error

        mdt = Config.MARKET_DATA_TYPE
        try:
            self.ib.reqMarketDataType(mdt)
            log.info(f"行情类型: {mdt} ({MDT_NAMES.get(mdt, '?')})")
        except Exception as e:
            log.warning(f"设置行情类型失败: {e}")

    def _on_error(self, reqId, errorCode, errorString, contract):
        """分级处理 IBKR 错误"""
        SILENT_CODES = {2103, 2104, 2119}
        if errorCode in SILENT_CODES:
            return
        DEBUG_CODES = {10167, 10197, 2105, 2106, 2107, 2158}
        if errorCode in DEBUG_CODES:
            log.debug(f"IBKR [{errorCode}] {errorString} (reqId={reqId})")
            return
        log.warning(f"IBKR Error {errorCode}: {errorString} (reqId={reqId})")

    def reconnect(self, interval=30):
        """无限重连"""
        attempt = 0
        while True:
            if self.ib.isConnected():
                return True
            attempt += 1
            try:
                self.ib.connect(Config.IBKR_HOST, Config.IBKR_PORT,
                                clientId=Config.IBKR_CLIENT_ID)
                log.info(f"重连成功（第 {attempt} 次尝试）")
                self.ib.reqMarketDataType(Config.MARKET_DATA_TYPE)
                self._qualified.clear()
                return True
            except Exception as e:
                log.warning(f"重连失败（第 {attempt} 次）: {e}")
                if attempt % 10 == 0:
                    try:
                        from notifier import push
                        push(f"⚠️ 【IBKR 重连】已重试 {attempt} 次仍未成功",
                             key=f"reconnect_alert_{attempt}")
                    except Exception:
                        pass
                time.sleep(interval)

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
        if code in self._invalid:
            return None
        if code in self._qualified:
            return self._qualified[code]

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
        """批量拉行情（不占订阅位）"""
        contracts = []
        code_map = {}
        for code in codes:
            c = self._get_contract(code)
            if c is None:
                continue
            contracts.append(c)
            code_map[c.conId] = code

        if not contracts:
            return {}

        try:
            tickers = self.ib.reqTickers(*contracts)
        except Exception as e:
            log.error(f"reqTickers 失败: {e}")
            return {}

        result = {}
        for ticker in tickers:
            code = code_map.get(ticker.contract.conId)
            if not code:
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
                    result[code] = fval
                    break

        return result

    def buy(self, code, amount_usd, price, wait_seconds=30):
        qty = int(amount_usd // price)
        if qty <= 0:
            log.warning(f"{code} 金额 {amount_usd} 不足买入 1 股")
            return None
        contract = self._get_contract(code)
        if contract is None:
            return None

        # 限价单：允许 2% 滑点
        slippage = Config.LIMIT_SLIPPAGE_PCT / 100.0
        limit_price = round(price * (1 + slippage), 2)

        order = LimitOrder("BUY", qty, limit_price)
        order.tif = "DAY"
        order.outsideRth = Config.TRADING_HOURS in ("extended", "all")

        log.info(f"{code} 限价买入 {qty} 股 @ {limit_price} "
                 f"(现价 {price}, 滑点 {Config.LIMIT_SLIPPAGE_PCT}%)")
        trade = self.ib.placeOrder(contract, order)

        # 第一段等待
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            self.ib.sleep(0.5)
            if trade.orderStatus.status in ("Filled", "Cancelled", "ApiCancelled", "Inactive"):
                break

        # 二次等待
        if trade.orderStatus.status in ("Submitted", "PreSubmitted", "PendingSubmit"):
            log.warning(f"{code} 订单未终态（{trade.orderStatus.status}），再等 30 秒")
            extra = time.time() + 30
            while time.time() < extra:
                self.ib.sleep(0.5)
                if trade.orderStatus.status in ("Filled", "Cancelled", "ApiCancelled", "Inactive"):
                    break

        log.info(f"买入 {code} 数量 {qty} 最终状态 {trade.orderStatus.status} "
                 f"filled={trade.orderStatus.filled}")
        return trade

    def sell_all(self, code, qty, wait_seconds=30):
        contract = self._get_contract(code)
        if contract is None:
            return None

        price = self.price(code)
        if price is None:
            log.error(f"{code} 无行情，无法卖出")
            return None

        slippage = Config.LIMIT_SLIPPAGE_PCT / 100.0
        limit_price = round(price * (1 - slippage), 2)

        order = LimitOrder("SELL", int(qty), limit_price)
        order.tif = "DAY"
        order.outsideRth = Config.TRADING_HOURS in ("extended", "all")

        log.info(f"{code} 限价卖出 {qty} 股 @ {limit_price} "
                 f"(现价 {price}, 滑点 {Config.LIMIT_SLIPPAGE_PCT}%)")
        trade = self.ib.placeOrder(contract, order)

        # 第一段等待
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            self.ib.sleep(0.5)
            if trade.orderStatus.status in ("Filled", "Cancelled", "ApiCancelled", "Inactive"):
                break

        # 二次等待
        if trade.orderStatus.status in ("Submitted", "PreSubmitted", "PendingSubmit"):
            log.warning(f"{code} 订单未终态（{trade.orderStatus.status}），再等 30 秒")
            extra = time.time() + 30
            while time.time() < extra:
                self.ib.sleep(0.5)
                if trade.orderStatus.status in ("Filled", "Cancelled", "ApiCancelled", "Inactive"):
                    break

        log.info(f"卖出 {code} 数量 {qty} 最终状态 {trade.orderStatus.status} "
                 f"filled={trade.orderStatus.filled}")
        return trade
