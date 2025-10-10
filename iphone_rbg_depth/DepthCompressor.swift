//
//  DepthCompressor.swift
//  iphone_rbg_depth
//
//  Compresses depth data for efficient transmission
//

import Foundation
import CoreVideo
import Accelerate
import UIKit

class DepthCompressor {

    enum CompressionFormat {
        case png        // Lossless, ~20-30 KB
        case jpeg       // Lossy, ~10-20 KB
        case raw16bit   // Raw 16-bit integers, ~100 KB
    }

    // MARK: - Public Methods

    /// Compress depth pixel buffer to Data
    /// - Parameters:
    ///   - depthPixelBuffer: The depth map from ARFrame
    ///   - format: Compression format to use
    /// - Returns: Compressed data ready for transmission
    static func compress(_ depthPixelBuffer: CVPixelBuffer, format: CompressionFormat = .png) -> Data? {
        CVPixelBufferLockBaseAddress(depthPixelBuffer, .readOnly)
        defer {
            CVPixelBufferUnlockBaseAddress(depthPixelBuffer, .readOnly)
        }

        let width = CVPixelBufferGetWidth(depthPixelBuffer)
        let height = CVPixelBufferGetHeight(depthPixelBuffer)

        guard let baseAddress = CVPixelBufferGetBaseAddress(depthPixelBuffer) else {
            return nil
        }

        // Depth data is Float32 (meters)
        let floatBuffer = baseAddress.assumingMemoryBound(to: Float32.self)
        let count = width * height

        switch format {
        case .png:
            return compressToPNG(floatBuffer: floatBuffer, width: width, height: height, count: count)

        case .jpeg:
            return compressToJPEG(floatBuffer: floatBuffer, width: width, height: height, count: count)

        case .raw16bit:
            return compressToRaw16Bit(floatBuffer: floatBuffer, count: count)
        }
    }

    /// Decompress depth data back to Float32 array
    /// - Parameters:
    ///   - data: Compressed depth data
    ///   - format: Format that was used for compression
    /// - Returns: Array of Float32 depth values (in meters)
    static func decompress(_ data: Data, format: CompressionFormat) -> [Float32]? {
        switch format {
        case .png, .jpeg:
            return decompressFromImage(data)

        case .raw16bit:
            return decompressFromRaw16Bit(data)
        }
    }

    // MARK: - Private Methods - Compression

    private static func compressToPNG(floatBuffer: UnsafeMutablePointer<Float32>, width: Int, height: Int, count: Int) -> Data? {
        // Convert Float32 (meters) to UInt16 (millimeters)
        // Range: 0-65535 mm = 0-65.535 meters
        var uint16Data = [UInt16](repeating: 0, count: count)

        for i in 0..<count {
            let depth = floatBuffer[i]
            if depth.isFinite && depth > 0 {
                // Convert meters to millimeters, clamp to UInt16 range
                let mm = min(depth * 1000.0, 65535.0)
                uint16Data[i] = UInt16(mm)
            } else {
                uint16Data[i] = 0  // Invalid depth
            }
        }

        // Create grayscale image from UInt16 data (16-bit per pixel)
        let colorSpace = CGColorSpaceCreateDeviceGray()
        let bitmapInfo = CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue).union(.byteOrder16Little)

        guard let context = CGContext(
            data: &uint16Data,
            width: width,
            height: height,
            bitsPerComponent: 16,
            bytesPerRow: width * 2,
            space: colorSpace,
            bitmapInfo: bitmapInfo.rawValue
        ) else {
            return nil
        }

        guard let cgImage = context.makeImage() else {
            return nil
        }

        let uiImage = UIImage(cgImage: cgImage)

        // Convert to PNG
        return uiImage.pngData()
    }

    private static func compressToJPEG(floatBuffer: UnsafeMutablePointer<Float32>, width: Int, height: Int, count: Int) -> Data? {
        // Convert to 8-bit grayscale for JPEG
        // Normalize depth values to 0-255 range
        var minDepth: Float = .infinity
        var maxDepth: Float = 0.0

        for i in 0..<count {
            let depth = floatBuffer[i]
            if depth.isFinite && depth > 0 {
                minDepth = min(minDepth, depth)
                maxDepth = max(maxDepth, depth)
            }
        }

        if minDepth == .infinity {
            minDepth = 0
            maxDepth = 10.0
        }

        let range = maxDepth - minDepth

        var uint8Data = [UInt8](repeating: 0, count: count)

        for i in 0..<count {
            let depth = floatBuffer[i]
            if depth.isFinite && depth > 0 {
                let normalized = (depth - minDepth) / range
                uint8Data[i] = UInt8(normalized * 255.0)
            } else {
                uint8Data[i] = 0
            }
        }

        // Create grayscale image
        let colorSpace = CGColorSpaceCreateDeviceGray()
        let bitmapInfo = CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue)

        guard let context = CGContext(
            data: &uint8Data,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width,
            space: colorSpace,
            bitmapInfo: bitmapInfo.rawValue
        ) else {
            return nil
        }

        guard let cgImage = context.makeImage() else {
            return nil
        }

        let uiImage = UIImage(cgImage: cgImage)

        // Convert to JPEG (lossy but smaller)
        return uiImage.jpegData(compressionQuality: 0.8)
    }

    private static func compressToRaw16Bit(floatBuffer: UnsafeMutablePointer<Float32>, count: Int) -> Data? {
        var uint16Data = [UInt16](repeating: 0, count: count)

        for i in 0..<count {
            let depth = floatBuffer[i]
            if depth.isFinite && depth > 0 {
                // Convert meters to millimeters
                let mm = min(depth * 1000.0, 65535.0)
                uint16Data[i] = UInt16(mm)
            }
        }

        return Data(bytes: uint16Data, count: count * 2)
    }

    // MARK: - Private Methods - Decompression

    private static func decompressFromImage(_ data: Data) -> [Float32]? {
        guard let uiImage = UIImage(data: data),
              let cgImage = uiImage.cgImage else {
            return nil
        }

        let width = cgImage.width
        let height = cgImage.height
        let count = width * height

        var uint16Data = [UInt16](repeating: 0, count: count)

        let colorSpace = CGColorSpaceCreateDeviceGray()
        let bitmapInfo = CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue).union(.byteOrder16Little)

        guard let context = CGContext(
            data: &uint16Data,
            width: width,
            height: height,
            bitsPerComponent: 16,
            bytesPerRow: width * 2,
            space: colorSpace,
            bitmapInfo: bitmapInfo.rawValue
        ) else {
            return nil
        }

        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))

        // Convert UInt16 (millimeters) back to Float32 (meters)
        var floatData = [Float32](repeating: 0, count: count)

        for i in 0..<count {
            let mm = Float32(uint16Data[i])
            floatData[i] = mm / 1000.0  // Convert mm to meters
        }

        return floatData
    }

    private static func decompressFromRaw16Bit(_ data: Data) -> [Float32]? {
        let count = data.count / 2
        var uint16Data = [UInt16](repeating: 0, count: count)

        data.copyBytes(to: UnsafeMutableBufferPointer(start: &uint16Data, count: count))

        var floatData = [Float32](repeating: 0, count: count)

        for i in 0..<count {
            let mm = Float32(uint16Data[i])
            floatData[i] = mm / 1000.0
        }

        return floatData
    }

    // MARK: - Utility

    /// Get compression info for a given depth buffer
    static func getCompressionInfo(for depthPixelBuffer: CVPixelBuffer, format: CompressionFormat) -> (originalSize: Int, compressedSize: Int, ratio: Double)? {
        let width = CVPixelBufferGetWidth(depthPixelBuffer)
        let height = CVPixelBufferGetHeight(depthPixelBuffer)
        let originalSize = width * height * 4  // Float32 = 4 bytes per pixel

        guard let compressed = compress(depthPixelBuffer, format: format) else {
            return nil
        }

        let compressedSize = compressed.count
        let ratio = Double(originalSize) / Double(compressedSize)

        return (originalSize, compressedSize, ratio)
    }
}
