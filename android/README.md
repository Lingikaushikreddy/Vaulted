# Android Build Instructions

## Native Libraries (Rust)

This application depends on the `aegis-engine` Rust library. The Kotlin bindings expect the shared library `libaegis_engine.so` to be available at runtime.

### Setup

1.  **Build the Rust Library**:
    Navigate to the `aegis-engine` directory and build for your target architecture (e.g., `aarch64-linux-android`).
    ```bash
    cd ../../aegis-engine
    cargo build --target aarch64-linux-android --release
    ```

2.  **Copy Shared Objects**:
    Copy the resulting `.so` file to the `jniLibs` directory.
    ```bash
    mkdir -p app/src/main/jniLibs/arm64-v8a
    cp ../../aegis-engine/target/aarch64-linux-android/release/libaegis_engine.so app/src/main/jniLibs/arm64-v8a/
    ```

3.  **Build Android App**:
    Use Gradle to build the application.
    ```bash
    ./gradlew build
    ```

## UniFFI Bindings

The Kotlin bindings in `src/main/java/uniffi/aegis_engine/` are generated automatically. If you modify the Rust API, regenerate them:
```bash
cargo run --bin uniffi-bindgen generate --library ... --language kotlin ...
```
