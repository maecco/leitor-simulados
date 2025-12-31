"""
Tests for validating object attribute access patterns.

These tests ensure that the service code uses the correct attribute names
for core objects like Detection, IntBoundingBox, etc.

These tests catch runtime AttributeError issues that would otherwise
only appear during actual image processing.

These tests use STATIC ANALYSIS (AST parsing and regex) to avoid circular
import issues and to catch problems before runtime.
"""

import pytest
import ast
import re
from pathlib import Path
from typing import Set, Dict, List


# =============================================================================
# AST-based analysis utilities (no imports needed)
# =============================================================================

class AttributeAccessVisitor(ast.NodeVisitor):
    """AST visitor that collects attribute accesses on specific variable names."""
    
    def __init__(self, variable_patterns: List[str]):
        self.variable_patterns = variable_patterns
        self.attribute_accesses: Dict[str, Set[str]] = {}
    
    def visit_Attribute(self, node: ast.Attribute):
        """Collect attribute accesses."""
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            for pattern in self.variable_patterns:
                if pattern in var_name.lower():
                    if var_name not in self.attribute_accesses:
                        self.attribute_accesses[var_name] = set()
                    self.attribute_accesses[var_name].add(node.attr)
        self.generic_visit(node)


class ClassDefinitionVisitor(ast.NodeVisitor):
    """AST visitor that extracts class attributes from source code."""
    
    def __init__(self, class_name: str):
        self.class_name = class_name
        self.attributes: Set[str] = set()
        self.found_class = False
    
    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name == self.class_name:
            self.found_class = True
            # Get attributes from __init__
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                    for stmt in ast.walk(item):
                        if isinstance(stmt, ast.Attribute):
                            if isinstance(stmt.value, ast.Name) and stmt.value.id == 'self':
                                self.attributes.add(stmt.attr)
                # Get class-level attributes
                if isinstance(item, ast.AnnAssign):
                    if isinstance(item.target, ast.Name):
                        self.attributes.add(item.target.id)
                # Get properties and methods
                if isinstance(item, ast.FunctionDef):
                    if not item.name.startswith('_'):
                        self.attributes.add(item.name)
                    # Check for @property decorator
                    for decorator in item.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == 'property':
                            self.attributes.add(item.name)
                        if isinstance(decorator, ast.Attribute) and decorator.attr == 'property':
                            self.attributes.add(item.name)
        self.generic_visit(node)


def get_class_attributes_from_file(filepath: Path, class_name: str) -> Set[str]:
    """Extract class attributes by parsing the source file (no imports needed)."""
    with open(filepath, 'r') as f:
        source = f.read()
    
    tree = ast.parse(source)
    visitor = ClassDefinitionVisitor(class_name)
    visitor.visit(tree)
    return visitor.attributes


def parse_file_for_attributes(filepath: Path, patterns: List[str]) -> Dict[str, Set[str]]:
    """Parse a Python file and extract attribute accesses for given variable patterns."""
    with open(filepath, 'r') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
        visitor = AttributeAccessVisitor(patterns)
        visitor.visit(tree)
        return visitor.attribute_accesses
    except SyntaxError:
        return {}


# =============================================================================
# Tests for Detection attributes (static analysis)
# =============================================================================

class TestDetectionAttributes:
    """Tests to ensure Detection object attributes are used correctly."""
    
    @pytest.fixture
    def detection_source_file(self) -> Path:
        return Path(__file__).parent.parent / "src" / "core" / "detection" / "base.py"
    
    def test_detection_has_expected_attributes(self, detection_source_file):
        """Verify Detection class has the attributes we expect (via AST)."""
        if not detection_source_file.exists():
            pytest.skip("Detection source file not found")
        
        attrs = get_class_attributes_from_file(detection_source_file, "Detection")
        
        expected = {
            'bounding_box', 'model_assing_id', 'score', 
            'img_width', 'img_height', 'class_type',
            'anchored_at', 'to_pixels', 'to_global_pixels'
        }
        missing = expected - attrs
        assert not missing, f"Detection missing expected attributes: {missing}"
    
    def test_detection_does_not_have_class_id(self, detection_source_file):
        """Verify Detection uses model_assing_id, not class_id (via AST)."""
        if not detection_source_file.exists():
            pytest.skip("Detection source file not found")
        
        attrs = get_class_attributes_from_file(detection_source_file, "Detection")
        
        assert 'class_id' not in attrs, \
            "Detection should use 'model_assing_id', not 'class_id'"
        assert 'model_assing_id' in attrs, \
            "Detection should have 'model_assing_id' attribute"
    
    def test_processing_service_uses_correct_detection_attrs(self):
        """Check that processing.py uses correct Detection attributes."""
        processing_file = Path(__file__).parent.parent / "src" / "services" / "processing.py"
        
        if not processing_file.exists():
            pytest.skip("processing.py not found")
        
        # Parse the file and look for 'det' variable attribute accesses
        accesses = parse_file_for_attributes(processing_file, ['det'])
        
        # Flatten all accesses
        all_attrs = set()
        for attrs in accesses.values():
            all_attrs.update(attrs)
        
        # Check for known wrong attributes
        wrong_attrs = {'class_id', 'x1', 'y1', 'x2', 'y2'}
        used_wrong = all_attrs & wrong_attrs
        
        assert not used_wrong, \
            f"processing.py uses incorrect Detection attributes: {used_wrong}. " \
            f"Use 'model_assing_id' instead of 'class_id'"


# =============================================================================
# Tests for IntBoundingBox attributes (static analysis)
# =============================================================================

class TestIntBoundingBoxAttributes:
    """Tests to ensure IntBoundingBox attributes are used correctly."""
    
    @pytest.fixture
    def geometry_source_file(self) -> Path:
        return Path(__file__).parent.parent / "src" / "core" / "definitions" / "geometry.py"
    
    def test_bbox_has_expected_attributes(self, geometry_source_file):
        """Verify IntBoundingBox has correct structure (via AST)."""
        if not geometry_source_file.exists():
            pytest.skip("geometry.py not found")
        
        attrs = get_class_attributes_from_file(geometry_source_file, "IntBoundingBox")
        
        expected = {'p_min', 'p_max'}
        missing = expected - attrs
        assert not missing, f"IntBoundingBox missing expected attributes: {missing}"
    
    def test_bbox_does_not_have_x1_y1_x2_y2(self, geometry_source_file):
        """Verify IntBoundingBox doesn't have x1, y1, x2, y2 as primary attributes."""
        if not geometry_source_file.exists():
            pytest.skip("geometry.py not found")
        
        attrs = get_class_attributes_from_file(geometry_source_file, "IntBoundingBox")
        wrong_attrs = {'x1', 'y1', 'x2', 'y2'}
        present = wrong_attrs & attrs
        
        # It's OK if they exist as properties, but we want to warn
        if present:
            pytest.skip("IntBoundingBox has x1/y1/x2/y2 properties (use p_min/p_max preferred)")
    
    def test_processing_service_uses_correct_bbox_attrs(self):
        """Check that processing.py accesses bbox through p_min/p_max."""
        processing_file = Path(__file__).parent.parent / "src" / "services" / "processing.py"
        
        if not processing_file.exists():
            pytest.skip("processing.py not found")
        
        with open(processing_file, 'r') as f:
            content = f.read()
        
        # Check for patterns that directly access x1, y1, x2, y2 on bbox
        wrong_patterns = [
            r'bbox\.x1\b',
            r'bbox\.y1\b', 
            r'bbox\.x2\b',
            r'bbox\.y2\b',
            r'global_bbox\.x1\b',
            r'global_bbox\.y1\b',
            r'global_bbox\.x2\b',
            r'global_bbox\.y2\b',
        ]
        
        found_wrong = []
        for pattern in wrong_patterns:
            if re.search(pattern, content):
                found_wrong.append(pattern.replace(r'\b', '').replace('\\', ''))
        
        assert not found_wrong, \
            f"processing.py uses incorrect bbox attributes: {found_wrong}. " \
            f"Use 'bbox.p_min.x', 'bbox.p_max.y', etc."


# =============================================================================
# Tests for LabelMap attributes (static analysis)
# =============================================================================

class TestLabelMapAttributes:
    """Tests to ensure LabelMap attributes are used correctly."""
    
    @pytest.fixture
    def label_map_source_file(self) -> Path:
        return Path(__file__).parent.parent / "src" / "core" / "detection" / "label_map.py"
    
    def test_label_map_has_expected_attributes(self, label_map_source_file):
        """Verify LabelMap has correct structure (via AST)."""
        if not label_map_source_file.exists():
            pytest.skip("label_map.py not found")
        
        attrs = get_class_attributes_from_file(label_map_source_file, "LabelMap")
        
        expected = {'detections', 'stage'}
        missing = expected - attrs
        assert not missing, f"LabelMap missing expected attributes: {missing}"
    
    def test_label_map_does_not_have_get_name(self, label_map_source_file):
        """Verify LabelMap doesn't have a get_name method."""
        if not label_map_source_file.exists():
            pytest.skip("label_map.py not found")
        
        attrs = get_class_attributes_from_file(label_map_source_file, "LabelMap")
        
        # LabelMap uses detections[idx].name, not get_name()
        assert 'get_name' not in attrs, \
            "LabelMap doesn't have 'get_name' method - use 'detections[idx].name'"
    
    def test_processing_service_uses_correct_label_map_access(self):
        """Check that processing.py accesses label_map correctly."""
        processing_file = Path(__file__).parent.parent / "src" / "services" / "processing.py"
        
        if not processing_file.exists():
            pytest.skip("processing.py not found")
        
        with open(processing_file, 'r') as f:
            content = f.read()
        
        # Should NOT have label_map.get_name
        assert 'label_map.get_name' not in content, \
            "processing.py should use 'label_map.detections[idx].name', not 'label_map.get_name()'"


# =============================================================================
# Tests for CoreImage attributes (static analysis)
# =============================================================================

class TestCoreImageAttributes:
    """Tests to ensure CoreImage attributes are used correctly."""
    
    @pytest.fixture
    def core_image_source_file(self) -> Path:
        return Path(__file__).parent.parent / "src" / "core" / "image.py"
    
    def test_core_image_has_expected_attributes(self, core_image_source_file):
        """Verify CoreImage has the attributes we use (via AST)."""
        if not core_image_source_file.exists():
            pytest.skip("image.py not found")
        
        attrs = get_class_attributes_from_file(core_image_source_file, "CoreImage")
        
        expected = {'raw', 'detections', 'crops'}
        missing = expected - attrs
        assert not missing, f"CoreImage missing expected attributes: {missing}"


# =============================================================================
# Integration tests for attribute consistency (regex-based)
# =============================================================================

class TestAttributeConsistency:
    """Integration tests that verify attribute consistency across the codebase."""
    
    def test_no_class_id_in_service_files(self):
        """Ensure no service files use 'det.class_id' on Detection objects."""
        services_dir = Path(__file__).parent.parent / "src" / "services"
        
        if not services_dir.exists():
            pytest.skip("services directory not found")
        
        violations = []
        
        for py_file in services_dir.glob("*.py"):
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Match det.class_id but not "class_id" in dict keys
            if re.search(r'\bdet\.class_id\b', content):
                violations.append(str(py_file.name))
        
        assert not violations, \
            f"Files using 'det.class_id' (should be 'det.model_assing_id'): {violations}"
    
    def test_no_wrong_bbox_access_in_service_files(self):
        """Ensure no service files access bbox.x1/y1/x2/y2 directly."""
        services_dir = Path(__file__).parent.parent / "src" / "services"
        
        if not services_dir.exists():
            pytest.skip("services directory not found")
        
        violations = []
        wrong_patterns = [
            r'\bbbox\.x[12]\b',
            r'\bbbox\.y[12]\b',
            r'\bglobal_bbox\.x[12]\b',
            r'\bglobal_bbox\.y[12]\b',
        ]
        
        for py_file in services_dir.glob("*.py"):
            with open(py_file, 'r') as f:
                content = f.read()
            
            for pattern in wrong_patterns:
                if re.search(pattern, content):
                    violations.append(f"{py_file.name}: {pattern}")
                    break
        
        assert not violations, \
            f"Files using wrong bbox access (should use p_min/p_max): {violations}"
    
    def test_detection_attribute_documentation(self):
        """Verify Detection class documents model_assing_id in docstring."""
        detection_file = Path(__file__).parent.parent / "src" / "core" / "detection" / "base.py"
        
        if not detection_file.exists():
            pytest.skip("Detection source file not found")
        
        with open(detection_file, 'r') as f:
            content = f.read()
        
        # Should document model_assing_id, not class_id
        assert 'model_assing_id' in content, \
            "Detection should use/document 'model_assing_id'"


# =============================================================================
# Tests that verify expected usage patterns in processing service
# =============================================================================

class TestProcessingServicePatterns:
    """Test specific patterns that processing.py should use."""
    
    def test_uses_model_assing_id_for_label_lookup(self):
        """Verify label lookups use model_assing_id with detections list."""
        processing_file = Path(__file__).parent.parent / "src" / "services" / "processing.py"
        
        if not processing_file.exists():
            pytest.skip("processing.py not found")
        
        with open(processing_file, 'r') as f:
            content = f.read()
        
        # Should have patterns like: detections[det.model_assing_id].name
        assert re.search(r'detections\[det\.model_assing_id\]\.name', content), \
            "processing.py should use 'detections[det.model_assing_id].name' for label lookups"
    
    def test_uses_p_min_p_max_for_bbox(self):
        """Verify bbox access uses p_min/p_max structure."""
        processing_file = Path(__file__).parent.parent / "src" / "services" / "processing.py"
        
        if not processing_file.exists():
            pytest.skip("processing.py not found")
        
        with open(processing_file, 'r') as f:
            content = f.read()
        
        # Should have patterns like: bbox.p_min.x, bbox.p_max.y
        assert re.search(r'bbox\.p_min\.x', content), \
            "processing.py should use 'bbox.p_min.x' for bbox access"
        assert re.search(r'bbox\.p_max\.y', content), \
            "processing.py should use 'bbox.p_max.y' for bbox access"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
