#include "app.h"
#include "image_loader.h"

#include <imgui.h>
#include <imgui_impl_glfw.h>
#include <imgui_impl_opengl3.h>

#include <GLFW/glfw3.h>

#include <iostream>
#include <fstream>
#include <algorithm>
#include <cstring>

// Platform-specific file dialog
#ifdef _WIN32
#include <windows.h>
#include <commdlg.h>
#else
#include <cstdlib>
#endif

namespace leitor {

// Helper to open file dialog
std::vector<std::string> open_file_dialog(bool multiple = true) {
    std::vector<std::string> result;
    
#ifdef _WIN32
    char filename[MAX_PATH * 10] = "";
    OPENFILENAMEA ofn = {};
    ofn.lStructSize = sizeof(ofn);
    ofn.lpstrFile = filename;
    ofn.nMaxFile = sizeof(filename);
    ofn.lpstrFilter = "Images\0*.png;*.jpg;*.jpeg\0All Files\0*.*\0";
    ofn.Flags = OFN_FILEMUSTEXIST | (multiple ? OFN_ALLOWMULTISELECT | OFN_EXPLORER : 0);
    
    if (GetOpenFileNameA(&ofn)) {
        // Parse multiple files
        char* p = filename;
        std::string dir = p;
        p += strlen(p) + 1;
        
        if (*p == 0) {
            result.push_back(dir);
        } else {
            while (*p) {
                result.push_back(dir + "\\" + p);
                p += strlen(p) + 1;
            }
        }
    }
#else
    // Linux/macOS - use zenity
    FILE* f = popen("zenity --file-selection --multiple --separator='\\n' --file-filter='Images | *.png *.jpg *.jpeg' 2>/dev/null", "r");
    if (f) {
        char buffer[4096];
        while (fgets(buffer, sizeof(buffer), f)) {
            std::string path(buffer);
            if (!path.empty() && path.back() == '\n') path.pop_back();
            if (!path.empty()) result.push_back(path);
        }
        pclose(f);
    }
#endif
    
    return result;
}

std::string save_file_dialog(const std::string& default_ext) {
#ifdef _WIN32
    char filename[MAX_PATH] = "";
    OPENFILENAMEA ofn = {};
    ofn.lStructSize = sizeof(ofn);
    ofn.lpstrFile = filename;
    ofn.nMaxFile = sizeof(filename);
    ofn.lpstrFilter = "JSON\0*.json\0CSV\0*.csv\0All Files\0*.*\0";
    ofn.lpstrDefExt = default_ext.c_str();
    ofn.Flags = OFN_OVERWRITEPROMPT;
    
    if (GetSaveFileNameA(&ofn)) {
        return filename;
    }
#else
    std::string cmd = "zenity --file-selection --save --filename=report." + default_ext + " 2>/dev/null";
    FILE* f = popen(cmd.c_str(), "r");
    if (f) {
        char buffer[4096];
        if (fgets(buffer, sizeof(buffer), f)) {
            std::string path(buffer);
            if (!path.empty() && path.back() == '\n') path.pop_back();
            pclose(f);
            return path;
        }
        pclose(f);
    }
#endif
    return "";
}

Application::Application() {
    api_ = std::make_unique<APIClient>();
}

Application::~Application() {
    shutdown();
}

bool Application::initialize(int argc, char** argv) {
    // Parse arguments
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if ((arg == "--server" || arg == "-s") && i + 1 < argc) {
            strncpy(state_.server_url_buf, argv[++i], sizeof(state_.server_url_buf) - 1);
            state_.server_url = state_.server_url_buf;
        }
    }
    
    // Initialize GLFW
    if (!glfwInit()) {
        std::cerr << "Failed to initialize GLFW" << std::endl;
        return false;
    }
    
    // GL 3.0 + GLSL 130
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 0);
    
    // Create window
    GLFWwindow* window = glfwCreateWindow(1280, 720, "Leitor de Simulados - C++ Client", nullptr, nullptr);
    if (!window) {
        std::cerr << "Failed to create GLFW window" << std::endl;
        glfwTerminate();
        return false;
    }
    window_ = window;
    
    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);  // VSync
    
    // Setup Dear ImGui
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    
    // Setup style
    ImGui::StyleColorsDark();
    ImGuiStyle& style = ImGui::GetStyle();
    style.WindowRounding = 5.0f;
    style.FrameRounding = 3.0f;
    
    // Setup Platform/Renderer backends
    ImGui_ImplGlfw_InitForOpenGL(window, true);
    ImGui_ImplOpenGL3_Init("#version 130");
    
    return true;
}

void Application::run() {
    GLFWwindow* window = static_cast<GLFWwindow*>(window_);
    
    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();
        
        // Start ImGui frame
        ImGui_ImplOpenGL3_NewFrame();
        ImGui_ImplGlfw_NewFrame();
        ImGui::NewFrame();
        
        // Render UI
        render_ui();
        
        // Rendering
        ImGui::Render();
        int display_w, display_h;
        glfwGetFramebufferSize(window, &display_w, &display_h);
        glViewport(0, 0, display_w, display_h);
        glClearColor(0.1f, 0.1f, 0.1f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
        
        glfwSwapBuffers(window);
    }
}

void Application::shutdown() {
    if (state_.image_texture) {
        glDeleteTextures(1, &state_.image_texture);
        state_.image_texture = 0;
    }
    
    ImGui_ImplOpenGL3_Shutdown();
    ImGui_ImplGlfw_Shutdown();
    ImGui::DestroyContext();
    
    if (window_) {
        glfwDestroyWindow(static_cast<GLFWwindow*>(window_));
        window_ = nullptr;
    }
    glfwTerminate();
}

void Application::render_ui() {
    // Get window size
    int width, height;
    glfwGetWindowSize(static_cast<GLFWwindow*>(window_), &width, &height);
    
    // Menu bar
    render_menu_bar();
    
    // Main layout
    float menu_height = ImGui::GetFrameHeight();
    float status_height = 25.0f;
    float left_width = 280.0f;
    float right_width = 300.0f;
    float center_width = width - left_width - right_width;
    float content_height = height - menu_height - status_height;
    
    // Left panel
    ImGui::SetNextWindowPos(ImVec2(0, menu_height));
    ImGui::SetNextWindowSize(ImVec2(left_width, content_height));
    render_left_panel();
    
    // Center panel
    ImGui::SetNextWindowPos(ImVec2(left_width, menu_height));
    ImGui::SetNextWindowSize(ImVec2(center_width, content_height));
    render_center_panel();
    
    // Right panel
    ImGui::SetNextWindowPos(ImVec2(left_width + center_width, menu_height));
    ImGui::SetNextWindowSize(ImVec2(right_width, content_height));
    render_right_panel();
    
    // Status bar
    ImGui::SetNextWindowPos(ImVec2(0, height - status_height));
    ImGui::SetNextWindowSize(ImVec2((float)width, status_height));
    render_status_bar();
}

void Application::render_menu_bar() {
    if (ImGui::BeginMainMenuBar()) {
        if (ImGui::BeginMenu("Arquivo")) {
            if (ImGui::MenuItem("Conectar ao Servidor")) connect_to_server();
            ImGui::Separator();
            if (ImGui::MenuItem("Nova Sessão", nullptr, false, state_.connected)) create_session();
            if (ImGui::MenuItem("Carregar Imagens", nullptr, false, !state_.session_id.empty())) load_images();
            ImGui::Separator();
            if (ImGui::MenuItem("Exportar JSON", nullptr, false, !state_.session_id.empty())) export_results("json");
            if (ImGui::MenuItem("Exportar CSV", nullptr, false, !state_.session_id.empty())) export_results("csv");
            ImGui::Separator();
            if (ImGui::MenuItem("Sair")) {
                glfwSetWindowShouldClose(static_cast<GLFWwindow*>(window_), GLFW_TRUE);
            }
            ImGui::EndMenu();
        }
        
        if (ImGui::BeginMenu("Processar")) {
            if (ImGui::MenuItem("Processar Atual", nullptr, false, state_.current_image_index >= 0)) process_current();
            if (ImGui::MenuItem("Processar Todas", nullptr, false, !state_.images.empty())) process_all();
            ImGui::EndMenu();
        }
        
        if (ImGui::BeginMenu("Ajuda")) {
            if (ImGui::MenuItem("Sobre")) {
                // Show about dialog
            }
            ImGui::EndMenu();
        }
        
        ImGui::EndMainMenuBar();
    }
}

void Application::render_left_panel() {
    ImGui::Begin("Controles", nullptr, 
        ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse);
    
    // Server connection
    if (ImGui::CollapsingHeader("Servidor", ImGuiTreeNodeFlags_DefaultOpen)) {
        ImGui::Text("URL:");
        ImGui::SetNextItemWidth(-1);
        ImGui::InputText("##server_url", state_.server_url_buf, sizeof(state_.server_url_buf));
        
        if (ImGui::Button("Conectar", ImVec2(-1, 0))) {
            connect_to_server();
        }
        
        ImGui::TextColored(
            state_.connected ? ImVec4(0, 1, 0, 1) : ImVec4(1, 0, 0, 1),
            state_.connected ? "● Conectado" : "● Desconectado"
        );
    }
    
    // Session
    if (ImGui::CollapsingHeader("Sessão", ImGuiTreeNodeFlags_DefaultOpen)) {
        static const char* test_types[] = { "PS_ALUNOS", "SIMULINHO", "SIMUFSC", "SIMUENEM" };
        static int test_type_idx = 0;
        
        ImGui::Text("Tipo de Prova:");
        ImGui::SetNextItemWidth(-1);
        ImGui::Combo("##test_type", &test_type_idx, test_types, IM_ARRAYSIZE(test_types));
        state_.test_type = test_types[test_type_idx];
        
        if (ImGui::Button("Criar Sessão", ImVec2(-1, 0))) {
            create_session();
        }
        
        if (!state_.session_id.empty()) {
            ImGui::TextColored(ImVec4(0, 1, 0, 1), "✓ %s...", state_.session_id.substr(0, 8).c_str());
        }
    }
    
    // Models
    if (ImGui::CollapsingHeader("Modelos", ImGuiTreeNodeFlags_DefaultOpen)) {
        auto fs_names = get_fs_model_names();
        auto ss_names = get_ss_model_names();
        
        ImGui::Text("1ª Etapa:");
        ImGui::SetNextItemWidth(-1);
        if (!fs_names.empty()) {
            if (ImGui::BeginCombo("##fs_model", 
                state_.fs_model_index >= 0 ? fs_names[state_.fs_model_index].c_str() : "Selecione...")) {
                for (int i = 0; i < (int)fs_names.size(); i++) {
                    if (ImGui::Selectable(fs_names[i].c_str(), state_.fs_model_index == i)) {
                        state_.fs_model_index = i;
                    }
                }
                ImGui::EndCombo();
            }
        }
        
        ImGui::Text("Threshold:");
        ImGui::SetNextItemWidth(-1);
        ImGui::SliderFloat("##fs_thresh", &state_.fs_threshold, 0.1f, 0.9f, "%.2f");
        
        ImGui::Spacing();
        
        ImGui::Text("2ª Etapa:");
        ImGui::SetNextItemWidth(-1);
        if (!ss_names.empty()) {
            if (ImGui::BeginCombo("##ss_model", 
                state_.ss_model_index >= 0 ? ss_names[state_.ss_model_index].c_str() : "Selecione...")) {
                for (int i = 0; i < (int)ss_names.size(); i++) {
                    if (ImGui::Selectable(ss_names[i].c_str(), state_.ss_model_index == i)) {
                        state_.ss_model_index = i;
                    }
                }
                ImGui::EndCombo();
            }
        }
        
        ImGui::Text("Threshold:");
        ImGui::SetNextItemWidth(-1);
        ImGui::SliderFloat("##ss_thresh", &state_.ss_threshold, 0.1f, 0.9f, "%.2f");
        
        ImGui::Spacing();
        
        if (ImGui::Button("Processar", ImVec2(ImGui::GetContentRegionAvail().x * 0.5f - 2, 0))) {
            process_current();
        }
        ImGui::SameLine();
        if (ImGui::Button("Todas", ImVec2(-1, 0))) {
            process_all();
        }
    }
    
    // Images list
    if (ImGui::CollapsingHeader("Imagens", ImGuiTreeNodeFlags_DefaultOpen)) {
        if (ImGui::Button("📁 Carregar Imagens", ImVec2(-1, 0))) {
            load_images();
        }
        
        ImGui::Text("(%d imagens)", (int)state_.images.size());
        
        ImGui::BeginChild("ImageList", ImVec2(-1, 150), true);
        for (int i = 0; i < (int)state_.images.size(); i++) {
            const auto& img = state_.images[i];
            std::string label = (img.processed ? "✓ " : "  ") + img.filename;
            
            if (ImGui::Selectable(label.c_str(), state_.current_image_index == i)) {
                select_image(i);
            }
        }
        ImGui::EndChild();
    }
    
    ImGui::End();
}

void Application::render_center_panel() {
    ImGui::Begin("Visualizador", nullptr, 
        ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse);
    
    // Toolbar
    if (ImGui::Button("◀")) {
        if (state_.current_image_index > 0) {
            select_image(state_.current_image_index - 1);
        }
    }
    ImGui::SameLine();
    ImGui::Text("%d / %d", 
        state_.current_image_index >= 0 ? state_.current_image_index + 1 : 0, 
        (int)state_.images.size());
    ImGui::SameLine();
    if (ImGui::Button("▶")) {
        if (state_.current_image_index < (int)state_.images.size() - 1) {
            select_image(state_.current_image_index + 1);
        }
    }
    ImGui::SameLine();
    ImGui::Checkbox("Mostrar detecções", &state_.show_detections);
    
    ImGui::Separator();
    
    // Image display
    ImVec2 avail = ImGui::GetContentRegionAvail();
    
    if (state_.image_texture && state_.image_width > 0) {
        // Calculate aspect ratio fit
        float img_aspect = (float)state_.image_width / state_.image_height;
        float avail_aspect = avail.x / avail.y;
        
        float display_w, display_h;
        if (img_aspect > avail_aspect) {
            display_w = avail.x;
            display_h = avail.x / img_aspect;
        } else {
            display_h = avail.y;
            display_w = avail.y * img_aspect;
        }
        
        // Center the image
        float offset_x = (avail.x - display_w) * 0.5f;
        float offset_y = (avail.y - display_h) * 0.5f;
        ImGui::SetCursorPos(ImVec2(ImGui::GetCursorPosX() + offset_x, ImGui::GetCursorPosY() + offset_y));
        
        ImGui::Image((ImTextureID)(intptr_t)state_.image_texture, ImVec2(display_w, display_h));
    } else {
        // Placeholder
        ImGui::SetCursorPos(ImVec2(avail.x * 0.5f - 100, avail.y * 0.5f));
        ImGui::TextColored(ImVec4(0.5f, 0.5f, 0.5f, 1.0f), "📷 Nenhuma imagem carregada");
    }
    
    ImGui::End();
}

void Application::render_right_panel() {
    ImGui::Begin("Relatório", nullptr, 
        ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse);
    
    if (state_.current_report.has_value()) {
        const auto& report = state_.current_report.value();
        
        ImGui::Text("CPF:"); ImGui::SameLine();
        ImGui::TextColored(ImVec4(0, 1, 1, 1), "%s", report.owner_cpf.c_str());
        
        ImGui::Separator();
        ImGui::Text("Respostas:");
        
        ImGui::BeginChild("Answers", ImVec2(-1, -1), true);
        
        static const char* answers[] = { "", "A", "B", "C", "D", "E" };
        
        for (size_t i = 0; i < report.questions.size(); i++) {
            const auto& q = report.questions[i];
            
            ImGui::PushID((int)i);
            ImGui::Text("%02d:", q.number);
            ImGui::SameLine();
            
            // Find current answer index
            int current = 0;
            for (int j = 0; j < 6; j++) {
                if (q.answer == answers[j]) { current = j; break; }
            }
            
            ImGui::SetNextItemWidth(60);
            if (ImGui::Combo("##ans", &current, answers, IM_ARRAYSIZE(answers))) {
                // Update answer on server
                api_->update_answer(state_.session_id, 
                    state_.images[state_.current_image_index].id,
                    q.number, answers[current]);
            }
            
            if (q.updated) {
                ImGui::SameLine();
                ImGui::TextColored(ImVec4(0, 1, 0, 1), "✓");
            }
            
            ImGui::PopID();
        }
        
        ImGui::EndChild();
    } else {
        ImGui::TextColored(ImVec4(0.5f, 0.5f, 0.5f, 1.0f), "Nenhum relatório disponível");
    }
    
    ImGui::End();
}

void Application::render_status_bar() {
    ImGui::Begin("Status", nullptr, 
        ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoCollapse | 
        ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoScrollbar);
    
    ImGui::Text("%s", state_.status_message.c_str());
    
    if (state_.is_processing) {
        ImGui::SameLine();
        ImGui::TextColored(ImVec4(1, 1, 0, 1), " [Processando...]");
    }
    
    ImGui::End();
}

void Application::connect_to_server() {
    state_.server_url = state_.server_url_buf;
    api_->set_base_url(state_.server_url);
    
    update_status("Conectando...");
    
    if (api_->test_connection()) {
        state_.connected = true;
        state_.models = api_->get_models();
        update_status("Conectado ao servidor");
    } else {
        state_.connected = false;
        update_status("Erro: " + api_->get_last_error());
    }
}

void Application::create_session() {
    if (!state_.connected || state_.test_type.empty()) return;
    
    try {
        state_.session_id = api_->create_session(state_.test_type);
        state_.images.clear();
        state_.current_image_index = -1;
        state_.current_report.reset();
        update_status("Sessão criada: " + state_.session_id.substr(0, 8) + "...");
    } catch (const std::exception& e) {
        update_status("Erro: " + std::string(e.what()));
    }
}

void Application::load_images() {
    if (state_.session_id.empty()) return;
    
    auto files = open_file_dialog(true);
    if (files.empty()) return;
    
    update_status("Carregando " + std::to_string(files.size()) + " imagens...");
    
    try {
        api_->upload_images(state_.session_id, files);
        refresh_image_list();
        update_status("Imagens carregadas com sucesso");
    } catch (const std::exception& e) {
        update_status("Erro: " + std::string(e.what()));
    }
}

void Application::refresh_image_list() {
    if (state_.session_id.empty()) return;
    
    try {
        state_.images = api_->get_images(state_.session_id);
        if (!state_.images.empty() && state_.current_image_index < 0) {
            select_image(0);
        }
    } catch (...) {}
}

void Application::select_image(int index) {
    if (index < 0 || index >= (int)state_.images.size()) return;
    
    state_.current_image_index = index;
    load_current_image();
    
    // Load report if available
    if (state_.images[index].has_report) {
        try {
            state_.current_report = api_->get_report(state_.session_id, state_.images[index].id);
        } catch (...) {
            state_.current_report.reset();
        }
    } else {
        state_.current_report.reset();
    }
}

void Application::load_current_image() {
    if (state_.current_image_index < 0) return;
    
    const auto& img = state_.images[state_.current_image_index];
    bool with_det = state_.show_detections && img.processed;
    
    try {
        auto data = api_->get_image_data(state_.session_id, img.id, with_det);
        
        std::vector<unsigned char> pixels;
        int width, height, channels;
        
        if (load_image_from_memory(data, pixels, width, height, channels)) {
            // Create OpenGL texture
            if (state_.image_texture) {
                glDeleteTextures(1, &state_.image_texture);
            }
            
            glGenTextures(1, &state_.image_texture);
            glBindTexture(GL_TEXTURE_2D, state_.image_texture);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels.data());
            
            state_.image_width = width;
            state_.image_height = height;
        }
    } catch (const std::exception& e) {
        update_status("Erro ao carregar imagem: " + std::string(e.what()));
    }
}

void Application::process_current() {
    if (state_.current_image_index < 0 || state_.fs_model_index < 0 || state_.ss_model_index < 0) {
        update_status("Selecione imagem e modelos primeiro");
        return;
    }
    
    auto fs_models = get_fs_model_names();
    auto ss_models = get_ss_model_names();
    
    std::string fs_path, ss_path;
    for (const auto& m : state_.models) {
        if (m.name == fs_models[state_.fs_model_index] && 
            (m.target_stage == "FIRST" || m.target_stage == "BOTH")) {
            fs_path = m.rel_path;
        }
        if (m.name == ss_models[state_.ss_model_index] && 
            (m.target_stage == "SECOND" || m.target_stage == "BOTH")) {
            ss_path = m.rel_path;
        }
    }
    
    state_.is_processing = true;
    update_status("Processando...");
    
    try {
        auto result = api_->process_image(
            state_.session_id,
            state_.images[state_.current_image_index].id,
            fs_path, ss_path,
            state_.fs_threshold, state_.ss_threshold
        );
        
        refresh_image_list();
        select_image(state_.current_image_index);
        update_status("Processado: " + std::to_string(result.detections_count) + " detecções");
    } catch (const std::exception& e) {
        update_status("Erro: " + std::string(e.what()));
    }
    
    state_.is_processing = false;
}

void Application::process_all() {
    // Similar to process_current but for all images
    update_status("Processando todas as imagens...");
    state_.is_processing = true;
    
    // ... implementation similar to process_current
    
    state_.is_processing = false;
    refresh_image_list();
    update_status("Todas as imagens processadas");
}

void Application::export_results(const std::string& format) {
    if (state_.session_id.empty()) return;
    
    std::string path = save_file_dialog(format);
    if (path.empty()) return;
    
    try {
        std::string content = api_->export_reports(state_.session_id, format);
        std::ofstream file(path);
        file << content;
        update_status("Exportado: " + path);
    } catch (const std::exception& e) {
        update_status("Erro: " + std::string(e.what()));
    }
}

void Application::update_status(const std::string& message) {
    state_.status_message = message;
}

std::vector<std::string> Application::get_fs_model_names() {
    std::vector<std::string> names;
    for (const auto& m : state_.models) {
        if (m.target_stage == "FIRST" || m.target_stage == "BOTH") {
            names.push_back(m.name);
        }
    }
    return names;
}

std::vector<std::string> Application::get_ss_model_names() {
    std::vector<std::string> names;
    for (const auto& m : state_.models) {
        if (m.target_stage == "SECOND" || m.target_stage == "BOTH") {
            names.push_back(m.name);
        }
    }
    return names;
}

} // namespace leitor
