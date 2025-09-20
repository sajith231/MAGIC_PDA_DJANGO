# run_service.py
import time
import logging
import sqlanydb
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

DSN = "pktc"

def main():
    logging.info("SyncService started")
    while True:
        try:
            conn = sqlanydb.connect(DSN=DSN, UID="dba", PWD="sql")
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            logging.info("DB heartbeat OK @ %s", datetime.now().strftime("%H:%M:%S"))
        except Exception as e:
            logging.error("Heartbeat failed: %s", e)
        time.sleep(30)

if __name__ == "__main__":
    main()