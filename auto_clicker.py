#!/usr/bin/env python3
"""
Auto Clicker — a lightweight, configurable auto clicker with a GUI.

Features:
  - Live cursor position display
  - Configurable click interval (ms)
  - Variance setting so clicks aren't perfectly uniform
  - Lock-in a target position or follow the cursor
  - Global hotkey to start/stop (F6)
"""

import random
import threading
import time
import tkinter as tk
from tkinter import ttk

import pyautogui

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
        self._thread: threading.Thread | None = None

    def start(self, interval_ms: int, variance_ms: int, target: Position | None):
        if self.running:
            return
        self.interval_ms = max(10, interval_ms)
        self.variance_ms = max(0, variance_ms)
        self.target = target
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            if self.target is not None:
                pyautogui.click(self.target.x, self.target.y)
            else:
                pyautogui.click()

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

        # Global hotkey: F6 to toggle start/stop
        self.bind_all("<F6>", lambda _e: self._toggle())

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # --- Cursor position ---
        pos_frame = ttk.LabelFrame(self, text="Cursor Position")
        pos_frame.grid(row=0, column=0, sticky="ew", **pad)

        self.pos_label = ttk.Label(pos_frame, text="X: —  Y: —", width=28)
        self.pos_label.grid(row=0, column=0, **pad)

        self.lock_btn = ttk.Button(
            pos_frame, text="Lock Position", command=self._toggle_lock
        )
        self.lock_btn.grid(row=0, column=1, **pad)

        # --- Interval ---
        interval_frame = ttk.LabelFrame(self, text="Click Interval")
        interval_frame.grid(row=1, column=0, sticky="ew", **pad)

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

        # --- Controls ---
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.grid(row=2, column=0, sticky="ew", **pad)

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

    def _start(self):
        try:
            interval = self.interval_var.get()
            variance = self.variance_var.get()
        except tk.TclError:
            return  # invalid input, ignore

        target = self.locked_position  # None means "follow cursor"
        self.clicker.start(interval, variance, target)

        self.toggle_btn.config(text="Stop  (F6)")
        self.status_label.config(text="Running", foreground="green")

    def _stop(self):
        self.clicker.stop()
        self.toggle_btn.config(text="Start  (F6)")
        self.status_label.config(text="Stopped", foreground="red")

    def _toggle_lock(self):
        if self.locked_position is not None:
            self.locked_position = None
            self.lock_btn.config(text="Lock Position")
        else:
            x, y = pyautogui.position()
            self.locked_position = Position(x, y)
            self.lock_btn.config(text=f"Unlock ({x}, {y})")

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
