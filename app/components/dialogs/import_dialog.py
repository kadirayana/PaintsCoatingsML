"""
Paint Formulation AI - Import Dialog
====================================
Dialog for Excel import with lazy material creation and user notifications.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional, List, Dict


class ImportProgressDialog(tk.Toplevel):
    """Dialog showing import progress and results"""
    
    def __init__(self, parent, title="İçe Aktarım"):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x400")
        self.transient(parent)
        
        # Make modal
        self.grab_set()
        
        self._create_ui()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="⏳ İçe aktarım hazırlanıyor...",
            font=('Segoe UI', 11)
        )
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        self.progress.pack(fill=tk.X, pady=10)
        self.progress.start(10)
        
        # Results text area with scrollbar
        results_frame = ttk.LabelFrame(main_frame, text="Sonuçlar", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(results_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.results_text = tk.Text(
            results_frame,
            wrap=tk.WORD,
            height=10,
            state='disabled',
            font=('Consolas', 9),
            bg='#1E1E1E',
            fg='#00FF00'
        )
        self.results_text.pack(fill=tk.BOTH, expand=True)
        self.results_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.results_text.yview)
        
        # Button frame
        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.close_btn = ttk.Button(
            self.button_frame,
            text="Kapat",
            command=self.destroy,
            state='disabled'
        )
        self.close_btn.pack(side=tk.RIGHT, padx=5)
        
        self.quickfix_btn = ttk.Button(
            self.button_frame,
            text="🔧 Eksik hammaddeleri Düzenle",
            command=self._on_quickfix,
            state='disabled'
        )
        self.quickfix_btn.pack(side=tk.RIGHT, padx=5)
        
        # Callbacks
        self.on_quickfix_callback = None
        self.incomplete_materials = []
    
    def update_status(self, message: str):
        """Update status label"""
        self.status_label.config(text=message)
        self.update_idletasks()
    
    def add_result_line(self, line: str):
        """Add a line to results"""
        self.results_text.config(state='normal')
        self.results_text.insert(tk.END, line + "\n")
        self.results_text.see(tk.END)
        self.results_text.config(state='disabled')
        self.update_idletasks()
    
    def show_result(self, result, on_quickfix: Callable = None):
        """Display final import result"""
        self.progress.stop()
        self.on_quickfix_callback = on_quickfix
        
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        
        if result.success:
            self.status_label.config(text="✅ İçe Aktarım Tamamlandı")
            
            self.results_text.insert(tk.END, "═" * 45 + "\n")
            self.results_text.insert(tk.END, "  İÇE AKTARIM BAŞARILI\n")
            self.results_text.insert(tk.END, "═" * 45 + "\n\n")
            
            self.results_text.insert(tk.END, f"📊 Formülasyon: {result.formulations_imported} adet\n")
            self.results_text.insert(tk.END, f"🧪 Yeni hammadde: {result.materials_created} adet\n")
            
            if result.incomplete_materials:
                self.incomplete_materials = result.incomplete_materials
                self.results_text.insert(tk.END, "\n" + "─" * 45 + "\n")
                self.results_text.insert(tk.END, "⚠️ EKSİK BİLGİLİ hammaddeler:\n")
                self.results_text.insert(tk.END, "─" * 45 + "\n\n")
                
                for mat in result.incomplete_materials[:10]:  # Show first 10
                    self.results_text.insert(tk.END, f"  • {mat.get('code', '')} - {mat.get('name', '')}\n")
                
                if len(result.incomplete_materials) > 10:
                    self.results_text.insert(tk.END, f"\n  ... ve {len(result.incomplete_materials) - 10} tane daha\n")
                
                self.results_text.insert(tk.END, "\n💡 Bu hammaddelerin fiziksel özelliklerini\n")
                self.results_text.insert(tk.END, "   hammaddeler sekmesinden tamamlayın.\n")
                
                # Enable quickfix button
                self.quickfix_btn.config(state='normal')
        else:
            self.status_label.config(text="❌ İçe Aktarım Başarısız")
            
            self.results_text.insert(tk.END, "═" * 45 + "\n")
            self.results_text.insert(tk.END, "  HATA\n")
            self.results_text.insert(tk.END, "═" * 45 + "\n\n")
            self.results_text.insert(tk.END, f"{result.message}\n")
        
        if result.errors:
            self.results_text.insert(tk.END, "\n" + "─" * 45 + "\n")
            self.results_text.insert(tk.END, "⚠️ UYARILAR:\n")
            self.results_text.insert(tk.END, "─" * 45 + "\n")
            for err in result.errors[:5]:
                self.results_text.insert(tk.END, f"  • {err}\n")
        
        self.results_text.config(state='disabled')
        self.close_btn.config(state='normal')
    
    def _on_quickfix(self):
        """Handle quickfix button click"""
        if self.on_quickfix_callback:
            self.on_quickfix_callback(self.incomplete_materials)
        self.destroy()


class IncompletematerialsNotification:
    """
    Utility class to show notifications about incomplete materials.
    """
    
    @staticmethod
    def show(parent, incomplete_count: int, on_goto_materials: Callable = None):
        """
        Show a notification dialog about incomplete materials.
        
        Args:
            parent: Parent widget
            incomplete_count: Number of incomplete materials
            on_goto_materials: Callback to navigate to materials tab
        """
        if incomplete_count == 0:
            return
        
        message = (
            f"⚠️ Dikkat!\n\n"
            f"Veritabanında {incomplete_count} adet eksik bilgili hammadde bulundu.\n\n"
            f"Bu hammaddelerin fiziksel özellikleri (yoğunluk, katı içeriği vb.) "
            f"tamamlanmadan ML modeli doğru tahminler yapamaz.\n\n"
            f"hammaddeler sekmesine gidip bu bilgileri doldurmak ister misiniz?"
        )
        
        result = messagebox.askyesno(
            "Eksik hammadde Bilgisi",
            message,
            parent=parent,
            icon='warning'
        )
        
        if result and on_goto_materials:
            on_goto_materials()
    
    @staticmethod
    def show_import_result(parent, result, on_goto_materials: Callable = None):
        """
        Show import result notification.
        
        Args:
            parent: Parent widget
            result: ImportResult object
            on_goto_materials: Callback to navigate to materials tab
        """
        if result.success:
            message = (
                f"✅ İçe Aktarım Başarılı!\n\n"
                f"• {result.formulations_imported} formülasyon eklendi\n"
            )
            
            if result.materials_created > 0:
                message += (
                    f"• {result.materials_created} yeni hammadde oluşturuldu\n\n"
                    f"⚠️ Uyarı: Yeni oluşturulan hammaddelerin fiziksel özellikleri eksik.\n"
                    f"Lütfen hammaddeler sekmesinden tamamlayın."
                )
                
                answer = messagebox.askyesno(
                    "İçe Aktarım Tamamlandı",
                    message + "\n\nhammaddeler sekmesine gitmek ister misiniz?",
                    parent=parent
                )
                
                if answer and on_goto_materials:
                    on_goto_materials()
            else:
                messagebox.showinfo("İçe Aktarım Tamamlandı", message, parent=parent)
        else:
            messagebox.showerror(
                "İçe Aktarım Hatası",
                f"❌ İçe aktarım başarısız!\n\n{result.message}",
                parent=parent
            )


class MaterialAutoCompleteEntry(ttk.Combobox):
    """
    Combobox with autocomplete functionality for material code/name.
    Implements two-way binding between code and name.
    """
    
    def __init__(self, parent, lookup_service, mode='code', on_change: Callable = None, **kwargs):
        """
        Args:
            parent: Parent widget
            lookup_service: MaterialLookupService instance
            mode: 'code' or 'name' - which field this represents
            on_change: Callback when value changes (receives selected material dict)
        """
        super().__init__(parent, **kwargs)
        
        self.lookup_service = lookup_service
        self.mode = mode
        self.on_change = on_change
        self._paired_widget = None
        
        # Set values based on mode
        self.refresh_values()
        
        # Bind events
        self.bind('<KeyRelease>', self._on_key_release)
        self.bind('<<ComboboxSelected>>', self._on_selected)
        self.bind('<FocusOut>', self._on_focus_out)
    
    def set_paired_widget(self, widget):
        """Set the paired widget for two-way binding"""
        self._paired_widget = widget
    
    def refresh_values(self):
        """Refresh the dropdown values from lookup service"""
        if self.mode == 'code':
            self['values'] = self.lookup_service.get_all_codes()
        else:
            self['values'] = self.lookup_service.get_all_names()
    
    def _on_key_release(self, event):
        """Handle typing for autocomplete"""
        value = self.get()
        if not value:
            return
        
        # Filter values that start with typed text
        if self.mode == 'code':
            all_values = self.lookup_service.get_all_codes()
        else:
            all_values = self.lookup_service.get_all_names()
        
        filtered = [v for v in all_values if v.lower().startswith(value.lower())]
        
        if filtered:
            self['values'] = filtered
        else:
            self['values'] = all_values
    
    def _on_selected(self, event=None):
        """Handle selection from dropdown"""
        value = self.get()
        self._update_paired_widget(value)
        self._notify_change(value)
    
    def _on_focus_out(self, event=None):
        """Handle focus out - validate and update"""
        value = self.get().strip()
        if value:
            self._update_paired_widget(value)
            self._notify_change(value)
    
    def _update_paired_widget(self, value: str):
        """Update the paired widget with corresponding value"""
        if not self._paired_widget:
            return
        
        if self.mode == 'code':
            # Get name by code
            name = self.lookup_service.get_name_by_code(value)
            if name:
                self._paired_widget.set(name)
        else:
            # Get code by name
            code = self.lookup_service.get_code_by_name(value)
            if code:
                self._paired_widget.set(code)
    
    def _notify_change(self, value: str):
        """Notify callback about change"""
        if self.on_change:
            material = self.lookup_service.get_material_by_code_or_name(value)
            self.on_change(material)
    
    def is_valid(self) -> bool:
        """Check if current value is a valid material"""
        value = self.get().strip()
        return self.lookup_service.is_valid_material(value) if value else False
    
    def is_complete(self) -> bool:
        """Check if current material has complete properties"""
        value = self.get().strip()
        return self.lookup_service.is_material_complete(value) if value else False


def create_import_button(parent, command: Callable, **kwargs) -> ttk.Button:
    """
    Create a styled import button for formulation editor.
    
    Args:
        parent: Parent widget
        command: Command to execute on click
        **kwargs: Additional button options
        
    Returns:
        ttk.Button
    """
    return ttk.Button(
        parent,
        text="📥 Excel'den İçe Aktar (Lazy)",
        command=command,
        **kwargs
    )
