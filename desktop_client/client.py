"""
Leitor de Simulados - Desktop Client
A lightweight desktop application that connects to the web server for processing
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import base64
from io import BytesIO
from PIL import Image, ImageTk

from api_client import APIClient


class DesktopClient(tk.Tk):
    """Main desktop client application"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Leitor de Simulados - Cliente")
        self.geometry("1200x800")
        self.minsize(900, 600)
        
        # State
        self.api = APIClient()
        self.session_id = None
        self.images = []
        self.current_index = -1
        self.current_image_tk = None
        
        # Setup UI
        self._create_menu()
        self._create_layout()
        self._create_status_bar()
        
        # Bind events
        self.bind("<Left>", lambda e: self._prev_image())
        self.bind("<Right>", lambda e: self._next_image())
        
        self._update_status("Desconectado")
    
    # =========================================================================
    # UI Creation
    # =========================================================================
    
    def _create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Arquivo", menu=file_menu)
        file_menu.add_command(label="Conectar ao Servidor...", command=self._show_connect_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Nova Sessão...", command=self._show_session_dialog)
        file_menu.add_command(label="Carregar Imagens...", command=self._load_images)
        file_menu.add_separator()
        file_menu.add_command(label="Exportar JSON", command=lambda: self._export("json"))
        file_menu.add_command(label="Exportar CSV", command=lambda: self._export("csv"))
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.quit)
        
        # Process menu
        process_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Processar", menu=process_menu)
        process_menu.add_command(label="Processar Imagem Atual", command=self._process_current)
        process_menu.add_command(label="Processar Todas", command=self._process_all)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ajuda", menu=help_menu)
        help_menu.add_command(label="Sobre", command=self._show_about)
    
    def _create_layout(self):
        """Create main layout"""
        # Main container
        self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Controls
        left_frame = ttk.Frame(self.main_paned, width=280)
        self.main_paned.add(left_frame, weight=0)
        self._create_left_panel(left_frame)
        
        # Center - Image viewer
        center_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(center_frame, weight=1)
        self._create_image_viewer(center_frame)
        
        # Right panel - Results
        right_frame = ttk.Frame(self.main_paned, width=300)
        self.main_paned.add(right_frame, weight=0)
        self._create_right_panel(right_frame)
    
    def _create_left_panel(self, parent):
        """Create left control panel"""
        # Server connection
        conn_frame = ttk.LabelFrame(parent, text="Servidor", padding=10)
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.server_var = tk.StringVar(value="http://localhost:8000")
        ttk.Label(conn_frame, text="URL:").pack(anchor=tk.W)
        ttk.Entry(conn_frame, textvariable=self.server_var).pack(fill=tk.X)
        
        btn_frame = ttk.Frame(conn_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        self.connect_btn = ttk.Button(btn_frame, text="Conectar", command=self._connect)
        self.connect_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.connection_label = ttk.Label(conn_frame, text="⚫ Desconectado", foreground="gray")
        self.connection_label.pack(pady=(5, 0))
        
        # Session
        session_frame = ttk.LabelFrame(parent, text="Sessão", padding=10)
        session_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(session_frame, text="Tipo de Prova:").pack(anchor=tk.W)
        self.test_type_var = tk.StringVar()
        self.test_type_combo = ttk.Combobox(session_frame, textvariable=self.test_type_var, state="readonly")
        self.test_type_combo.pack(fill=tk.X)
        
        ttk.Button(session_frame, text="Criar Sessão", command=self._create_session).pack(fill=tk.X, pady=(5, 0))
        
        self.session_label = ttk.Label(session_frame, text="Nenhuma sessão", foreground="gray")
        self.session_label.pack(pady=(5, 0))
        
        # Models
        model_frame = ttk.LabelFrame(parent, text="Modelos", padding=10)
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(model_frame, text="1ª Etapa:").pack(anchor=tk.W)
        self.fs_model_var = tk.StringVar()
        self.fs_model_combo = ttk.Combobox(model_frame, textvariable=self.fs_model_var, state="readonly")
        self.fs_model_combo.pack(fill=tk.X)
        
        ttk.Label(model_frame, text="Threshold:").pack(anchor=tk.W, pady=(5, 0))
        self.fs_threshold_var = tk.DoubleVar(value=0.5)
        fs_scale = ttk.Scale(model_frame, from_=0.1, to=0.9, variable=self.fs_threshold_var, orient=tk.HORIZONTAL)
        fs_scale.pack(fill=tk.X)
        
        ttk.Label(model_frame, text="2ª Etapa:").pack(anchor=tk.W, pady=(10, 0))
        self.ss_model_var = tk.StringVar()
        self.ss_model_combo = ttk.Combobox(model_frame, textvariable=self.ss_model_var, state="readonly")
        self.ss_model_combo.pack(fill=tk.X)
        
        ttk.Label(model_frame, text="Threshold:").pack(anchor=tk.W, pady=(5, 0))
        self.ss_threshold_var = tk.DoubleVar(value=0.5)
        ss_scale = ttk.Scale(model_frame, from_=0.1, to=0.9, variable=self.ss_threshold_var, orient=tk.HORIZONTAL)
        ss_scale.pack(fill=tk.X)
        
        # Process buttons
        btn_frame = ttk.Frame(model_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="Processar", command=self._process_current).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(btn_frame, text="Todas", command=self._process_all).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        # Image list
        list_frame = ttk.LabelFrame(parent, text="Imagens", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(list_frame, text="📁 Carregar Imagens", command=self._load_images).pack(fill=tk.X)
        
        # Listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.image_listbox = tk.Listbox(list_container, yscrollcommand=scrollbar.set)
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.image_listbox.yview)
        
        self.image_listbox.bind("<<ListboxSelect>>", self._on_image_select)
    
    def _create_image_viewer(self, parent):
        """Create center image viewer"""
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X)
        
        ttk.Button(toolbar, text="◀", width=3, command=self._prev_image).pack(side=tk.LEFT)
        self.image_counter_label = ttk.Label(toolbar, text="0 / 0")
        self.image_counter_label.pack(side=tk.LEFT, padx=10)
        ttk.Button(toolbar, text="▶", width=3, command=self._next_image).pack(side=tk.LEFT)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        self.show_detections_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Mostrar detecções", variable=self.show_detections_var,
                       command=self._refresh_image).pack(side=tk.LEFT)
        
        # Canvas for image
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.canvas = tk.Canvas(canvas_frame, bg="#2d2d2d", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Placeholder text
        self.canvas.create_text(
            400, 300, text="📷 Nenhuma imagem carregada",
            fill="#666666", font=("Arial", 14), tags="placeholder"
        )
    
    def _create_right_panel(self, parent):
        """Create right results panel"""
        # Report section
        report_frame = ttk.LabelFrame(parent, text="Relatório", padding=10)
        report_frame.pack(fill=tk.BOTH, expand=True)
        
        # CPF
        cpf_frame = ttk.Frame(report_frame)
        cpf_frame.pack(fill=tk.X)
        ttk.Label(cpf_frame, text="CPF:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.cpf_label = ttk.Label(cpf_frame, text="-")
        self.cpf_label.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Separator(report_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Answers
        ttk.Label(report_frame, text="Respostas:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # Scrollable answers frame
        answers_container = ttk.Frame(report_frame)
        answers_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        canvas = tk.Canvas(answers_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(answers_container, orient=tk.VERTICAL, command=canvas.yview)
        self.answers_frame = ttk.Frame(canvas)
        
        self.answers_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.answers_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.answer_widgets = []
    
    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = ttk.Label(self, text="Pronto", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    # =========================================================================
    # Actions
    # =========================================================================
    
    def _connect(self):
        """Connect to server"""
        url = self.server_var.get().strip()
        if not url:
            messagebox.showerror("Erro", "Digite a URL do servidor")
            return
        
        self._update_status("Conectando...")
        self.api.base_url = url
        
        def do_connect():
            try:
                models = self.api.get_models()
                test_types = ["PS_ALUNOS", "SIMULINHO", "SIMUFSC", "SIMUENEM"]
                
                self.after(0, lambda: self._on_connected(models, test_types))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: self._on_connect_error(msg))
        
        threading.Thread(target=do_connect, daemon=True).start()
    
    def _on_connected(self, models, test_types):
        """Handle successful connection"""
        self.connection_label.config(text="🟢 Conectado", foreground="green")
        self._update_status("Conectado ao servidor")
        
        # Populate test types
        self.test_type_combo["values"] = test_types
        if test_types:
            self.test_type_combo.current(0)
        
        # Populate models
        fs_models = [m["name"] for m in models if m["target_stage"] in ("FIRST", "BOTH")]
        ss_models = [m["name"] for m in models if m["target_stage"] in ("SECOND", "BOTH")]
        
        self._models = models  # Store for later use
        
        self.fs_model_combo["values"] = fs_models
        self.ss_model_combo["values"] = ss_models
        if fs_models:
            self.fs_model_combo.current(0)
        if ss_models:
            self.ss_model_combo.current(0)
    
    def _on_connect_error(self, error):
        """Handle connection error"""
        self.connection_label.config(text="🔴 Erro", foreground="red")
        self._update_status(f"Erro: {error}")
        messagebox.showerror("Erro de Conexão", f"Não foi possível conectar:\n{error}")
    
    def _create_session(self):
        """Create a new session"""
        if not self.api.base_url:
            messagebox.showerror("Erro", "Conecte ao servidor primeiro")
            return
        
        test_type = self.test_type_var.get()
        if not test_type:
            messagebox.showerror("Erro", "Selecione o tipo de prova")
            return
        
        self._update_status("Criando sessão...")
        
        def do_create():
            try:
                result = self.api.create_session(test_type)
                self.after(0, lambda: self._on_session_created(result))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: messagebox.showerror("Erro", msg))
        
        threading.Thread(target=do_create, daemon=True).start()
    
    def _on_session_created(self, result):
        """Handle session created"""
        self.session_id = result["session_id"]
        self.session_label.config(
            text=f"✓ {self.session_id[:8]}...",
            foreground="green"
        )
        self._update_status("Sessão criada")
        self.images = []
        self.current_index = -1
        self._update_image_list()
    
    def _load_images(self):
        """Load images from disk"""
        if not self.session_id:
            messagebox.showerror("Erro", "Crie uma sessão primeiro")
            return
        
        files = filedialog.askopenfilenames(
            title="Selecionar Imagens",
            filetypes=[
                ("Imagens", "*.png *.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Todos", "*.*")
            ]
        )
        
        if not files:
            return
        
        self._update_status(f"Carregando {len(files)} imagens...")
        
        def do_upload():
            try:
                result = self.api.upload_images(self.session_id, files)
                self.after(0, lambda: self._on_images_uploaded(result))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: messagebox.showerror("Erro", msg))
        
        threading.Thread(target=do_upload, daemon=True).start()
    
    def _on_images_uploaded(self, result):
        """Handle images uploaded"""
        self._update_status(f"{result['total']} imagens carregadas")
        self._refresh_image_list()
    
    def _refresh_image_list(self):
        """Refresh the image list from server"""
        if not self.session_id:
            return
        
        def do_refresh():
            try:
                result = self.api.get_images(self.session_id)
                self.after(0, lambda: self._on_images_refreshed(result["images"]))
            except Exception as e:
                self.after(0, lambda: self._update_status(f"Erro: {e}"))
        
        threading.Thread(target=do_refresh, daemon=True).start()
    
    def _on_images_refreshed(self, images):
        """Handle images list refreshed"""
        self.images = images
        self._update_image_list()
        
        if images and self.current_index < 0:
            self.current_index = 0
            self._load_current_image()
    
    def _update_image_list(self):
        """Update the image listbox"""
        self.image_listbox.delete(0, tk.END)
        
        for i, img in enumerate(self.images):
            prefix = "✓ " if img.get("processed") else "  "
            self.image_listbox.insert(tk.END, f"{prefix}{img['filename']}")
        
        self._update_image_counter()
    
    def _update_image_counter(self):
        """Update image counter label"""
        total = len(self.images)
        current = self.current_index + 1 if self.current_index >= 0 else 0
        self.image_counter_label.config(text=f"{current} / {total}")
    
    def _on_image_select(self, event):
        """Handle image selection from listbox"""
        selection = self.image_listbox.curselection()
        if selection:
            self.current_index = selection[0]
            self._load_current_image()
    
    def _prev_image(self):
        """Go to previous image"""
        if self.current_index > 0:
            self.current_index -= 1
            self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(self.current_index)
            self._load_current_image()
    
    def _next_image(self):
        """Go to next image"""
        if self.current_index < len(self.images) - 1:
            self.current_index += 1
            self.image_listbox.selection_clear(0, tk.END)
            self.image_listbox.selection_set(self.current_index)
            self._load_current_image()
    
    def _load_current_image(self):
        """Load the current image from server"""
        if self.current_index < 0 or self.current_index >= len(self.images):
            return
        
        img_data = self.images[self.current_index]
        show_detections = self.show_detections_var.get() and img_data.get("processed")
        
        def do_load():
            try:
                result = self.api.get_image(self.session_id, img_data["id"], show_detections)
                self.after(0, lambda: self._display_image(result))
                
                # Also load report if processed
                if img_data.get("has_report"):
                    report = self.api.get_report(self.session_id, img_data["id"])
                    self.after(0, lambda: self._display_report(report["report"]))
                else:
                    self.after(0, lambda: self._clear_report())
            except Exception as e:
                self.after(0, lambda: self._update_status(f"Erro: {e}"))
        
        threading.Thread(target=do_load, daemon=True).start()
        self._update_image_counter()
    
    def _refresh_image(self):
        """Refresh current image (e.g., toggle detections)"""
        self._load_current_image()
    
    def _display_image(self, result):
        """Display image on canvas"""
        try:
            # Decode base64 image
            img_bytes = base64.b64decode(result["image"])
            img = Image.open(BytesIO(img_bytes))
            
            # Resize to fit canvas
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                img_ratio = img.width / img.height
                canvas_ratio = canvas_width / canvas_height
                
                if img_ratio > canvas_ratio:
                    new_width = canvas_width
                    new_height = int(canvas_width / img_ratio)
                else:
                    new_height = canvas_height
                    new_width = int(canvas_height * img_ratio)
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.current_image_tk = ImageTk.PhotoImage(img)
            
            # Display on canvas
            self.canvas.delete("all")
            self.canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                image=self.current_image_tk, anchor=tk.CENTER
            )
        except Exception as e:
            self._update_status(f"Erro ao exibir imagem: {e}")
    
    def _display_report(self, report):
        """Display report in right panel"""
        # Clear previous
        for widget in self.answer_widgets:
            widget.destroy()
        self.answer_widgets.clear()
        
        # Set CPF
        self.cpf_label.config(text=report.get("owner_cpf", "-"))
        
        # Create answer widgets
        questions = report.get("questions", [])
        
        for q in questions:
            frame = ttk.Frame(self.answers_frame)
            frame.pack(fill=tk.X, pady=1)
            
            ttk.Label(frame, text=f"{q['number']:02d}:", width=4).pack(side=tk.LEFT)
            
            answer_var = tk.StringVar(value=q.get("answer", ""))
            combo = ttk.Combobox(frame, textvariable=answer_var, width=5, state="readonly")
            combo["values"] = ["", "A", "B", "C", "D", "E"]
            combo.pack(side=tk.LEFT, padx=(5, 0))
            
            # Mark updated answers
            if q.get("updated"):
                combo.config(style="Updated.TCombobox")
            
            self.answer_widgets.append(frame)
    
    def _clear_report(self):
        """Clear the report panel"""
        self.cpf_label.config(text="-")
        for widget in self.answer_widgets:
            widget.destroy()
        self.answer_widgets.clear()
    
    def _get_selected_model_path(self, model_name, stage):
        """Get model path from name"""
        for m in self._models:
            if m["name"] == model_name and m["target_stage"] in (stage, "BOTH"):
                return m["rel_path"]
        return None
    
    def _process_current(self):
        """Process current image"""
        if not self.session_id or self.current_index < 0:
            messagebox.showerror("Erro", "Selecione uma imagem primeiro")
            return
        
        fs_model = self._get_selected_model_path(self.fs_model_var.get(), "FIRST")
        ss_model = self._get_selected_model_path(self.ss_model_var.get(), "SECOND")
        
        if not fs_model or not ss_model:
            messagebox.showerror("Erro", "Selecione os modelos")
            return
        
        img_data = self.images[self.current_index]
        self._update_status("Processando...")
        
        def do_process():
            try:
                result = self.api.process_image(
                    self.session_id,
                    img_data["id"],
                    fs_model,
                    ss_model,
                    self.fs_threshold_var.get(),
                    self.ss_threshold_var.get()
                )
                self.after(0, lambda: self._on_processed(result))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: messagebox.showerror("Erro", msg))
        
        threading.Thread(target=do_process, daemon=True).start()
    
    def _on_processed(self, result):
        """Handle image processed"""
        self._update_status(f"Processado: {result['detections_count']} detecções")
        self._refresh_image_list()
        self._load_current_image()
    
    def _process_all(self):
        """Process all images"""
        if not self.session_id or not self.images:
            messagebox.showerror("Erro", "Carregue imagens primeiro")
            return
        
        fs_model = self._get_selected_model_path(self.fs_model_var.get(), "FIRST")
        ss_model = self._get_selected_model_path(self.ss_model_var.get(), "SECOND")
        
        if not fs_model or not ss_model:
            messagebox.showerror("Erro", "Selecione os modelos")
            return
        
        self._update_status("Processando todas as imagens...")
        
        def do_process():
            try:
                result = self.api.process_all_images(
                    self.session_id,
                    fs_model,
                    ss_model,
                    self.fs_threshold_var.get(),
                    self.ss_threshold_var.get()
                )
                self.after(0, lambda: self._on_all_processed(result))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: messagebox.showerror("Erro", msg))
        
        threading.Thread(target=do_process, daemon=True).start()
    
    def _on_all_processed(self, result):
        """Handle all images processed"""
        success = sum(1 for r in result["results"] if r["status"] == "success")
        self._update_status(f"Processado: {success}/{len(result['results'])} imagens")
        self._refresh_image_list()
        self._load_current_image()
    
    def _export(self, format):
        """Export results"""
        if not self.session_id:
            messagebox.showerror("Erro", "Nenhuma sessão ativa")
            return
        
        ext = ".json" if format == "json" else ".csv"
        filename = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(format.upper(), f"*{ext}")]
        )
        
        if not filename:
            return
        
        def do_export():
            try:
                result = self.api.export_reports(self.session_id, format)
                
                if format == "json":
                    import json
                    content = json.dumps(result, indent=2, ensure_ascii=False)
                else:
                    content = result.get("csv", "")
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                
                self.after(0, lambda fn=filename: self._update_status(f"Exportado: {fn}"))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda msg=error_msg: messagebox.showerror("Erro", msg))
        
        threading.Thread(target=do_export, daemon=True).start()
    
    def _update_status(self, message):
        """Update status bar"""
        self.status_bar.config(text=message)
    
    def _show_connect_dialog(self):
        """Show connect dialog"""
        self.server_var.set(self.server_var.get())
        self._connect()
    
    def _show_session_dialog(self):
        """Show session dialog"""
        self._create_session()
    
    def _show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "Sobre",
            "Leitor de Simulados - Cliente Desktop\n\n"
            "Versão 2.0\n\n"
            "Aplicação cliente para conexão com o\n"
            "servidor de processamento de simulados."
        )


if __name__ == "__main__":
    app = DesktopClient()
    app.mainloop()
