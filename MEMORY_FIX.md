# Memory Issue Fix - Phase 2

## Problem
The app was crashing after a few seconds with memory warnings:
- "ARSession is retaining 11-12 ARFrames"
- "Camera will stop delivering frames"
- App terminated due to excessive memory usage

## Root Cause
1. **Too many frames being processed**: ARKit delivers 30-60 frames per second
2. **Expensive image conversions**: Converting CVPixelBuffer → UIImage for every frame
3. **No throttling**: Processing every single frame created memory pressure
4. **Frame retention**: Holding references to ARFrames in async closures

## Solutions Applied

### 1. Frame Throttling (15 FPS)
```swift
private let targetFrameInterval: TimeInterval = 1.0 / 15.0
```
- Only process 1 frame every 66ms (~15 FPS)
- Skip frames if processing is already in progress
- ARKit still runs at 30fps, but we only visualize at 15fps

### 2. Process One Frame at a Time
```swift
private var isProcessingFrame = false
```
- Prevents queue backup
- Ensures we never hold multiple frames in memory
- Drops frames if processing takes too long (better than crashing!)

### 3. Reduced AR Session Frame Rate
```swift
if let format = ARWorldTrackingConfiguration.supportedVideoFormats.first(where: {
    $0.framesPerSecond == 30
}) {
    configuration.videoFormat = format
}
```
- Reduced from 60 FPS to 30 FPS capture
- Less data to process overall

### 4. Disabled Unnecessary Features
```swift
configuration.planeDetection = []  // Disabled plane detection
// Smoothed depth disabled (can enable later if needed)
```
- Saves processing power and memory
- These aren't needed for streaming

### 5. Autoreleasepool
```swift
autoreleasepool {
    self.rgbImageView.image = rgbImage
    self.depthImageView.image = depthImage
}
```
- Ensures temporary objects are released immediately
- Prevents memory buildup

### 6. Memory Warning Handler
```swift
override func didReceiveMemoryWarning() {
    // Clear images to free memory
}
```
- Clears displayed images if system is low on memory
- Helps prevent crash

## Expected Behavior Now

### Frame Processing:
- **AR Capture**: 30 FPS
- **Visualization**: ~15 FPS (throttled)
- **Display**: Smooth, no stuttering
- **Memory**: Stable, no growth over time

### Console Output:
```
✓ LiDAR is supported on this device
✓ Scene depth enabled
✓ Using 30 FPS video format
✓ AR Session started at reduced frame rate

=== Frame Data ===
RGB: 1920x1440
Depth: 256x192
Processing at ~15 FPS (throttled)
==================
```

### No More Errors:
- ❌ No "retaining 11 ARFrames" warnings
- ❌ No "camera will stop delivering" errors
- ❌ No memory crashes

## Performance Trade-offs

| Aspect | Before | After |
|--------|--------|-------|
| Visualization FPS | 30-60 | ~15 |
| Memory Usage | Growing (crash) | Stable |
| CPU Usage | Very High | Moderate |
| Battery Life | Poor | Better |
| Smoothness | Smooth until crash | Smooth forever |

## Why 15 FPS is OK

1. **Human perception**: 15 FPS is acceptable for monitoring/debugging
2. **Streaming**: Will use similar rates over network anyway
3. **Stability**: Much better than crashing after 5 seconds!
4. **Adjustable**: Can be changed via `targetFrameInterval` if needed

## Testing the Fix

### Run the app and verify:

1. ✅ **Startup**: App launches successfully
2. ✅ **Display**: Both RGB and depth show up
3. ✅ **Stability**: Runs for 60+ seconds without crashing
4. ✅ **Console**: No "retaining ARFrames" warnings
5. ✅ **Smoothness**: Visualization updates regularly

### Monitor in Xcode:

1. Open **Debug Navigator** (Cmd+7)
2. Select **Memory**
3. Watch memory usage over time
4. Should stabilize around 200-400 MB (device dependent)
5. Should NOT continuously grow

## Future Optimizations (Phase 3+)

In Phase 3, we'll add proper video encoding which will be even more efficient:
- Hardware-accelerated H.264 encoding for RGB
- Efficient depth compression
- Better memory management with video buffers
- Potential to increase back to 30 FPS

## If Still Having Issues

### If memory still grows:
1. Reduce FPS further: `1.0 / 10.0` (10 FPS)
2. Check for image caching in UIImageView
3. Profile with Instruments (Allocations)

### If visualization is too choppy:
1. Increase FPS: `1.0 / 20.0` (20 FPS)
2. Optimize DepthImageConverter.swift
3. Use lower resolution video format

### To adjust frame rate:
Change this line in ARViewController.swift:
```swift
private let targetFrameInterval: TimeInterval = 1.0 / 15.0
//                                                    ^^ change this number
// 10 = 10 FPS (more stable, choppier)
// 15 = 15 FPS (balanced) - DEFAULT
// 20 = 20 FPS (smoother, more memory)
// 30 = 30 FPS (smoothest, might crash)
```

## Summary

The app now:
- ✅ Runs stably without crashing
- ✅ Uses reasonable memory
- ✅ Displays both RGB and depth in real-time
- ✅ Ready for Phase 3 (compression and encoding)

The visualization is slightly less smooth (15 FPS vs 30 FPS), but this is a necessary trade-off for stability. Once we implement proper video encoding in Phase 3, performance will improve significantly.
