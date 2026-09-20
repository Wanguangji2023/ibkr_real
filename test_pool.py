# test_pool.py
from data_loader import load_buy_pool

pool = load_buy_pool()
print(f"股票池: {len(pool)} 支")
for code, info in pool.items():
    print(f"  {code:10s}  区间={info['range']:20s}  "
          f"次2价={info['buy_price']:.4f}")