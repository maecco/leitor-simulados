#include "image_loader.h"
#include <cstring>
#include <stdexcept>

#ifdef HAS_STB_IMAGE
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_ONLY_PNG
#include "stb_image.h"
#endif

namespace {

// Base64 decoding table
static const unsigned char base64_decode_table[256] = {
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 62, 64, 64, 64, 63,
    52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 64, 64, 64, 64, 64, 64,
    64,  0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14,
    15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 64, 64, 64, 64, 64,
    64, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
    41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64,
    64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64, 64
};

} // anonymous namespace

namespace leitor {

std::vector<unsigned char> base64_decode(const std::string& encoded) {
    size_t in_len = encoded.size();
    if (in_len % 4 != 0) {
        throw std::runtime_error("Invalid base64 length");
    }
    
    size_t out_len = in_len / 4 * 3;
    if (in_len > 0 && encoded[in_len - 1] == '=') out_len--;
    if (in_len > 1 && encoded[in_len - 2] == '=') out_len--;
    
    std::vector<unsigned char> decoded(out_len);
    
    size_t j = 0;
    for (size_t i = 0; i < in_len;) {
        uint32_t a = encoded[i] == '=' ? 0 : base64_decode_table[(unsigned char)encoded[i]]; i++;
        uint32_t b = encoded[i] == '=' ? 0 : base64_decode_table[(unsigned char)encoded[i]]; i++;
        uint32_t c = encoded[i] == '=' ? 0 : base64_decode_table[(unsigned char)encoded[i]]; i++;
        uint32_t d = encoded[i] == '=' ? 0 : base64_decode_table[(unsigned char)encoded[i]]; i++;
        
        uint32_t triple = (a << 18) + (b << 12) + (c << 6) + d;
        
        if (j < out_len) decoded[j++] = (triple >> 16) & 0xFF;
        if (j < out_len) decoded[j++] = (triple >> 8) & 0xFF;
        if (j < out_len) decoded[j++] = triple & 0xFF;
    }
    
    return decoded;
}

#ifdef HAS_STB_IMAGE
bool load_image_from_memory(const std::vector<unsigned char>& data,
                            std::vector<unsigned char>& pixels,
                            int& width, int& height, int& channels) {
    unsigned char* img = stbi_load_from_memory(
        data.data(), (int)data.size(), &width, &height, &channels, 4
    );
    
    if (!img) {
        return false;
    }
    
    pixels.assign(img, img + (width * height * 4));
    stbi_image_free(img);
    channels = 4;  // Always convert to RGBA
    return true;
}
#else
// Placeholder - returns false (image loading disabled)
bool load_image_from_memory(const std::vector<unsigned char>& data,
                            std::vector<unsigned char>& pixels,
                            int& width, int& height, int& channels) {
    (void)data; (void)pixels; (void)width; (void)height; (void)channels;
    // To enable: download stb_image.h and define HAS_STB_IMAGE
    return false;
}
#endif

} // namespace leitor
