#pragma once

#include <string>
#include <vector>
#include <memory>
#include <optional>
#include "api_client.h"

// Forward declarations for OpenGL
typedef unsigned int GLuint;

namespace leitor {

// Application state
struct AppState {
    // Connection
    std::string server_url = "http://localhost:8000";
    bool connected = false;
    
    // Session
    std::string session_id;
    std::string test_type;
    
    // Models
    std::vector<ModelInfo> models;
    int fs_model_index = -1;
    int ss_model_index = -1;
    float fs_threshold = 0.5f;
    float ss_threshold = 0.5f;
    
    // Images
    std::vector<ImageInfo> images;
    int current_image_index = -1;
    bool show_detections = true;
    
    // Current image texture
    GLuint image_texture = 0;
    int image_width = 0;
    int image_height = 0;
    
    // Report
    std::optional<Report> current_report;
    
    // UI state
    std::string status_message = "Disconnected";
    bool is_processing = false;
    char server_url_buf[256] = "http://localhost:8000";
};

// Main application class
class Application {
public:
    Application();
    ~Application();
    
    bool initialize(int argc, char** argv);
    void run();
    void shutdown();
    
private:
    // Window and rendering
    void* window_ = nullptr;  // GLFWwindow*
    
    // State
    AppState state_;
    std::unique_ptr<APIClient> api_;
    
    // UI rendering
    void render_ui();
    void render_menu_bar();
    void render_left_panel();
    void render_center_panel();
    void render_right_panel();
    void render_status_bar();
    
    // Actions
    void connect_to_server();
    void create_session();
    void load_images();
    void refresh_image_list();
    void select_image(int index);
    void load_current_image();
    void process_current();
    void process_all();
    void export_results(const std::string& format);
    
    // Helpers
    void update_status(const std::string& message);
    bool load_texture_from_memory(const std::vector<unsigned char>& data, GLuint* out_texture, int* out_width, int* out_height);
    std::vector<std::string> get_fs_model_names();
    std::vector<std::string> get_ss_model_names();
};

} // namespace leitor
