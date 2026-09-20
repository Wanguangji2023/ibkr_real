# rebuild_tp.py
rows = []
profit = 0.065
drawdown = 0.015
while profit <= 0.2001:
    rows.append((round(profit, 4), round(drawdown, 6)))
    profit = round(profit + 0.001, 4)
    drawdown = round(drawdown - 0.0001, 6)

with open("dynamic_take_profit.csv", "w", encoding="utf-8", newline="") as f:
    f.write("profit,drawdown\n")
    for p, d in rows:
        f.write(f"{p},{d}\n")

print(f"已生成 {len(rows)} 行")
print("前3行预览:")
with open("dynamic_take_profit.csv", encoding="utf-8") as f:
    for i, line in enumerate(f):
        print(repr(line))
        if i >= 3:
            break