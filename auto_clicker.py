#!/usr/bin/env python3
"""
Auto Clicker — a lightweight, configurable auto clicker with a GUI.

Features:
  - Live cursor position display
  - Configurable click interval (ms)
  - Variance setting so clicks aren't perfectly uniform
  - Lock-in a target position or follow the cursor
  - Global hotkey to start/stop (F6)
  - Global hotkey to capture cursor position (F7)
  - Window filter so clicks only fire when a chosen window is active
"""

import random
import threading
import time
import tkinter as tk
from tkinter import ttk

import pyautogui
import pygetwindow as gw

# Safety: disable pyautogui's built-in pause so we control timing ourselves.
pyautogui.PAUSE = 0
# Fail-safe: move mouse to upper-left corner to abort.
pyautogui.FAILSAFE = True


class Position:
    """Simple mutable container for an (x, y) screen coordinate."""

    def __init__(self, x: int = 0, y: int = 0):
        self.x = x
        self.y = y


class Clicker:
    """Background thread that performs clicks at a configurable interval."""

    def __init__(self):
        self.running = False
        self.interval_ms: int = 100
        self.variance_ms: int = 0
        self.target: Position | None = None  # None = follow cursor
        self.window_title: str = ""  # empty = click regardless of window
        self.max_clicks: int = 0  # 0 = unlimited
        self.click_count: int = 0
        self.on_finished: callable = None  # called when max_clicks reached
        self._thread: threading.Thread | None = None

    def start(
        self,
        interval_ms: int,
        variance_ms: int,
        target: Position | None,
        window_title: str = "",
        max_clicks: int = 0,
    ):
        if self.running:
            return
        self.interval_ms = max(10, interval_ms)
        self.variance_ms = max(0, variance_ms)
        self.target = target
        self.window_title = window_title
        self.max_clicks = max(0, max_clicks)
        self.click_count = 0
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _is_target_window_active(self) -> bool:
        """Return True if we should click (no filter, or the right window is focused)."""
        if not self.window_title:
            return True
        try:
            active = gw.getActiveWindowTitle() or ""
            return self.window_title in active
        except Exception:
            return False

    def _loop(self):
        while self.running:
            if self._is_target_window_active():
                if self.target is not None:
                    pyautogui.click(self.target.x, self.target.y)
                else:
                    pyautogui.click()

                self.click_count += 1
                if self.max_clicks > 0 and self.click_count >= self.max_clicks:
                    self.running = False
                    if self.on_finished:
                        self.on_finished()
                    break

            delay_ms = self.interval_ms
            if self.variance_ms > 0:
                delay_ms += random.randint(-self.variance_ms, self.variance_ms)
                delay_ms = max(10, delay_ms)  # never go below 10 ms

            time.sleep(delay_ms / 1000.0)


class App(tk.Tk):
    """Main GUI window."""

    POLL_MS = 50  # how often we refresh the cursor position label

    def __init__(self):
        super().__init__()
        self.title("Auto Clicker")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.clicker = Clicker()
        self.locked_position: Position | None = None

        self._build_ui()
        self._poll_cursor()

        # Global hotkey: F6 to toggle start/stop, F7 to capture cursor position
        self.bind_all("<F6>", lambda _e: self._toggle())
        self.bind_all("<F7>", lambda _e: self._capture_position())

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # --- Cursor position ---
        pos_frame = ttk.LabelFrame(self, text="Cursor Position")
        pos_frame.grid(row=0, column=0, sticky="ew", **pad)

        self.pos_label = ttk.Label(pos_frame, text="X: —  Y: —", width=28)
        self.pos_label.grid(row=0, column=0, columnspan=3, **pad)

        # --- Target position entry ---
        target_frame = ttk.LabelFrame(self, text="Target Position")
        target_frame.grid(row=1, column=0, sticky="ew", **pad)

        ttk.Label(target_frame, text="X:").grid(row=0, column=0, **pad)
        self.target_x_var = tk.StringVar()
        self.target_x_entry = ttk.Entry(
            target_frame, textvariable=self.target_x_var, width=7
        )
        self.target_x_entry.grid(row=0, column=1, **pad)

        ttk.Label(target_frame, text="Y:").grid(row=0, column=2, **pad)
        self.target_y_var = tk.StringVar()
        self.target_y_entry = ttk.Entry(
            target_frame, textvariable=self.target_y_var, width=7
        )
        self.target_y_entry.grid(row=0, column=3, **pad)

        self.set_btn = ttk.Button(
            target_frame, text="Set", command=self._set_target
        )
        self.set_btn.grid(row=0, column=4, **pad)

        self.capture_btn = ttk.Button(
            target_frame, text="Capture (F7)", command=self._capture_position
        )
        self.capture_btn.grid(row=1, column=0, columnspan=3, **pad)

        self.clear_btn = ttk.Button(
            target_frame, text="Clear", command=self._clear_target
        )
        self.clear_btn.grid(row=1, column=3, columnspan=2, **pad)

        self.target_status = ttk.Label(
            target_frame, text="No target — clicks follow cursor", foreground="gray"
        )
        self.target_status.grid(row=2, column=0, columnspan=5, **pad)

        # --- Window filter ---
        win_frame = ttk.LabelFrame(self, text="Window Filter")
        win_frame.grid(row=2, column=0, sticky="ew", **pad)

        self.window_var = tk.StringVar(value="(Any window)")
        self.window_combo = ttk.Combobox(
            win_frame, textvariable=self.window_var, state="readonly", width=32
        )
        self.window_combo.grid(row=0, column=0, **pad)
        self._refresh_windows()

        self.refresh_btn = ttk.Button(
            win_frame, text="Refresh", command=self._refresh_windows
        )
        self.refresh_btn.grid(row=0, column=1, **pad)

        ttk.Label(
            win_frame,
            text="Clicks only fire when this window is active",
            foreground="gray",
        ).grid(row=1, column=0, columnspan=2, **pad)

        # --- Interval ---
        interval_frame = ttk.LabelFrame(self, text="Click Interval")
        interval_frame.grid(row=3, column=0, sticky="ew", **pad)

        ttk.Label(interval_frame, text="Interval (ms):").grid(
            row=0, column=0, **pad
        )
        self.interval_var = tk.IntVar(value=100)
        self.interval_entry = ttk.Entry(
            interval_frame, textvariable=self.interval_var, width=10
        )
        self.interval_entry.grid(row=0, column=1, **pad)

        # --- Variance ---
        ttk.Label(interval_frame, text="Variance (ms):").grid(
            row=1, column=0, **pad
        )
        self.variance_var = tk.IntVar(value=0)
        self.variance_entry = ttk.Entry(
            interval_frame, textvariable=self.variance_var, width=10
        )
        self.variance_entry.grid(row=1, column=1, **pad)

        ttk.Label(
            interval_frame,
            text="Each click = interval +/- random(variance)",
            foreground="gray",
        ).grid(row=2, column=0, columnspan=2, **pad)

        # --- Click limit ---
        ttk.Label(interval_frame, text="Click limit:").grid(
            row=3, column=0, **pad
        )
        self.limit_var = tk.IntVar(value=0)
        self.limit_entry = ttk.Entry(
            interval_frame, textvariable=self.limit_var, width=10
        )
        self.limit_entry.grid(row=3, column=1, **pad)

        ttk.Label(
            interval_frame,
            text="0 = unlimited",
            foreground="gray",
        ).grid(row=4, column=0, columnspan=2, **pad)

        # --- Controls ---
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.grid(row=4, column=0, sticky="ew", **pad)

        self.toggle_btn = ttk.Button(
            ctrl_frame, text="Start  (F6)", command=self._toggle
        )
        self.toggle_btn.grid(row=0, column=0, **pad)

        self.status_label = ttk.Label(ctrl_frame, text="Stopped", foreground="red")
        self.status_label.grid(row=0, column=1, **pad)

    # ----------------------------------------------------------- actions
    def _toggle(self):
        if self.clicker.running:
            self._stop()
        else:
            self._start()

    def _refresh_windows(self):
        """Populate the window dropdown with currently open windows."""
        any_option = "(Any window)"
        titles = sorted(
            {t for t in gw.getAllTitles() if t.strip()},
            key=str.casefold,
        )
        self.window_combo["values"] = [any_option] + titles
        if self.window_var.get() not in self.window_combo["values"]:
            self.window_var.set(any_option)

    def _start(self):
        try:
            interval = self.interval_var.get()
            variance = self.variance_var.get()
            limit = self.limit_var.get()
        except tk.TclError:
            return  # invalid input, ignore

        target = self.locked_position  # None means "follow cursor"
        win = self.window_var.get()
        window_title = "" if win == "(Any window)" else win

        self.clicker.on_finished = lambda: self.after(0, self._on_clicker_finished)
        self.clicker.start(interval, variance, target, window_title, limit)

        self.toggle_btn.config(text="Stop  (F6)")
        if limit > 0:
            self.status_label.config(text=f"Running (0/{limit})", foreground="green")
            self._poll_click_count()
        else:
            self.status_label.config(text="Running", foreground="green")

    def _stop(self):
        self.clicker.stop()
        self.toggle_btn.config(text="Start  (F6)")
        self.status_label.config(text="Stopped", foreground="red")

    def _on_clicker_finished(self):
        """Called from the clicker thread (via after) when max_clicks is reached."""
        count = self.clicker.click_count
        self.toggle_btn.config(text="Start  (F6)")
        self.status_label.config(
            text=f"Done ({count} clicks)", foreground="orange"
        )

    def _poll_click_count(self):
        """Update the status label with the current click count while running."""
        if not self.clicker.running:
            return
        count = self.clicker.click_count
        limit = self.clicker.max_clicks
        self.status_label.config(text=f"Running ({count}/{limit})")
        self.after(self.POLL_MS, self._poll_click_count)

    def _capture_position(self):
        """Snapshot the current cursor position into the X/Y fields and lock it."""
        x, y = pyautogui.position()
        self.target_x_var.set(str(x))
        self.target_y_var.set(str(y))
        self._apply_target(x, y)

    def _set_target(self):
        """Lock the target to whatever is typed in the X/Y fields."""
        try:
            x = int(self.target_x_var.get())
            y = int(self.target_y_var.get())
        except ValueError:
            return
        self._apply_target(x, y)

    def _clear_target(self):
        """Remove the locked target so clicks follow the cursor."""
        self.locked_position = None
        self.target_x_var.set("")
        self.target_y_var.set("")
        self.target_status.config(
            text="No target — clicks follow cursor", foreground="gray"
        )

    def _apply_target(self, x: int, y: int):
        self.locked_position = Position(x, y)
        self.target_status.config(
            text=f"Target locked: ({x}, {y})", foreground="blue"
        )

    # -------------------------------------------------------- cursor poll
    def _poll_cursor(self):
        x, y = pyautogui.position()
        self.pos_label.config(text=f"X: {x}  Y: {y}")
        self.after(self.POLL_MS, self._poll_cursor)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
