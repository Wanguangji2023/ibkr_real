# check_load.py
from state_store import load_invalid_contracts
from config import Config
import os

print("CWD:", os.getcwd())
print("Config.INVALID_CONTRACTS:", Config.INVALID_CONTRACTS)
print("绝对路径:", os.path.abspath(Config.INVALID_CONTRACTS))
print("存在:", os.path.exists(Config.INVALID_CONTRACTS))
print("大小:", os.path.getsize(Config.INVALID_CONTRACTS) if os.path.exists(Config.INVALID_CONTRACTS) else "N/A")

codes = load_invalid_contracts()
print("加载结果:", codes)
print("类型:", type(codes))
print("长度:", len(codes))