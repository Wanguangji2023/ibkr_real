# rebuild_tp.py
"""
重新生成 dynamic_take_profit.csv
- 逗号分隔
- 前两档修正为数学自洽（回撤后盈利 >= 5%）
- 覆盖 0.065 ~ 0.201，步长 0.001
"""

rows = []

# 第 1 档：6.5%，回撤 1.40%（回撤后 5.009%）
rows.append((0.065, 0.014))

# 第 2 档：6.6%，回撤 1.48%（回撤后 5.11%）
rows.append((0.066, 0.0148))

# 从 6.7% 开始，按原规律：每 +0.1% 涨幅，回撤 -0.01%
profit = 0.067
drawdown = 0.0148
while profit <= 0.2001:
    rows.append((round(profit, 4), round(drawdown, 6)))
    profit = round(profit + 0.001, 4)
    drawdown = round(drawdown - 0.0001, 6)

# 写入（逗号分隔，utf-8）
with open("dynamic_take_profit.csv", "w", encoding="utf-8", newline="") as f:
    f.write("profit,drawdown\n")
    for p, d in rows:
        f.write(f"{p},{d}\n")

print(f"已生成 {len(rows)} 行")
print("前 5 行:")
with open("dynamic_take_profit.csv", encoding="utf-8") as f:
    for i, line in enumerate(f):
        print(repr(line))
        if i >= 4:
            break

print("\n末 3 行:")
with open("dynamic_take_profit.csv", encoding="utf-8") as f:
    lines = f.readlines()
    for line in lines[-3:]:
        print(repr(line))