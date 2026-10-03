#!/usr/bin/env python3
import curses
import time
from pathlib import Path

TELEMETRY_FILES = {
    "Shared Memory Metrics": "telemetry/tollbridge_system/shared_memory_metrics.log",
    "Concurrency Results": "telemetry/tollbridge_system/concurrency_results.log",
    "Submission Concurrency": "telemetry/tollbridge_system/submission_concurrency.log",
    "Live Benchmark (JSONL)": "logs/live_benchmark.jsonl",
    "Core 128 Benchmark": "logs/core128_benchmark.jsonl"
}

def tail_file(filepath, lines=2):
    path = Path(filepath)
    if not path.exists():
        return ["[Inactive / Not Found]"]
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            return [line.strip() for line in all_lines[-lines:] if line.strip()]
    except Exception as e:
        return [f"[Read Error: {e}]"]

def main(stdscr):
    # Initialize curses settings
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(1000) # Refresh every 1 second

    # Initialize color pairs if terminal supports them
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)

    while True:
        try:
            # Handle user input (Press 'q' to quit)
            key = stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                break

            stdscr.erase()
            height, width = stdscr.getmaxyx()

            if height < 20 or width < 75:
                stdscr.addstr(0, 0, "Terminal window too small! Please expand.")
                stdscr.refresh()
                continue

            # Header Banner
            title = " SOVEREIGN INTELLIGENCE PROTOCOL — LIVE SYSTEM TUI "
            header_attr = curses.color_pair(2) | curses.A_BOLD
            stdscr.addstr(0, max(0, (width - len(title)) // 2), title[:width], header_attr)

            # Render Subsystem Windows
            row = 2
            for name, path in TELEMETRY_FILES.items():
                if row >= height - 2:
                    break
                
                # Subsystem Section Title
                section_title = f"▶ {name} ({path})"
                stdscr.addstr(row, 2, section_title[:width-4], curses.color_pair(3) | curses.A_BOLD)
                row += 1

                # Tail entries
                entries = tail_file(path, lines=2)
                for entry in entries:
                    if row >= height - 2:
                        break
                    display_line = f"    {entry}"
                    stdscr.addstr(row, 2, display_line[:width-4], curses.color_pair(1))
                    row += 1
                row += 1 # Spacing

            # Bottom Status Bar
            status_bar = f" [STATUS: ACTIVE] | Timestamp: {time.strftime('%H:%M:%S')} | Press 'q' to Quit "
            bar_attr = curses.color_pair(4)
            stdscr.addstr(height - 1, 0, status_bar.ljust(width)[:width], bar_attr)

            stdscr.refresh()

        except Exception:
            pass

if __name__ == "__main__":
    curses.wrapper(main)
