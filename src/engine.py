import time
import sys
import os

# Ensure the src directory is in the module search path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from utils.logger import AsyncJSONLogger

def main():
    logger = AsyncJSONLogger("logs/sovereign.jsonl")
    logger.log("INFO", "Sovereign Intelligence Protocol engine starting up", core_version="2.0.0")
    
    try:
        counter = 0
        while True:
            counter += 1
            logger.log("DEBUG", f"Heartbeat pulse executed", sequence=counter)
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.log("INFO", "Engine shutdown initiated by operator")
    finally:
        logger.close()
        print("Engine cleanly shut down.")

if __name__ == "__main__":
    main()
