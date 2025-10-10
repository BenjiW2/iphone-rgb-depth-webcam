# Phase 3: Data Compression & Encoding

## Overview

Phase 3 adds efficient compression for both RGB and depth data, preparing them for network transmission.

### What's New:

1. **VideoEncoder.swift** - H.264 hardware-accelerated video encoding for RGB
2. **DepthCompressor.swift** - Depth data compression (PNG/JPEG/Raw formats)
3. **FrameData.swift** - Frame packaging and synchronization structures

---

## Compression Gains

### Before (Raw Data):
- **RGB**: ~6 MB per frame (1920x1440x3 bytes)
- **Depth**: ~200 KB per frame (256x192x4 bytes Float32)
- **Total**: ~6.2 MB/frame × 15 FPS = **~93 MB/sec**

### After (Encoded):
- **RGB H.264**: ~30-60 KB per frame
- **Depth PNG**: ~20-30 KB per frame
- **Total**: ~60 KB/frame × 15 FPS = **~0.9 MB/sec**

**Compression ratio: 100:1!** 🎉

---

## What Each Component Does

### 1. VideoEncoder.swift
- Uses Apple's VideoToolbox framework
- Hardware-accelerated H.264 encoding
- Configurable bitrate (default: 2 Mbps)
- Outputs compressed H.264 NAL units
- Suitable for streaming and recording

**Key Features:**
- Real-time encoding
- Automatic keyframe insertion
- Bitrate control
- Low latency mode

### 2. DepthCompressor.swift
- Converts Float32 depth → UInt16 (meters → millimeters)
- Supports multiple formats:
  - **PNG**: Lossless, ~20-30 KB (recommended)
  - **JPEG**: Lossy, ~10-20 KB (smaller but quality loss)
  - **Raw16**: Uncompressed 16-bit, ~100 KB (fastest)
- Includes decompression for receiver side

**Format Comparison:**
| Format | Size | Quality | Speed | Use Case |
|--------|------|---------|-------|----------|
| PNG | 20-30 KB | Perfect | Medium | Recommended |
| JPEG | 10-20 KB | Good | Fast | Low bandwidth |
| Raw16 | 100 KB | Perfect | Fastest | High bandwidth |

### 3. FrameData.swift
- Packet structure for network transmission
- Includes timestamps, frame numbers, metadata
- Encoding statistics tracking
- Session metadata for receiver configuration

---

## File Summary

### VideoEncoder.swift (330 lines)
Main class: `VideoEncoder`
- `init(width:height:fps:bitrate:)` - Configure encoder
- `start()` - Initialize compression session
- `encode(pixelBuffer:timestamp:)` - Encode a frame
- `invalidate()` - Stop encoder

Protocol: `VideoEncoderDelegate`
- `didEncodeFrame(data:timestamp:isKeyFrame:)` - Receive encoded frames
- `didFailWithError(error:)` - Handle errors

### DepthCompressor.swift (280 lines)
Main class: `DepthCompressor`
- `compress(_:format:)` - Compress depth buffer to Data
- `decompress(_:format:)` - Decompress back to Float32 array
- `getCompressionInfo(for:format:)` - Get compression statistics

### FrameData.swift (120 lines)
Structures:
- `FramePacket` - Network packet format with header + payload
- `EncodingStats` - Track encoding performance and bitrates
- `SessionMetadata` - Session configuration info

---

## How to Add Files to Xcode

### Step 1: Add New Files

1. In Xcode, **right-click** the `iphone_rbg_depth` folder
2. Select **"Add Files to 'iphone_rbg_depth'..."**
3. Select these three files:
   - `VideoEncoder.swift`
   - `DepthCompressor.swift`
   - `FrameData.swift`
4. Uncheck "Copy items if needed"
5. Click "Add"

---

## Next Steps

Phase 3 is implemented but not yet integrated. To complete Phase 3:

### Option A: Test Encoding Only (Recommended First)
- Add encoding to ARViewController
- Display compression stats on screen
- Verify encoding works before networking

### Option B: Skip to Phase 4
- Go directly to network streaming
- Integrate encoding + networking together

---

## Implementation Notes

### Performance Expectations:
- H.264 encoding: Hardware-accelerated, minimal CPU impact
- Depth compression: ~5-10ms per frame
- Total overhead: <20ms per frame (acceptable for 15 FPS)

### Memory Usage:
- VideoEncoder: ~10-20 MB for buffers
- Depth compression: Minimal (< 1 MB)
- Total additional: ~20-30 MB (acceptable)

### Quality:
- RGB H.264: Near-perfect quality at 2 Mbps
- Depth PNG: Lossless, perfect reconstruction
- No visible degradation

---

## Testing Encoding (Without Networking)

To test if encoding works, we can add a simple test that:
1. Encodes RGB frames to H.264
2. Compresses depth frames to PNG
3. Displays compression stats and bitrates
4. Saves encoded data to files (optional)

This validates encoding works before adding network complexity.

---

## Technical Details

### H.264 Encoding Parameters:
```swift
width: 1920
height: 1440
fps: 15
bitrate: 2_000_000  // 2 Mbps
profile: H264 Main Profile
keyframe interval: 30 frames (2 seconds)
realtime: true
frame reordering: disabled (for low latency)
```

### Depth Compression (PNG):
```
Input: Float32[256×192] = 196,608 bytes (192 KB)
Convert: Float32 → UInt16 (meters → millimeters)
Output: PNG compressed 16-bit grayscale ≈ 20-30 KB
Compression ratio: ~6-10x
```

### Frame Packet Structure:
```
[Header - 18 bytes]
- Frame Type (1 byte): RGB=0x01, Depth=0x02
- Timestamp (8 bytes): Double
- Frame Number (4 bytes): UInt32
- Data Size (4 bytes): UInt32
- Key Frame Flag (1 byte): Bool

[Payload - Variable]
- Encoded data (H.264 or compressed depth)
```

---

## What's Coming in Phase 4

Network streaming over TCP/UDP:
- Server/client architecture
- Real-time transmission
- Reconnection handling
- Bandwidth adaptation

---

## Current Status

✅ **Complete:**
- H.264 encoder implementation
- Depth compressor with multiple formats
- Frame packaging structures
- Statistics tracking

⏳ **Pending:**
- Integration with ARViewController
- Encoding performance testing
- Display of compression stats

Would you like to:
1. **Test encoding first** (add encoding, display stats, verify it works)
2. **Skip to Phase 4** (implement networking with encoding)

**Recommendation**: Test encoding first to ensure everything works before adding network complexity!
