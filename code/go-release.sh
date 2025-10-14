#!/bin/bash

# Check if the binary name and release version are provided as arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <binary_name> <release_version>"
    exit 1
fi

# Set the binary name and release version from the arguments
BINARY_NAME="$1"
RELEASE_VERSION="$2"

# Create the output directory if it doesn't exist
mkdir -p ./bin

# Function to build for a specific OS and architecture
build() {
    local os=$1
    local arch=$2
    local output_name="${BINARY_NAME}_${RELEASE_VERSION}_${os}_${arch}"

    if [ "$os" == "windows" ]; then
        output_name="${output_name}.exe"
    fi

    # Set the environment variables for cross-compilation
    GOOS=$os GOARCH=$arch go build -ldflags="-s -w" -o "./bin/${output_name}" ./main.go
}

# Build for Linux
build linux amd64
build linux arm64

# Build for macOS
build darwin amd64
build darwin arm64

# Build for Windows
build windows amd64
build windows arm64

echo "Builds completed. Binaries are located in ./bin."
