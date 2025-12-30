#pragma once

#include <string>
#include <vector>
#include <optional>
#include <functional>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace leitor {

// Data structures
struct ModelInfo {
    std::string name;
    std::string model_type;
    std::string target_stage;
    std::string rel_path;
};

struct ImageInfo {
    std::string id;
    std::string filename;
    bool processed;
    bool has_report;
};

struct QuestionAnswer {
    int number;
    std::string answer;
    bool updated;
};

struct Report {
    std::string owner_cpf;
    std::string test_type;
    std::vector<QuestionAnswer> questions;
};

struct ProcessingResult {
    std::string status;
    std::string image_id;
    int detections_count;
    std::optional<Report> report;
};

// API Client class
class APIClient {
public:
    APIClient(const std::string& base_url = "http://localhost:8000");
    ~APIClient();
    
    void set_base_url(const std::string& url) { base_url_ = url; }
    std::string get_base_url() const { return base_url_; }
    
    // Connection
    bool test_connection();
    
    // Session
    std::string create_session(const std::string& test_type);
    json get_session(const std::string& session_id);
    bool delete_session(const std::string& session_id);
    
    // Models
    std::vector<ModelInfo> get_models();
    
    // Images
    json upload_images(const std::string& session_id, const std::vector<std::string>& file_paths);
    std::vector<ImageInfo> get_images(const std::string& session_id);
    std::vector<unsigned char> get_image_data(const std::string& session_id, 
                                               const std::string& image_id, 
                                               bool with_detections = false);
    
    // Processing
    ProcessingResult process_image(const std::string& session_id,
                                   const std::string& image_id,
                                   const std::string& fs_model,
                                   const std::string& ss_model,
                                   float fs_threshold = 0.5f,
                                   float ss_threshold = 0.5f);
    
    std::vector<ProcessingResult> process_all_images(const std::string& session_id,
                                                      const std::string& fs_model,
                                                      const std::string& ss_model,
                                                      float fs_threshold = 0.5f,
                                                      float ss_threshold = 0.5f);
    
    // Reports
    Report get_report(const std::string& session_id, const std::string& image_id);
    std::vector<Report> get_all_reports(const std::string& session_id);
    bool update_answer(const std::string& session_id, 
                       const std::string& image_id,
                       int question_number, 
                       const std::string& answer);
    
    // Export
    std::string export_reports(const std::string& session_id, const std::string& format = "json");
    
    // Error handling
    std::string get_last_error() const { return last_error_; }
    
private:
    std::string base_url_;
    std::string last_error_;
    
    // HTTP methods
    json http_get(const std::string& endpoint);
    json http_post(const std::string& endpoint, const std::string& data = "");
    json http_post_form(const std::string& endpoint, const std::vector<std::pair<std::string, std::string>>& fields);
    json http_post_files(const std::string& endpoint, const std::vector<std::string>& file_paths);
    json http_delete(const std::string& endpoint);
    
    std::string url_encode(const std::string& str);
};

} // namespace leitor
