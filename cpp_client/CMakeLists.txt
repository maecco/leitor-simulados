cmake_minimum_required(VERSION 3.16)
project(leitor_client VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Find required packages
find_package(CURL REQUIRED)
find_package(OpenGL REQUIRED)
find_package(glfw3 REQUIRED)

# Include directories
include_directories(
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/third_party/imgui
    ${CMAKE_SOURCE_DIR}/third_party/imgui/backends
    ${CMAKE_SOURCE_DIR}/third_party/nlohmann
    ${CMAKE_SOURCE_DIR}/third_party/stb
    ${CURL_INCLUDE_DIRS}
)

# ImGui sources
set(IMGUI_SOURCES
    third_party/imgui/imgui.cpp
    third_party/imgui/imgui_draw.cpp
    third_party/imgui/imgui_tables.cpp
    third_party/imgui/imgui_widgets.cpp
    third_party/imgui/imgui_demo.cpp
    third_party/imgui/backends/imgui_impl_glfw.cpp
    third_party/imgui/backends/imgui_impl_opengl3.cpp
)

# Application sources
set(APP_SOURCES
    src/main.cpp
    src/app.cpp
    src/api_client.cpp
    src/image_loader.cpp
)

# Create executable
add_executable(leitor_client ${APP_SOURCES} ${IMGUI_SOURCES})

# Enable stb_image support
target_compile_definitions(leitor_client PRIVATE HAS_STB_IMAGE)

# Link libraries
target_link_libraries(leitor_client
    ${CURL_LIBRARIES}
    OpenGL::GL
    glfw
)

# Platform-specific settings
if(WIN32)
    target_link_libraries(leitor_client ws2_32)
endif()

if(APPLE)
    target_link_libraries(leitor_client "-framework Cocoa" "-framework IOKit")
endif()

if(UNIX AND NOT APPLE)
    target_link_libraries(leitor_client dl pthread)
endif()

# Install
install(TARGETS leitor_client DESTINATION bin)
