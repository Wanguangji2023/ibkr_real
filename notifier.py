import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
from config import Config
from logger import get_logger

log = get_logger("notifier")

_last_push = {}


def _can_push(key):
    if key is None:
        return True
    now = time.time()
    if key in _last_push and now - _last_push[key] < Config.PUSH_MIN_INTERVAL:
        return False
    _last_push[key] = now
    return True


# ========== 钉钉 ==========
def _dingding_sign_url():
    """返回带签名的钉钉 URL；没有 secret 则原样返回"""
    webhook = Config.DINGDING_WEBHOOK
    secret = Config.DINGDING_SECRET
    if not webhook:
        return None
    if not secret:
        return webhook
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return f"{webhook}&timestamp={timestamp}&sign={sign}"


def _dingding(text):
    url = _dingding_sign_url()
    if not url:
        return
    try:
        r = requests.post(url,
                          json={"msgtype": "text",
                                "text": {"content": text}},
                          timeout=5)
        if r.status_code != 200:
            log.error(f"钉钉推送失败: {r.status_code} {r.text}")
    except Exception as e:
        log.error(f"钉钉推送异常: {e}")


# ========== 飞书 ==========
def _feishu_sign(timestamp, secret):
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def _feishu(text):
    webhook = Config.FEISHU_WEBHOOK
    secret = Config.FEISHU_SECRET
    if not webhook:
        return
    payload = {"msg_type": "text", "content": {"text": text}}
    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = _feishu_sign(timestamp, secret)
    try:
        r = requests.post(webhook, json=payload, timeout=5)
        if r.status_code != 200:
            log.error(f"飞书推送失败: {r.status_code} {r.text}")
    except Exception as e:
        log.error(f"飞书推送异常: {e}")


# ========== 统一入口 ==========
def push(text, key=None):
    if not _can_push(key):
        return
    if Config.PUSH_MODE in ("dingding", "both"):
        _dingding(text)
    if Config.PUSH_MODE in ("feishu", "both"):
        _feishu(text)
    log.info(f"[PUSH] {text}")