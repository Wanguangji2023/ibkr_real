IBKR 美股自动交易程序 —— 完整运行文档===原文档补充修定版
版本：v1.0
最后更新：2026-10-01
适用：IBKR 模拟账户 / 实盘账户（美股）

在已稳定运行的版本之上，已更新到git
接下来依据新的总结尽可能实现自动化交易，为完全自动化实盘做准备

===》代表新增加的要求或补充或新增

卖出侧：持仓盈利 ≥5% 激活动态止盈，按"涨幅越高、回撤容忍越小"的规则清仓。
卖出补充：


买入侧：基于指定的 xlsx 股票池，价格回调后回弹 1% 买入，每支 300 USD。

消息推送：钉钉 / 飞书，覆盖止盈激活、买入信号、异常等场景。

状态持久化：持仓、止盈状态、买入信号、黑名单、静默期等跨重启保留。

运行时间控制：仅在美国交易时段运行，非交易时段休眠。

二、目录结构
text
IBKR_deepseek/
├── ibkr_real.py                          # 主程序入口
├── .env                                  # 配置文件
├── dynamic_take_profit.csv               # 动态止盈表
├── holding_pnl.csv                       # 持仓输入（模拟盘/离线回测）
├── US所有市值8千万以上...已精减.xlsx      # 买入池输入 1
├── US所有市值8千万以下...已精减.xlsx      # 买入池输入 2
├── config.py                             # 配置加载
├── logger.py                             # 日志
├── market_time.py                        # 交易时段判断
├── state_store.py                        # 状态文件读写
├── state_persist.py                      # 运行时状态持久化
├── data_loader.py                        # 输入文件加载
├── notifier.py                           # 钉钉/飞书推送
├── init_state.py                         # 初始化状态文件（跑一次）
├── strategy/
│   ├── __init__.py
│   ├── sell_strategy.py                  # 卖出策略
│   └── buy_strategy.py                   # 买入策略
├── broker/
│   ├── __init__.py
│   └── ibkr_client.py                    # IBKR API 封装
└── ibkr_data/
    ├── executed_buys.xlsx                # 已执行买入黑名单
    ├── silence_list.xlsx                 # 卖出后静默期
    ├── loss_watch.xlsx                   # 亏损 >5% 记录
    ├── invalid_contracts.xlsx            # 无效合约黑名单
    ├── out_of_range_high.xlsx            # 超出区间最高
    ├── out_of_range_low.xlsx             # 超出区间最低
    ├── runtime_states.json               # 运行时状态
    └── logs/
        └── ibkr.log                      # 运行日志
三、环境要求
项	要求
Python	3.10+
操作系统	Linux / macOS / Windows
IBKR 客户端	IB Gateway（推荐）或 TWS
网络	能访问 IBKR API 端口（本地或同网）
依赖安装
bash
pip install python-dotenv openpyxl pandas requests ib_insync exchange_calendars pytz
四、IBKR 客户端配置
4.1 端口对照
客户端	模式	端口
IB Gateway	模拟	4002
IB Gateway	实盘	4001
TWS	模拟	7497
TWS	实盘	7496
推荐使用 IB Gateway（模拟），端口 4002。

4.2 API 设置
IB Gateway → Configure → Settings → API → Settings：

项	值
Read-Only API	不勾选
Socket Port	4002（模拟）
Trusted IPs	127.0.0.1
Allow connections from localhost only	勾选
Download open orders on connection	勾选
4.3 ⚠️ 关键：不要同时登录 Web 端 / 手机 App
IBKR 的"多会话"限制：同一账户在 Web + IB Gateway 同时登录，会导致：

Error 10197：无法获得市场数据

usfarm（美股数据农场）消失

行情返回 nan

规则：

跑程序时：只开 IB Gateway，不登录 Web / 手机 App / TWS

查账户时：先关 IB Gateway，再登录 Web

4.4 行情类型
类型	说明	是否需订阅
1 = Live	实时	需订阅
3 = Delayed	延迟 15 分钟	模拟账户可免费订阅
模拟账户默认用 MARKET_DATA_TYPE=3（延迟）。

如果 marketDataType 一直返回 1 → 说明：

未订阅（登录 IBKR 官网 → Account Management → Market Data Subscriptions 勾选）

或同时登录了 Web 端 / 手机 App

五、配置文件 .env
5.1 完整模板
ini
# ========== 运行模式 ==========
MODE=demo

# ========== IBKR 连接 ==========
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1
ACCOUNT_ID=DUQ670663

# ========== 行情类型 ==========
MARKET_DATA_TYPE=3

# ========== 推送 ==========
PUSH_MODE=both
DINGDING_WEBHOOK=
DINGDING_SECRET=
FEISHU_WEBHOOK=
FEISHU_SECRET=
PUSH_MIN_INTERVAL=60

# ========== 交易开关 ==========
AUTO_BUY=false
AUTO_SELL=false

# ========== 持仓与买入 ==========
MAX_HOLDINGS=5
BUY_AMOUNT_USD=300
MIN_BALANCE_USD=200
MIN_RANGE=32-64
SILENCE_DAYS=15
BUY_PRICE_COLUMN=I

# ========== Sheet 名 ==========
SHEET1_NAME=价格区间处理结果
SHEET2_NAME=双区间再分表格

# ========== 运行时间 ==========
TRADE_ONLY_MARKET_HOURS=false
PRE_POST_MARKET=false
LOOP_INTERVAL=30

# ========== 输入文件 ==========
HOLDING_CSV=holding_pnl.csv
XLSX_ABOVE=US所有市值8千万以上无场外双区间相同再算幅度幅度计算okx标黄_已标注_已精减.xlsx
XLSX_BELOW=US所有市值8千万以下无场外双区间相同再算幅度幅度计算okx标黄_已标注_已精减.xlsx

# ========== 数据目录 ==========
DATA_DIR=ibkr_data
LOG_DIR=ibkr_data/logs
LOG_MAX_FILES=10
LOG_MAX_BYTES=10485760
5.2 关键配置说明
配置项	说明
MODE	demo（模拟）/ live（实盘）
IBKR_CLIENT_ID	固定值，不要频繁改（会产生残留会话）
MARKET_DATA_TYPE	3（延迟，模拟账户默认）
PUSH_MIN_INTERVAL	同一信号最小推送间隔（秒）
AUTO_BUY	true 自动买入 / false 只推送
AUTO_SELL	true 自动卖出 / false 只推送
MAX_HOLDINGS	实盘最大持仓数（模拟盘不限）
BUY_AMOUNT_USD	单笔买入金额
MIN_BALANCE_USD	账户最低余额，低于不买入
MIN_RANGE	最低区间（含本身）
SILENCE_DAYS	卖出后静默期（NYSE 交易日）
TRADE_ONLY_MARKET_HOURS	只在交易时段运行
LOOP_INTERVAL	主循环间隔（秒）
5.3 ⚠️ 重要：注释必须独占一行
错误写法（会解析失败）：

ini
PUSH_MIN_INTERVAL=60           # 秒
正确写法：

ini
# 同一信号最小推送间隔（秒）
PUSH_MIN_INTERVAL=60
六、首次启动
步骤 1：确认 IB Gateway 已登录
打开 IB Gateway → 登录模拟账户

主界面显示：市场数据农场 ON: hfarm, usfarm

不要登录 Web 端 / 手机 App

步骤 2：初始化状态文件（仅一次）
bash
python init_state.py
预期输出：

text
✅ 已创建: ibkr_data\executed_buys.xlsx
✅ 已创建: ibkr_data\silence_list.xlsx
✅ 已创建: ibkr_data\loss_watch.xlsx
✅ 已创建: ibkr_data\invalid_contracts.xlsx
✅ 已创建: ibkr_data\out_of_range_high.xlsx
✅ 已创建: ibkr_data\out_of_range_low.xlsx

初始化完成。
步骤 3：验证环境
bash
python test_env.py
预期：全部 ✅。

步骤 4：验证 IBKR 连接 + 行情
bash
python test_single_price.py
预期：

text
--- AAPL ---
  price = 34x.xx

--- CABO ---
  price = 1x.xx

--- ORGO ---
  price = 1.xx
如果 price = None → 见第八章"故障排查"。

步骤 5：启动主程序
bash
python ibkr_real.py
预期启动日志：

text
[INFO] sell: 已加载动态止盈表 136 行，...
✅ 所有输入文件存在
[INFO] main: === IBKR 自动交易程序启动 ===
[INFO] ibkr: 已连接 IBKR 127.0.0.1:4002 账户 ['DUQ670663']
[INFO] ibkr: 行情类型: 3 (Delayed)
[INFO] state_persist: 已恢复状态：sell=5 buy=8
[INFO] main: 股票池 9 支；黑名单 3；静默期 1；无效合约 1
[INFO] main: 美股持仓 5 支: ['CABO', 'ORGO', 'AAPL', 'JUNS', 'WETO']
[INFO] main: 持仓行情: 5/5 支成功
[INFO] main: [SELL] CABO 现价13.11 -> hold (未激活)
...
Ctrl+C 退出。

七、日常运行
7.1 启动
bash
# 确保 IB Gateway 已登录
python ibkr_real.py
7.2 停止
推荐：Ctrl+C（触发 KeyboardInterrupt，程序正常退出，断开连接）

不推荐：kill -9（强杀，会留下残留 API 会话）

7.3 后台运行（Linux）
bash
nohup python ibkr_real.py > ibkr_data/nohup.log 2>&1 &
查看日志：

bash
tail -f ibkr_data/logs/ibkr.log
7.4 运行中的日志解读
正常日志：

text
[INFO] main: 持仓行情: 5/5 支成功              ← 持仓行情 OK
[INFO] main: 批量拉行情: 9/9 支成功             ← 候选行情 OK
[INFO] main: [SELL] AAPL 现价340.91 -> hold (持有 盈利11.07%)   ← 持仓判断
[INFO] main: [BUY] AIXI 现价1.62 -> buy ({...})  ← 买入信号
[INFO] notifier: [PUSH] 【买入信号-未执行】AIXI  ← 推送
关键状态：

日志	含义
持仓行情: X/5	持仓行情成功率，X=0 说明行情有问题
批量拉行情: X/9	候选行情成功率
[SELL] ... hold	持仓未触发卖点
[SELL] ... sell	触发清仓
[BUY] ... buy	触发买入信号
[BUY-DRY]	AUTO_BUY=false，只推送不下单
[PUSH] 【已买入】	已下单成功
八、故障排查
8.1 行情全部拿不到（price = None）
症状：

text
[INFO] main: 持仓行情: 0/5 支成功
[WARNING] ibkr: AAPL 无有效价格
原因（按概率）：

同时登录了 Web 端 / 手机 App → Error 10197

IB Gateway 状态异常 → usfarm 消失

API 会话残留 → 多次强杀进程

解决：

关闭所有 Web 端 / 手机 App / TWS

完全重启 IB Gateway（File → Exit，不是关窗口）

杀所有 Python 进程：

bash
pkill -f python
等 5 分钟

重开 IB Gateway

跑 test_single_price.py 验证

8.2 marketDataType: 1 顽固不变
症状：reqMarketDataType(3) 调用成功，但 ticker 仍显示 1。

原因：IBKR 没给你的模拟账户"延迟行情"权限。

解决：

登录 https://www.interactivebrokers.com

Account Management → Settings → Market Data Subscriptions

勾选 "US Securities Snapshot and Futures Value Bundle"（模拟账户免费）

等 15 分钟

重启 IB Gateway

跑 test_set_type.py 验证

8.3 Error 10197
含义：同时存在多个真实账户交易会话时无法获得市场数据。

解决：关闭所有其他 IBKR 登录（Web / App / TWS / 其他电脑）。

8.4 Error 200: No security definition
含义：IBKR 里找不到该股票（已退市/改名/OTC）。

解决：程序自动加入 invalid_contracts.xlsx 黑名单，后续跳过。无需人工处理。

8.5 PermissionError: [Errno 13] Permission denied
原因：Excel / WPS 打开着状态文件。

解决：

关闭 Excel / WPS

或换个文件名（程序不锁文件）

查看状态文件用 Python 脚本，不要用 Excel

8.6 程序崩溃 / 卡死
检查：

bash
tail -100 ibkr_data/logs/ibkr.log
常见原因：

IBKR 断线 → 程序崩溃（待加断线重连）

状态文件损坏 → 删掉 ibkr_data/*.xlsx 重建

.env 配置错误 → 跑 test_env.py

8.7 推送收不到
检查：

.env 里 PUSH_MODE（dingding / feishu / both）

Webhook URL 是否正确

Secret 是否正确

钉钉/飞书安全设置：关键词是否包含（如"交易"）

测试：

bash
python test_notifier.py
九、状态文件说明
文件	内容	作用
executed_buys.xlsx	已买入的股票	黑名单，每支只买一次
silence_list.xlsx	卖出后静默期	15 交易日内不再买入
loss_watch.xlsx	亏损 >5% 的股票	回本（≥0%）即可清仓
invalid_contracts.xlsx	无效合约	自动跳过
out_of_range_high.xlsx	超出区间最高	审计日志（不参与判断）
out_of_range_low.xlsx	超出区间最低	审计日志（不参与判断）
runtime_states.json	止盈/买入状态	重启恢复
9.1 手动维护
恢复某支股票可买入：

从 executed_buys.xlsx 删掉该行

清除静默期：

从 silence_list.xlsx 删掉该行

清除亏损观察：

从 loss_watch.xlsx 删掉该行

⚠️ 不要用 Excel 打开——用 Python 脚本或复制一份再看。

十、策略说明
10.1 卖出策略（动态止盈）
触发：

盈利 ≥5% → 激活，记录参考最高价

盈利每 +1% → 推送一次

按 dynamic_take_profit.csv 查回撤比例

止盈价 = 参考最高价 × (1 − 回撤比例)

清仓硬条件：现价 ≤ 止盈价 且 回撤后盈利 ≥5%

动态止盈表（dynamic_take_profit.csv）：

涨幅	回撤
6.5%	1.40%
6.6%	1.48%
7.0%	1.45%
8.0%	1.35%
…	…
20.0%	0.15%
亏损个股特例：

亏损 >5% → 记录到 loss_watch.xlsx

回本（盈利 ≥0%）即可清仓，不受 5% 硬条件限制

10.2 买入策略（双区间回调）
股票池筛选（同时满足）：

Sheet2 双区间再分表格 A 列背景为黄色

Sheet1 价格区间处理结果 C 列 = E 列

区间 ≥ 32-64（含本身）

买入信号：

现价 < 次2价（Sheet2 I 列）→ 激活监听

记录 min_price（只降不升）

现价 ≥ min_price × 1.01 且 现价 < 次2价 → 触发

检查：无持仓、不在黑名单、不在静默期、账户余额 ≥200 USD、未超出区间

买入金额：

余额	买入金额
< 200 USD	不买
200–300 USD	全部余额
≥ 300 USD	300 USD
10.3 区间超出
区间：Sheet2 的 C 列（最高）/ D 列（最低）为数值。

现价 > C → 超出最高

现价 < D → 超出最低

严格比较（等于不算超出）

超出后：

本轮跳过（动态排除）

推送一次（不重复）

写入 out_of_range_high/low.xlsx

价格回到区间内 → 自动恢复可买入

十一、推送消息说明
场景	消息
止盈激活	【止盈激活】AAPL 成本 306.93 现价 340.91 盈利 11.07%
盈利每 +1%	【盈利提醒】AAPL 盈利 11.07% 最高价 341.37
买入信号（未执行）	【买入信号-未执行】AIXI 金额300.00 价格1.6200
已买入	【已买入】AIXI 金额300.00 价格1.6200
已清仓	【已清仓】AAPL 动态止盈 峰值11.07% ...
超出区间高	⚠️【超出区间高】GMEX 现价3.21 > 区间最高0.666
超出区间低	⚠️【超出区间低】REKR 现价0.3872 < 区间最低0.3966
程序异常	【程序异常】...
去重：同一信号 PUSH_MIN_INTERVAL 秒内不重复推。

十二、日志
路径：ibkr_data/logs/ibkr.log

轮转：最多 10 个文件，每个 10MB

实时查看：

bash
tail -f ibkr_data/logs/ibkr.log
过滤错误：

bash
grep ERROR ibkr_data/logs/ibkr.log
十三、模拟盘 → 实盘切换
13.1 切到实盘前必须确认
□ 模拟盘跑满 1 周，无异常
□ AUTO_BUY / AUTO_SELL 模拟盘实测通过
□ 断线重连已加
□ 状态持久化验证
□ 推送验证
13.2 切换步骤
.env 改：

ini
MODE=live
IBKR_PORT=4001        # IB Gateway 实盘端口
ACCOUNT_ID=U1234567   # 实盘账户
IB Gateway 切换为实盘账户登录

AUTO_BUY / AUTO_SELL 先设 false，观察 1 天

确认信号合理后，打开 true

小资金试运行（如 $1000）

十四、常见问题 FAQ
Q1：为什么 marketDataType 是 1 不是 3？

A：未订阅或同时登录 Web 端。见 8.2。

Q2：为什么股票池比预期少？

A：筛选条件：

Sheet2 A 列黄色

Sheet1 C = E

区间 ≥ 32-64

ACGN 等无效合约被剔除

Q3：为什么某支股票一直不买？

A：检查：

executed_buys.xlsx 是否已记录

silence_list.xlsx 是否在静默期

现价是否在区间内

min_price 是否已刷新（runtime_states.json）

Q4：程序崩溃后重启，状态会丢吗？

A：不会。runtime_states.json 恢复止盈/买入状态。但 IBKR 断线后的状态可能不准（需要 reconnect()）。

Q5：能不能跑两个实例？

A：不能。同一账户 + 同 clientId 会冲突。多实例必须用不同 clientId，但会产生"多会话"问题。建议只跑一个。

Q6：非交易时段程序在干什么？

A：TRADE_ONLY_MARKET_HOURS=true 时，程序休眠到下一个开盘（不循环）。false 时，24 小时循环。

Q7：如何手动清仓某支股票？

A：在 IBKR Gateway 里手动卖。程序下轮检测到持仓变化会自动更新。

Q8：为什么 CABO 亏损 26% 还被记录到 loss_watch？

A：模拟账户自然波动。持仓亏损 >5% 自动记录。回本（≥0%）后自动清仓。

十五、已知限制 / 待改进
项	状态
断线重连	待加（client.reconnect()）
主循环异常退出	待改（内部 try/except）
批量行情浪费（run_sell）	待修
check_market_data 未调用	待修
loss_watch 重复记录	✅ 已修
状态保存时机	待改（买卖后立即保存）
全局变量过多	待重构
十六、快速命令参考
bash
# 初始化（仅一次）
python init_state.py

# 验证 .env
python test_env.py

# 验证 IBKR 连接 + 行情
python test_single_price.py

# 验证推送
python test_notifier.py

# 启动主程序
python ibkr_real.py

# 后台运行
nohup python ibkr_real.py > ibkr_data/nohup.log 2>&1 &

# 查看日志
tail -f ibkr_data/logs/ibkr.log

# 停止
Ctrl+C
# 或
pkill -f ibkr_real.py
十七、安全提醒
.env 含 webhook / secret，不要提交到 git。

runtime_states.json / 状态 xlsx 不要用 Excel 打开。

跑程序时只开 IB Gateway，不要同时登录 Web / 手机 App。

实盘前先在模拟盘验证 1 周。

不要强杀进程（kill -9），用 Ctrl+C 正常退出。

十八、技术支持
遇到问题：

先看第八章"故障排查"

看日志 ibkr_data/logs/ibkr.log

看钉钉/飞书推送的告警

关键判断：

行情问题 → 检查 IB Gateway + 多会话

订单问题 → 检查 IBKR 账户余额 + 权限

推送问题 → 检查 webhook + 安全设置

文档结束。

建议打印或保存一份，作为日常操作参考。

本回答由 AI 生成，内容仅供参考，请仔细甄别
