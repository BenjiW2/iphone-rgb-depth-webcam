//
//  ARViewController.swift
//  iphone_rbg_depth
//
//  ARKit View Controller for recording RGB and LiDAR depth videos
//

import UIKit
import ARKit
import AVFoundation
import CoreMedia

class ARViewController: UIViewController, ARSessionDelegate {

    // MARK: - Properties
    var arSession: ARSession!
    var rgbImageView: UIImageView!
    var depthImageView: UIImageView!
    var statusLabel: UILabel!
    var lidarStatusLabel: UILabel!
    var fpsLabel: UILabel!
    var recordButton: UIButton!
    var recordingStatusLabel: UILabel!

    private var frameCount = 0
    private var lastFPSUpdate = Date()
    private var isProcessingFrame = false
    private var lastFrameTime = Date()
    private let targetFrameInterval: TimeInterval = 1.0 / 30.0  // Process at 30 FPS

    // Recording components
    private var videoRecorder: VideoRecorder?
    private var isRecording = false

    // MARK: - Lifecycle
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        setupAR()
        checkLiDARAvailability()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        arSession.pause()

        // Stop recording if active
        if isRecording {
            stopRecording()
        }
    }

    // MARK: - UI Setup

    func setupUI() {
        view.backgroundColor = .black

        // Create side-by-side image views
        let stackView = UIStackView()
        stackView.axis = .horizontal
        stackView.distribution = .fillEqually
        stackView.spacing = 2
        stackView.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stackView)

        rgbImageView = UIImageView()
        rgbImageView.contentMode = .scaleAspectFit
        rgbImageView.backgroundColor = .darkGray
        stackView.addArrangedSubview(rgbImageView)

        depthImageView = UIImageView()
        depthImageView.contentMode = .scaleAspectFit
        depthImageView.backgroundColor = .darkGray
        stackView.addArrangedSubview(depthImageView)

        // Status label
        statusLabel = UILabel()
        statusLabel.text = "Initializing..."
        statusLabel.textColor = .white
        statusLabel.textAlignment = .left
        statusLabel.numberOfLines = 0
        statusLabel.font = UIFont.monospacedSystemFont(ofSize: 12, weight: .regular)
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(statusLabel)

        // LiDAR status
        lidarStatusLabel = UILabel()
        lidarStatusLabel.textColor = .green
        lidarStatusLabel.textAlignment = .left
        lidarStatusLabel.font = UIFont.systemFont(ofSize: 12, weight: .semibold)
        lidarStatusLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(lidarStatusLabel)

        // FPS label
        fpsLabel = UILabel()
        fpsLabel.text = "FPS: 0.0"
        fpsLabel.textColor = .yellow
        fpsLabel.textAlignment = .left
        fpsLabel.font = UIFont.monospacedSystemFont(ofSize: 12, weight: .regular)
        fpsLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(fpsLabel)

        // Recording status label
        recordingStatusLabel = UILabel()
        recordingStatusLabel.text = "Ready to record"
        recordingStatusLabel.textColor = .cyan
        recordingStatusLabel.textAlignment = .center
        recordingStatusLabel.font = UIFont.systemFont(ofSize: 14, weight: .semibold)
        recordingStatusLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(recordingStatusLabel)

        // Record button
        recordButton = UIButton(type: .system)
        recordButton.setTitle("⏺ START RECORDING", for: .normal)
        recordButton.setTitleColor(.white, for: .normal)
        recordButton.backgroundColor = .red
        recordButton.layer.cornerRadius = 25
        recordButton.titleLabel?.font = UIFont.systemFont(ofSize: 18, weight: .bold)
        recordButton.addTarget(self, action: #selector(recordButtonTapped), for: .touchUpInside)
        recordButton.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(recordButton)

        // Layout constraints
        NSLayoutConstraint.activate([
            stackView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 100),
            stackView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            stackView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            stackView.heightAnchor.constraint(equalTo: view.heightAnchor, multiplier: 0.5),

            statusLabel.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 10),
            statusLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 10),
            statusLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -10),

            lidarStatusLabel.topAnchor.constraint(equalTo: statusLabel.bottomAnchor, constant: 5),
            lidarStatusLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 10),

            fpsLabel.topAnchor.constraint(equalTo: lidarStatusLabel.bottomAnchor, constant: 5),
            fpsLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 10),

            recordingStatusLabel.bottomAnchor.constraint(equalTo: recordButton.topAnchor, constant: -10),
            recordingStatusLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),

            recordButton.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -20),
            recordButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            recordButton.widthAnchor.constraint(equalToConstant: 250),
            recordButton.heightAnchor.constraint(equalToConstant: 50)
        ])
    }

    // MARK: - AR Setup

    func setupAR() {
        arSession = ARSession()
        arSession.delegate = self

        let configuration = ARWorldTrackingConfiguration()

        // Enable scene depth if available
        if ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth) {
            configuration.frameSemantics.insert(.sceneDepth)
        }

        // Find and use the video format with 30 FPS
        let availableFormats = ARWorldTrackingConfiguration.supportedVideoFormats
        if let format30fps = availableFormats.first(where: { $0.framesPerSecond == 30 }) {
            configuration.videoFormat = format30fps
            print("✓ Using 30 FPS video format")
        }

        arSession.run(configuration)
        print("✓ AR Session started")
    }

    func checkLiDARAvailability() {
        if ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth) {
            lidarStatusLabel.text = "✓ LiDAR Supported"
            lidarStatusLabel.textColor = .green
            print("✓ LiDAR is supported on this device")
        } else {
            lidarStatusLabel.text = "✗ LiDAR Not Available"
            lidarStatusLabel.textColor = .red
            print("✗ LiDAR is not supported on this device")
        }
    }

    // MARK: - Recording Control

    @objc func recordButtonTapped() {
        if isRecording {
            stopRecording()
        } else {
            startRecording()
        }
    }

    func startRecording() {
        videoRecorder = VideoRecorder()

        // Get dimensions from AR session
        let rgbWidth = 1920
        let rgbHeight = 1440
        let depthWidth = 256
        let depthHeight = 192
        let fps = 30

        do {
            try videoRecorder?.startRecording(
                rgbWidth: rgbWidth,
                rgbHeight: rgbHeight,
                depthWidth: depthWidth,
                depthHeight: depthHeight,
                fps: fps
            )

            isRecording = true

            // Update UI
            recordButton.setTitle("⏹ STOP RECORDING", for: .normal)
            recordButton.backgroundColor = .systemGray
            recordingStatusLabel.text = "Recording..."
            recordingStatusLabel.textColor = .red

            print("🎬 Recording started")

        } catch {
            print("❌ Failed to start recording: \(error.localizedDescription)")
            recordingStatusLabel.text = "Error: \(error.localizedDescription)"
            recordingStatusLabel.textColor = .red
        }
    }

    func stopRecording() {
        guard let recorder = videoRecorder else { return }

        isRecording = false

        // Update UI
        recordButton.setTitle("⏺ START RECORDING", for: .normal)
        recordButton.backgroundColor = .red
        recordButton.isEnabled = false
        recordingStatusLabel.text = "Saving..."
        recordingStatusLabel.textColor = .yellow

        recorder.stopRecording { [weak self] rgbURL, depthURL, error in
            guard let self = self else { return }

            if let error = error {
                DispatchQueue.main.async {
                    self.recordingStatusLabel.text = "Error: \(error.localizedDescription)"
                    self.recordingStatusLabel.textColor = .red
                    self.recordButton.isEnabled = true
                }
                return
            }

            guard let rgbURL = rgbURL, let depthURL = depthURL else {
                DispatchQueue.main.async {
                    self.recordingStatusLabel.text = "Recording failed"
                    self.recordingStatusLabel.textColor = .red
                    self.recordButton.isEnabled = true
                }
                return
            }

            // Save to Photos
            VideoRecorder.saveToPhotos(rgbURL: rgbURL, depthURL: depthURL) { success, error in
                DispatchQueue.main.async {
                    if success {
                        self.recordingStatusLabel.text = "✅ Saved to Photos!"
                        self.recordingStatusLabel.textColor = .green
                    } else {
                        self.recordingStatusLabel.text = "Error saving: \(error?.localizedDescription ?? "unknown")"
                        self.recordingStatusLabel.textColor = .red
                    }

                    self.recordButton.isEnabled = true

                    // Reset status after 3 seconds
                    DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
                        self.recordingStatusLabel.text = "Ready to record"
                        self.recordingStatusLabel.textColor = .cyan
                    }
                }
            }
        }

        videoRecorder = nil
    }

    // MARK: - ARSessionDelegate

    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        updateFPS()

        // Throttle frame processing
        let now = Date()
        guard now.timeIntervalSince(lastFrameTime) >= targetFrameInterval else { return }
        guard !isProcessingFrame else { return }

        isProcessingFrame = true
        lastFrameTime = now

        // Get buffers
        let rgbPixelBuffer = frame.capturedImage
        let depthPixelBuffer = frame.sceneDepth?.depthMap
        let timestamp = CMTime(seconds: frame.timestamp, preferredTimescale: 600)

        // Write frames if recording
        if isRecording {
            videoRecorder?.writeRGBFrame(rgbPixelBuffer, timestamp: timestamp)

            if let depthBuffer = depthPixelBuffer {
                videoRecorder?.writeDepthFrame(depthBuffer, timestamp: timestamp)
            }

            // Update recording status
            if let frameCount = videoRecorder?.getFrameCount() {
                DispatchQueue.main.async {
                    self.recordingStatusLabel.text = "Recording... \(frameCount) frames"
                }
            }
        }

        // Process on background queue for visualization
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else {
                self?.isProcessingFrame = false
                return
            }

            // Convert images for display
            let rgbImage = DepthImageConverter.convertRGBToImage(rgbPixelBuffer)
            var depthImage: UIImage?

            if let depthBuffer = depthPixelBuffer {
                depthImage = DepthImageConverter.convertDepthToImage(depthBuffer)
            }

            // Update UI on main thread
            DispatchQueue.main.async {
                autoreleasepool {
                    self.rgbImageView.image = rgbImage
                    self.depthImageView.image = depthImage

                    // Log on first successful frame only
                    if self.frameCount == 1 {
                        if let rgbWidth = rgbImage?.size.width, let rgbHeight = rgbImage?.size.height {
                            print("\n=== Frame Data ===")
                            print("RGB: \(Int(rgbWidth))x\(Int(rgbHeight))")

                            if let depthImage = depthImage {
                                print("Depth: \(Int(depthImage.size.width))x\(Int(depthImage.size.height))")
                            }

                            print("Processing at ~30 FPS")
                            print("==================\n")
                        }
                    }

                    self.isProcessingFrame = false
                }
            }
        }
    }

    func updateFPS() {
        frameCount += 1

        let elapsed = Date().timeIntervalSince(lastFPSUpdate)
        if elapsed >= 1.0 {
            let fps = Double(frameCount) / elapsed
            DispatchQueue.main.async {
                self.fpsLabel.text = String(format: "FPS: %.1f", fps)
            }

            frameCount = 0
            lastFPSUpdate = Date()
        }
    }

    func session(_ session: ARSession, didFailWithError error: Error) {
        print("❌ AR Session failed: \(error.localizedDescription)")
        DispatchQueue.main.async {
            self.statusLabel.text = "AR Error: \(error.localizedDescription)"
            self.statusLabel.textColor = .red
        }
    }
}
