#include "api_client.h"
#include <curl/curl.h>
#include <sstream>
#include <fstream>
#include <stdexcept>

namespace leitor {

// CURL write callback
static size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* userp) {
    size_t total = size * nmemb;
    userp->append((char*)contents, total);
    return total;
}

APIClient::APIClient(const std::string& base_url) : base_url_(base_url) {
    curl_global_init(CURL_GLOBAL_ALL);
}

APIClient::~APIClient() {
    curl_global_cleanup();
}

bool APIClient::test_connection() {
    try {
        auto result = http_get("/api/models");
        return result.contains("models");
    } catch (...) {
        return false;
    }
}

std::string APIClient::create_session(const std::string& test_type) {
    auto result = http_post_form("/api/session/create", {{"test_type", test_type}});
    return result["session_id"].get<std::string>();
}

json APIClient::get_session(const std::string& session_id) {
    return http_get("/api/session/" + session_id);
}

bool APIClient::delete_session(const std::string& session_id) {
    try {
        http_delete("/api/session/" + session_id);
        return true;
    } catch (...) {
        return false;
    }
}

std::vector<ModelInfo> APIClient::get_models() {
    auto result = http_get("/api/models");
    std::vector<ModelInfo> models;
    
    for (const auto& m : result["models"]) {
        ModelInfo info;
        info.name = m["name"].get<std::string>();
        info.model_type = m["model_type"].get<std::string>();
        info.target_stage = m["target_stage"].get<std::string>();
        info.rel_path = m["rel_path"].get<std::string>();
        models.push_back(info);
    }
    
    return models;
}

json APIClient::upload_images(const std::string& session_id, const std::vector<std::string>& file_paths) {
    return http_post_files("/api/upload/" + session_id, file_paths);
}

std::vector<ImageInfo> APIClient::get_images(const std::string& session_id) {
    auto result = http_get("/api/images/" + session_id);
    std::vector<ImageInfo> images;
    
    for (const auto& img : result["images"]) {
        ImageInfo info;
        info.id = img["id"].get<std::string>();
        info.filename = img["filename"].get<std::string>();
        info.processed = img["processed"].get<bool>();
        info.has_report = img["has_report"].get<bool>();
        images.push_back(info);
    }
    
    return images;
}

std::vector<unsigned char> APIClient::get_image_data(const std::string& session_id, 
                                                      const std::string& image_id, 
                                                      bool with_detections) {
    std::string endpoint = "/api/image/" + session_id + "/" + image_id;
    if (with_detections) {
        endpoint += "?with_detections=true";
    }
    
    auto result = http_get(endpoint);
    std::string base64_data = result["image"].get<std::string>();
    
    // Decode base64
    // Using simple base64 decode (see image_loader.cpp)
    extern std::vector<unsigned char> base64_decode(const std::string&);
    return base64_decode(base64_data);
}

ProcessingResult APIClient::process_image(const std::string& session_id,
                                          const std::string& image_id,
                                          const std::string& fs_model,
                                          const std::string& ss_model,
                                          float fs_threshold,
                                          float ss_threshold) {
    auto result = http_post_form("/api/process/" + session_id + "/" + image_id, {
        {"fs_model", fs_model},
        {"ss_model", ss_model},
        {"fs_threshold", std::to_string(fs_threshold)},
        {"ss_threshold", std::to_string(ss_threshold)}
    });
    
    ProcessingResult pr;
    pr.status = result["status"].get<std::string>();
    pr.image_id = result["image_id"].get<std::string>();
    pr.detections_count = result["detections_count"].get<int>();
    
    if (result.contains("report") && !result["report"].is_null()) {
        Report report;
        report.owner_cpf = result["report"]["owner_cpf"].get<std::string>();
        report.test_type = result["report"]["test_type"].get<std::string>();
        
        for (const auto& q : result["report"]["questions"]) {
            QuestionAnswer qa;
            qa.number = q["number"].get<int>();
            qa.answer = q["answer"].get<std::string>();
            qa.updated = q["updated"].get<bool>();
            report.questions.push_back(qa);
        }
        pr.report = report;
    }
    
    return pr;
}

std::vector<ProcessingResult> APIClient::process_all_images(const std::string& session_id,
                                                             const std::string& fs_model,
                                                             const std::string& ss_model,
                                                             float fs_threshold,
                                                             float ss_threshold) {
    auto result = http_post_form("/api/process-all/" + session_id, {
        {"fs_model", fs_model},
        {"ss_model", ss_model},
        {"fs_threshold", std::to_string(fs_threshold)},
        {"ss_threshold", std::to_string(ss_threshold)}
    });
    
    std::vector<ProcessingResult> results;
    for (const auto& r : result["results"]) {
        ProcessingResult pr;
        pr.status = r["status"].get<std::string>();
        pr.image_id = r["image_id"].get<std::string>();
        pr.detections_count = r.value("detections_count", 0);
        results.push_back(pr);
    }
    
    return results;
}

Report APIClient::get_report(const std::string& session_id, const std::string& image_id) {
    auto result = http_get("/api/report/" + session_id + "/" + image_id);
    
    Report report;
    report.owner_cpf = result["report"]["owner_cpf"].get<std::string>();
    report.test_type = result["report"]["test_type"].get<std::string>();
    
    for (const auto& q : result["report"]["questions"]) {
        QuestionAnswer qa;
        qa.number = q["number"].get<int>();
        qa.answer = q["answer"].get<std::string>();
        qa.updated = q["updated"].get<bool>();
        report.questions.push_back(qa);
    }
    
    return report;
}

std::vector<Report> APIClient::get_all_reports(const std::string& session_id) {
    auto result = http_get("/api/reports/" + session_id);
    std::vector<Report> reports;
    
    for (const auto& r : result["reports"]) {
        Report report;
        report.owner_cpf = r["report"]["owner_cpf"].get<std::string>();
        report.test_type = r["report"]["test_type"].get<std::string>();
        
        for (const auto& q : r["report"]["questions"]) {
            QuestionAnswer qa;
            qa.number = q["number"].get<int>();
            qa.answer = q["answer"].get<std::string>();
            qa.updated = q["updated"].get<bool>();
            report.questions.push_back(qa);
        }
        reports.push_back(report);
    }
    
    return reports;
}

bool APIClient::update_answer(const std::string& session_id, 
                               const std::string& image_id,
                               int question_number, 
                               const std::string& answer) {
    try {
        http_post_form("/api/update-answer/" + session_id + "/" + image_id, {
            {"question_number", std::to_string(question_number)},
            {"answer", answer}
        });
        return true;
    } catch (...) {
        return false;
    }
}

std::string APIClient::export_reports(const std::string& session_id, const std::string& format) {
    auto result = http_get("/api/export/" + session_id + "?format=" + format);
    return result.dump(2);
}

// HTTP implementation using libcurl
json APIClient::http_get(const std::string& endpoint) {
    CURL* curl = curl_easy_init();
    std::string response;
    
    if (curl) {
        std::string url = base_url_ + endpoint;
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
        
        CURLcode res = curl_easy_perform(curl);
        long http_code = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
        curl_easy_cleanup(curl);
        
        if (res != CURLE_OK) {
            last_error_ = curl_easy_strerror(res);
            throw std::runtime_error(last_error_);
        }
        
        if (http_code >= 400) {
            last_error_ = "HTTP " + std::to_string(http_code);
            throw std::runtime_error(last_error_);
        }
    }
    
    return json::parse(response);
}

json APIClient::http_post(const std::string& endpoint, const std::string& data) {
    CURL* curl = curl_easy_init();
    std::string response;
    
    if (curl) {
        std::string url = base_url_ + endpoint;
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_POST, 1L);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, data.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 120L);
        
        CURLcode res = curl_easy_perform(curl);
        curl_easy_cleanup(curl);
        
        if (res != CURLE_OK) {
            last_error_ = curl_easy_strerror(res);
            throw std::runtime_error(last_error_);
        }
    }
    
    return json::parse(response);
}

json APIClient::http_post_form(const std::string& endpoint, 
                                const std::vector<std::pair<std::string, std::string>>& fields) {
    CURL* curl = curl_easy_init();
    std::string response;
    
    if (curl) {
        std::string url = base_url_ + endpoint;
        
        // Build form data
        curl_mime* form = curl_mime_init(curl);
        for (const auto& field : fields) {
            curl_mimepart* part = curl_mime_addpart(form);
            curl_mime_name(part, field.first.c_str());
            curl_mime_data(part, field.second.c_str(), CURL_ZERO_TERMINATED);
        }
        
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_MIMEPOST, form);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 120L);
        
        CURLcode res = curl_easy_perform(curl);
        long http_code = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
        
        curl_mime_free(form);
        curl_easy_cleanup(curl);
        
        if (res != CURLE_OK) {
            last_error_ = curl_easy_strerror(res);
            throw std::runtime_error(last_error_);
        }
        
        if (http_code >= 400) {
            last_error_ = "HTTP " + std::to_string(http_code) + ": " + response;
            throw std::runtime_error(last_error_);
        }
    }
    
    return json::parse(response);
}

json APIClient::http_post_files(const std::string& endpoint, const std::vector<std::string>& file_paths) {
    CURL* curl = curl_easy_init();
    std::string response;
    
    if (curl) {
        std::string url = base_url_ + endpoint;
        
        curl_mime* form = curl_mime_init(curl);
        for (const auto& path : file_paths) {
            curl_mimepart* part = curl_mime_addpart(form);
            curl_mime_name(part, "files");
            curl_mime_filedata(part, path.c_str());
        }
        
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_MIMEPOST, form);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 300L);  // Longer timeout for uploads
        
        CURLcode res = curl_easy_perform(curl);
        curl_mime_free(form);
        curl_easy_cleanup(curl);
        
        if (res != CURLE_OK) {
            last_error_ = curl_easy_strerror(res);
            throw std::runtime_error(last_error_);
        }
    }
    
    return json::parse(response);
}

json APIClient::http_delete(const std::string& endpoint) {
    CURL* curl = curl_easy_init();
    std::string response;
    
    if (curl) {
        std::string url = base_url_ + endpoint;
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "DELETE");
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
        
        CURLcode res = curl_easy_perform(curl);
        curl_easy_cleanup(curl);
        
        if (res != CURLE_OK) {
            last_error_ = curl_easy_strerror(res);
            throw std::runtime_error(last_error_);
        }
    }
    
    return json::parse(response);
}

std::string APIClient::url_encode(const std::string& str) {
    CURL* curl = curl_easy_init();
    char* encoded = curl_easy_escape(curl, str.c_str(), str.length());
    std::string result(encoded);
    curl_free(encoded);
    curl_easy_cleanup(curl);
    return result;
}

} // namespace leitor
