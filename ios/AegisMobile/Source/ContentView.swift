import SwiftUI
// import AegisMobile // Assuming the module is named AegisMobile or similar based on Xcode targets

struct ContentView: View {
    @State private var statusMessage: String = "Initializing..."

    var body: some View {
        VStack {
            Image(systemName: "lock.shield")
                .imageScale(.large)
                .foregroundColor(.accentColor)
            Text("Aegis Vault")
                .font(.title)
            Text(statusMessage)
                .padding()
        }
        .padding()
        .onAppear {
            initializeVault()
        }
    }

    func initializeVault() {
        // In a real app, use the Documents directory
        let paths = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)
        let documentsDirectory = paths[0]
        let vaultPath = documentsDirectory.path

        // Mock Key (32 bytes)
        let keyData = Data(count: 32)

        do {
            let vault = try MobileVault(path: vaultPath, key: keyData)
            statusMessage = "Vault Initialized Successfully!\nStorage: \(vaultPath)"
        } catch {
            statusMessage = "Failed to initialize vault: \(error)"
        }
    }
}
