from datetime import datetime, timedelta
import pytz
import exchange_calendars as xcals

ET = pytz.timezone("America/New_York")
NYSE = xcals.get_calendar("XNYS")


def now_et():
    return datetime.now(ET)


def is_trading_now(pre_post=False):
    """判断当前是否处于交易时段"""
    now = now_et()
    session = NYSE.date_to_session(now.date(), direction="next")
    open_utc = NYSE.session_open(session)
    close_utc = NYSE.session_close(session)

    open_et = open_utc.tz_convert(ET)
    close_et = close_utc.tz_convert(ET)

    if pre_post:
        # 盘前 4:00 开始，盘后 20:00 结束
        start = open_et - timedelta(hours=5, minutes=30)
        end = close_et + timedelta(hours=4)
    else:
        start = open_et
        end = close_et

    return start <= now <= end


def next_open_et():
    """返回下一个开盘时间（ET）"""
    now = now_et()
    session = NYSE.date_to_session(now.date(), direction="next")
    open_utc = NYSE.session_open(session)
    open_et = open_utc.tz_convert(ET)
    if open_et <= now:
        nxt = NYSE.next_session(session)
        open_et = NYSE.session_open(nxt).tz_convert(ET)
    return open_et


def sleep_until_next_open():
    import time
    target = next_open_et()
    delta = (target - now_et()).total_seconds()
    if delta > 0:
        time.sleep(delta)