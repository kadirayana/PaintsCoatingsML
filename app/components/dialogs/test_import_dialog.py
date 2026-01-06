"""
Paint Formulation AI - Test Results Import Dialog
=================================================
UI dialog for test results import with validation report.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import threading
from typing import Callable, Optional


class TestResultsImportDialog(tk.Toplevel):
    """
    Dialog for test results import with:
    - File selection
    - Validation report before import
    - Duplicate handling options
    - Progress tracking
    """
    
    def __init__(
        self,
        parent,
        db_manager,
        project_id: Optional[int] = None,
        project_name: str = "",
        on_import_complete: Callable = None
    ):
        super().__init__(parent)
        
        self.db_manager = db_manager
        self.project_id = project_id
        self.project_name = project_name
        self.on_import_complete = on_import_complete
        
        self.file_path = None
        self.validation_result = None
        
        self.title("📊 Test Sonuçları İçe Aktar")
        self.geometry("700x650")
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
        
        # === Step 1: File Selection ===
        file_frame = ttk.LabelFrame(main_frame, text="1️⃣ Dosya Seçimi", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        file_row = ttk.Frame(file_frame)
        file_row.pack(fill=tk.X)
        
        self.file_label = ttk.Label(file_row, text="Dosya seçilmedi", foreground='gray')
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            file_row,
            text="📂 Dosya Seç",
            command=self._select_file
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            file_row,
            text="📥 Şablon İndir",
            command=self._download_template
        ).pack(side=tk.RIGHT, padx=5)
        
        # Project info
        if self.project_name:
            ttk.Label(
                file_frame,
                text=f"Proje: {self.project_name}",
                font=('Segoe UI', 9, 'italic'),
                foreground='blue'
            ).pack(pady=(5, 0))
        
        # === Step 2: Validation Report ===
        validation_frame = ttk.LabelFrame(main_frame, text="2️⃣ Doğrulama Raporu", padding=10)
        validation_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Summary stats
        stats_frame = ttk.Frame(validation_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stat_labels = {}
        stats = [
            ('total', '📋 Toplam:', '0'),
            ('valid', '✅ Geçerli:', '0'),
            ('invalid', '❌ Geçersiz:', '0'),
            ('duplicate', '🔄 Mevcut:', '0'),
            ('orphaned', '❓ Sahipsiz:', '0')
        ]
        
        for key, label, default in stats:
            frame = ttk.Frame(stats_frame)
            frame.pack(side=tk.LEFT, padx=10)
            ttk.Label(frame, text=label).pack(side=tk.LEFT)
            lbl = ttk.Label(frame, text=default, font=('Segoe UI', 10, 'bold'))
            lbl.pack(side=tk.LEFT, padx=3)
            self.stat_labels[key] = lbl
        
        # Validation details table
        table_frame = ttk.Frame(validation_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview for validation results
        columns = ('row', 'code', 'date', 'status', 'errors')
        self.validation_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            height=10,
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )
        
        self.validation_tree.heading('row', text='Satır')
        self.validation_tree.heading('code', text='Formülasyon')
        self.validation_tree.heading('date', text='Tarih')
        self.validation_tree.heading('status', text='Durum')
        self.validation_tree.heading('errors', text='Hatalar')
        
        self.validation_tree.column('row', width=50, anchor='center')
        self.validation_tree.column('code', width=120)
        self.validation_tree.column('date', width=100)
        self.validation_tree.column('status', width=80, anchor='center')
        self.validation_tree.column('errors', width=300)
        
        self.validation_tree.pack(fill=tk.BOTH, expand=True)
        
        y_scroll.config(command=self.validation_tree.yview)
        x_scroll.config(command=self.validation_tree.xview)
        
        # Configure row tags for coloring
        self.validation_tree.tag_configure('valid', foreground='green')
        self.validation_tree.tag_configure('invalid', foreground='red')
        self.validation_tree.tag_configure('duplicate', foreground='orange')
        
        # === Step 3: Import Options ===
        options_frame = ttk.LabelFrame(main_frame, text="3️⃣ İçe Aktarım Seçenekleri", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.update_duplicates_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Mevcut kayıtları güncelle (aynı formülasyon + tarih)",
            variable=self.update_duplicates_var
        ).pack(anchor='w')
        
        ttk.Label(
            options_frame,
            text="⚠️ İşaretlenmezse mevcut kayıtlar atlanır",
            font=('Segoe UI', 8),
            foreground='gray'
        ).pack(anchor='w', padx=20)
        
        # === Progress ===
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="", foreground='gray')
        self.status_label.pack()
        
        # === Buttons ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        self.validate_btn = ttk.Button(
            btn_frame,
            text="🔍 Doğrula",
            command=self._validate_file,
            state='disabled'
        )
        self.validate_btn.pack(side=tk.LEFT, padx=5)
        
        self.import_btn = ttk.Button(
            btn_frame,
            text="📥 İçe Aktar",
            command=self._start_import,
            state='disabled',
            style='Accent.TButton'
        )
        self.import_btn.pack(side=tk.LEFT, padx=5, ipadx=20)
        
        ttk.Button(
            btn_frame,
            text="Kapat",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)
    
    def _select_file(self):
        """Handle file selection"""
        file_path = filedialog.askopenfilename(
            title="Test Sonuçları Excel Dosyası",
            filetypes=[
                ("Excel Dosyaları", "*.xlsx *.xls"),
                ("Tüm Dosyalar", "*.*")
            ],
            parent=self
        )
        
        if file_path:
            self.file_path = file_path
            self.file_label.config(
                text=os.path.basename(file_path),
                foreground='black'
            )
            self.validate_btn.config(state='normal')
            
            # Auto-validate
            self._validate_file()
    
    def _download_template(self):
        """Download template with untested formulations"""
        try:
            from src.data_handlers.test_results_workflow import TestResultsTemplateGenerator
            
            generator = TestResultsTemplateGenerator(self.db_manager)
            wb, filename = generator.generate_template(
                project_id=self.project_id,
                project_name=self.project_name,
                prefill_untested=True
            )
            
            # Ask for save location
            save_path = filedialog.asksaveasfilename(
                title="Şablonu Kaydet",
                defaultextension=".xlsx",
                initialfile=filename,
                filetypes=[("Excel Dosyası", "*.xlsx")],
                parent=self
            )
            
            if save_path:
                wb.save(save_path)
                messagebox.showinfo(
                    "Başarılı",
                    f"Şablon kaydedildi:\n{save_path}\n\n"
                    f"Test edilmemiş formülasyonlar şablona eklendi.",
                    parent=self
                )
                
        except Exception as e:
            messagebox.showerror("Hata", f"Şablon oluşturulamadı:\n{e}", parent=self)
    
    def _validate_file(self):
        """Validate the selected file"""
        if not self.file_path:
            return
        
        self.status_label.config(text="⏳ Dosya doğrulanıyor...")
        self.progress.start(10)
        self.validate_btn.config(state='disabled')
        self.import_btn.config(state='disabled')
        
        # Clear previous results
        for item in self.validation_tree.get_children():
            self.validation_tree.delete(item)
        
        # Run in thread
        threading.Thread(target=self._do_validation, daemon=True).start()
    
    def _do_validation(self):
        """Perform validation in background"""
        try:
            from src.data_handlers.test_results_workflow import TestResultsImportHandler
            
            handler = TestResultsImportHandler(self.db_manager)
            self.validation_result = handler.validate_import(
                self.file_path,
                self.project_id
            )
            
            self.after(0, self._show_validation_results)
            
        except Exception as e:
            self.after(0, lambda: self._show_error(str(e)))
    
    def _show_validation_results(self):
        """Display validation results"""
        self.progress.stop()
        
        if not self.validation_result:
            self.status_label.config(text="❌ Doğrulama başarısız")
            return
        
        result = self.validation_result
        
        # Update stats
        self.stat_labels['total'].config(text=str(result.total_rows))
        self.stat_labels['valid'].config(
            text=str(result.valid_rows),
            foreground='green' if result.valid_rows > 0 else 'gray'
        )
        self.stat_labels['invalid'].config(
            text=str(result.invalid_rows),
            foreground='red' if result.invalid_rows > 0 else 'gray'
        )
        self.stat_labels['duplicate'].config(
            text=str(result.duplicate_rows),
            foreground='orange' if result.duplicate_rows > 0 else 'gray'
        )
        self.stat_labels['orphaned'].config(
            text=str(result.orphaned_rows),
            foreground='red' if result.orphaned_rows > 0 else 'gray'
        )
        
        # Populate table
        for row in result.rows:
            if row.is_valid:
                if row.is_duplicate:
                    status = "🔄 Mevcut"
                    tag = 'duplicate'
                else:
                    status = "✅ Geçerli"
                    tag = 'valid'
            else:
                status = "❌ Geçersiz"
                tag = 'invalid'
            
            date_str = row.test_date.strftime("%Y-%m-%d") if row.test_date else "-"
            errors_str = "; ".join(row.validation_errors) if row.validation_errors else ""
            
            self.validation_tree.insert(
                '',
                'end',
                values=(row.row_number, row.formulation_code, date_str, status, errors_str),
                tags=(tag,)
            )
        
        # Update status and buttons
        if result.can_import:
            self.status_label.config(
                text=f"✅ {result.valid_rows} kayıt içe aktarılmaya hazır",
                foreground='green'
            )
            self.import_btn.config(state='normal')
        else:
            self.status_label.config(
                text="❌ İçe aktarılacak geçerli kayıt yok",
                foreground='red'
            )
        
        self.validate_btn.config(state='normal')
        
        # Show errors if any
        if result.errors:
            messagebox.showwarning(
                "Doğrulama Uyarıları",
                "\n".join(result.errors),
                parent=self
            )
    
    def _show_error(self, error: str):
        """Show error message"""
        self.progress.stop()
        self.status_label.config(text=f"❌ Hata: {error}", foreground='red')
        self.validate_btn.config(state='normal')
    
    def _start_import(self):
        """Start the import process"""
        if not self.validation_result or not self.validation_result.can_import:
            return
        
        # Confirm
        msg = f"📊 {self.validation_result.valid_rows} test sonucu içe aktarılacak."
        
        if self.validation_result.duplicate_rows > 0:
            if self.update_duplicates_var.get():
                msg += f"\n🔄 {self.validation_result.duplicate_rows} mevcut kayıt güncellenecek."
            else:
                msg += f"\n⏭ {self.validation_result.duplicate_rows} mevcut kayıt atlanacak."
        
        if self.validation_result.invalid_rows > 0:
            msg += f"\n❌ {self.validation_result.invalid_rows} geçersiz kayıt atlanacak."
        
        msg += "\n\nDevam edilsin mi?"
        
        if not messagebox.askyesno("İçe Aktarımı Onayla", msg, parent=self):
            return
        
        # Disable controls
        self.import_btn.config(state='disabled')
        self.validate_btn.config(state='disabled')
        
        # Start progress
        self.progress.start(10)
        self.status_label.config(text="⏳ İçe aktarılıyor...")
        
        # Run in thread
        threading.Thread(target=self._do_import, daemon=True).start()
    
    def _do_import(self):
        """Perform import in background"""
        try:
            from src.data_handlers.test_results_workflow import TestResultsImportHandler
            
            handler = TestResultsImportHandler(self.db_manager)
            result = handler.import_with_transaction(
                self.validation_result,
                update_duplicates=self.update_duplicates_var.get(),
                on_progress=lambda msg: self.after(0, lambda m=msg: self.status_label.config(text=m))
            )
            
            self.after(0, lambda: self._on_import_complete(result))
            
        except Exception as e:
            self.after(0, lambda: self._show_error(str(e)))
    
    def _on_import_complete(self, result):
        """Handle import completion"""
        self.progress.stop()
        
        if result.success:
            self.status_label.config(
                text=f"✅ {result.imported_count} eklendi, {result.updated_count} güncellendi",
                foreground='green'
            )
            
            messagebox.showinfo(
                "İçe Aktarım Tamamlandı",
                f"✅ Test sonuçları başarıyla içe aktarıldı!\n\n"
                f"📥 Yeni: {result.imported_count}\n"
                f"🔄 Güncellenen: {result.updated_count}\n"
                f"⏭ Atlanan: {result.skipped_count}",
                parent=self
            )
            
            if self.on_import_complete:
                self.on_import_complete()
            
            self.destroy()
        else:
            self.status_label.config(
                text=f"❌ {result.message}",
                foreground='red'
            )
            
            if result.rollback_performed:
                messagebox.showerror(
                    "İçe Aktarım Hatası",
                    f"❌ Hata oluştu, değişiklikler geri alındı.\n\n{result.message}",
                    parent=self
                )
            
            self.validate_btn.config(state='normal')
            self.import_btn.config(state='normal')


class ValidationReportDialog(tk.Toplevel):
    """
    Standalone dialog to show validation report before import.
    """
    
    def __init__(
        self,
        parent,
        validation_result,
        on_confirm: Callable = None,
        on_cancel: Callable = None
    ):
        super().__init__(parent)
        
        self.validation_result = validation_result
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.confirmed = False
        
        self.title("📋 Doğrulama Raporu")
        self.geometry("500x400")
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
        
        result = self.validation_result
        
        # Summary
        summary_text = (
            f"📊 DOĞRULAMA RAPORU\n\n"
            f"Toplam Satır: {result.total_rows}\n"
            f"✅ Geçerli: {result.valid_rows}\n"
            f"❌ Geçersiz: {result.invalid_rows}\n"
            f"🔄 Mevcut: {result.duplicate_rows}\n"
            f"❓ Sahipsiz: {result.orphaned_rows}"
        )
        
        ttk.Label(
            main_frame,
            text=summary_text,
            font=('Consolas', 10),
            justify=tk.LEFT
        ).pack(pady=10)
        
        # Can import message
        if result.can_import:
            msg = f"✅ {result.valid_rows} test sonucu içe aktarılmaya hazır."
            color = 'green'
        else:
            msg = "❌ İçe aktarılacak geçerli veri yok."
            color = 'red'
        
        ttk.Label(
            main_frame,
            text=msg,
            font=('Segoe UI', 11, 'bold'),
            foreground=color
        ).pack(pady=20)
        
        # Errors list
        if result.invalid_rows > 0:
            errors_frame = ttk.LabelFrame(main_frame, text="Hatalar", padding=10)
            errors_frame.pack(fill=tk.BOTH, expand=True)
            
            error_text = tk.Text(errors_frame, height=8, state='disabled', wrap=tk.WORD)
            error_text.pack(fill=tk.BOTH, expand=True)
            
            error_text.config(state='normal')
            for row in result.rows:
                if not row.is_valid:
                    error_text.insert(tk.END, f"Satır {row.row_number}: {row.formulation_code}\n")
                    for err in row.validation_errors:
                        error_text.insert(tk.END, f"  → {err}\n")
                    error_text.insert(tk.END, "\n")
            error_text.config(state='disabled')
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        if result.can_import:
            ttk.Button(
                btn_frame,
                text="📥 İçe Aktar",
                command=self._confirm,
                style='Accent.TButton'
            ).pack(side=tk.LEFT, padx=5, ipadx=20)
        
        ttk.Button(
            btn_frame,
            text="İptal",
            command=self._cancel
        ).pack(side=tk.RIGHT, padx=5)
    
    def _confirm(self):
        self.confirmed = True
        if self.on_confirm:
            self.on_confirm()
        self.destroy()
    
    def _cancel(self):
        if self.on_cancel:
            self.on_cancel()
        self.destroy()
