import tkinter as tk
from tkinter import ttk, filedialog
import threading
from pathlib import Path

from gui import Config, semititle_font
from api.sync_channel import ProgressTracker
from utils.memory import MemoryTracker, MemoryCategory

class TimeBombPopup(tk.Toplevel):
    """
    A temporary popup window that auto-closes after a set timer.

    Parameters
    ----------
    root : tk.Tk
        The root application window.
    parent : tk.Widget
        The parent widget that created this popup.
    title : str
        Title of the popup window.
    message : str
        Message to display in the popup.
    timer : int, optional
        Time (in seconds) before the popup auto-closes (default is 3 seconds).
    destroy_parent : bool, optional
        Whether to destroy the parent widget upon closing (default is False).
    """
    def __init__(self, root, parent, title, message, timer=3, destroy_parent=False):
        super().__init__(root)
        self.title(title)
        self.destroy_parent = destroy_parent
        self.timer = timer
        self.parent = parent
        self.root = root
        self.geometry("200x100")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text=message).pack(pady=10)
        tk.Button(self, text="OK", command=self.destroy).pack(pady=10)
        self.after(timer * 1000, self.destroy)

    def destroy(self):
        """Closes the popup and optionally destroys the parent widget."""
        super().destroy()
        if self.destroy_parent:
            self.parent.destroy()


class ExportYoloPopup(tk.Toplevel):
    """
    A popup window to configure and export YOLO-formatted data.

    Parameters
    ----------
    root : tk.Tk
        The root application window.
    """
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.title("Export YOLO")
        self.geometry("350x200")
        self.resizable(False, False)
        self.transient(root)
        self.grab_set()
        
        tk.Label(self, text="Select destination folder:", font=semititle_font).grid(row=0, column=0, columnspan=2, pady=5)
        
        self.base_folder_var = tk.StringVar(value="No folder selected")
        self.folder_label = tk.Label(self, textvariable=self.base_folder_var)
        self.folder_label.grid(row=1, column=0, columnspan=2, pady=5)
        
        tk.Button(self, text="Browse", command=self.select_base_folder).grid(row=2, column=0, pady=5, padx=5)
        
        self.config_frame = tk.Frame(self)
        self.config_frame.grid(row=2, column=1, pady=5, padx=5)
        self.save_images_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.config_frame, text="Save images", variable=self.save_images_var).pack()
        self.global_anchoring_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.config_frame, text="Global reference", variable=self.global_anchoring_var).pack()
        
        tk.Label(self, text="Folder name:", font=semititle_font).grid(row=3, column=0, pady=5, padx=5)
        self.folder_name_var = tk.StringVar(value="detections")
        tk.Entry(self, textvariable=self.folder_name_var).grid(row=3, column=1, pady=5, padx=5)
        
        tk.Button(self, text="Export", command=self.export_yolo, width=25).grid(row=4, columnspan=2, column=0, pady=5)

    def select_base_folder(self):
        """Opens a file dialog to select the base folder for export."""
        base_folder = filedialog.askdirectory()
        self.base_folder_var.set(base_folder or "No folder selected")

    def export_yolo(self):
        """Exports data in YOLO format to the selected directory."""
        base_folder = self.base_folder_var.get()
        if base_folder == "No folder selected":
            return
        folder_name = self.folder_name_var.get()
        save_images = self.save_images_var.get()
        ref = self.global_anchoring_var.get()
        fullpath = Path(base_folder) / folder_name
        success = Config.api.export_yolo(fullpath, save_images, ref)
        
        title = "Success" if success else "Error"
        message = "Exported successfully!" if success else "Error exporting data"
        TimeBombPopup(self.root, self, title, message, destroy_parent=success)


class SaveAsPopup(tk.Toplevel):
    """
    A popup window for selecting a file format and saving a report.

    Parameters
    ----------
    root : tk.Tk
        The root application window.
    """
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.title("Choose Save Format")
        self.geometry("300x150")
        self.transient(root)
        self.grab_set()
        
        tk.Label(self, text="Select File Format:").pack(pady=5)
        
        self.formats_dict = Config.api.get_report_output_formats()
        formats = list(self.formats_dict.keys())
        
        self.format_type_var = tk.StringVar(value=formats[0])
        format_menu = ttk.Combobox(self, textvariable=self.format_type_var, values=formats, state="readonly")
        format_menu.pack(pady=5)
        
        tk.Button(self, text="Browse", command=self.save_as).pack(pady=10)

    def save_as(self):
        """Opens a file dialog and saves the report in the selected format."""
        exporter_name = self.format_type_var.get()
        format_ext = self.formats_dict[exporter_name]
        filetypes = [(exporter_name, '*' + format_ext.value)]
        fullpath = filedialog.asksaveasfilename(defaultextension="", filetypes=filetypes)
        
        if fullpath:
            try:
                Config.api.save_report(fullpath, exporter_name)
                TimeBombPopup(self.root, self, "Success", "Report saved successfully!", destroy_parent=True)
            except Exception as e:
                TimeBombPopup(self.root, self, "Error", str(e), destroy_parent=False)
                raise e

class ProgressPopup(tk.Toplevel):
    """
    A popup window displaying a progress bar for long-running tasks.

    Parameters
    ----------
    root : tk.Tk
        The root application window.
    thread_function : callable
        The function to execute in a separate thread.
    thread_args : list
        Arguments to pass to the thread function.
    """
    def __init__(
            self,
            root,
            thread_function,
            thread_args,
            progress_tracker,
            img_files
        ):
        super().__init__(root)
        self.root = root
        self.title("Applying Pipeline")
        self.geometry("300x100")
        self.resizable(False, False)
        self.transient(self.root)
        self.grab_set()
        
        self.__init_widgets()
        
        self.names = [Path(img_file).name for img_file in img_files]
        self.float_interval = 100 / len(self.names)
        self.progress_tracker : ProgressTracker = progress_tracker
        self.protocol("WM_DELETE_WINDOW", self.__on_close)
        
        # Start the worker and waching thread
        self.thread = threading.Thread(
            target=thread_function, args=thread_args, daemon=True
        )
        self.waching_thread = threading.Thread(
            target=self.__update_progress, daemon=True
        )
        self.thread.start()
        self.waching_thread.start()


    def __init_widgets(self):
        """Initializes the widgets in the popup window."""
        self.label = tk.Label(self, text="Applying pipeline...")
        self.label.pack(pady=10)
        
        self.progress_label = tk.Label(self, text="0%")
        self.progress_label.pack()
        
        self.progress = ttk.Progressbar(
            self, orient="horizontal", length=300, mode="determinate"
        )
        self.progress.pack()

    def __update_progress(self):
        """Updates the progress bar safely from the main thread."""
        
        while True:
            # get_step() is a blocking call
            step = self.progress_tracker.get_step()

            if not self.progress_tracker.running():
                break
            elif self.progress_tracker.is_finished():
                self.progress["value"] = 100.0
                self.progress_label["text"] = "100%"
                self.label["text"] = "Completed!"
                break

            value = self.float_interval * step
            name = self.names[step]

            self.progress["value"] = value
            self.progress_label["text"] = f"{value:.2f}%"
            self.label["text"] = name


    def __on_close(self):
        """Handles the popup closing event."""
        self.progress_tracker.shutdown()
        self.destroy()


class MemoryTrackerPopup(tk.Toplevel):
    """
    A popup window displaying memory tracking statistics.

    Parameters
    ----------
    root : tk.Tk
        The root application window.
    """
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.title("Memory Tracker")
        self.geometry("600x500")
        self.resizable(True, True)
        # Note: Not using transient() or grab_set() to allow interaction with main window
        
        self._auto_refresh = tk.BooleanVar(value=False)
        self._refresh_job = None
        
        self._create_widgets()
        self._refresh_stats()
        
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_widgets(self):
        """Create the popup widgets."""
        # Header frame with status and controls
        header_frame = tk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Status indicator
        self.status_label = tk.Label(
            header_frame, 
            text="Status: DISABLED",
            font=("Helvetica", 12, "bold")
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Auto-refresh checkbox
        tk.Checkbutton(
            header_frame,
            text="Auto-refresh (1s)",
            variable=self._auto_refresh,
            command=self._toggle_auto_refresh
        ).pack(side=tk.RIGHT)
        
        # Refresh button
        tk.Button(
            header_frame,
            text="Refresh",
            command=self._refresh_stats
        ).pack(side=tk.RIGHT, padx=5)
        
        # Summary frame
        summary_frame = tk.LabelFrame(self, text="Summary", padx=10, pady=5)
        summary_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.total_alloc_label = tk.Label(summary_frame, text="Total Allocated: 0 MB")
        self.total_alloc_label.pack(anchor=tk.W)
        
        self.total_dealloc_label = tk.Label(summary_frame, text="Total Deallocated: 0 MB")
        self.total_dealloc_label.pack(anchor=tk.W)
        
        self.active_label = tk.Label(summary_frame, text="Currently Active: 0 MB (0 objects)")
        self.active_label.pack(anchor=tk.W)
        
        # Category breakdown frame
        category_frame = tk.LabelFrame(self, text="By Category", padx=10, pady=5)
        category_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview for categories
        columns = ("Category", "Count", "Size (MB)")
        self.category_tree = ttk.Treeview(category_frame, columns=columns, show="headings", height=6)
        self.category_tree.heading("Category", text="Category")
        self.category_tree.heading("Count", text="Count")
        self.category_tree.heading("Size (MB)", text="Size (MB)")
        self.category_tree.column("Category", width=200)
        self.category_tree.column("Count", width=80, anchor=tk.CENTER)
        self.category_tree.column("Size (MB)", width=100, anchor=tk.CENTER)
        self.category_tree.pack(fill=tk.BOTH, expand=True)
        
        # Active allocations frame
        alloc_frame = tk.LabelFrame(self, text="Active Allocations (Top 20 by size)", padx=10, pady=5)
        alloc_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview for allocations
        alloc_columns = ("Type", "Size (MB)", "Source", "Description")
        self.alloc_tree = ttk.Treeview(alloc_frame, columns=alloc_columns, show="headings", height=8)
        self.alloc_tree.heading("Type", text="Type")
        self.alloc_tree.heading("Size (MB)", text="Size (MB)")
        self.alloc_tree.heading("Source", text="Source")
        self.alloc_tree.heading("Description", text="Description")
        self.alloc_tree.column("Type", width=100)
        self.alloc_tree.column("Size (MB)", width=80, anchor=tk.CENTER)
        self.alloc_tree.column("Source", width=150)
        self.alloc_tree.column("Description", width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(alloc_frame, orient=tk.VERTICAL, command=self.alloc_tree.yview)
        self.alloc_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.alloc_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bottom buttons
        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(
            button_frame,
            text="Print to Console",
            command=lambda: MemoryTracker.print_report(detailed=True)
        ).pack(side=tk.LEFT)
        
        tk.Button(
            button_frame,
            text="Reset Tracking",
            command=self._reset_and_refresh
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="Close",
            command=self._on_close
        ).pack(side=tk.RIGHT)
    
    def _refresh_stats(self):
        """Refresh the displayed statistics."""
        stats = MemoryTracker.get_stats()
        
        # Update status
        status_text = "ENABLED" if stats["enabled"] else "DISABLED"
        status_color = "green" if stats["enabled"] else "red"
        self.status_label.config(text=f"Status: {status_text}", fg=status_color)
        
        # Update summary
        total_alloc_mb = stats["total_allocated_bytes"] / (1024 * 1024)
        total_dealloc_mb = stats["total_deallocated_bytes"] / (1024 * 1024)
        active_mb = stats["active_allocations_bytes"] / (1024 * 1024)
        
        self.total_alloc_label.config(text=f"Total Allocated: {total_alloc_mb:.2f} MB")
        self.total_dealloc_label.config(text=f"Total Deallocated: {total_dealloc_mb:.2f} MB")
        self.active_label.config(
            text=f"Currently Active: {active_mb:.2f} MB ({stats['active_allocations_count']} objects)"
        )
        
        # Update category tree
        for item in self.category_tree.get_children():
            self.category_tree.delete(item)
        
        for cat_name, cat_stats in sorted(stats["by_category"].items()):
            cat_mb = cat_stats["bytes"] / (1024 * 1024)
            self.category_tree.insert("", tk.END, values=(cat_name, cat_stats["count"], f"{cat_mb:.2f}"))
        
        # Update allocations tree
        for item in self.alloc_tree.get_children():
            self.alloc_tree.delete(item)
        
        allocations = MemoryTracker.get_active_allocations()
        allocations.sort(key=lambda a: a.size_bytes, reverse=True)
        
        for alloc in allocations[:20]:
            size_mb = alloc.size_bytes / (1024 * 1024)
            self.alloc_tree.insert("", tk.END, values=(
                alloc.object_type,
                f"{size_mb:.2f}",
                alloc.source,
                alloc.description
            ))
    
    def _toggle_auto_refresh(self):
        """Toggle auto-refresh mode."""
        if self._auto_refresh.get():
            self._schedule_refresh()
        elif self._refresh_job:
            self.after_cancel(self._refresh_job)
            self._refresh_job = None
    
    def _schedule_refresh(self):
        """Schedule the next auto-refresh."""
        self._refresh_stats()
        if self._auto_refresh.get():
            self._refresh_job = self.after(1000, self._schedule_refresh)
    
    def _reset_and_refresh(self):
        """Reset tracking data and refresh display."""
        MemoryTracker.reset()
        self._refresh_stats()
    
    def _on_close(self):
        """Handle popup closing."""
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
        self.destroy()