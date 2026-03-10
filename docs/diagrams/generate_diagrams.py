from __future__ import annotations

from pathlib import Path
from textwrap import wrap
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FontLike = Any


def _font(size: int) -> FontLike:
    for candidate in ("arial.ttf", "segoeui.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    width_chars: int,
    font: FontLike,
    fill: str = "#111111",
) -> int:
    lines: list[str] = []
    for block in text.split("\n"):
        if not block.strip():
            lines.append("")
            continue
        lines.extend(wrap(block, width=width_chars))
    text_bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_h = int((text_bbox[3] - text_bbox[1]) + 8)
    yy: int = y
    for line in lines:
        draw.text((x, yy), line, fill=fill, font=font)
        yy += line_h
    return int(yy)


def _box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    title: str,
    body: str,
    title_font: FontLike,
    body_font: FontLike,
    fill: str,
) -> None:
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=18, fill=fill, outline="#204060", width=3)
    draw.text((x1 + 18, y1 + 14), title, fill="#0a2a43", font=title_font)
    _draw_wrapped_text(draw, body, x1 + 18, y1 + 52, width_chars=48, font=body_font)


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str = "#1d4e89") -> None:
    draw.line([start, end], fill=color, width=5)
    ex, ey = end
    draw.polygon([(ex, ey), (ex - 10, ey - 18), (ex + 10, ey - 18)], fill=color)


def create_workflow_diagram() -> None:
    img = Image.new("RGB", (1800, 2500), "#f7fbff")
    draw = ImageDraw.Draw(img)

    h1 = _font(52)
    h2 = _font(30)
    body = _font(24)

    draw.text((70, 40), "WRO 2026 FE - Beginner Quick Start Workflow", fill="#07233b", font=h1)
    draw.text((70, 112), "From git clone to calibration and vehicle test", fill="#27577e", font=h2)

    boxes = [
        ("1) Clone project", "git clone https://github.com/sjhallo07/wro2026-fe-vehicle.git\ncd wro2026-fe-vehicle"),
        ("2) Install Python packages", "python3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt"),
        ("3) Upload Arduino sketch", "Open src/arduino/motor_control.ino\nSelect Arduino Uno + correct port\nClick Upload"),
        ("4) Connect hardware", "USB: Raspberry Pi -> Arduino\nCamera -> Raspberry Pi CSI/USB\nServo + ESC -> Arduino pins as in sketch"),
        ("5) Test serial communication", "python3 src/examples/rpi_arduino_serial_test.py --port /dev/ttyACM0\n(Windows bench test: --port COM3)"),
        ("6) Calibrate colors", "python3 src/utils/calibration.py\nPress S to save, Q to quit"),
        ("7) Run driving program", "python3 src/main.py\nCheck camera window and command feedback"),
    ]

    start_y = 210
    box_h = 275
    gap = 65
    x1, x2 = 120, 1680

    for i, (title, content) in enumerate(boxes):
        y1 = start_y + i * (box_h + gap)
        y2 = y1 + box_h
        _box(draw, (x1, y1, x2, y2), title, content, h2, body, fill="#eaf4ff")
        if i < len(boxes) - 1:
            _arrow(draw, (900, y2 + 8), (900, y2 + gap - 8))

    img.save(ROOT / "01_quick_start_workflow.png", format="PNG")


def create_connection_diagram() -> None:
    img = Image.new("RGB", (1800, 1200), "#fcfeff")
    draw = ImageDraw.Draw(img)

    h1 = _font(48)
    h2 = _font(28)
    body = _font(24)

    draw.text((60, 36), "Raspberry Pi + Arduino Connection Overview", fill="#07233b", font=h1)
    draw.text((60, 98), "Use this as a physical setup checklist", fill="#27577e", font=h2)

    # Device boxes
    devices = {
        "Raspberry Pi": (110, 250, 620, 560),
        "Arduino Uno": (720, 250, 1230, 560),
        "Camera": (110, 700, 620, 1030),
        "Steering Servo": (720, 700, 965, 1030),
        "ESC / Motor": (985, 700, 1230, 1030),
        "Power/Battery": (1340, 250, 1710, 1030),
    }

    for name, rect in devices.items():
        _box(draw, rect, name, "", h2, body, fill="#edf8f0")

    # Labels inside boxes
    draw.text((155, 332), "Runs Python code", fill="#163a2f", font=body)
    draw.text((155, 370), "OpenCV + serial", fill="#163a2f", font=body)

    draw.text((760, 332), "Receives S/T commands", fill="#163a2f", font=body)
    draw.text((760, 370), "Controls PWM outputs", fill="#163a2f", font=body)

    draw.text((150, 812), "Detect pillars", fill="#163a2f", font=body)
    draw.text((150, 850), "(red/green/magenta)", fill="#163a2f", font=body)

    draw.text((743, 812), "Signal on pin 10", fill="#163a2f", font=body)
    draw.text((1010, 812), "Signal on pin 9", fill="#163a2f", font=body)

    draw.text((1380, 520), "Provide safe voltage", fill="#163a2f", font=body)
    draw.text((1380, 558), "and common GND", fill="#163a2f", font=body)

    # Connection arrows
    _arrow(draw, (620, 405), (720, 405))  # Pi -> Arduino USB serial
    draw.text((635, 365), "USB serial", fill="#1d4e89", font=body)

    _arrow(draw, (365, 700), (365, 560))  # Camera -> Pi
    draw.text((235, 625), "CSI/USB video", fill="#1d4e89", font=body)

    _arrow(draw, (845, 700), (845, 560))  # Servo <- Arduino
    draw.text((740, 625), "PWM signal", fill="#1d4e89", font=body)

    _arrow(draw, (1105, 700), (1105, 560))  # ESC <- Arduino
    draw.text((1035, 625), "PWM signal", fill="#1d4e89", font=body)

    _arrow(draw, (1340, 420), (1230, 420))  # Power to Arduino
    _arrow(draw, (1340, 500), (620, 500))   # Power/GND to Pi side
    draw.text((1260, 455), "Power + GND", fill="#1d4e89", font=body)

    draw.text(
        (60, 1110),
        "Safety note: Always test wheels off the ground first, and verify neutral throttle (T1500) before driving.",
        fill="#7a2500",
        font=body,
    )

    img.save(ROOT / "02_connection_overview.png", format="PNG")


if __name__ == "__main__":
    create_workflow_diagram()
    create_connection_diagram()
    print("Generated: docs/diagrams/01_quick_start_workflow.png")
    print("Generated: docs/diagrams/02_connection_overview.png")
