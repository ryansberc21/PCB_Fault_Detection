# Jetson Training Image Capture

This repo includes a small capture script that saves camera images into `trainingImages/`.
It can also commit and push the new images to the GitHub remote for this repo.

## 1. Set up the Jetson

Clone your repo onto the Jetson if it is not already there:

```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

Install OpenCV for Python:

```bash
sudo apt update
sudo apt install -y python3-opencv
```

If you prefer pip:

```bash
python3 -m pip install opencv-python
```

Make sure the Jetson can push to GitHub. The easiest options are GitHub CLI auth or an SSH key:

```bash
git remote -v
ssh -T git@github.com
```

## 2. Capture Images

For a USB webcam:

```bash
python3 jetson_capture.py --camera-type usb --count 10 --interval 2
```

For a Jetson CSI ribbon camera:

```bash
python3 jetson_capture.py --camera-type csi --count 10 --interval 2
```

The images will be written to:

```text
trainingImages/
```

## 3. Capture and Push to GitHub

Use `--push` to add, commit, and push the captured images:

```bash
python3 jetson_capture.py --camera-type usb --count 10 --interval 2 --push
```

With a custom commit message:

```bash
python3 jetson_capture.py --camera-type csi --count 25 --interval 1 --push --message "Add new field training images"
```

## Useful Options

```text
--count          Number of images to take.
--interval       Seconds between images.
--width          Image width. Default: 1280.
--height         Image height. Default: 720.
--prefix         Filename prefix. Default: jetson.
--camera-index   USB camera index. Default: 0.
--sensor-id      CSI camera sensor id. Default: 0.
--flip-method    CSI camera orientation adjustment, 0-7.
```

## Troubleshooting

If the camera does not open, try the other camera type:

```bash
python3 jetson_capture.py --camera-type csi
python3 jetson_capture.py --camera-type usb
```

For USB cameras, check devices:

```bash
ls /dev/video*
```

If `git push` fails, confirm the repo remote and authentication:

```bash
git remote -v
ssh -T git@github.com
```
