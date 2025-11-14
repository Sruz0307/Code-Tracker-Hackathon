# watcher.py
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ChangeHandler(FileSystemEventHandler):
    def __init__(self, callback, debounce_interval=0.5):
        self.callback = callback
        self.debounce_interval = debounce_interval
        self.last_called = {}

    def on_modified(self, event):
        if not event.src_path.endswith(".py"):
            return

        now = time.time()
        last_time = self.last_called.get(event.src_path, 0)

        # Ignore if the same file was triggered very recently
        if now - last_time < self.debounce_interval:
            return

        self.last_called[event.src_path] = now
        self.callback(event.src_path)

def watch_folder(folder_path, on_change):
    event_handler = ChangeHandler(on_change)
    observer = Observer()
    observer.schedule(event_handler, folder_path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
