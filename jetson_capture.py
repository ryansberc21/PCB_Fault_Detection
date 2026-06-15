#!/usr/bin/env python3
"""Capture images on a Jetson and optionally push them to GitHub."""

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


def gstreamer_pipeline(
    sensor_id: int,
    capture_width: int,
    capture_height: int,
    display_width: int,
    display_height: int,
    framerate: int,
    flip_method: int,
) -> str:
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width=(int){capture_width}, height=(int){capture_height}, "
        f"format=(string)NV12, framerate=(fraction){framerate}/1 ! "
        f"nvvidconv flip-method={flip_method} ! "
        f"video/x-raw, width=(int){display_width}, height=(int){display_height}, "
        "format=(string)BGRx ! videoconvert ! video/x-raw, format=(string)BGR ! appsink"
    )


def open_camera(args: argparse.Namespace) -> cv2.VideoCapture:
    if args.camera_type == "csi":
        pipeline = gstreamer_pipeline(
            sensor_id=args.sensor_id,
            capture_width=args.width,
            capture_height=args.height,
            display_width=args.width,
            display_height=args.height,
            framerate=args.fps,
            flip_method=args.flip_method,
        )
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    else:
        cap = cv2.VideoCapture(args.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        cap.set(cv2.CAP_PROP_FPS, args.fps)

    if not cap.isOpened():
        raise RuntimeError(
            "Could not open camera. Check the camera connection and try "
            "`--camera-type usb` or `--camera-type csi`."
        )

    return cap


def capture_images(args: argparse.Namespace) -> list[Path]:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    cap = open_camera(args)
    saved_paths: list[Path] = []

    try:
        # Let exposure and white balance settle before the first capture.
        for _ in range(max(args.warmup_frames, 0)):
            cap.read()
            time.sleep(0.03)

        for index in range(args.count):
            ok, frame = cap.read()
            if not ok or frame is None:
                raise RuntimeError("Camera returned an empty frame.")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            image_path = IMAGE_DIR / f"{args.prefix}_{timestamp}_{index + 1:03d}.jpg"

            if not cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_JPEG_QUALITY, args.quality]):
                raise RuntimeError(f"Failed to write image: {image_path}")

            saved_paths.append(image_path)
            print(f"saved {image_path.relative_to(REPO_ROOT)}")

            if index < args.count - 1:
                time.sleep(args.interval)
    finally:
        cap.release()

    return saved_paths


def run_git(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def push_images(paths: list[Path], message: str) -> None:
    if not paths:
        print("no images captured; skipping git push")
        return

    relative_paths = [str(path.relative_to(REPO_ROOT)) for path in paths]
    run_git(["git", "add", "-f", *relative_paths])
    run_git(["git", "commit", "-m", message])
    run_git(["git", "push"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture Jetson camera images into trainingImages/ and optionally push them."
    )
    parser.add_argument("--camera-type", choices=["usb", "csi"], default="usb")
    parser.add_argument("--camera-index", type=int, default=0, help="USB camera index.")
    parser.add_argument("--sensor-id", type=int, default=0, help="CSI camera sensor id.")
    parser.add_argument("--count", type=int, default=1, help="Number of images to capture.")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between images.")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--flip-method", type=int, default=0, help="CSI camera flip method, 0-7.")
    parser.add_argument("--warmup-frames", type=int, default=15)
    parser.add_argument("--quality", type=int, default=95, help="JPEG quality, 1-100.")
    parser.add_argument("--prefix", default="jetson")
    parser.add_argument("--push", action="store_true", help="Commit and push captured images.")
    parser.add_argument(
        "--message",
        default=None,
        help="Git commit message. Defaults to a timestamped capture message.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    if not 1 <= args.quality <= 100:
        raise SystemExit("--quality must be between 1 and 100")

    try:
        paths = capture_images(args)
        if args.push:
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
