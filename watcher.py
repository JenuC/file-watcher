import sys
import time
import logging
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


class MyEventHandler(FileSystemEventHandler):
    def __init__(self, console: Console):
        self.console = console
        super().__init__()

    def on_created(self, event):
        if not event.is_directory:
            self.console.print(Text(f"File created: {event.src_path}", style="green"))

    def on_modified(self, event):
        if not event.is_directory:
            self.console.print(Text(f"File modified: {event.src_path}", style="yellow"))

    def on_deleted(self, event):
        if not event.is_directory:
            self.console.print(Text(f"File deleted: {event.src_path}", style="red"))

    def on_moved(self, event):
        if not event.is_directory:
            self.console.print(
                Text(
                    f"File moved from {event.src_path} to {event.dest_path}",
                    style="blue",
                )
            )


if __name__ == "__main__":
    console = Console()
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    path = sys.argv[1] if len(sys.argv) > 1 else "."
    event_handler = MyEventHandler(console)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        console.print("[bold magenta]Watcher stopped by user.[/bold magenta]")
    observer.join()
    console.print("[bold magenta]Watcher finished.[/bold magenta]")
