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

Capture images using the CSI ribbon camera. Captured images are automatically added, committed, and pushed to your remote GitHub repository on successful completion.

```bash
python3 jetson_capture.py --count 10
```

With a custom commit message:

```bash
python3 jetson_capture.py --count 25 --message "Add new field training images"
```

The images will be written to:

```text
trainingImages/
```

## Useful Options

```text
--count          Number of images to take. Default: 1.
--sensor-id      CSI camera sensor id. Default: 0.
--message        Optional git commit message.
```

## Troubleshooting

If the camera does not open, ensure it is connected properly and the sensor-id is correct.

If `git push` fails, confirm the repo remote and authentication:

```bash
git remote -v
ssh -T git@github.com
```

