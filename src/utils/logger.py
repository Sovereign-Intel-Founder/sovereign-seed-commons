import json, os, queue, threading, time

class AsyncJSONLogger:
    def __init__(self, log_path="logs/sovereign.jsonl"):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.queue = queue.Queue(maxsize=10000)
        self.log_path = log_path
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._process_queue, daemon=True)
        self._worker.start()

    def log(self, level, message, **kwargs):
        payload = {"timestamp": time.time(), "level": level, "message": message, **kwargs}
        try:
            self.queue.put_nowait(json.dumps(payload))
        except queue.Full:
            pass

    def _process_queue(self):
        with open(self.log_path, "a", encoding="utf-8") as f:
            while not self._stop_event.is_set() or not self.queue.empty():
                try:
                    item = self.queue.get(timeout=0.1)
                    f.write(item + "\n")
                    f.flush()
                    self.queue.task_done()
                except queue.Empty:
                    continue

    def close(self):
        self._stop_event.set()
        self._worker.join()
