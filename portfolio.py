# portfolio.py
from datetime import datetime
from openpyxl import Workbook, load_workbook
import os
from config import Config

PORTFOLIO_PATH = os.path.join(Config.DATA_DIR, "portfolio.xlsx")

HEADERS = ["代码", "数量", "成本价", "现价", "市值", "盈亏金额", "盈亏%",
           "更新时间"]


def save_portfolio(holdings, prices):
    """
    holdings: {code: {"qty":, "cost":}}
    prices: {code: price}
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "持仓盈亏"
    ws.append(HEADERS)

    total_cost = 0
    total_value = 0
    total_pnl = 0

    for code, h in holdings.items():
        qty = h.get("qty")
        cost = h.get("cost")
        if not qty or not cost:
            continue
        price = prices.get(code)
        if price is None:
            # 拿不到行情，跳过
            ws.append([code, qty, cost, None, None, None, None,
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            continue

        market_value = qty * price
        cost_value = qty * cost
        pnl = market_value - cost_value
        pnl_pct = pnl / cost_value if cost_value > 0 else 0

        total_cost += cost_value
        total_value += market_value
        total_pnl += pnl

        ws.append([
            code,
            qty,
            round(cost, 4),
            round(price, 4),
            round(market_value, 2),
            round(pnl, 2),
            f"{pnl_pct * 100:.2f}%",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ])

    # 汇总行
    ws.append([])
    ws.append(["合计", None, None, None,
               round(total_value, 2),
               round(total_pnl, 2),
               f"{total_pnl / total_cost * 100:.2f}%" if total_cost > 0 else "",
               datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

    wb.save(PORTFOLIO_PATH)