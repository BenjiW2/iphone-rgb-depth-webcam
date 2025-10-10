//
//  ARViewControllerRepresentable.swift
//  iphone_rbg_depth
//
//  SwiftUI wrapper for ARViewController
//

import SwiftUI

struct ARViewControllerRepresentable: UIViewControllerRepresentable {

    func makeUIViewController(context: Context) -> ARViewController {
        return ARViewController()
    }

    func updateUIViewController(_ uiViewController: ARViewController, context: Context) {
        // Update the view controller if needed
    }
}
