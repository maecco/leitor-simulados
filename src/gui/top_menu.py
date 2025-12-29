import tkinter as tk
from tkinter import Menu, filedialog

from .event_system import EventBus
from .popups import SaveAsPopup, ExportYoloPopup, MemoryTrackerPopup

from utils.memory import MemoryTracker

class TopMenu(tk.Menu):
    """Represents the top menu bar in the GUI.
    
    Attributes
    ----------
    root : tk.Tk
        The root Tkinter window.
    """
    
    def __init__(self, root):
        """Initializes the top menu bar with different menu options.
        
        Parameters
        ----------
        root : tk.Tk
            The root Tkinter window.
        """
        super().__init__(root, bg="lightblue")
        self.root = root

        # Menu Arquivo
        menu_arquivo = Menu(self, tearoff=0)
        menu_arquivo.add_command(label="Abrir Pasta", command=self.open_folder)
        menu_arquivo.add_command(
            label="Salvar respostas", command=self.save_report
        )
        self.add_cascade(label="Arquivo", menu=menu_arquivo)

        # Menu Ferramentas
        menu_ferramentas = Menu(self, tearoff=0)
        menu_ferramentas.add_checkbutton(label="Debug")
        self.add_cascade(label="Ferramentas", menu=menu_ferramentas)

        # Menu Detecções
        menu_deteccoes = Menu(self, tearoff=0)
        menu_deteccoes.add_command(
            label="Exportar YOLO",
            command=self.export_yolo
        )
        menu_deteccoes.add_command(
            label="Exportar Imagens com Respostas",
            command=self.export_images
        )
        self.add_cascade(label="Exportar", menu=menu_deteccoes)

        # Menu Debug / Memory
        menu_debug = Menu(self, tearoff=0)
        self._memory_tracking_var = tk.BooleanVar(value=False)
        self._print_tracking_var = tk.BooleanVar(value=False)
        menu_debug.add_checkbutton(
            label="Enable Memory Tracking",
            variable=self._memory_tracking_var,
            command=self._toggle_memory_tracking
        )
        menu_debug.add_checkbutton(
            label="Print on Track",
            variable=self._print_tracking_var,
            command=self._toggle_print_tracking
        )
        menu_debug.add_separator()
        menu_debug.add_command(
            label="Show Memory Report",
            command=self._show_memory_report
        )
        menu_debug.add_command(
            label="Print Memory Report (Console)",
            command=self._print_memory_report
        )
        menu_debug.add_command(
            label="Reset Memory Tracking",
            command=self._reset_memory_tracking
        )
        self.add_cascade(label="Debug", menu=menu_debug)

    def open_folder(self):
        """Opens a folder selection dialog and publishes the selected folder path."""
        file = filedialog.askdirectory()
        if file:
            EventBus.publish("<<open_folder>>", file)
    
    def save_report(self):
        """Opens the 'Save As' popup to allow the user to save a report."""
        SaveAsPopup(self.root)

    def export_yolo(self):
        """Opens the 'Export YOLO' popup for exporting image detections."""
        ExportYoloPopup(self.root)

    def export_images(self):
        out_path = filedialog.askdirectory()
        if out_path:
            EventBus.publish("<<export_report_images>>", out_path)

    def _toggle_memory_tracking(self):
        """Toggle memory tracking on/off."""
        if self._memory_tracking_var.get():
            MemoryTracker.enable(print_on_track=self._print_tracking_var.get())
        else:
            MemoryTracker.disable()
    
    def _toggle_print_tracking(self):
        """Toggle print-on-track setting."""
        if MemoryTracker.is_enabled():
            tracker = MemoryTracker.get_instance()
            tracker._print_on_track = self._print_tracking_var.get()
    
    def _show_memory_report(self):
        """Show memory report in a popup window."""
        MemoryTrackerPopup(self.root)
    
    def _print_memory_report(self):
        """Print memory report to console."""
        MemoryTracker.print_report(detailed=True)
    
    def _reset_memory_tracking(self):
        """Reset all memory tracking data."""
        MemoryTracker.reset()
        
        