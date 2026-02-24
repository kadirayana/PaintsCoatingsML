"""
Paint Formulation AI - Smart Import Dialog
==========================================
UI dialog for intelligent Excel workflow with metadata validation.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading
from typing import Callable, Optional


class SmartImportDialog(tk.Toplevel):
    """
    Dialog for intelligent Excel import with:
    - Project context validation
    - Formula name editing
    - Progress tracking
    - Transaction results
    """
    
    def __init__(
        self,
        parent,
        db_manager,
        current_project_id: Optional[int] = None,
        current_project_name: str = "",
        on_import_complete: Callable = None,
        on_goto_materials: Callable = None
    ):
        super().__init__(parent)
        
        self.db_manager = db_manager
        self.current_project_id = current_project_id
        self.current_project_name = current_project_name
        self.on_import_complete = on_import_complete
        self.on_goto_materials = on_goto_materials
        
        self.file_path = None
        self.import_context = None
        self.result = None
        
        self.title("🧠 Akıllı Excel İçe Aktarım")
        self.geometry("600x550")
        self.transient(parent)
        self.grab_set()
        
        self._create_ui()
        self._center_on_parent(parent)
    
    def _center_on_parent(self, parent):
        """Center dialog on parent window"""
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === Step 1: File Selection ===
        file_frame = ttk.LabelFrame(main_frame, text="1️⃣ Dosya Seçimi", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_label = ttk.Label(file_frame, text="Dosya seçilmedi", foreground='gray')
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            file_frame,
            text="📂 Dosya Seç",
            command=self._select_file
        ).pack(side=tk.RIGHT, padx=5)
        
        # === Step 2: Context Validation ===
        context_frame = ttk.LabelFrame(main_frame, text="2️⃣ Proje Doğrulama", padding=10)
        context_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Current project
        curr_row = ttk.Frame(context_frame)
        curr_row.pack(fill=tk.X, pady=2)
        ttk.Label(curr_row, text="Mevcut Proje:", width=15).pack(side=tk.LEFT)
        self.current_project_label = ttk.Label(
            curr_row, 
            text=self.current_project_name or "(Proje seçilmedi)",
            font=('Segoe UI', 10, 'bold')
        )
        self.current_project_label.pack(side=tk.LEFT)
        
        # File project
        file_row = ttk.Frame(context_frame)
        file_row.pack(fill=tk.X, pady=2)
        ttk.Label(file_row, text="Dosya Projesi:", width=15).pack(side=tk.LEFT)
        self.file_project_label = ttk.Label(file_row, text="-", foreground='gray')
        self.file_project_label.pack(side=tk.LEFT)
        
        # Warning area
        self.warning_label = ttk.Label(
            context_frame, 
            text="",
            foreground='orange',
            wraplength=500
        )
        self.warning_label.pack(fill=tk.X, pady=(5, 0))
        
        # === Step 3: Formulation Details ===
        details_frame = ttk.LabelFrame(main_frame, text="3️⃣ Formülasyon Bilgileri", padding=10)
        details_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Formula name
        name_row = ttk.Frame(details_frame)
        name_row.pack(fill=tk.X, pady=2)
        ttk.Label(name_row, text="Formülasyon Adı:", width=15).pack(side=tk.LEFT)
        self.formula_name_var = tk.StringVar()
        self.formula_name_entry = ttk.Entry(name_row, textvariable=self.formula_name_var, width=40)
        self.formula_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Formula code (auto-generated)
        code_row = ttk.Frame(details_frame)
        code_row.pack(fill=tk.X, pady=2)
        ttk.Label(code_row, text="Formül Kodu:", width=15).pack(side=tk.LEFT)
        self.formula_code_var = tk.StringVar()
        self.formula_code_entry = ttk.Entry(code_row, textvariable=self.formula_code_var, width=20)
        self.formula_code_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(code_row, text="(otomatik)", foreground='gray').pack(side=tk.LEFT)
        
        # === Step 4: Progress & Results ===
        progress_frame = ttk.LabelFrame(main_frame, text="4️⃣ İşlem Durumu", padding=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 5))
        
        # Status text
        self.status_label = ttk.Label(progress_frame, text="", foreground='gray')
        self.status_label.pack(pady=2)
        
        # Results area (terminal style)
        results_scroll = ttk.Scrollbar(progress_frame)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_text = tk.Text(
            progress_frame,
            height=8,
            wrap=tk.WORD,
            state='disabled',
            font=('Consolas', 9),
            bg='#1E1E1E',
            fg='#00FF00'
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)
        self.results_text.config(yscrollcommand=results_scroll.set)
        results_scroll.config(command=self.results_text.yview)
        
        # === Buttons ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.import_btn = ttk.Button(
            btn_frame,
            text="📥 İçe Aktar",
            command=self._start_import,
            state='disabled',
            style='Accent.TButton'
        )
        self.import_btn.pack(side=tk.LEFT, padx=5, ipadx=20, ipady=5)
        
        self.fix_materials_btn = ttk.Button(
            btn_frame,
            text="🔧 Eksik hammaddeleri Düzenle",
            command=self._goto_materials,
            state='disabled'
        )
        self.fix_materials_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Kapat",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)
    
    def _select_file(self):
        """Handle file selection"""
        file_path = filedialog.askopenfilename(
            title="Excel Dosyası Seç",
            filetypes=[
                ("Excel Dosyaları", "*.xlsx *.xls"),
                ("Tüm Dosyalar", "*.*")
            ],
            parent=self
        )
        
        if not file_path:
            return
        
        self.file_path = file_path
        self.file_label.config(text=os.path.basename(file_path), foreground='black')
        
        # Read context
        self._read_context()
    
    def _read_context(self):
        """Read and validate import context"""
        try:
            from src.data_handlers.smart_excel_workflow import IntelligentImportHandler
            
            handler = IntelligentImportHandler(self.db_manager)
            self.import_context = handler.read_import_context(
                self.file_path,
                self.current_project_id,
                self.current_project_name
            )
            
            # Update UI
            if self.import_context.file_project_name:
                self.file_project_label.config(
                    text=self.import_context.file_project_name,
                    foreground='black'
                )
            else:
                self.file_project_label.config(
                    text="(Metadata bulunamadı)",
                    foreground='gray'
                )
            
            # Show warning if mismatch
            if self.import_context.requires_confirmation:
                self.warning_label.config(
                    text=f"⚠️ {self.import_context.mismatch_warning}"
                )
            else:
                self.warning_label.config(text="✅ Proje eşleşmesi doğrulandı")
            
            # Set suggested formula name
            self.formula_name_var.set(self.import_context.suggested_formula_name)
            
            # Enable import button
            self.import_btn.config(state='normal')
            
        except Exception as e:
            self._log_result(f"❌ Hata: {e}")
    
    def _start_import(self):
        """Start the import process"""
        if not self.file_path:
            messagebox.showwarning("Uyarı", "Lütfen bir dosya seçin", parent=self)
            return
        
        # Confirm if mismatch
        if self.import_context and self.import_context.requires_confirmation:
            if not messagebox.askyesno(
                "Proje Uyumsuzluğu",
                self.import_context.mismatch_warning,
                parent=self
            ):
                return
        
        # Disable controls
        self.import_btn.config(state='disabled')
        self.formula_name_entry.config(state='disabled')
        
        # Start progress
        self.progress.start(10)
        self._log_result("═" * 45)
        self._log_result("  İÇE AKTARIM BAŞLIYOR")
        self._log_result("═" * 45 + "\n")
        
        # Run in thread
        threading.Thread(target=self._do_import, daemon=True).start()
    
    def _do_import(self):
        """Perform the import in background thread"""
        try:
            from src.data_handlers.smart_excel_workflow import IntelligentImportHandler
            
            handler = IntelligentImportHandler(self.db_manager)
            
            self.result = handler.import_with_transaction(
                file_path=self.file_path,
                project_id=self.current_project_id,
                formula_name=self.formula_name_var.get(),
                formula_code=self.formula_code_var.get() or None,
                on_progress=lambda msg: self.after(0, lambda m=msg: self._log_result(m))
            )
            
            # Update UI on main thread
            self.after(0, self._on_import_complete)
            
        except Exception as e:
            self.after(0, lambda: self._on_import_error(str(e)))
    
    def _on_import_complete(self):
        """Handle import completion"""
        self.progress.stop()
        
        if self.result.success:
            self._log_result("\n" + "═" * 45)
            self._log_result("  ✅ İÇE AKTARIM BAŞARILI")
            self._log_result("═" * 45)
            self._log_result(f"\n📋 Formülasyon ID: {self.result.formulation_id}")
            self._log_result(f"📝 Formül Kodu: {self.result.formulation_code}")
            self._log_result(f"🧪 Bileşen Sayısı: {self.result.components_count}")
            
            self.status_label.config(
                text="✅ İçe aktarım tamamlandı!",
                foreground='green'
            )
            
            # Check for incomplete materials
            try:
                incomplete = self.db_manager.get_incomplete_materials()
                if incomplete:
                    self._log_result(f"\n⚠️ {len(incomplete)} eksik bilgili hammadde var")
                    self.fix_materials_btn.config(state='normal')
            except Exception:
                pass
            
            # Callback
            if self.on_import_complete:
                self.on_import_complete(
                    self.result.formulation_id,
                    self.result.formulation_code
                )
        else:
            self._log_result("\n" + "═" * 45)
            self._log_result("  ❌ İÇE AKTARIM BAŞARISIZ")
            self._log_result("═" * 45)
            self._log_result(f"\n{self.result.message}")
            
            if self.result.rollback_performed:
                self._log_result("\n🔙 Değişiklikler geri alındı (ROLLBACK)")
            
            if self.result.validation_errors:
                self._log_result("\n⚠️ Doğrulama Hataları:")
                for err in self.result.validation_errors[:5]:
                    self._log_result(f"  • {err}")
            
            self.status_label.config(
                text="❌ İçe aktarım başarısız",
                foreground='red'
            )
            
            self.import_btn.config(state='normal')
            self.formula_name_entry.config(state='normal')
    
    def _on_import_error(self, error: str):
        """Handle import error"""
        self.progress.stop()
        self._log_result(f"\n❌ Kritik Hata: {error}")
        self.status_label.config(text="❌ Hata oluştu", foreground='red')
        self.import_btn.config(state='normal')
        self.formula_name_entry.config(state='normal')
    
    def _log_result(self, message: str):
        """Add message to results area"""
        self.results_text.config(state='normal')
        self.results_text.insert(tk.END, message + "\n")
        self.results_text.see(tk.END)
        self.results_text.config(state='disabled')
    
    def _goto_materials(self):
        """Navigate to materials tab"""
        if self.on_goto_materials:
            self.on_goto_materials()
        self.destroy()


class TemplateDownloadDialog(tk.Toplevel):
    """Dialog for downloading smart template"""
    
    def __init__(
        self,
        parent,
        db_manager,
        project_id: Optional[int] = None,
        project_name: str = ""
    ):
        super().__init__(parent)
        
        self.db_manager = db_manager
        self.project_id = project_id
        self.project_name = project_name
        
        self.title("📥 Şablon İndir")
        self.geometry("450x200")
        self.transient(parent)
        self.grab_set()
        
        self._create_ui()
        self._center_on_parent(parent)
    
    def _center_on_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Info
        ttk.Label(
            main_frame,
            text="📋 Formülasyon Şablonu",
            font=('Segoe UI', 12, 'bold')
        ).pack(pady=(0, 10))
        
        ttk.Label(
            main_frame,
            text=(
                "Bu şablon proje bilgilerini içerir ve\n"
                "formülasyon verilerini kolayca içe aktarmanızı sağlar."
            ),
            justify=tk.CENTER
        ).pack(pady=5)
        
        # Project info
        if self.project_name:
            ttk.Label(
                main_frame,
                text=f"Proje: {self.project_name}",
                font=('Segoe UI', 10, 'bold'),
                foreground='blue'
            ).pack(pady=10)
        
        # Include sample data
        self.include_sample_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            main_frame,
            text="Örnek veriler ekle",
            variable=self.include_sample_var
        ).pack(pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        ttk.Button(
            btn_frame,
            text="📥 İndir",
            command=self._download,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=5, ipadx=20)
        
        ttk.Button(
            btn_frame,
            text="İptal",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)
    
    def _download(self):
        """Download the template"""
        try:
            from src.data_handlers.smart_excel_workflow import SmartTemplateGenerator
            
            generator = SmartTemplateGenerator(self.db_manager)
            wb = generator.get_workbook(
                project_id=self.project_id,
                project_name=self.project_name,
                include_sample_data=self.include_sample_var.get()
            )
            
            suggested_name = generator._generate_filename(self.project_name)
            
            # Ask for save location
            file_path = filedialog.asksaveasfilename(
                title="Şablonu Kaydet",
                defaultextension=".xlsx",
                initialfile=suggested_name,
                filetypes=[("Excel Dosyası", "*.xlsx")],
                parent=self
            )
            
            if file_path:
                wb.save(file_path)
                messagebox.showinfo(
                    "Başarılı",
                    f"Şablon kaydedildi:\n{file_path}",
                    parent=self
                )
                self.destroy()
                
        except Exception as e:
            messagebox.showerror(
                "Hata",
                f"Şablon oluşturulamadı:\n{e}",
                parent=self
            )
