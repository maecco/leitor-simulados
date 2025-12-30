#include "app.h"
#include <iostream>

int main(int argc, char** argv) {
    std::cout << "==================================================" << std::endl;
    std::cout << "  📝 Leitor de Simulados - C++ Client" << std::endl;
    std::cout << "==================================================" << std::endl;
    
    leitor::Application app;
    
    if (!app.initialize(argc, argv)) {
        std::cerr << "Failed to initialize application" << std::endl;
        return 1;
    }
    
    app.run();
    app.shutdown();
    
    return 0;
}
