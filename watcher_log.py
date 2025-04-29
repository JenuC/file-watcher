import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from rich.console import Console
from rich.text import Text
from rich.panel import Panel


class FileWatcher:
    def __init__(self, watch_path="."):
        self.console = Console()
        self.watch_path = watch_path
        self.file_history = {}
        self.running = False
        self.observer = None
        self.input_thread = None

    def _calculate_lifetime(self, events):
        """Calculate the lifetime of a file based on its events."""
        if not events:
            return "N/A"
        
        first_event = events[0][0]  # First event timestamp
        if events[-1][1] == "Deleted":
            last_event = events[-1][0]  # Use deletion time
            lifetime = last_event - first_event
        else:
            lifetime = datetime.now() - first_event
        
        seconds = lifetime.total_seconds()
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"

    def _log_event(self, event_type, file_path, dest_path=None):
        current_time = datetime.now()
        
        if file_path not in self.file_history:
            self.file_history[file_path] = []
        self.file_history[file_path].append((current_time, event_type, dest_path))

    def _is_event_relevant(self, file_path):
        """Checks if the event is relevant (not .git files)."""
        path = Path(file_path)
        return ".git" not in path.parts

    def get_file_lifetimes(self):
        """Return a list of files and their lifetimes in order of creation."""
        sorted_files = sorted(self.file_history.items(), 
                            key=lambda x: x[1][0][0] if x[1] else datetime.max)
        
        lifetimes = []
        for path, events in sorted_files:
            if not events:
                continue
            lifetime = self._calculate_lifetime(events)
            lifetimes.append((path, lifetime))
        return lifetimes

    def start(self):
        """Start watching files."""
        if self.running:
            return

        class EventHandler(FileSystemEventHandler):
            def __init__(self, parent):
                self.parent = parent
                super().__init__()

            def on_created(self, event):
                if not event.is_directory and self.parent._is_event_relevant(event.src_path):
                    self.parent._log_event("Created", event.src_path)

            def on_modified(self, event):
                if not event.is_directory and self.parent._is_event_relevant(event.src_path):
                    self.parent._log_event("Modified", event.src_path)

            def on_deleted(self, event):
                if not event.is_directory and self.parent._is_event_relevant(event.src_path):
                    self.parent._log_event("Deleted", event.src_path)

            def on_moved(self, event):
                if (not event.is_directory and 
                    self.parent._is_event_relevant(event.src_path) and 
                    self.parent._is_event_relevant(event.dest_path)):
                    self.parent._log_event("Moved", event.src_path, event.dest_path)

        self.running = True
        self.observer = Observer()
        self.observer.schedule(EventHandler(self), self.watch_path, recursive=True)
        self.observer.start()

        def check_user_input():
            while self.running:
                user_input = input()
                if user_input.strip() == ":q":
                    self.stop()
                    break

        self.input_thread = threading.Thread(target=check_user_input, daemon=True)
        self.input_thread.start()

    def stop(self):
        """Stop watching files."""
        if not self.running:
            return
            
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
        if self.input_thread:
            self.input_thread.join()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


if __name__ == "__main__":
    # Example usage
    with FileWatcher() as watcher:
        try:
            while watcher.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            watcher.stop()
        
        # Print file lifetimes
        lifetimes = watcher.get_file_lifetimes()
        for path, lifetime in lifetimes:
            print(f"{path}: {lifetime}")
