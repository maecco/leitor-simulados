import sys
import threading
import time
import warnings
import weakref
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum, auto
from functools import wraps


class MemoryCategory(Enum):
    """Categories of memory allocations for tracking purposes."""
    CORE_IMAGE = auto()         # CoreImage raw numpy arrays
    CORE_IMAGE_CROP = auto()    # Cropped images from CoreImage
    GUI_DISPLAY = auto()        # Display images in GUI (cv2 resized)
    GUI_PHOTOIMAGE = auto()     # PhotoImage objects in Tkinter
    CACHE = auto()              # Cached data structures
    DETECTION = auto()          # Detection-related data
    OTHER = auto()              # Miscellaneous allocations


@dataclass
class MemoryAllocation:
    """Represents a single memory allocation event."""
    category: MemoryCategory
    size_bytes: int
    timestamp: float
    source: str              # Source location (file:line or description)
    object_id: int           # id() of the allocated object
    object_type: str         # Type name of the object
    description: str = ""    # Optional description
    deallocated: bool = False
    dealloc_timestamp: Optional[float] = None


@dataclass
class MemorySnapshot:
    """A snapshot of memory state at a point in time."""
    timestamp: float
    total_allocated: int
    total_deallocated: int
    active_allocations: int
    by_category: Dict[MemoryCategory, int] = field(default_factory=dict)


class MemoryTracker:
    """
    A singleton class for tracking memory allocations and deallocations.
    
    This tracker is designed to monitor image-related memory usage in both
    the GUI and core processing components of the application.
    
    Usage:
        # Enable tracking
        MemoryTracker.enable()
        
        # Track an allocation
        MemoryTracker.track_allocation(
            obj=image_array,
            category=MemoryCategory.CORE_IMAGE,
            source="core/image.py:45",
            description="Loading image from disk"
        )
        
        # Track deallocation
        MemoryTracker.track_deallocation(obj)
        
        # Get current stats
        stats = MemoryTracker.get_stats()
        
        # Print report
        MemoryTracker.print_report()
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._enabled = False
        self._allocations: Dict[int, MemoryAllocation] = {}
        self._history: List[MemoryAllocation] = []
        self._snapshots: List[MemorySnapshot] = []
        self._weak_refs: Dict[int, weakref.ref] = {}
        self._callbacks: List[Callable[[MemoryAllocation, bool], None]] = []
        self._auto_snapshot_interval: Optional[float] = None
        self._last_snapshot_time: float = 0
        self._total_allocated: int = 0
        self._total_deallocated: int = 0
        self._print_on_track: bool = False
        self._track_lock = threading.Lock()
    
    @classmethod
    def get_instance(cls) -> 'MemoryTracker':
        """Get the singleton instance."""
        return cls()
    
    @classmethod
    def enable(cls, print_on_track: bool = False):
        """Enable memory tracking."""
        instance = cls.get_instance()
        instance._enabled = True
        instance._print_on_track = print_on_track
        print("[MemoryTracker] Memory tracking ENABLED")
    
    @classmethod
    def disable(cls):
        """Disable memory tracking."""
        instance = cls.get_instance()
        instance._enabled = False
        print("[MemoryTracker] Memory tracking DISABLED")
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if tracking is enabled."""
        return cls.get_instance()._enabled
    
    @classmethod
    def reset(cls):
        """Reset all tracking data."""
        instance = cls.get_instance()
        with instance._track_lock:
            instance._allocations.clear()
            instance._history.clear()
            instance._snapshots.clear()
            instance._weak_refs.clear()
            instance._total_allocated = 0
            instance._total_deallocated = 0
        print("[MemoryTracker] Tracking data RESET")
    
    @classmethod
    def track_allocation(
        cls,
        obj: Any,
        category: MemoryCategory,
        source: str = "",
        description: str = ""
    ) -> Optional[MemoryAllocation]:
        """
        Track a memory allocation.
        
        Parameters
        ----------
        obj : Any
            The allocated object (typically a numpy array or PIL Image).
        category : MemoryCategory
            The category of the allocation.
        source : str
            Source location or identifier.
        description : str
            Optional description of the allocation.
            
        Returns
        -------
        Optional[MemoryAllocation]
            The allocation record, or None if tracking is disabled.
        """
        instance = cls.get_instance()
        if not instance._enabled:
            return None
        
        obj_id = id(obj)
        size = cls._get_object_size(obj)
        
        allocation = MemoryAllocation(
            category=category,
            size_bytes=size,
            timestamp=time.time(),
            source=source,
            object_id=obj_id,
            object_type=type(obj).__name__,
            description=description
        )
        
        with instance._track_lock:
            instance._allocations[obj_id] = allocation
            instance._history.append(allocation)
            instance._total_allocated += size
            
            # Create weak reference for automatic deallocation tracking
            try:
                def on_delete(ref, alloc=allocation):
                    cls._on_object_deleted(alloc)
                instance._weak_refs[obj_id] = weakref.ref(obj, on_delete)
            except TypeError:
                # Object doesn't support weak references
                pass
        
        if instance._print_on_track:
            cls._print_allocation(allocation, is_alloc=True)
        
        # Call registered callbacks
        for callback in instance._callbacks:
            try:
                callback(allocation, True)
            except Exception as e:
                warnings.warn(
                    f"[MemoryTracker] Callback {callback.__name__} failed: {e}",
                    RuntimeWarning
                )
        
        return allocation
    
    @classmethod
    def track_deallocation(cls, obj: Any) -> bool:
        """
        Track the deallocation of an object.
        
        Parameters
        ----------
        obj : Any
            The object being deallocated.
            
        Returns
        -------
        bool
            True if the object was being tracked, False otherwise.
        """
        instance = cls.get_instance()
        if not instance._enabled:
            return False
        
        obj_id = id(obj)
        
        with instance._track_lock:
            if obj_id not in instance._allocations:
                return False
            
            allocation = instance._allocations[obj_id]
            allocation.deallocated = True
            allocation.dealloc_timestamp = time.time()
            instance._total_deallocated += allocation.size_bytes
            
            del instance._allocations[obj_id]
            if obj_id in instance._weak_refs:
                del instance._weak_refs[obj_id]
        
        if instance._print_on_track:
            cls._print_allocation(allocation, is_alloc=False)
        
        # Call registered callbacks
        for callback in instance._callbacks:
            try:
                callback(allocation, False)
            except Exception as e:
                warnings.warn(
                    f"[MemoryTracker] Callback {callback.__name__} failed: {e}",
                    RuntimeWarning
                )
        
        return True
    
    @classmethod
    def _on_object_deleted(cls, allocation: MemoryAllocation):
        """Called when a tracked object is garbage collected."""
        instance = cls.get_instance()
        if not instance._enabled:
            return
        
        with instance._track_lock:
            if allocation.object_id in instance._allocations:
                allocation.deallocated = True
                allocation.dealloc_timestamp = time.time()
                instance._total_deallocated += allocation.size_bytes
                del instance._allocations[allocation.object_id]
                if allocation.object_id in instance._weak_refs:
                    del instance._weak_refs[allocation.object_id]
        
        if instance._print_on_track:
            cls._print_allocation(allocation, is_alloc=False, auto=True)
    
    @classmethod
    def _get_object_size(cls, obj: Any) -> int:
        """Get the memory size of an object in bytes."""
        # Handle numpy arrays
        if hasattr(obj, 'nbytes'):
            return obj.nbytes
        
        # Handle PIL Images
        if hasattr(obj, 'size') and hasattr(obj, 'mode'):
            try:
                width, height = obj.size
                mode = obj.mode
                # Estimate bytes per pixel based on mode
                bpp = {'1': 1, 'L': 1, 'P': 1, 'RGB': 3, 'RGBA': 4, 
                       'CMYK': 4, 'YCbCr': 3, 'LAB': 3, 'HSV': 3,
                       'I': 4, 'F': 4}.get(mode, 3)
                return width * height * bpp
            except Exception:
                pass
        
        # Fallback to sys.getsizeof
        return sys.getsizeof(obj)
    
    @classmethod
    def _print_allocation(cls, alloc: MemoryAllocation, is_alloc: bool, auto: bool = False):
        """Print an allocation/deallocation event."""
        action = "ALLOC" if is_alloc else ("AUTO-DEALLOC" if auto else "DEALLOC")
        size_mb = alloc.size_bytes / (1024 * 1024)
        print(
            f"[MemoryTracker] {action:12} | "
            f"{alloc.category.name:18} | "
            f"{size_mb:8.2f} MB | "
            f"{alloc.object_type:20} | "
            f"{alloc.source}"
        )
        if alloc.description:
            print(f"               └─ {alloc.description}")
    
    @classmethod
    def take_snapshot(cls) -> MemorySnapshot:
        """Take a snapshot of current memory state."""
        instance = cls.get_instance()
        
        by_category: Dict[MemoryCategory, int] = {}
        total_active = 0
        
        with instance._track_lock:
            for alloc in instance._allocations.values():
                total_active += alloc.size_bytes
                by_category[alloc.category] = by_category.get(alloc.category, 0) + alloc.size_bytes
        
        snapshot = MemorySnapshot(
            timestamp=time.time(),
            total_allocated=instance._total_allocated,
            total_deallocated=instance._total_deallocated,
            active_allocations=len(instance._allocations),
            by_category=by_category
        )
        
        with instance._track_lock:
            instance._snapshots.append(snapshot)
        
        return snapshot
    
    @classmethod
    def get_stats(cls) -> dict:
        """Get current memory statistics."""
        instance = cls.get_instance()
        
        with instance._track_lock:
            by_category: Dict[str, dict] = {}
            for alloc in instance._allocations.values():
                cat_name = alloc.category.name
                if cat_name not in by_category:
                    by_category[cat_name] = {"count": 0, "bytes": 0}
                by_category[cat_name]["count"] += 1
                by_category[cat_name]["bytes"] += alloc.size_bytes
            
            return {
                "enabled": instance._enabled,
                "total_allocated_bytes": instance._total_allocated,
                "total_deallocated_bytes": instance._total_deallocated,
                "active_allocations_count": len(instance._allocations),
                "active_allocations_bytes": sum(a.size_bytes for a in instance._allocations.values()),
                "by_category": by_category,
                "history_count": len(instance._history)
            }
    
    @classmethod
    def get_active_allocations(cls, category: Optional[MemoryCategory] = None) -> List[MemoryAllocation]:
        """Get list of active (non-deallocated) allocations."""
        instance = cls.get_instance()
        
        with instance._track_lock:
            allocs = list(instance._allocations.values())
        
        if category:
            allocs = [a for a in allocs if a.category == category]
        
        return allocs
    
    @classmethod
    def print_report(cls, detailed: bool = False):
        """Print a formatted memory report."""
        stats = cls.get_stats()
        
        print("\n" + "=" * 70)
        print("                    MEMORY TRACKING REPORT")
        print("=" * 70)
        
        total_alloc_mb = stats["total_allocated_bytes"] / (1024 * 1024)
        total_dealloc_mb = stats["total_deallocated_bytes"] / (1024 * 1024)
        active_mb = stats["active_allocations_bytes"] / (1024 * 1024)
        
        print(f"\n{'Status:':<25} {'ENABLED' if stats['enabled'] else 'DISABLED'}")
        print(f"{'Total Allocated:':<25} {total_alloc_mb:>10.2f} MB")
        print(f"{'Total Deallocated:':<25} {total_dealloc_mb:>10.2f} MB")
        print(f"{'Currently Active:':<25} {active_mb:>10.2f} MB ({stats['active_allocations_count']} objects)")
        
        if stats["by_category"]:
            print("\n" + "-" * 50)
            print("By Category:")
            print("-" * 50)
            for cat_name, cat_stats in sorted(stats["by_category"].items()):
                cat_mb = cat_stats["bytes"] / (1024 * 1024)
                print(f"  {cat_name:<20} {cat_mb:>8.2f} MB  ({cat_stats['count']} objects)")
        
        if detailed:
            instance = cls.get_instance()
            print("\n" + "-" * 50)
            print("Active Allocations Detail:")
            print("-" * 50)
            with instance._track_lock:
                for alloc in sorted(instance._allocations.values(), 
                                   key=lambda a: a.size_bytes, reverse=True)[:20]:
                    size_mb = alloc.size_bytes / (1024 * 1024)
                    print(f"  [{alloc.category.name:18}] {size_mb:>8.2f} MB - {alloc.object_type} @ {alloc.source}")
                    if alloc.description:
                        print(f"     └─ {alloc.description}")
        
        print("\n" + "=" * 70 + "\n")
    
    @classmethod
    def register_callback(cls, callback: Callable[[MemoryAllocation, bool], None]):
        """Register a callback for allocation/deallocation events."""
        instance = cls.get_instance()
        instance._callbacks.append(callback)
    
    @classmethod
    def unregister_callback(cls, callback: Callable[[MemoryAllocation, bool], None]):
        """Unregister a callback."""
        instance = cls.get_instance()
        if callback in instance._callbacks:
            instance._callbacks.remove(callback)


def track_image_memory(category: MemoryCategory, description: str = ""):
    """
    Decorator to automatically track memory for functions that return images.
    
    Usage:
        @track_image_memory(MemoryCategory.CORE_IMAGE, "Loading from disk")
        def load_image(path):
            return cv2.imread(path)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result is not None and MemoryTracker.is_enabled():
                source = f"{func.__module__}.{func.__name__}"
                MemoryTracker.track_allocation(
                    result, category, source, description
                )
            return result
        return wrapper
    return decorator


class cache_readonly_property:
    """
    A decorator-based descriptor for creating cached read-only properties.

    This class allows for the caching of computed properties in an instance's 
    dictionary upon first access, preventing redundant calculations. The property 
    is read-only, and attempts to modify it will raise an AttributeError.

    Attributes
    ----------
    func : function
        The function used to compute the property's value.
    name : str
        The name of the property.

    Methods
    -------
    __get__(instance, owner)
        Retrieves the cached value of the property, computing and storing it if necessary.
    __set__(instance, value)
        Raises an AttributeError since the property is read-only.
    invalidate(instance)
        Removes the cached value from the instance's dictionary.
    """

    def __init__(self, func):
        """
        Initializes the descriptor with the provided function.

        Parameters
        ----------
        func : function
            The function used to compute the property's value.
        """
        self.func = func
        self.name = func.__name__

    def __get__(self, instance, owner):
        """
        Retrieves the cached property value, computing and storing it if necessary.

        Parameters
        ----------
        instance : object
            The instance on which the property is accessed.
        owner : type
            The class of the instance.

        Returns
        -------
        Any
            The computed and cached property value.
        """
        if instance is None:
            return self
        value = self.func(instance)
        instance.__dict__[self.name] = value

        # Update the tracking list in the instance
        if not hasattr(instance, "_cached_properties"):
            instance._cached_properties = [self]
        else:
            instance._cached_properties.append(self)

        return value

    def __set__(self, instance, value):
        """
        Prevents modification of the cached property.

        Parameters
        ----------
        instance : object
            The instance on which the property is accessed.
        value : Any
            The value being assigned.

        Raises
        ------
        AttributeError
            If an attempt is made to modify the property.
        """
        raise AttributeError(f"{self.name} is a read-only property")

    def invalidate(self, instance):
        """
        Deletes the cached property value from the instance.

        Parameters
        ----------
        instance : object
            The instance whose cached property should be invalidated.
        """
        del instance.__dict__[self.name]