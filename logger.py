import os
import glob
import logging
from logging.handlers import RotatingFileHandler
from config import Config


def _cleanup_old_logs(log_dir, max_files):
    files = sorted(glob.glob(os.path.join(log_dir, "*.log")),
                   key=os.path.getmtime)
    while len(files) > max_files:
        os.remove(files.pop(0))


def get_logger(name="ibkr"):
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    fh = RotatingFileHandler(
        os.path.join(Config.LOG_DIR, "ibkr.log"),
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_MAX_FILES,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    _cleanup_old_logs(Config.LOG_DIR, Config.LOG_MAX_FILES)
    return logger