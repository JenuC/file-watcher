import sys
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text
from rich.tree import Tree
from rich.panel import Panel


class MyEventHandler(FileSystemEventHandler):
    def __init__(self, console: Console, log_file: Path):
        self.console = console
        self.log_file = log_file
        self.file_history = {}
        self.log_file.parent.mkdir(parents=True, exist_ok=True)  # Ensure log dir exists
        self.end_tree = []
        super().__init__()

    def _log_event(self, event_type, file_path, dest_path=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if dest_path:
            log_message = f"{timestamp} - {event_type}: {file_path} -> {dest_path}"
        else:
            log_message = f"{timestamp} - {event_type}: {file_path}"

        with open(self.log_file, "a") as f:
            f.write(log_message + "\n")

        if file_path not in self.file_history:
            self.file_history[file_path] = []
        self.file_history[file_path].append((timestamp, event_type, dest_path))

        if dest_path:
            self._build_tree(file_path, timestamp, event_type, dest_path)
        else:
            self._build_tree(file_path, timestamp, event_type)

    def _build_tree(self, path, timestamp, event_type, dest_path=None):
        """Build the tree for the end of the program."""

        if dest_path:
            self.end_tree.append(
                f"{timestamp} - {event_type}: {path} -> {dest_path}"
            )
        else:
            self.end_tree.append(
                f"{timestamp} - {event_type}: {path}"
            )

    def _print_tree(self):
        """Print the tree in the log file and console at the end."""
        tree_dict = {}
        for line in self.end_tree:
            parts = line.split(" - ", 2)
            timestamp = parts[0]
            event_info = parts[1]

            if " -> " in event_info:
                event_type, paths = event_info.split(": ", 1)
                src_path, dest_path = paths.split(" -> ")
                path = src_path
            else:
                event_type, path = event_info.split(": ", 1)

            if path not in tree_dict:
                tree_dict[path] = []
            tree_dict[path].append(line)

        for path in tree_dict:
            tree = Tree(f"File History for {path}")
            for line in tree_dict[path]:
                tree.add(line)
            with open(self.log_file, "a") as f:
                f.write(f"\nFile History for {path}\n")
                for line in tree_dict[path]:
                    f.write(f"{line}\n")
            self.console.print(Panel(tree))

    def on_created(self, event):
        if not event.is_directory and self._is_event_relevant(event.src_path):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log_event("Created", event.src_path)
            self.console.print(Text(f"{timestamp} - File created: {event.src_path}", style="green"))

    def on_modified(self, event):
        if not event.is_directory and self._is_event_relevant(event.src_path):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log_event("Modified", event.src_path)
            self.console.print(Text(f"{timestamp} - File modified: {event.src_path}", style="yellow"))

    def on_deleted(self, event):
        if not event.is_directory and self._is_event_relevant(event.src_path):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log_event("Deleted", event.src_path)
            self.console.print(Text(f"{timestamp} - File deleted: {event.src_path}", style="red"))

    def on_moved(self, event):
        if (
            not event.is_directory
            and self._is_event_relevant(event.src_path)
            and self._is_event_relevant(event.dest_path)
        ):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._log_event("Moved", event.src_path, event.dest_path)
            self.console.print(
                Text(
                    f"{timestamp} - File moved from {event.src_path} to {event.dest_path}",
                    style="blue",
                )
            )

    def _is_event_relevant(self, file_path):
        """Checks if the event is relevant (not the log file or .git files)."""
        path = Path(file_path)
        return path != self.log_file and ".git" not in path.parts


class WatcherState:
    def __init__(self):
        self.running = True


if __name__ == "__main__":
    console = Console()
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    path = sys.argv[1] if len(sys.argv) > 1 else "."
    log_dir = Path("./logs")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"watcher_{timestamp}.log"

    event_handler = MyEventHandler(console, log_file)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    state = WatcherState()

    def check_user_input():
        while state.running:
            user_input = input()
            if user_input.strip() == ":q":
                state.running = False
                break

    input_thread = threading.Thread(target=check_user_input, daemon=True)
    input_thread.start()

    try:
        while state.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        state.running = False
        console.print("[bold magenta]Watcher stopped by user.[/bold magenta]")
        event_handler._print_tree()
    finally:
        observer.stop()
        observer.join()
        console.print("[bold magenta]Watcher finished.[/bold magenta]")
