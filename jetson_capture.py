#!/usr/bin/env python3
"""Capture images on a Jetson CSI camera and automatically push them to GitHub."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import cv2
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: opencv-python. Install it with `python3 -m pip install opencv-python`."
    ) from exc


REPO_ROOT = Path(__file__).resolve().parent
IMAGE_DIR = REPO_ROOT / "trainingImages"

# Default configuration constants
INTERVAL = 1
WIDTH = 1280
HEIGHT = 720
FPS = 30
FLIP_METHOD = 0
WARMUP_FRAMES = 15
QUALITY = 95
PREFIX = "jetson"


# Generates the GStreamer pipeline string required to initialize and configure 
# the Jetson CSI camera sensor. Uses 'appsink max-buffers=1 drop=true' to prevent 
# old frames from queueing up, ensuring we always retrieve the latest real-time frame.
def gstreamer_pipeline(
    sensor_id: int,
    capture_width: int = WIDTH,
    capture_height: int = HEIGHT,
    display_width: int = WIDTH,
    display_height: int = HEIGHT,
    framerate: int = FPS,
    flip_method: int = FLIP_METHOD,
) -> str:
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, "
        f"format=(string)NV12, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, "
        "format=(string)BGRx ! videoconvert ! video/x-raw, format=(string)BGR ! "
        "appsink max-buffers=1 drop=true"
    )


# Establishes connection to the CSI camera device using OpenCV and the custom 
# GStreamer pipeline. Raises a RuntimeError if the camera interface fails to open.
def open_camera(sensor_id: int) -> cv2.VideoCapture:
    pipeline = gstreamer_pipeline(sensor_id=sensor_id)
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open CSI camera with sensor-id={sensor_id}. Check the connection."
        )

    return cap


# Performs camera warmup, grabs frames from the camera feed, saves them to 
# local storage under the trainingImages/ folder with timestamps, and returns 
# a list of saved image file paths.
def capture_images(count: int, sensor_id: int) -> list[Path]:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    cap = open_camera(sensor_id)
    saved_paths: list[Path] = []

    try:
        # Let exposure and white balance settle before the first capture.
        for _ in range(max(WARMUP_FRAMES, 0)):
            cap.read()
            time.sleep(0.03)

        for index in range(count):
            # Capture the photo frame from the camera (real-time, no buffer lag)
            ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError("Camera returned an empty frame.")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            image_path = IMAGE_DIR / f"{PREFIX}_{timestamp}_{index + 1:03d}.jpg"

            # Save the captured frame to a JPEG file
            if not cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_JPEG_QUALITY, QUALITY]):
                raise RuntimeError(f"Failed to write image: {image_path}")

            saved_paths.append(image_path)
            print(f"saved {image_path.relative_to(REPO_ROOT)}")

            if index < count - 1:
                time.sleep(INTERVAL)
    finally:
        cap.release()

    return saved_paths


# Runs a shell-based git command within the root directory of the repository.
def run_git(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True)


# Stages the newly captured image files, commits them using a timestamped or 
# custom commit message, and pushes the commits to the remote GitHub repository.
def push_images(paths: list[Path], message: str) -> None:
    if not paths:
        print("no images captured; skipping git push")
        return

    relative_paths = [str(path.relative_to(REPO_ROOT)) for path in paths]
    run_git(["git", "add", "-f", *relative_paths])
    run_git(["git", "commit", "-m", message])
    run_git(["git", "push"])


# Defines and parses command-line arguments to allow configuring capture count, 
# target CSI camera sensor ID, and custom commit messages.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture Jetson CSI camera images and automatically push them to GitHub."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of images to capture.",
    )
    parser.add_argument(
        "--sensor-id",
        type=int,
        default=0,
        help="CSI camera sensor id.",
    )
    parser.add_argument(
        "--message",
        default=None,
        help="Git commit message. Defaults to a timestamped capture message.",
    )
    return parser.parse_args()


# Executes the full application sequence: parses arguments, starts capture, 
# generates the commit message, and pushes results to Git. Returns status code.
def main() -> int:
    args = parse_args()
    if args.count < 1:
        raise SystemExit("--count must be at least 1")

    try:
        paths = capture_images(args.count, args.sensor_id)
        message = args.message or f"Add Jetson training images {datetime.now():%Y-%m-%d %H:%M:%S}"
        push_images(paths, message)
    except subprocess.CalledProcessError as exc:
        print(f"git command failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
