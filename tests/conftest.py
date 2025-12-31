"""
Pytest configuration and fixtures for Leitor de Simulados tests
"""
import pytest
import sys
from pathlib import Path
from io import BytesIO

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import cv2


@pytest.fixture
def sample_image_bytes():
    """Create a simple test image as bytes"""
    # Create a simple 100x100 white image with some shapes
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    
    # Draw some test shapes
    cv2.rectangle(img, (10, 10), (30, 30), (0, 0, 0), -1)  # Black square
    cv2.circle(img, (60, 60), 15, (128, 128, 128), -1)  # Gray circle
    
    # Encode to JPEG bytes
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()


@pytest.fixture
def sample_image_bytes_large():
    """Create a larger test image similar to real exam sheets"""
    # Create a 800x1100 white image (approximate A4 ratio)
    img = np.ones((1100, 800, 3), dtype=np.uint8) * 255
    
    # Draw some mock "bubbles" in a grid
    for row in range(10):
        for col in range(5):
            x = 100 + col * 60
            y = 200 + row * 80
            cv2.circle(img, (x, y), 10, (0, 0, 0), 1)
    
    # Draw a header area
    cv2.rectangle(img, (50, 50), (750, 150), (200, 200, 200), -1)
    
    _, buffer = cv2.imencode('.jpg', img)
    return buffer.tobytes()


@pytest.fixture
def temp_image_file(tmp_path, sample_image_bytes):
    """Create a temporary image file"""
    img_path = tmp_path / "test_image.jpg"
    img_path.write_bytes(sample_image_bytes)
    return img_path


@pytest.fixture
def temp_image_files(tmp_path, sample_image_bytes):
    """Create multiple temporary image files"""
    paths = []
    for i in range(3):
        img_path = tmp_path / f"test_image_{i}.jpg"
        img_path.write_bytes(sample_image_bytes)
        paths.append(img_path)
    return paths
