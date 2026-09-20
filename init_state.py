"""
初始化 ibkr_data 目录及状态文件。
只需运行一次。
"""
import os
from openpyxl import Workbook

DATA_DIR = "ibkr_data"

FILES = {
    "executed_buys.xlsx": ["代码", "名称", "买入日期", "买入价", "数量", "金额", "状态"],
    "silence_list.xlsx":  ["代码", "卖出日期", "静默到期日", "备注"],
    "loss_watch.xlsx":    ["代码", "成本价", "最低价", "最大亏损%", "记录日期", "备注"],
    "invalid_contracts.xlsx": ["代码", "记录时间", "原因"],
}


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "logs"), exist_ok=True)

    for fname, headers in FILES.items():
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            print(f"已存在，跳过: {path}")
            continue
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        wb.save(path)
        print(f"已创建: {path}")

    print("\n初始化完成。")


if __name__ == "__main__":
    main()