#!/usr/bin/env python3
"""
RGB + Depth Receiver
Receives H.264 RGB and PNG depth streams from iPhone
"""

import socket
import struct
import json
import cv2
import numpy as np
from datetime import datetime
import subprocess
import os
import threading

# Frame types
FRAME_TYPE_RGB = 0x01
FRAME_TYPE_DEPTH = 0x02
FRAME_TYPE_METADATA = 0x03

# Header format: type(1) + timestamp(8) + frame_num(4) + data_size(4) + is_key(1) = 18 bytes
HEADER_SIZE = 18
HEADER_FORMAT = '<BdIIB'  # Little-endian: byte, double, uint, uint, byte (iOS uses little-endian)

class FrameReceiver:
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.metadata = None

        # Stats
        self.frames_received = {'rgb': 0, 'depth': 0}
        self.bytes_received = {'rgb': 0, 'depth': 0}
        self.start_time = None

        # For H.264 decoding
        self.h264_pipe = None
        self.decoder_thread = None
        self.latest_rgb_frame = None
        self.rgb_lock = threading.Lock()

        # For depth
        self.latest_depth_frame = None
        self.depth_lock = threading.Lock()

    def start(self):
        """Start TCP server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)

        print(f"🎧 Server listening on {self.host}:{self.port}")
        print(f"📱 Waiting for iPhone connection...")

        self.client_socket, addr = self.server_socket.accept()
        print(f"✅ Connected to {addr}")

        self.start_time = datetime.now()

        # Start H.264 decoder
        self.start_h264_decoder()

    def start_h264_decoder(self):
        """Start FFmpeg process for H.264 decoding"""
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'h264',
            '-i', 'pipe:0',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            'pipe:1'
        ]

        self.h264_pipe = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=10**8
        )

        # Start thread to read decoded frames
        self.decoder_thread = threading.Thread(target=self._decode_h264_frames, daemon=True)
        self.decoder_thread.start()

    def _decode_h264_frames(self):
        """Background thread to decode H.264 frames"""
        if self.metadata is None:
            print("⚠️ Decoder thread started but no metadata yet")
            return

        width = self.metadata.get('rgbWidth', 1920)
        height = self.metadata.get('rgbHeight', 1440)
        frame_size = width * height * 3  # BGR24

        print(f"🎬 Decoder thread running: expecting {width}x{height} frames ({frame_size} bytes each)")

        frame_count = 0
        while True:
            try:
                raw_frame = self.h264_pipe.stdout.read(frame_size)
                if len(raw_frame) != frame_size:
                    print(f"⚠️ Decoder: expected {frame_size} bytes, got {len(raw_frame)}")
                    break

                frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((height, width, 3))

                with self.rgb_lock:
                    self.latest_rgb_frame = frame

                frame_count += 1
                if frame_count == 1:
                    print(f"✅ First RGB frame decoded successfully!")

            except Exception as e:
                print(f"❌ Decoder error: {e}")
                break

        print(f"🛑 Decoder thread exiting (decoded {frame_count} frames)")

    def receive_frame(self):
        """Receive one frame packet"""
        try:
            # Read header
            header_data = self._recv_exact(HEADER_SIZE)
            if not header_data:
                return None

            frame_type, timestamp, frame_num, data_size, is_key = struct.unpack(HEADER_FORMAT, header_data)

            # Read payload
            payload = self._recv_exact(data_size)
            if not payload:
                return None

            return {
                'type': frame_type,
                'timestamp': timestamp,
                'frame_num': frame_num,
                'data_size': data_size,
                'is_key': bool(is_key),
                'data': payload
            }

        except Exception as e:
            print(f"❌ Receive error: {e}")
            return None

    def _recv_exact(self, size):
        """Receive exact number of bytes"""
        data = b''
        while len(data) < size:
            chunk = self.client_socket.recv(size - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def process_frame(self, frame):
        """Process received frame"""
        frame_type = frame['type']

        if frame_type == FRAME_TYPE_METADATA:
            # Parse metadata
            self.metadata = json.loads(frame['data'].decode('utf-8'))
            print(f"\n📋 Session Metadata:")
            print(f"   Session ID: {self.metadata['sessionId']}")
            print(f"   RGB: {self.metadata['rgbWidth']}x{self.metadata['rgbHeight']}")
            print(f"   Depth: {self.metadata['depthWidth']}x{self.metadata['depthHeight']}")
            print(f"   FPS: {self.metadata['fps']}")
            print(f"   RGB Bitrate: {self.metadata['rgbBitrate'] / 1_000_000:.1f} Mbps")
            print()

            # Restart decoder thread now that we have metadata
            if self.decoder_thread and not self.decoder_thread.is_alive():
                self.decoder_thread = threading.Thread(target=self._decode_h264_frames, daemon=True)
                self.decoder_thread.start()
                print("✅ H.264 decoder thread started")

        elif frame_type == FRAME_TYPE_RGB:
            # Send H.264 data to decoder
            if self.h264_pipe:
                try:
                    self.h264_pipe.stdin.write(frame['data'])
                    self.h264_pipe.stdin.flush()
                except:
                    pass

            self.frames_received['rgb'] += 1
            self.bytes_received['rgb'] += frame['data_size']

            if frame['is_key']:
                print(f"🔑 Keyframe #{frame['frame_num']}: {frame['data_size'] / 1024:.1f} KB")

        elif frame_type == FRAME_TYPE_DEPTH:
            # Decode PNG depth
            depth_array = np.frombuffer(frame['data'], dtype=np.uint8)
            depth_image = cv2.imdecode(depth_array, cv2.IMREAD_UNCHANGED)

            if depth_image is not None:
                with self.depth_lock:
                    self.latest_depth_frame = depth_image
                print(f"📊 Depth frame #{frame['frame_num']}: {depth_image.shape}, {frame['data_size'] / 1024:.1f} KB")
            else:
                print(f"❌ Failed to decode depth frame #{frame['frame_num']}")

            self.frames_received['depth'] += 1
            self.bytes_received['depth'] += frame['data_size']

    def get_latest_frames(self):
        """Get latest RGB and depth frames for display"""
        with self.rgb_lock:
            rgb = self.latest_rgb_frame.copy() if self.latest_rgb_frame is not None else None
        with self.depth_lock:
            depth = self.latest_depth_frame.copy() if self.latest_depth_frame is not None else None
        return rgb, depth

    def get_stats(self):
        """Get streaming statistics"""
        if self.start_time is None:
            return ""

        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return ""

        rgb_kbps = (self.bytes_received['rgb'] * 8 / 1000) / elapsed
        depth_kbps = (self.bytes_received['depth'] * 8 / 1000) / elapsed
        total_kbps = rgb_kbps + depth_kbps

        rgb_fps = self.frames_received['rgb'] / elapsed
        depth_fps = self.frames_received['depth'] / elapsed

        return (f"RGB: {self.frames_received['rgb']} frames ({rgb_fps:.1f} fps, {rgb_kbps:.0f} kbps) | "
                f"Depth: {self.frames_received['depth']} frames ({depth_fps:.1f} fps, {depth_kbps:.0f} kbps) | "
                f"Total: {total_kbps:.0f} kbps")

    def cleanup(self):
        """Cleanup resources"""
        if self.h264_pipe:
            self.h264_pipe.terminate()
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()

def main():
    print("=" * 60)
    print("  iPhone RGB + Depth Receiver")
    print("=" * 60)
    print()

    # Check if FFmpeg is available
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except:
        print("❌ FFmpeg not found! Please install:")
        print("   Mac: brew install ffmpeg")
        print("   Linux: sudo apt-get install ffmpeg")
        return

    receiver = FrameReceiver(host='0.0.0.0', port=8888)

    try:
        receiver.start()

        # Create display windows
        cv2.namedWindow('RGB Stream', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Depth Stream', cv2.WINDOW_NORMAL)

        # Resize windows to be more visible
        cv2.resizeWindow('RGB Stream', 960, 720)
        cv2.resizeWindow('Depth Stream', 640, 480)

        # Move windows to specific positions
        cv2.moveWindow('RGB Stream', 50, 50)
        cv2.moveWindow('Depth Stream', 1050, 50)

        print("📺 Display windows opened (should appear on screen)")
        print("   If you don't see them, check Mission Control or other desktops")
        print("Press 'q' to quit\n")

        frame_count = 0

        while True:
            # Receive frame
            frame = receiver.receive_frame()
            if frame is None:
                print("❌ Connection lost")
                break

            # Process frame
            receiver.process_frame(frame)
            frame_count += 1

            # Update display every 5 frames
            if frame_count % 5 == 0:
                rgb, depth = receiver.get_latest_frames()

                if rgb is not None:
                    cv2.imshow('RGB Stream', rgb)

                if depth is not None:
                    # Normalize depth for display
                    depth_normalized = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                    depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
                    cv2.imshow('Depth Stream', depth_colored)

                # Print stats
                if frame_count % 30 == 0:
                    print(receiver.get_stats())

            # Check for quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        receiver.cleanup()
        cv2.destroyAllWindows()
        print("👋 Goodbye!")

if __name__ == '__main__':
    main()
