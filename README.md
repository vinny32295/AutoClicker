# Auto Clicker

A lightweight auto clicker with a GUI, built in Python. Designed to run locally on any machine.

## Features

- **Live cursor tracking** — displays current mouse X/Y coordinates in real time
- **Lock position** — lock in a screen coordinate so clicks always hit the same spot, or leave unlocked to click wherever the cursor is
- **Configurable interval** — set the delay between clicks in milliseconds
- **Variance** — add randomness so clicks aren't perfectly uniform (each click = interval +/- random value up to variance)
- **Global hotkey** — press **F6** to start/stop without needing to focus the window
- **Fail-safe** — move your mouse to the upper-left corner of the screen to instantly abort

## Quick Start

### Windows

```cmd
git clone https://github.com/vinny32295/AutoClicker.git
cd AutoClicker
pip install -r requirements.txt
python auto_clicker.py
```

### macOS / Linux

```bash
git clone https://github.com/vinny32295/AutoClicker.git
cd AutoClicker
pip install -r requirements.txt
python auto_clicker.py
```

On Linux you may also need:
```bash
sudo apt install python3-tk scrot
```

## Requirements

- Python 3.10+
- `pyautogui` — performs the clicks and reads cursor position
- `pynput` — transitive dependency for input control

## Usage

1. Launch the app — a small always-on-top window appears.
2. Set **Interval (ms)** — the base delay between clicks (minimum 10 ms).
3. Set **Variance (ms)** — optional randomness added to each interval.
   For example, interval=100 and variance=20 means each click waits between 80–120 ms.
4. Optionally click **Lock Position** to freeze the target coordinates. If unlocked, clicks happen wherever your cursor currently is.
5. Press **Start (F6)** or hit the **F6** key to begin clicking.
6. Press **Stop (F6)** or hit **F6** again to stop.

## Safety

PyAutoGUI's fail-safe is enabled: quickly move your mouse to the **top-left corner** (0, 0) of the screen to raise an exception and stop the clicker immediately.
