import sqlanydb
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")

def _get_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

def get_connection():
    cfg = _get_config()
    dsn = cfg.get("dsn", "pktc")
    logging.info("Attempting connection with DSN: %s", dsn)
    conn = sqlanydb.connect(DSN=dsn)   # <-- let DSN supply credentials
    logging.info("Database connection established!")
    return conn