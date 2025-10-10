# Phase 2: RGB & Depth Visualization

## What's New in Phase 2

I've updated the app to display RGB and depth data side-by-side:

### New Files Created:
1. **DepthImageConverter.swift** - Utility to convert depth data to grayscale images
2. **ARViewController.swift** - Updated to show split-screen view

### What Changed:
- Removed the 3D AR view
- Added **two image views**: RGB (left) and Depth (right)
- RGB shows the live camera feed
- Depth shows grayscale visualization:
  - **Black** = very close objects
  - **White** = far away objects
  - **Gray shades** = distances in between

---

## How to Add New File to Xcode

### Step 1: Add DepthImageConverter.swift

1. In Xcode, **right-click** on the `iphone_rbg_depth` folder (yellow folder)
2. Select **"Add Files to 'iphone_rbg_depth'..."**
3. Navigate to and select: `DepthImageConverter.swift`
4. Make sure **"Copy items if needed"** is UNCHECKED
5. Click **"Add"**

**OR use drag-and-drop:**
- Drag `DepthImageConverter.swift` from Finder directly into Xcode's `iphone_rbg_depth` folder

---

## Build and Run

1. **Build** the project (Cmd+B) to check for errors
2. **Run** on your iPhone (Cmd+R)

---

## Expected Results

### On Your iPhone Screen:

```
┌─────────────────────────────────────┐
│  [RGB Camera]  │  [Depth Grayscale] │
│                │                    │
│    Left Half   │    Right Half      │
│                │                    │
└─────────────────────────────────────┘
│  Status Bar (Bottom)                │
│  RGB 1920x1440 | Depth 256x192      │
│  ✓ LiDAR Supported                  │
│  FPS: 30.0                          │
└─────────────────────────────────────┘
```

### What You Should See:

**Left Side (RGB):**
- Live color camera feed
- Full color video from the iPhone camera
- Updates in real-time

**Right Side (Depth):**
- Grayscale depth visualization
- Objects closer to you appear **darker**
- Objects farther away appear **lighter**
- You should see clear depth gradients

**Bottom Status Bar:**
- Resolution info for both streams
- LiDAR status (green checkmark)
- FPS counter (~30-60)

---

## Testing the Depth Visualization

Try these experiments:

### 1. **Hand Test**
- Hold your hand close to the camera
- Your hand should appear **very dark** in the depth view
- Move it away slowly - it should get **lighter**

### 2. **Room Depth**
- Point at a wall 2-3 feet away - should be **medium gray**
- Point at objects 10+ feet away - should be **light gray/white**

### 3. **Multiple Depths**
- Look at a scene with objects at different distances
- You should see clear depth layers in the depth view

### 4. **Motion Test**
- Walk through a room
- Depth map should update smoothly as you move

---

## Troubleshooting

### ❌ Build Error: "Cannot find 'DepthImageConverter' in scope"
- Make sure you added `DepthImageConverter.swift` to the project (Step 1 above)
- Clean build folder: Product → Clean Build Folder (Cmd+Shift+K)
- Rebuild

### ❌ Depth side shows only gray/black
- Make sure you're on a LiDAR-enabled device (iPhone 12 Pro+)
- Check console for "Depth: NOT AVAILABLE" message
- Verify LiDAR status shows green checkmark

### ❌ App is slow / low FPS
- Depth processing is CPU-intensive
- FPS may drop to 15-30 on older devices
- This is normal - we'll optimize in Phase 3

### ❌ Images look rotated or distorted
- This is expected - image orientation handling will be improved later
- For now, hold phone in portrait mode

---

## What's Working Now

- ✅ RGB camera capture and display
- ✅ Depth map capture and visualization
- ✅ Real-time side-by-side view
- ✅ Grayscale depth rendering
- ✅ FPS monitoring
- ✅ Performance optimized with background queue

---

## Next: Phase 3

Once Phase 2 is working, Phase 3 will add:
- **H.264 video encoding** for RGB stream
- **Compression** for depth data
- **Frame synchronization** with timestamps
- **Data rate monitoring**

This prepares the data for network streaming in Phase 4.

---

## Technical Details

### Depth Visualization Algorithm:
- Extracts Float32 depth values (in meters)
- Finds min/max depth in frame
- Normalizes to 0-255 range
- Inverts (close = dark, far = light)
- Converts to grayscale UIImage

### Performance:
- Image conversion on background queue
- UI updates on main thread
- ~30-60 FPS depending on device

### Depth Data:
- Resolution: 256x192 pixels (typical)
- Format: Float32 (meters)
- Range: ~0.5m to 5m for LiDAR
- Invalid depths shown as black
