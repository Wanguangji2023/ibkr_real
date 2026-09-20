# test_state.py
from state_store import (
    append_executed_buy, load_executed_buys,
    append_silence, load_silence,
    append_loss_watch, load_loss_watch,
    append_invalid_contract, load_invalid_contracts,
)

print("=== 买入记录 ===")
append_executed_buy("TEST1", "测试股", 1.0, 100, 100.0, "TEST")
print("after append:", load_executed_buys())

print("\n=== 静默期 ===")
append_silence("TEST2", "测试清仓")
print("after append:", load_silence())

print("\n=== 亏损观察 ===")
append_loss_watch("TEST3", 10.0, 9.0, -0.10, "测试")
print("after append:", load_loss_watch())

print("\n=== 无效合约 ===")
append_invalid_contract("TEST4", "测试")
print("after append:", load_invalid_contracts())