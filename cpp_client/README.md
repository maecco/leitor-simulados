# C++ Desktop Client for Leitor de Simulados

A lightweight, native C++ client that connects to the Leitor de Simulados server using Dear ImGui for the graphical interface.

## Features

- Native C++ application with minimal dependencies
- Modern Dear ImGui interface with GLFW/OpenGL backend
- HTTP communication with the Python FastAPI server via libcurl
- Image viewing with detection overlays
- Real-time answer editing and export

## Dependencies

- **CMake** >= 3.16
- **libcurl** - HTTP client
- **nlohmann/json** - JSON parsing (header-only)
- **stb_image** - Image loading (header-only)
- **Dear ImGui** - GUI
- **GLFW** - Window management
- **OpenGL** - Rendering

## Setup

### 1. Install system packages

**Ubuntu/Debian:**
```bash
sudo apt-get install build-essential cmake libcurl4-openssl-dev libglfw3-dev libgl1-mesa-dev
```

**Fedora:**
```bash
sudo dnf install cmake gcc-c++ libcurl-devel glfw-devel mesa-libGL-devel
```

**Arch:**
```bash
sudo pacman -S cmake base-devel curl glfw-x11 mesa
```

**macOS:**
```bash
brew install cmake curl glfw
```

**Windows (with vcpkg):**
```powershell
vcpkg install curl glfw3 opengl
```

### 2. Download third-party libraries

```bash
cd cpp_client
chmod +x setup_deps.sh
./setup_deps.sh
```

This downloads Dear ImGui, nlohmann/json, and stb_image into `third_party/`.

### 3. Build

```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
```

For Windows with vcpkg:
```powershell
mkdir build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=[vcpkg root]/scripts/buildsystems/vcpkg.cmake
cmake --build . --config Release
```

## Running

First, start the Python server:
```bash
cd /home/maecco/dev/leitor-simulados
/path/to/venv/bin/python run_web.py
```

Then run the client:
```bash
./build/leitor_client
```

### Command line options

```bash
./leitor_client                              # Connect to localhost:8000
./leitor_client --server http://server:8000  # Connect to remote server
```

## Project Structure

```
cpp_client/
├── CMakeLists.txt       # Build configuration
├── README.md            # This file
├── setup_deps.sh        # Dependency download script
├── include/
│   ├── api_client.h     # HTTP API client
│   ├── app.h            # Main application class
│   └── image_loader.h   # Image loading utilities
├── src/
│   ├── main.cpp         # Entry point
│   ├── app.cpp          # Application implementation
│   ├── api_client.cpp   # API client implementation
│   └── image_loader.cpp # Image loading implementation
└── third_party/         # Downloaded by setup_deps.sh
    ├── imgui/           # Dear ImGui
    ├── nlohmann/        # JSON library
    └── stb/             # stb_image
```
