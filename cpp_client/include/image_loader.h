#pragma once

#include <vector>
#include <string>

namespace leitor {

// Simple image loader for JPEG/PNG
// Returns raw pixel data (RGBA)
bool load_image_from_memory(const std::vector<unsigned char>& data,
                            std::vector<unsigned char>& pixels,
                            int& width, int& height, int& channels);

// Decode base64 string to bytes
std::vector<unsigned char> base64_decode(const std::string& encoded);

} // namespace leitor
