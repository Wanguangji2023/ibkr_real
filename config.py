import os
from dotenv import load_dotenv

load_dotenv()

# ========== 行情类型 ==========
MARKET_DATA_TYPE = int(os.getenv("MARKET_DATA_TYPE", "3"))

class Config:
    MODE = os.getenv("MODE", "live").lower()

    IBKR_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
    IBKR_PORT = int(os.getenv("IBKR_PORT", "7497"))
    IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "1"))
    ACCOUNT_ID = os.getenv("ACCOUNT_ID", "")
    

    # ========== 行情类型 ==========
    MARKET_DATA_TYPE = int(os.getenv("MARKET_DATA_TYPE", "3"))

    # PUSH_MODE = os.getenv("PUSH_MODE", "none").lower()
    # DINGDING_WEBHOOK = os.getenv("DINGDING_WEBHOOK", "")
    # FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK", "")
    # PUSH_MIN_INTERVAL = int(os.getenv("PUSH_MIN_INTERVAL", "60"))
    # ========== 推送 ==========
    PUSH_MODE = os.getenv("PUSH_MODE", "none").lower()
    DINGDING_WEBHOOK = os.getenv("DINGDING_WEBHOOK", "")
    DINGDING_SECRET = os.getenv("DINGDING_SECRET", "")
    FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK", "")
    FEISHU_SECRET = os.getenv("FEISHU_SECRET", "")
    PUSH_MIN_INTERVAL = int(os.getenv("PUSH_MIN_INTERVAL", "60"))
    LOOP_INTERVAL = int(os.getenv("LOOP_INTERVAL", "90"))


    AUTO_BUY = os.getenv("AUTO_BUY", "true").lower() == "true"
    AUTO_SELL = os.getenv("AUTO_SELL", "true").lower() == "true"

    MAX_HOLDINGS = int(os.getenv("MAX_HOLDINGS", "5"))
    BUY_AMOUNT_USD = float(os.getenv("BUY_AMOUNT_USD", "300"))
    MIN_BALANCE_USD = float(os.getenv("MIN_BALANCE_USD", "200"))
    MIN_RANGE = os.getenv("MIN_RANGE", "32-64")

    SILENCE_DAYS = int(os.getenv("SILENCE_DAYS", "15"))

    BUY_PRICE_COLUMN = os.getenv("BUY_PRICE_COLUMN", "I").upper()

    SHEET1_NAME = os.getenv("SHEET1_NAME", "价格区间处理结果")
    SHEET2_NAME = os.getenv("SHEET2_NAME", "双区间再分表格")

    TRADE_ONLY_MARKET_HOURS = os.getenv("TRADE_ONLY_MARKET_HOURS", "true").lower() == "true"
    PRE_POST_MARKET = os.getenv("PRE_POST_MARKET", "false").lower() == "true"

    HOLDING_CSV = os.getenv("HOLDING_CSV", "holding_pnl.csv")
    XLSX_ABOVE = os.getenv("XLSX_ABOVE", "US所有市值8千万以上无场外双区间相同再算幅度幅度计算okx标黄_已标注.xlsx")
    XLSX_BELOW = os.getenv("XLSX_BELOW", "US所有市值8千万以下无场外双区间相同再算幅度幅度计算okx标黄_已标注.xlsx")

    DATA_DIR = os.getenv("DATA_DIR", "ibkr_data")
    LOG_DIR = os.getenv("LOG_DIR", "ibkr_data/logs")
    LOG_MAX_FILES = int(os.getenv("LOG_MAX_FILES", "10"))
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))

    # 派生路径
    EXECUTED_BUYS = os.path.join(DATA_DIR, "executed_buys.xlsx")
    SILENCE_LIST = os.path.join(DATA_DIR, "silence_list.xlsx")
    LOSS_WATCH = os.path.join(DATA_DIR, "loss_watch.xlsx")
    DYNAMIC_TP = "dynamic_take_profit.csv"
    INVALID_CONTRACTS = os.path.join(DATA_DIR, "invalid_contracts.xlsx")

# # config.py 末尾
# def check_files():
#     """启动时检查关键文件是否存在"""
#     import os
#     missing = []
#     for name, path in [
#         ("HOLDING_CSV", HOLDING_CSV),
#         ("XLSX_ABOVE", XLSX_ABOVE),
#         ("XLSX_BELOW", XLSX_BELOW),
#         ("DYNAMIC_TP", DYNAMIC_TP),
#     ]:
#         if not os.path.exists(path):
#             missing.append(f"  {name} = {path}")
#     if missing:
#         print("❌ 以下文件不存在，请检查 .env：")
#         print("\n".join(missing))
#         raise FileNotFoundError(f"缺少 {len(missing)} 个文件")
def check_files():
    """启动时检查关键文件是否存在"""
    import os
    missing = []
    for name, path in [
        ("HOLDING_CSV", Config.HOLDING_CSV),
        ("XLSX_ABOVE", Config.XLSX_ABOVE),
        ("XLSX_BELOW", Config.XLSX_BELOW),
        ("DYNAMIC_TP", Config.DYNAMIC_TP),
    ]:
        if not os.path.exists(path):
            missing.append(f"  {name} = {path}")
    if missing:
        print("❌ 以下文件不存在，请检查 .env：")
        print("\n".join(missing))
        raise FileNotFoundError(f"缺少 {len(missing)} 个文件")
    print("✅ 所有输入文件存在")


    # config.py 末尾
def print_runtime_info():
    mdt_names = {1: "Live (实时)", 2: "Frozen", 3: "Delayed (延迟)", 4: "Delayed-Frozen"}
    print(f"运行模式: {Config.MODE}")
    print(f"行情类型: {Config.MARKET_DATA_TYPE} "
          f"({mdt_names.get(Config.MARKET_DATA_TYPE, '?')})")
    print(f"交易时段限制: {Config.TRADE_ONLY_MARKET_HOURS}")
    print(f"自动买入: {Config.AUTO_BUY}")
    print(f"自动卖出: {Config.AUTO_SELL}")
    print(f"推送模式: {Config.PUSH_MODE}")