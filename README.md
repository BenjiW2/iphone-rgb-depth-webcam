# iPhone RGB + LiDAR Streaming App

Stream RGB camera and LiDAR depth data from iPhone to computer over network.

## Project Structure

```
iphone_rbg_depth/
├── iphone_rbg_depth/
│   ├── ARViewController.swift                 # Main ARKit controller (NEW)
│   ├── ARViewControllerRepresentable.swift   # SwiftUI wrapper (NEW)
│   ├── ContentView.swift                     # App UI (UPDATED)
│   ├── iphone_rbg_depthApp.swift            # App entry point
│   ├── Info.plist                           # Permissions (NEW)
│   └── Assets.xcassets/                     # App assets
├── iphone_rbg_depth.xcodeproj/              # Xcode project
├── PHASE1_SETUP.md                          # Phase 1 instructions
└── README.md                                # This file
```

## Requirements

- **Device**: iPhone 12 Pro or later (for LiDAR)
- **iOS**: 14.0 or later
- **Xcode**: 13.0 or later
- **macOS**: Big Sur or later (for development)

## Current Status: Phase 1 Complete ✅

### What's Implemented

- ✅ ARKit session with LiDAR support
- ✅ RGB frame capture
- ✅ Depth frame capture
- ✅ LiDAR availability detection
- ✅ FPS monitoring
- ✅ Status UI overlay
- ✅ Camera & network permissions

### Next: Manual Xcode Setup Required

Before you can run the app, you need to complete a few manual steps in Xcode.

**📖 See [PHASE1_SETUP.md](PHASE1_SETUP.md) for detailed instructions.**

### Quick Start

1. Open `iphone_rbg_depth.xcodeproj` in Xcode
2. Add the new Swift files to the project (ARViewController.swift, ARViewControllerRepresentable.swift)
3. Configure Info.plist in Build Settings
4. Connect iPhone 12 Pro or later
5. Build and run (Cmd+R)

## Implementation Phases

- [x] **Phase 1**: ARKit setup & LiDAR detection (CURRENT)
- [ ] **Phase 2**: RGB & depth visualization
- [ ] **Phase 3**: Data compression & encoding
- [ ] **Phase 4**: Network streaming
- [ ] **Phase 5**: Receiver application
- [ ] **Phase 6**: Polish & optimization

## Key Features (When Complete)

- Real-time RGB video streaming (H.264)
- Real-time depth map streaming
- Network transmission over WiFi
- Low latency (<100ms target)
- Synchronized RGB + depth frames
- Python/C++ receiver for desktop

## Architecture

```
iPhone (Sender)                    Computer (Receiver)
┌─────────────────┐               ┌──────────────────┐
│   ARKit         │               │   TCP Server     │
│   ├─ RGB Camera │──────────────>│   ├─ H.264       │
│   └─ LiDAR      │   Network     │   └─ Depth Data  │
│                 │               │                  │
│   Encoder       │               │   Decoder        │
│   └─ H.264      │               │   └─ OpenCV      │
└─────────────────┘               └──────────────────┘
```

## Testing Phase 1

Run the app and verify:

1. **Camera permission** prompt appears
2. **Live AR view** displays
3. **Status shows**: "RGB: 1920x1440, Depth: 256x192"
4. **LiDAR status**: "✓ LiDAR Supported" (green)
5. **FPS counter**: Shows 30-60 FPS
6. **Console output**: Frame data logged

## Development Notes

- Built with Swift 5.0+
- Uses ARKit, AVFoundation, Network frameworks
- SwiftUI for UI, UIKit for AR view
- Requires physical device (simulator not supported)

## License

Educational/Personal Project
