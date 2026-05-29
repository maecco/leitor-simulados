__all__ = ["Axis", "Line", "IntPoint", "FloatPoint", "FloatBoundingBox", "IntBoundingBox"]

from dataclasses import dataclass, field
from enum import Enum



# SECTION: Other

class Axis(Enum):
    NULL = -1
    VERTICAL = 0
    HORIZONTAL = 1
    BOTH = 2

    @property
    def counterAxis(self):
        if self == Axis.NULL or self == Axis.BOTH:
            return Axis.NULL
        else:
            return Axis.HORIZONTAL if self == Axis.VERTICAL else Axis.VERTICAL


@dataclass
class Line:
    """Represents a line segment with two endpoints (x1, y1) and (x2, y2)."""
    x1: int = 0
    y1: int = 0
    x2: int = 0
    y2: int = 0

    @classmethod
    def from_list(cls, coords: list[int]) -> Line:
        """Create a Line from a list of coordinates [x1, y1, x2, y2]."""
        if len(coords) != 4:
            raise ValueError("Expected 4 coordinates [x1, y1, x2, y2]")
        return cls(coords[0], coords[1], coords[2], coords[3])

    def __post_init__(self):
        # Support legacy initialization with list
        pass

    def __getitem__(self, index: int) -> int:
        if index == 0:   return self.x1
        elif index == 1: return self.y1
        elif index == 2: return self.x2
        elif index == 3: return self.y2
        else: raise IndexError("Index out of range")

    def __setitem__(self, index: int, value: int) -> None:
        if index == 0:   self.x1 = value
        elif index == 1: self.y1 = value
        elif index == 2: self.x2 = value
        elif index == 3: self.y2 = value
        else: raise IndexError("Index out of range")

    def __iter__(self):
        return iter((self.x1, self.y1, self.x2, self.y2))

    def __repr__(self):
        return f"Line({self.x1}, {self.y1}, {self.x2}, {self.y2})"



# SECTION: Points

@dataclass
class IntPoint():
    x: int = field(default=0)
    y: int = field(default=0)

    def __iter__(self):
        return iter((self.x, self.y))
    
    def __eq__(self, value):
        return self.x == value.x and self.y == value.y


@dataclass
class FloatPoint():
    x: float = field(default=0)
    y: float = field(default=0)

    def __iter__(self):
        return iter((self.x, self.y))
    
    def __eq__(self, value):
        return self.x == value.x and self.y == value.y



# SECTION: Bounding Boxes

@dataclass
class FloatBoundingBox():
    p_min: FloatPoint = field(default_factory=FloatPoint)
    p_max: FloatPoint = field(default_factory=FloatPoint)

    #Constructors
    @classmethod
    def from_floats(cls, x_min, y_min, x_max, y_max):
        return cls(
            p_min = FloatPoint(x_min, y_min),
            p_max = FloatPoint(x_max, y_max),
        )
    @classmethod
    def from_yolo(cls, x_center, y_center, width, height):
        x_min = x_center - width / 2
        y_min = y_center - height / 2
        x_max = x_center + width / 2
        y_max = y_center + height / 2
        return cls.from_floats(x_min, y_min, x_max, y_max)

    def __getitem__(self, index):
        if index == 0:   return self.p_min.x
        elif index == 1: return self.p_min.y
        elif index == 2: return self.p_max.x
        elif index == 3: return self.p_max.y
        else: raise IndexError("Index out of range")

    def __iter__(self):
        return iter((*self.p_min, *self.p_max))
    
    def __eq__(self, value):
        return self.p_min == value.p_min and self.p_max == value.p_max
    
    def __hash__(self):
        return hash((*self.p_min, *self.p_max))


@dataclass
class IntBoundingBox():
    p_min: IntPoint = field(default_factory=IntPoint)
    p_max: IntPoint = field(default_factory=IntPoint)

    #Constructors
    @classmethod
    def from_ints(cls, x_min, y_min, x_max, y_max):
        return cls(
            p_min = IntPoint(x_min, y_min),
            p_max = IntPoint(x_max, y_max),
        )

    def __getitem__(self, index):
        if index == 0:   return self.p_min.x
        elif index == 1: return self.p_min.y
        elif index == 2: return self.p_max.x
        elif index == 3: return self.p_max.y
        else: raise IndexError("Index out of range")

    def __iter__(self):
        return iter((*self.p_min, *self.p_max))
    
    def __eq__(self, value):
        return self.p_min == value.p_min and self.p_max == value.p_max
    
    def __hash__(self):
        return hash((*self.p_min, *self.p_max))
