# iPhone RGB + LiDAR Depth Streaming

Realtime RGB + depth capture from an iPhone Pro device, with two primary receiver paths:

- macOS/Linux display receiver for validation and OBS integration
- Linux/Raspberry Pi virtual webcam bridge for robotics pipelines

This repository also supports local on-device recording to Photos.

## What Works Where

| Goal | iPhone | macOS | Linux / Raspberry Pi |
|---|---|---|---|
| Capture RGB + LiDAR depth | ✅ | N/A | N/A |
| Stream over TCP (USB or WiFi) | ✅ | ✅ | ✅ |
| Preview RGB + depth windows (`receiver.py`) | N/A | ✅ | ✅ |
| Feed two virtual webcam devices (`/dev/video*`) | N/A | ❌ | ✅ |
| Use in OBS | N/A | ✅ | ✅ |
| Use in Photo Booth | N/A | ✅ (via OBS Virtual Camera) | N/A |

## Current Stream Format

The current iPhone streaming path sends:

- `RGB`: JPEG frames
- `Depth`: PNG (16-bit depth in millimeters)
- Transport: TCP custom packet protocol (18-byte header + payload)

Header layout:

- `type` (1 byte): RGB `0x01`, Depth `0x02`, Metadata `0x03`
- `timestamp` (8 bytes, little-endian double)
- `frame_number` (4 bytes, little-endian uint32)
- `payload_size` (4 bytes, little-endian uint32)
- `is_key` (1 byte)

## Repository Layout

```text
iphone_rgb_depth/
├── iphone_rbg_depth/
│   ├── ARViewController.swift
│   ├── VideoRecorder.swift
│   ├── DepthCompressor.swift
│   └── ...
├── receiver.py                    # Cross-platform preview receiver (OpenCV windows)
├── receiver_virtual_webcam.py     # Linux/Pi bridge to /dev/video* (RGB + depth 8-bit)
├── PI_WEBCAM_QUICKSTART.md        # Linux/Pi focused setup
└── README.md
```

## iPhone Setup (Sender)

Requirements:

- iPhone 12 Pro or later (LiDAR required)
- Xcode + Apple signing setup

Build:

1. Open `iphone_rbg_depth.xcodeproj`.
2. Configure signing in Xcode target settings.
3. Connect iPhone via USB and trust the computer.
4. Build and run.
5. Grant camera and local-network permissions when prompted.

In-app controls:

- `START RECORDING`: saves RGB+depth videos to Photos
- `START STREAMING`: prompts for receiver host + port (default host is USB-friendly `172.20.10.2`)

## Transport: USB Cable First (Recommended)

Use iPhone Personal Hotspot over USB.

### On iPhone

1. Connect iPhone to host (Mac/Linux/Pi) via cable.
2. Enable `Settings > Personal Hotspot`.

### On host

- Typical USB tether subnet is `172.20.10.x`.
- Host is often `172.20.10.2`.
- Start receiver on port `8888` and use that host IP in iPhone stream dialog.

Linux note if no USB network appears:

```bash
sudo modprobe ipheth
ip addr
```

WiFi is also supported as fallback.

## Workflow A: macOS + OBS (+ Photo Booth)

This is the easiest validation path on Mac.

### 1) Install dependencies

```bash
brew install ffmpeg
python3 -m venv venv
source venv/bin/activate
pip install opencv-python numpy
```

### 2) Start receiver on Mac

```bash
python3 receiver.py
```

It opens two windows:

- `RGB Stream`
- `Depth Stream`

### 3) Start iPhone streaming

- Tap `START STREAMING`
- Enter host IP (USB often `172.20.10.2`)
- Port `8888`

### 4) Add sources in OBS

Option 1 (recommended on Mac):

1. Add `Window Capture` source for `RGB Stream` window.
2. Add `Window Capture` source for `Depth Stream` window.
3. Build one scene per stream, or a combined scene.

Option 2:

- Use display capture and crop, but window capture is cleaner.

### 5) Make it visible to Photo Booth

1. In OBS, click `Start Virtual Camera`.
2. Open Photo Booth.
3. Select camera source `OBS Virtual Camera`.

Notes:

- Photo Booth gets one virtual camera feed at a time (whatever scene OBS virtual camera outputs).
- macOS does not use `v4l2loopback`, so the Linux virtual-webcam script does not apply on Mac.

## Workflow B: Linux / Raspberry Pi Robotics (Two Virtual Webcams)

This path exposes two camera devices for robotics tools.

### 1) Install dependencies

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg python3-opencv python3-numpy v4l2loopback-dkms v4l2loopback-utils v4l-utils
```

### 2) Create loopback devices

```bash
sudo modprobe -r v4l2loopback 2>/dev/null || true
sudo modprobe v4l2loopback devices=2 video_nr=10,11 card_label="iPhone RGB","iPhone Depth" exclusive_caps=1
```

Expected devices:

- `/dev/video10` = RGB
- `/dev/video11` = Depth (8-bit normalized)

### 3) Start virtual webcam bridge

```bash
python3 receiver_virtual_webcam.py --host 0.0.0.0 --port 8888 --rgb-device /dev/video10 --depth-device /dev/video11 --depth-min-m 0.3 --depth-max-m 5.0
```

Optional:

- `--invert-depth` (near bright, far dark)

### 4) Start iPhone streaming

- Host IP: Pi/host USB IP (often `172.20.10.2`) or WiFi IP
- Port: `8888`

### 5) Validate devices

```bash
v4l2-ctl -d /dev/video10 --list-formats-ext
v4l2-ctl -d /dev/video11 --list-formats-ext
```

```bash
ffplay -f v4l2 -framerate 30 -video_size 640x480 /dev/video10
ffplay -f v4l2 -framerate 30 -video_size 640x480 /dev/video11
```

### 6) Use in OpenCV

```python
import cv2

rgb = cv2.VideoCapture('/dev/video10')
depth = cv2.VideoCapture('/dev/video11')

while True:
    ok1, f1 = rgb.read()
    ok2, f2 = depth.read()
    if ok1:
        cv2.imshow('rgb', f1)
    if ok2:
        cv2.imshow('depth8', f2)
    if cv2.waitKey(1) == ord('q'):
        break
```

### 7) Use in ROS 2 (example)

If using `v4l2_camera` package, run one node per device:

```bash
ros2 run v4l2_camera v4l2_camera_node --ros-args -p video_device:=/dev/video10 -p image_size:=[1920,1440]
ros2 run v4l2_camera v4l2_camera_node --ros-args -p video_device:=/dev/video11 -p image_size:=[256,192]
```

Adjust parameters to your distro/package version.

## Workflow C: On-Phone Only (No Receiver)

If you do not need live streaming:

1. Use `START RECORDING`.
2. Capture scene.
3. Stop recording.
4. RGB + depth videos are saved to Photos.

## Receiver Scripts

### `receiver.py`

- Cross-platform preview (`RGB Stream` + `Depth Stream` windows)
- Supports current JPEG RGB metadata and legacy H.264 streams
- Good for Mac validation and OBS window capture workflows

### `receiver_virtual_webcam.py`

- Linux only
- Converts stream to two `/dev/video*` outputs via `v4l2loopback`
- Depth output is normalized to 8-bit for compatibility

## OBS Integration Summary

- macOS: use `receiver.py` + `Window Capture`; use OBS Virtual Camera for Photo Booth/Zoom/Meet.
- Linux: either use `receiver.py` window capture or directly add `/dev/video10` and `/dev/video11` as `Video Capture Device` sources.

## Tuning

### iPhone sender (`iphone_rbg_depth/ARViewController.swift`)

- Stream FPS target: `streamFrameInterval`
- RGB JPEG quality: `streamJPEGQuality`

### Linux depth normalization (`receiver_virtual_webcam.py`)

- `--depth-min-m`
- `--depth-max-m`
- `--invert-depth`

## Troubleshooting

### iPhone cannot connect

- Confirm host IP + port in iPhone dialog.
- Confirm receiver is already running.
- Confirm firewall allows TCP `8888`.
- On USB tethering, verify host interface has `172.20.10.x` address.

### `receiver.py` shows no RGB

- Check metadata print for `RGB Encoding`.
- If using H.264 sender path, install FFmpeg.
- For JPEG sender path (current app), FFmpeg is optional.

### Linux virtual webcams not appearing

- Re-run `modprobe v4l2loopback ...` command.
- Check `ls /dev/video*`.
- Ensure `receiver_virtual_webcam.py` points to correct device IDs.

### High latency or dropped frames

- Prefer USB transport over WiFi.
- Lower stream rate (increase `streamFrameInterval`).
- Reduce JPEG quality (`streamJPEGQuality`) on iPhone.

## Known Limits

- macOS cannot use Linux `v4l2loopback` virtual webcams.
- Photo Booth accepts one OBS virtual camera output at a time.
- Depth virtual webcam path is 8-bit normalized for compatibility (not metric depth fidelity).

## Additional Doc

- Linux/Pi quickstart: `PI_WEBCAM_QUICKSTART.md`
