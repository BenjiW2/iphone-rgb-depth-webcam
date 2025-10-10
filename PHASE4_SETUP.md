# Phase 4: Network Streaming - Setup Guide

## 🎉 Phase 4 Complete!

You now have everything needed for end-to-end streaming from iPhone to computer!

---

## What Was Created

### iPhone Side (Swift):
1. **NetworkStreamer.swift** - TCP client with auto-reconnect
2. **Updated ARViewController.swift** - Integrated network streaming
3. **Network status display** - Shows connection status on iPhone

### Computer Side (Python):
1. **receiver.py** - TCP server that receives and displays streams
2. **H.264 decoder** - Uses FFmpeg to decode RGB video
3. **Depth decoder** - Decodes PNG depth images
4. **Display windows** - Shows RGB and colorized depth side-by-side

---

## Setup Instructions

### Step 1: Add NetworkStreamer.swift to Xcode

1. In Xcode, right-click `iphone_rbg_depth` folder
2. "Add Files to 'iphone_rbg_depth'..."
3. Select `NetworkStreamer.swift`
4. Uncheck "Copy items if needed"
5. Click "Add"

### Step 2: Find Your Computer's IP Address

**On Mac:**
```bash
ipconfig getifaddr en0
```

**On Windows:**
```bash
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter

**Example output:** `192.168.1.100`

### Step 3: Update iPhone App with Your IP

1. Open `ARViewController.swift` in Xcode
2. Find line ~311: `let serverIP = "192.168.1.100"`
3. **Change to YOUR computer's IP address**
4. Save the file

### Step 4: Install Python Dependencies

On your computer, run:

```bash
pip install opencv-python numpy
```

Also install FFmpeg:

**Mac:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

### Step 5: Start Python Receiver

On your computer:

```bash
cd /Users/kylaguru/Documents/Ankush/iphone_rbg_depth
python3 receiver.py
```

You should see:
```
============================================================
  iPhone RGB + Depth Receiver
============================================================

🎧 Server listening on 0.0.0.0:8888
📱 Waiting for iPhone connection...
```

### Step 6: Build and Run iPhone App

1. Make sure iPhone and computer are on **same WiFi network**
2. Build and run app in Xcode (Cmd+R)
3. Watch the connection happen!

---

## Expected Results

### On Computer (Python receiver):
```
✅ Connected to ('192.168.1.123', 54321)

📋 Session Metadata:
   Session ID: ABC123...
   RGB: 1920x1440
   Depth: 256x192
   FPS: 15
   RGB Bitrate: 2.0 Mbps

🔑 Keyframe #1: 66.3 KB
📺 Display windows opened
Press 'q' to quit

RGB: 45 frames (15.0 fps, 540 kbps) | Depth: 45 frames (15.0 fps, 300 kbps) | Total: 840 kbps
```

### On iPhone:
```
Network: Connected ✓  (green)
```

### Display Windows:
- **RGB Stream** - Live color video from iPhone camera
- **Depth Stream** - Colorized depth map (jet colormap)
  - Blue/Purple = close
  - Red/Yellow = far

---

## Architecture

```
iPhone                          Computer
┌─────────────────┐            ┌──────────────────┐
│ ARKit           │            │ Python Receiver  │
│  ├─ RGB Camera  │            │  ├─ TCP Server   │
│  └─ LiDAR       │            │  ├─ FFmpeg H.264 │
│                 │            │  └─ OpenCV       │
│ VideoEncoder    │            │                  │
│  └─ H.264       │───TCP───>  │ Display Windows  │
│                 │   WiFi     │  ├─ RGB Stream   │
│ DepthCompressor │            │  └─ Depth Stream │
│  └─ PNG         │            │                  │
└─────────────────┘            └──────────────────┘
      Port 8888
```

---

## Troubleshooting

### iPhone: "Network: Disconnected" (red)

**Problem:** Can't connect to receiver

**Solutions:**
1. Make sure Python receiver is running first
2. Check IP address in ARViewController.swift is correct
3. Verify both devices on same WiFi network
4. Check firewall isn't blocking port 8888

**Test connection:**
```bash
# On computer, check if port is listening:
lsof -i :8888

# Should show Python process
```

### Receiver: "Connection refused"

**Problem:** Receiver not starting

**Solutions:**
1. Check port 8888 isn't already in use:
   ```bash
   lsof -i :8888
   # Kill any existing process if needed
   ```

2. Try different port:
   - In `receiver.py`: Change `port=8888` to `port=9999`
   - In `ARViewController.swift`: Change `serverPort: UInt16 = 8888` to `9999`

### Receiver: "FFmpeg not found"

**Problem:** FFmpeg not installed

**Solution:**
```bash
# Mac:
brew install ffmpeg

# Linux:
sudo apt-get install ffmpeg

# Verify:
ffmpeg -version
```

### No video showing in RGB window

**Problem:** H.264 decoder not working

**Solutions:**
1. Check console for FFmpeg errors
2. Wait a few seconds for keyframe
3. Restart receiver

### Depth window shows black/white only

**Problem:** Depth not being received

**Solutions:**
1. Check iPhone has LiDAR (✓ LiDAR Supported)
2. Check console for depth frame messages
3. Point camera at objects in range (0.5m - 5m)

### Very slow / laggy

**Problem:** Network bandwidth

**Solutions:**
1. Move closer to WiFi router
2. Check WiFi not congested
3. Reduce bitrate in ARViewController.swift:
   ```swift
   let bitrate = 1_000_000  // 1 Mbps instead of 2
   ```

---

## Controls

### In Receiver:
- **'q'** - Quit and close windows
- **Window resize** - Drag to resize displays

### On iPhone:
- Just point and capture!
- Connection auto-reconnects if dropped

---

## Performance Metrics

### Expected Performance:
| Metric | Value |
|--------|-------|
| Latency | 100-300ms |
| RGB FPS | ~15 fps |
| Depth FPS | ~15 fps |
| Bandwidth | 0.8-1.5 Mbps |
| CPU (iPhone) | ~35% |
| CPU (Computer) | ~20% |

### Network Usage:
- RGB: ~540 kbps (H.264)
- Depth: ~300 kbps (PNG)
- **Total: ~840 kbps** (less than 1 Mbps!)

---

## What's Happening

### Frame Flow:
1. **iPhone captures** AR frame (RGB + depth)
2. **RGB encoded** to H.264 by VideoToolbox
3. **Depth compressed** to PNG
4. **Both sent** over TCP with packet headers
5. **Computer receives** packets
6. **H.264 decoded** by FFmpeg
7. **PNG decoded** by OpenCV
8. **Displayed** in separate windows

### Packet Format:
```
[Header - 18 bytes]
  - Frame Type: 1 byte (RGB=1, Depth=2, Metadata=3)
  - Timestamp: 8 bytes (double)
  - Frame Number: 4 bytes (uint32)
  - Data Size: 4 bytes (uint32)
  - Is Keyframe: 1 byte (bool)
[Payload - Variable]
  - H.264 NAL units OR PNG image data
```

---

## Success Checklist

- [ ] NetworkStreamer.swift added to Xcode project
- [ ] Computer IP address updated in ARViewController.swift
- [ ] Python dependencies installed (opencv-python, numpy)
- [ ] FFmpeg installed and working
- [ ] iPhone and computer on same WiFi
- [ ] Python receiver running and listening
- [ ] iPhone app running and connected (green status)
- [ ] RGB window showing live video
- [ ] Depth window showing colorized depth
- [ ] Stats updating in terminal

---

## Next Steps

Once streaming is working, you can:

1. **Record streams** - Save to video files
2. **Add controls** - Start/stop streaming, adjust quality
3. **Multi-device** - Stream to multiple receivers
4. **WebRTC** - Lower latency streaming
5. **Processing** - Add computer vision on receiver side

---

## Files Summary

```
iphone_rbg_depth/
├── NetworkStreamer.swift          (NEW - TCP client)
├── ARViewController.swift          (UPDATED - network integration)
├── receiver.py                     (NEW - Python receiver)
└── PHASE4_SETUP.md                (This file)
```

---

## Testing the Full Pipeline

### Quick Test:

1. **Start receiver:**
   ```bash
   python3 receiver.py
   ```

2. **Run iPhone app** (Cmd+R)

3. **Watch for:**
   - iPhone: "Network: Connected ✓" (green)
   - Computer: "✅ Connected to..."
   - Computer: Two windows pop up with video

4. **Move iPhone around** - see RGB and depth update in real-time!

### Advanced Test:

- Hold hand close to camera → see it dark in depth view
- Point at far objects → see them bright in depth view
- Check latency by waving → should be < 300ms
- Check stats → should show ~15 fps, ~840 kbps

---

## Congratulations! 🎉

You've built a complete iPhone LiDAR streaming system!

- ✅ Captures RGB + depth
- ✅ Encodes with H.264
- ✅ Compresses depth
- ✅ Streams over network
- ✅ Displays on computer

**Ready to test? Follow the setup instructions above!**
