#!/bin/bash
# Setup script for C++ client dependencies

set -e
cd "$(dirname "$0")"

echo "📦 Setting up third-party dependencies..."

mkdir -p third_party

# Download stb_image.h (for image decoding)
echo "⬇️  Downloading stb_image.h..."
mkdir -p third_party/stb
curl -sL https://raw.githubusercontent.com/nothings/stb/master/stb_image.h -o third_party/stb/stb_image.h

# Download nlohmann/json (header-only)
echo "⬇️  Downloading nlohmann/json..."
mkdir -p third_party/nlohmann
curl -sL https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp -o third_party/nlohmann/json.hpp

# Download Dear ImGui
echo "⬇️  Downloading Dear ImGui..."
IMGUI_VERSION="v1.90.1"
curl -sL "https://github.com/ocornut/imgui/archive/refs/tags/${IMGUI_VERSION}.tar.gz" | tar -xz -C third_party/
mv third_party/imgui-* third_party/imgui 2>/dev/null || true

# Download GLFW (optional - usually available via package manager)
# echo "⬇️  Downloading GLFW..."
# Can be installed via: sudo apt install libglfw3-dev

echo "✅ Dependencies downloaded!"
echo ""
echo "📋 System dependencies needed (install via package manager):"
echo "   Ubuntu/Debian: sudo apt install cmake build-essential libcurl4-openssl-dev libglfw3-dev libgl1-mesa-dev"
echo "   Fedora:        sudo dnf install cmake gcc-c++ libcurl-devel glfw-devel mesa-libGL-devel"
echo "   Arch:          sudo pacman -S cmake curl glfw-x11"
echo ""
echo "🔨 To build:"
echo "   mkdir build && cd build"
echo "   cmake .."
echo "   make"
