#!/usr/bin/env python3
"""
iPhone RGB + Depth receiver for Linux virtual webcams.

This script accepts the existing TCP packet protocol used by `receiver.py`, then
publishes:
- RGB stream to one v4l2loopback device
- 8-bit normalized depth stream to another v4l2loopback device
"""

import argparse
import json
import os
import socket
import struct
import subprocess
import threading
import time
from datetime import datetime

import cv2
import numpy as np


# Frame types
FRAME_TYPE_RGB = 0x01
FRAME_TYPE_DEPTH = 0x02
FRAME_TYPE_METADATA = 0x03

# Header format: type(1) + timestamp(8) + frame_num(4) + data_size(4) + is_key(1)
HEADER_SIZE = 18
HEADER_FORMAT = "<BdIIB"


class V4L2Writer:
    """Writes raw frames to a v4l2loopback device through FFmpeg."""

    def __init__(self, device, width, height, fps, input_pix_fmt, output_pix_fmt="yuyv422"):
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.input_pix_fmt = input_pix_fmt
        self.output_pix_fmt = output_pix_fmt
        self.process = None

    def start(self):
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-f",
            "rawvideo",
            "-pix_fmt",
            self.input_pix_fmt,
            "-video_size",
            f"{self.width}x{self.height}",
            "-framerate",
            str(self.fps),
            "-i",
            "pipe:0",
            "-f",
            "v4l2",
            "-pix_fmt",
            self.output_pix_fmt,
            self.device,
        ]

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            bufsize=10**8,
        )

    def write(self, frame_bytes):
        if self.process is None or self.process.stdin is None:
            return False

        try:
            self.process.stdin.write(frame_bytes)
            self.process.stdin.flush()
            return True
        except (BrokenPipeError, OSError):
            return False

    def close(self):
        if self.process is None:
            return
        try:
            if self.process.stdin:
                self.process.stdin.close()
            self.process.terminate()
            self.process.wait(timeout=2.0)
        except Exception:
            self.process.kill()
        finally:
            self.process = None


class WebcamBridgeReceiver:
    def __init__(
        self,
        host,
        port,
        rgb_device,
        depth_device,
        depth_min_m,
        depth_max_m,
        invert_depth,
    ):
        self.host = host
        self.port = port
        self.rgb_device = rgb_device
        self.depth_device = depth_device
        self.depth_min_m = depth_min_m
        self.depth_max_m = depth_max_m
        self.invert_depth = invert_depth

        self.server_socket = None
        self.client_socket = None
        self.metadata = None

        self.h264_pipe = None
        self.decoder_thread = None
        self.stop_event = threading.Event()
        self.rgb_encoding = "h264"

        self.rgb_writer = None
        self.depth_writer = None

        self.frames_received = {"rgb": 0, "depth": 0}
        self.frames_published = {"rgb": 0, "depth": 0}
        self.bytes_received = {"rgb": 0, "depth": 0}
        self.start_time = None
        self.last_stats_time = time.monotonic()

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)

        print(f"Listening on {self.host}:{self.port}")
        print("Waiting for iPhone connection...")

        self.client_socket, addr = self.server_socket.accept()
        self.start_time = datetime.now()
        print(f"Connected: {addr[0]}:{addr[1]}")

    def receive_frame(self):
        try:
            header_data = self._recv_exact(HEADER_SIZE)
            if not header_data:
                return None

            frame_type, timestamp, frame_num, data_size, is_key = struct.unpack(HEADER_FORMAT, header_data)
            payload = self._recv_exact(data_size)
            if not payload:
                return None

            return {
                "type": frame_type,
                "timestamp": timestamp,
                "frame_num": frame_num,
                "data_size": data_size,
                "is_key": bool(is_key),
                "data": payload,
            }
        except Exception as exc:
            print(f"Receive error: {exc}")
            return None

    def _recv_exact(self, size):
        data = b""
        while len(data) < size:
            chunk = self.client_socket.recv(size - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def process_frame(self, frame):
        frame_type = frame["type"]

        if frame_type == FRAME_TYPE_METADATA:
            self._handle_metadata(frame["data"])
            return

        if frame_type == FRAME_TYPE_RGB:
            self.frames_received["rgb"] += 1
            self.bytes_received["rgb"] += frame["data_size"]
            self._process_rgb_packet(frame["data"])
            return

        if frame_type == FRAME_TYPE_DEPTH:
            self.frames_received["depth"] += 1
            self.bytes_received["depth"] += frame["data_size"]
            self._process_depth_packet(frame["data"])

    def _handle_metadata(self, metadata_bytes):
        self.metadata = json.loads(metadata_bytes.decode("utf-8"))

        rgb_w = int(self.metadata.get("rgbWidth", 1920))
        rgb_h = int(self.metadata.get("rgbHeight", 1440))
        depth_w = int(self.metadata.get("depthWidth", 256))
        depth_h = int(self.metadata.get("depthHeight", 192))
        fps = int(self.metadata.get("fps", 30))
        self.rgb_encoding = str(self.metadata.get("rgbEncoding", "h264")).lower()

        print("Session metadata:")
        print(f"  RGB: {rgb_w}x{rgb_h}")
        print(f"  Depth: {depth_w}x{depth_h}")
        print(f"  FPS: {fps}")
        print(f"  RGB encoding: {self.rgb_encoding}")
        print(f"  Depth normalization: {self.depth_min_m:.2f}m to {self.depth_max_m:.2f}m")

        # Start virtual webcam sinks once metadata is known.
        if self.rgb_writer is None:
            self.rgb_writer = V4L2Writer(
                device=self.rgb_device,
                width=rgb_w,
                height=rgb_h,
                fps=fps,
                input_pix_fmt="bgr24",
                output_pix_fmt="yuyv422",
            )
            self.rgb_writer.start()
            print(f"RGB virtual webcam: {self.rgb_device}")

        if self.depth_writer is None:
            self.depth_writer = V4L2Writer(
                device=self.depth_device,
                width=depth_w,
                height=depth_h,
                fps=fps,
                input_pix_fmt="gray",
                output_pix_fmt="yuyv422",
            )
            self.depth_writer.start()
            print(f"Depth virtual webcam (8-bit): {self.depth_device}")

        if self.rgb_encoding == "h264" and self.h264_pipe is None:
            self._start_h264_decoder(rgb_w, rgb_h)

    def _process_rgb_packet(self, payload):
        if self.rgb_encoding in ("jpeg", "jpg"):
            rgb_array = np.frombuffer(payload, dtype=np.uint8)
            rgb_image = cv2.imdecode(rgb_array, cv2.IMREAD_COLOR)
            if rgb_image is None:
                return

            if self.rgb_writer:
                if rgb_image.shape[1] != self.rgb_writer.width or rgb_image.shape[0] != self.rgb_writer.height:
                    rgb_image = cv2.resize(
                        rgb_image,
                        (self.rgb_writer.width, self.rgb_writer.height),
                        interpolation=cv2.INTER_AREA,
                    )
                if self.rgb_writer.write(rgb_image.tobytes()):
                    self.frames_published["rgb"] += 1
            return

        if self.h264_pipe and self.h264_pipe.stdin:
            try:
                self.h264_pipe.stdin.write(payload)
                self.h264_pipe.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

    def _start_h264_decoder(self, width, height):
        ffmpeg_cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "h264",
            "-i",
            "pipe:0",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "pipe:1",
        ]

        self.h264_pipe = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=10**8,
        )

        self.decoder_thread = threading.Thread(
            target=self._decode_h264_frames,
            args=(width, height),
            daemon=True,
        )
        self.decoder_thread.start()

    def _decode_h264_frames(self, width, height):
        frame_size = width * height * 3

        while not self.stop_event.is_set():
            if self.h264_pipe is None or self.h264_pipe.stdout is None:
                return

            try:
                raw_frame = self.h264_pipe.stdout.read(frame_size)
                if len(raw_frame) != frame_size:
                    return

                if self.rgb_writer and self.rgb_writer.write(raw_frame):
                    self.frames_published["rgb"] += 1
            except Exception:
                return

    def _process_depth_packet(self, payload):
        depth_array = np.frombuffer(payload, dtype=np.uint8)
        depth_image = cv2.imdecode(depth_array, cv2.IMREAD_UNCHANGED)
        if depth_image is None:
            return

        depth_u16 = self._to_uint16_mm(depth_image)
        if depth_u16 is None:
            return

        depth_u8 = self._normalize_depth_to_u8(depth_u16)

        if self.depth_writer and self.depth_writer.write(depth_u8.tobytes()):
            self.frames_published["depth"] += 1

    def _to_uint16_mm(self, depth_image):
        if depth_image.ndim == 3:
            depth_image = depth_image[:, :, 0]

        if depth_image.dtype == np.uint16:
            return depth_image

        if depth_image.dtype == np.float32:
            depth_mm = np.clip(depth_image * 1000.0, 0.0, 65535.0)
            return depth_mm.astype(np.uint16)

        if depth_image.dtype == np.uint8:
            # Fallback for already-normalized depth streams.
            return (depth_image.astype(np.uint16) * 257).astype(np.uint16)

        return None

    def _normalize_depth_to_u8(self, depth_u16):
        depth_m = depth_u16.astype(np.float32) / 1000.0
        valid = depth_u16 > 0

        denom = max(1e-6, self.depth_max_m - self.depth_min_m)
        scaled = np.clip((depth_m - self.depth_min_m) / denom, 0.0, 1.0)
        if self.invert_depth:
            scaled = 1.0 - scaled

        out = np.zeros(depth_u16.shape, dtype=np.uint8)
        out[valid] = (scaled[valid] * 255.0).astype(np.uint8)
        return out

    def maybe_print_stats(self):
        now = time.monotonic()
        if now - self.last_stats_time < 2.0:
            return
        self.last_stats_time = now

        if self.start_time is None:
            return

        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed <= 0:
            return

        rgb_rx_fps = self.frames_received["rgb"] / elapsed
        depth_rx_fps = self.frames_received["depth"] / elapsed
        rgb_pub_fps = self.frames_published["rgb"] / elapsed
        depth_pub_fps = self.frames_published["depth"] / elapsed

        rgb_kbps = (self.bytes_received["rgb"] * 8 / 1000) / elapsed
        depth_kbps = (self.bytes_received["depth"] * 8 / 1000) / elapsed

        print(
            "RX rgb/depth fps: "
            f"{rgb_rx_fps:.1f}/{depth_rx_fps:.1f} | "
            "PUB rgb/depth fps: "
            f"{rgb_pub_fps:.1f}/{depth_pub_fps:.1f} | "
            "BW kbps: "
            f"{rgb_kbps + depth_kbps:.0f}"
        )

    def cleanup(self):
        self.stop_event.set()

        if self.rgb_writer:
            self.rgb_writer.close()
        if self.depth_writer:
            self.depth_writer.close()

        if self.h264_pipe:
            try:
                if self.h264_pipe.stdin:
                    self.h264_pipe.stdin.close()
                self.h264_pipe.terminate()
                self.h264_pipe.wait(timeout=2.0)
            except Exception:
                self.h264_pipe.kill()

        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()


def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def check_device(path):
    return os.path.exists(path) and path.startswith("/dev/video")


def parse_args():
    parser = argparse.ArgumentParser(description="Bridge iPhone RGB+depth stream to virtual webcams")
    parser.add_argument("--host", default="0.0.0.0", help="TCP listen host")
    parser.add_argument("--port", type=int, default=8888, help="TCP listen port")
    parser.add_argument("--rgb-device", default="/dev/video10", help="v4l2loopback RGB device")
    parser.add_argument("--depth-device", default="/dev/video11", help="v4l2loopback depth device")
    parser.add_argument("--depth-min-m", type=float, default=0.3, help="depth normalization near limit (meters)")
    parser.add_argument("--depth-max-m", type=float, default=5.0, help="depth normalization far limit (meters)")
    parser.add_argument(
        "--invert-depth",
        action="store_true",
        help="invert depth normalization (near=bright, far=dark)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.depth_max_m <= args.depth_min_m:
        raise ValueError("--depth-max-m must be greater than --depth-min-m")

    if not check_ffmpeg():
        print("ffmpeg not found. Install ffmpeg first.")
        return

    if not check_device(args.rgb_device):
        print(f"Warning: RGB device {args.rgb_device} does not look valid.")
    if not check_device(args.depth_device):
        print(f"Warning: Depth device {args.depth_device} does not look valid.")

    receiver = WebcamBridgeReceiver(
        host=args.host,
        port=args.port,
        rgb_device=args.rgb_device,
        depth_device=args.depth_device,
        depth_min_m=args.depth_min_m,
        depth_max_m=args.depth_max_m,
        invert_depth=args.invert_depth,
    )

    try:
        receiver.start()
        while True:
            frame = receiver.receive_frame()
            if frame is None:
                print("Connection closed.")
                break
            receiver.process_frame(frame)
            receiver.maybe_print_stats()
    except KeyboardInterrupt:
        print("Interrupted.")
    finally:
        receiver.cleanup()


if __name__ == "__main__":
    main()
