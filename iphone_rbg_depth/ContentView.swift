//
//  ContentView.swift
//  iphone_rbg_depth
//
//  Created by Kyla Guru on 10/10/25.
//

import SwiftUI

struct ContentView: View {
    var body: some View {
        ARViewControllerRepresentable()
            .edgesIgnoringSafeArea(.all)
    }
}

#Preview {
    ContentView()
}
