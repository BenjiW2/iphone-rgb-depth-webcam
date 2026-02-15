# RGB + Depth (8-bit) Virtual Webcam Quickstart

This guide runs on Linux (including Raspberry Pi OS) and exposes two virtual webcams:

- `RGB`: full-color iPhone camera stream
- `Depth`: 8-bit normalized depth stream for compatibility checks

## 1) Install dependencies

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3-opencv python3-numpy v4l2loopback-dkms v4l2loopback-utils v4l-utils
```

## 2) Create two loopback camera devices

```bash
sudo modprobe -r v4l2loopback 2>/dev/null || true
sudo modprobe v4l2loopback devices=2 video_nr=10,11 card_label="iPhone RGB","iPhone Depth" exclusive_caps=1
```

You should now have:

- `/dev/video10` (RGB)
- `/dev/video11` (Depth)

## 3) Start the bridge receiver

From this repo:

```bash
python3 receiver_virtual_webcam.py --host 0.0.0.0 --port 8888 --rgb-device /dev/video10 --depth-device /dev/video11 --depth-min-m 0.3 --depth-max-m 5.0
```

Optional:

- `--invert-depth` if you want near objects brighter.

## 4) Start iPhone streaming to this Linux/Pi IP

Set the iPhone sender to connect to your Linux/Pi IP on port `8888`.

## 5) Verify both webcams locally

List formats:

```bash
v4l2-ctl -d /dev/video10 --list-formats-ext
v4l2-ctl -d /dev/video11 --list-formats-ext
```

Quick visual check:

```bash
ffplay -f v4l2 -framerate 30 -video_size 640x480 /dev/video10
ffplay -f v4l2 -framerate 30 -video_size 640x480 /dev/video11
```

OpenCV check:

```python
import cv2

rgb = cv2.VideoCapture("/dev/video10")
depth = cv2.VideoCapture("/dev/video11")

while True:
    ok1, f1 = rgb.read()
    ok2, f2 = depth.read()
    if ok1:
        cv2.imshow("RGB", f1)
    if ok2:
        cv2.imshow("Depth8", f2)
    if cv2.waitKey(1) == ord("q"):
        break
```

## Notes

- This script expects the existing TCP packet protocol used by `receiver.py`.
- Depth is converted to 8-bit for broad webcam compatibility.
- For robotics pipelines that need metric depth later, keep a separate raw-depth path in parallel.
