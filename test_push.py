# test_push.py
import notifier

notifier.push("【测试】交易推送 1", key=None)
notifier.push("【测试】交易推送 2", key=None)
print("推送完成，检查手机")