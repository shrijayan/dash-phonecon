// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "DashPhone",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "DashPhone",
            path: "DashPhone"
        )
    ]
)
