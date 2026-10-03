#!/usr/bin/env python3
import curses
import time
import json
from pathlib import Path

def get_latest_metric(filepath):
    path = Path(filepath)
    if not path.exists():
        return {"status": "Inactive / File Missing"}
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("{"):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        pass
                return {"raw": line}
    except Exception as e:
        return {"error": str(e)}
    return {"status": "No data"}

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(500) # Refresh twice a second for live telemetry feel

    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Active metrics
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Titles / Highlights
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Borders
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Status Bar
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Subheaders

    while True:
        key = stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            break

        stdscr.erase()
        height, width = stdscr.getmaxyx()

        if height < 22 or width < 80:
            stdscr.addstr(0, 0, "Terminal window too small! Please expand for performance board.")
            stdscr.refresh()
            time.sleep(0.5)
            continue

        # Header Banner
        title = " SOVEREIGN INTELLIGENCE PROTOCOL — PERFORMANCE DISPLAY BOARD "
        stdscr.addstr(0, max(0, (width - len(title)) // 2), title[:width], curses.color_pair(2) | curses.A_BOLD)

        # -------------------------------------------------------------
        # CARD 1: Pipeline Throughput & Concurrency
        # -------------------------------------------------------------
        stdscr.addstr(2, 2, "┌─ PIPELINE THROUGHPUT & CONCURRENCY METRICS ─────────────────┐", curses.color_pair(3))
        
        conc_data = get_latest_metric("telemetry/tollbridge_system/concurrency_results.log")
        sub_data = get_latest_metric("telemetry/tollbridge_system/submission_concurrency.log")

        stdscr.addstr(3, 4, "Concurrency Engine:", curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(3, 26, f"{str(conc_data)[:width-30]}", curses.color_pair(1))

        stdscr.addstr(4, 4, "Submission Engine:", curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(4, 26, f"{str(sub_data)[:width-30]}", curses.color_pair(1))
        
        stdscr.addstr(5, 2, "└─────────────────────────────────────────────────────────────┘", curses.color_pair(3))

        # -------------------------------------------------------------
        # CARD 2: Live Arbitrage Ring Buffer & Core Telemetry
        # -------------------------------------------------------------
        stdscr.addstr(7, 2, "┌─ LIVE ARBITRAGE RING & CORE BENCHMARK STREAM ───────────────┐", curses.color_pair(3))

        live_bench = get_latest_metric("logs/live_benchmark.jsonl")
        core_bench = get_latest_metric("logs/core128_benchmark.jsonl")

        stdscr.addstr(8, 4, "Arbitrage Ring Tick:", curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(8, 26, f"{str(live_bench)[:width-30]}", curses.color_pair(2))

        stdscr.addstr(9, 4, "Core 128 Checkpoint:", curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(9, 26, f"{str(core_bench)[:width-30]}", curses.color_pair(2))

        stdscr.addstr(10, 2, "└─────────────────────────────────────────────────────────────┘", curses.color_pair(3))

        # -------------------------------------------------------------
        # CARD 3: Shared Memory & System Health Summary
        # -------------------------------------------------------------
        stdscr.addstr(12, 2, "┌─ SHARED MEMORY & SUBSYSTEM HEALTH ──────────────────────────┐", curses.color_pair(3))
        
        shm_data = get_latest_metric("telemetry/tollbridge_system/shared_memory_metrics.log")
        stdscr.addstr(13, 4, "SHM Ring Status:", curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(13, 26, f"{str(shm_data)[:width-30]}", curses.color_pair(1))

        stdscr.addstr(14, 2, "└─────────────────────────────────────────────────────────────┘", curses.color_pair(3))

        # Bottom Status Bar
        status_bar = f" [BOARD MODE: ACTIVE TELEMETRY] | Refresh: 500ms | Timestamp: {time.strftime('%H:%M:%S')} | Press 'q' to Quit"
        try:
            stdscr.addstr(height - 1, 0, status_bar.ljust(width - 1)[:width - 1], curses.color_pair(4))
        except Exception:
            pass

        stdscr.refresh()
        time.sleep(0.5)

if __name__ == "__main__":
    curses.wrapper(main)
