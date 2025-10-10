# Quick Xcode Setup Guide - Phase 1

## Fix: Build Error "Multiple commands produce Info.plist"

✅ **This has been fixed!** The custom Info.plist has been removed. Follow the steps below to complete setup.

---

## Step-by-Step Setup (5 minutes)

### Step 1: Add Swift Files to Project

1. **Open** `iphone_rbg_depth.xcodeproj` in Xcode
2. In the **Project Navigator** (left sidebar), find the `iphone_rbg_depth` folder (yellow folder icon)
3. **Right-click** on the `iphone_rbg_depth` folder
4. Select **"Add Files to 'iphone_rbg_depth'..."**
5. In the file picker, select these files:
   - ✅ `ARViewController.swift`
   - ✅ `ARViewControllerRepresentable.swift`
6. **IMPORTANT**: Make sure "Copy items if needed" is **UNCHECKED**
7. Click **"Add"**

**Verify**: You should now see both files in the Project Navigator under the `iphone_rbg_depth` folder.

---

### Step 2: Add Camera & Network Permissions

1. In the Project Navigator, click the **blue project icon** at the very top (named `iphone_rbg_depth`)
2. In the main editor area, select the **`iphone_rbg_depth` target** (under "TARGETS")
3. Click the **"Info"** tab (next to "General", "Build Settings", etc.)
4. Look for the section **"Custom iOS Target Properties"**
5. Click the **"+"** button to add a new property

**Add Permission 1:**
- In the dropdown that appears, start typing: `Camera`
- Select: **"Privacy - Camera Usage Description"**
- In the "Value" column, enter: `This app requires camera access to capture RGB video for streaming`

**Add Permission 2:**
- Click the **"+"** button again
- Start typing: `Local Network`
- Select: **"Privacy - Local Network Usage Description"**
- In the "Value" column, enter: `This app requires local network access to stream RGB and depth data to other devices`

**Verify**: You should see both entries in the Custom iOS Target Properties list.

---

### Step 3: Configure Deployment Settings

Still in the same target settings:

1. Click the **"General"** tab
2. Under **"Deployment Info"**:
   - **Minimum Deployments**: Leave as iOS 18.6 (or change to iOS 14.0 if you want broader device support)
   - **Supported Destinations**: iPhone (iPad can be unchecked, but not required)

---

### Step 4: Build and Run

1. **Connect your iPhone** (must be iPhone 12 Pro or later for LiDAR)
2. **Unlock the iPhone**
3. At the top of Xcode, select your iPhone from the device dropdown (next to the scheme selector)
4. Click the **▶️ Play button** (or press `Cmd + R`)

**First time**: Xcode may ask to enable Developer Mode on your iPhone. Follow the prompts.

---

## Expected Results ✅

### On your iPhone screen:
- Camera permission prompt (tap "Allow")
- Live AR camera view
- Three status labels at the top:
  - **Status**: `RGB: 1920x1440` (or similar)
  - **Status**: `Depth: 256x192` (or similar)
  - **LiDAR Status**: `✓ LiDAR Supported` (in green)
  - **FPS**: `FPS: 30.0` (or around 30-60)

### In Xcode Console (bottom panel):
```
✓ LiDAR is supported on this device
✓ Scene depth enabled
✓ Smoothed scene depth enabled
✓ AR Session started

=== Frame Data ===
RGB: 1920x1440
Depth: 256x192
Timestamp: 123456.789
==================
```

---

## Troubleshooting

### ❌ Build fails with "No such module 'ARKit'"
- Make sure you're building for a physical iOS device, not the simulator
- Check that the deployment target is iOS 14.0 or later

### ❌ "Camera access denied"
- On your iPhone: Settings → Privacy & Security → Camera → iphone_rbg_depth → Toggle ON

### ❌ LiDAR shows "✗ LiDAR NOT Supported" (in red)
- You need iPhone 12 Pro, 13 Pro, 14 Pro, 15 Pro, or newer
- Older iPhones don't have LiDAR sensors

### ❌ App crashes immediately
- Check Xcode console for error messages
- Make sure both Swift files were added to the project (Step 1)
- Verify camera permissions were added (Step 2)

### ❌ "Command CodeSign failed" or certificate errors
- In Xcode: Project Settings → Signing & Capabilities
- Select your Apple ID under "Team"
- Let Xcode automatically manage signing

---

## What You've Built

At this point, you have:
- ✅ AR session running with LiDAR
- ✅ RGB frames being captured (1920x1440)
- ✅ Depth frames being captured (256x192)
- ✅ FPS monitoring (~30-60 fps)
- ✅ Status display showing everything is working

---

## Next: Phase 2

Once this is working, Phase 2 will add:
- Side-by-side visualization of RGB and depth
- Depth displayed as a grayscale image
- Touch controls to toggle views

Let me know when Phase 1 is working!
