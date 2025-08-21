import logging
import os

def get_logger(name: str = "automation"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    # Create logs folder alongside script
    base_dir = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(base_dir, "output")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "run.log")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger
