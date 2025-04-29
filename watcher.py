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
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.last_log_message = None
        super().__init__()

    def _log_event(self, event_type, file_path, dest_path=None):
        current_time = datetime.now()
        timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        if dest_path:
            log_message = f"{timestamp_str} - {event_type}: {file_path} -> {dest_path}"
        else:
            log_message = f"{timestamp_str} - {event_type}: {file_path}"

        # Only log if message is different from last one
        if log_message != self.last_log_message:
            with open(self.log_file, "a") as f:
                f.write(log_message + "\n")
            
            if file_path not in self.file_history:
                self.file_history[file_path] = []
            # Store the actual datetime object along with the event info
            self.file_history[file_path].append((current_time, event_type, dest_path))
            
            self.last_log_message = log_message

    def _calculate_lifetime(self, events):
        """Calculate the lifetime of a file based on its events."""
        if not events:
            return "N/A"
        
        first_event = events[0][0]  # First event timestamp
        last_event = events[-1][0]  # Use last event time
        
        lifetime = last_event - first_event
        seconds = lifetime.total_seconds()
        
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            return f"{seconds/60:.1f} minutes"
        else:
            return f"{seconds/3600:.1f} hours"

    def _print_tree(self):
        """Print the tree in the log file and console at the end."""
        # First write a summary to the log file
        with open(self.log_file, "a") as f:
            f.write("\n=== File History Summary ===\n")
            
            # Sort files by creation time
            sorted_files = sorted(self.file_history.items(), 
                                key=lambda x: x[1][0][0] if x[1] else datetime.max)
            
            for path, events in sorted_files:
                if not events:
                    continue
                    
                lifetime = self._calculate_lifetime(events)
                creation_time = events[0][0].strftime("%Y-%m-%d %H:%M:%S")
                
                # Write to log file
                f.write(f"\nFile: {path}\n")
                f.write(f"Created: {creation_time}\n")
                f.write(f"Lifetime: {lifetime}\n")
                f.write("Events:\n")
                
                for time, event_type, dest_path in events:
                    time_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    if dest_path:
                        f.write(f"  {time_str} - {event_type} -> {dest_path}\n")
                    else:
                        f.write(f"  {time_str} - {event_type}\n")
                f.write("\n")  # Add extra newline between files

        # Now print to console with rich formatting
        for path, events in sorted_files:
            if not events:
                continue
                
            tree = Tree(f"[bold]File: {path}[/bold]")
            lifetime = self._calculate_lifetime(events)
            creation_time = events[0][0].strftime("%Y-%m-%d %H:%M:%S")
            
            tree.add(f"[blue]Created: {creation_time}[/blue]")
            tree.add(f"[green]Lifetime: {lifetime}[/green]")
            
            events_branch = tree.add("Events:")
            for time, event_type, dest_path in events:
                time_str = time.strftime("%Y-%m-%d %H:%M:%S")
                if dest_path:
                    events_branch.add(f"[yellow]{time_str} - {event_type} -> {dest_path}[/yellow]")
                else:
                    events_branch.add(f"[yellow]{time_str} - {event_type}[/yellow]")
            
            self.console.print(Panel(tree))
            self.console.print()  # Add extra newline between files

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
    finally:
        observer.stop()
        observer.join()
        event_handler._print_tree()
        console.print("[bold magenta]Watcher finished.[/bold magenta]")
