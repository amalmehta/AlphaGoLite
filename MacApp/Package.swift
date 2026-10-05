// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "AlphaGoLite",
    platforms: [.macOS(.v14)],
    targets: [
        .target(name: "GoEngine"),
        .executableTarget(name: "AlphaGoLite", dependencies: ["GoEngine"]),
        .testTarget(name: "GoEngineTests", dependencies: ["GoEngine"],
                    resources: [.copy("test_vectors.json")]),
    ]
)
