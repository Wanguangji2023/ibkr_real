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
    # 输入目录（所有 .xlsx 自动加载）
    INPUT_DIR = os.getenv("INPUT_DIR", "input_data")

    DATA_DIR = os.getenv("DATA_DIR", "ibkr_data")
    LOG_DIR = os.getenv("LOG_DIR", "ibkr_data/logs")
    LOG_MAX_FILES = int(os.getenv("LOG_MAX_FILES", "10"))
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
    # 交易时段（rth/extended/all）
    TRADING_HOURS = os.getenv("TRADING_HOURS", "rth").lower()
    # 盘前盘后/夜盘限价单滑点（%）
    LIMIT_SLIPPAGE_PCT = float(os.getenv("LIMIT_SLIPPAGE_PCT", "2.0"))

    # 买入池筛选颜色（yellow/red/both）
    BUY_POOL_COLOR = os.getenv("BUY_POOL_COLOR", "yellow").lower()

    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "6.25")) / 100.0
    # 高于此涨幅，用固定回撤
    HIGH_PROFIT_THRESHOLD = float(os.getenv("HIGH_PROFIT_THRESHOLD", "20.0")) / 100.0
    # 高涨幅时的固定回撤
    HIGH_PROFIT_DRAWDOWN = float(os.getenv("HIGH_PROFIT_DRAWDOWN", "1.5")) / 100.0

    # 派生路径
    EXECUTED_BUYS = os.path.join(DATA_DIR, "executed_buys.xlsx")
    SILENCE_LIST = os.path.join(DATA_DIR, "silence_list.xlsx")
    LOSS_WATCH = os.path.join(DATA_DIR, "loss_watch.xlsx")
    DYNAMIC_TP = "dynamic_take_profit.csv"
    INVALID_CONTRACTS = os.path.join(DATA_DIR, "invalid_contracts.xlsx")
    OUT_OF_RANGE_HIGH = os.path.join(DATA_DIR, "out_of_range_high.xlsx")
    OUT_OF_RANGE_LOW = os.path.join(DATA_DIR, "out_of_range_low.xlsx")

# def check_files():
#     """启动时检查关键文件是否存在"""
#     import os
#     missing = []
#     for name, path in [
#         ("HOLDING_CSV", Config.HOLDING_CSV),
#         ("XLSX_ABOVE", Config.XLSX_ABOVE),
#         ("XLSX_BELOW", Config.XLSX_BELOW),
#         ("DYNAMIC_TP", Config.DYNAMIC_TP),
#     ]:
#         if not os.path.exists(path):
#             missing.append(f"  {name} = {path}")
#     if missing:
#         print("❌ 以下文件不存在，请检查 .env：")
#         print("\n".join(missing))
#         raise FileNotFoundError(f"缺少 {len(missing)} 个文件")
#     print("✅ 所有输入文件存在")
# def check_files():
#     missing = []
#     for name, path in [
#         ("HOLDING_CSV", Config.HOLDING_CSV),
#         ("DYNAMIC_TP", Config.DYNAMIC_TP),
#     ]:
#         if not os.path.exists(path):
#             missing.append(f"  {name} = {path}")

#     # 检查 input_data 目录
#     if not os.path.isdir(Config.INPUT_DIR):
#         missing.append(f"  INPUT_DIR = {Config.INPUT_DIR}（目录不存在）")
#     else:
#         import glob
#         files = glob.glob(os.path.join(Config.INPUT_DIR, "*.xlsx"))
#         files = [f for f in files if not os.path.basename(f).startswith("~$")]
#         if not files:
#             missing.append(f"  INPUT_DIR = {Config.INPUT_DIR}（目录下无 .xlsx）")

#     if missing:
#         print("❌ 以下文件/目录不存在：")
#         print("\n".join(missing))
#         raise FileNotFoundError(f"缺少 {len(missing)} 个")
#     print("✅ 所有输入文件存在")

#     # config.py 末尾
def check_files():
    """检查输入文件/目录"""
    missing = []

    # 必需文件
    for name, path in [
        ("HOLDING_CSV", Config.HOLDING_CSV),
        ("DYNAMIC_TP", Config.DYNAMIC_TP),
    ]:
        if not os.path.exists(path):
            missing.append(f"  {name} = {path}")

    # input_data 目录
    if not os.path.isdir(Config.INPUT_DIR):
        missing.append(f"  INPUT_DIR = {Config.INPUT_DIR}（目录不存在）")
    else:
        import glob
        files = glob.glob(os.path.join(Config.INPUT_DIR, "*.xlsx"))
        files = [f for f in files if not os.path.basename(f).startswith("~$")]
        if not files:
            missing.append(f"  INPUT_DIR = {Config.INPUT_DIR}（目录下无 .xlsx）")

    if missing:
        print("❌ 以下文件/目录不存在：")
        print("\n".join(missing))
        raise FileNotFoundError(f"缺少 {len(missing)} 个")

    print("✅ 所有输入文件存在")
    
def print_runtime_info():
    mdt_names = {1: "Live (实时)", 2: "Frozen", 3: "Delayed (延迟)", 4: "Delayed-Frozen"}
    print(f"运行模式: {Config.MODE}")
    print(f"行情类型: {Config.MARKET_DATA_TYPE} "
          f"({mdt_names.get(Config.MARKET_DATA_TYPE, '?')})")
    print(f"交易时段限制: {Config.TRADE_ONLY_MARKET_HOURS}")
    print(f"自动买入: {Config.AUTO_BUY}")
    print(f"自动卖出: {Config.AUTO_SELL}")
    print(f"推送模式: {Config.PUSH_MODE}")