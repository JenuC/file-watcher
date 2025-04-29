from watcher_log import FileWatcher
import time
import sys
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

# Get wait time from command line or use default
wait_time = int(sys.argv[1]) if len(sys.argv) > 1 else 10

print(f"Starting file watcher for {wait_time} seconds...")
print("Create, modify, or delete files in the current directory")

with FileWatcher(".") as watcher:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        refresh_per_second=10
    ) as progress:
        task = progress.add_task("Watching files...", total=wait_time)
        while not progress.finished:
            progress.update(task, advance=0.1)
            time.sleep(0.1)

# Show final file lifetimes
lifetimes = watcher.get_file_lifetimes()
if lifetimes:
    print("\nFile lifetimes:")
    for path, lifetime in lifetimes:
        print(f"{path}: {lifetime}")
else:
    print("\nNo file changes detected.")