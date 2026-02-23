"""
Paint Formulation AI - Material Management Panel
=================================================
Malzeme yönetimi ve kimyasal özellik düzenleme paneli.

Özellikler:
- Malzeme listesi görüntüleme ve filtreleme
- pH, limit değerleri düzenleme
- Bulk import/export
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Dict, List, Optional
import logging
import json

from app.theme import COLORS, ICONS, configure_treeview_tags
from src.core.i18n import t, I18nMixin
from src.core.translation_keys import TK

logger = logging.getLogger(__name__)


class MaterialManagementPanel(ttk.Frame, I18nMixin):
    """
    Malzeme Yönetim Paneli
    
    Kimyasal özellikleri (pH, limitler) düzenleme arayüzü sağlar.
    Dynamic form fields based on selected category.
    """
    
    # Kategori listesi
    CATEGORIES = ['binder', 'pigment', 'filler', 'solvent', 'additive', 
                  'defoamer', 'thickener', 'dispersant', 'drier', 'biocide']
    
    # Category to visible fields mapping
    # Each category shows relevant properties, hides irrelevant ones
    CATEGORY_FIELDS = {
        'binder': {
            'sections': ['basic', 'physical', 'chemical', 'limits', 'cost'],
            'fields': ['name', 'category', 'code', 'density', 'solid_content', 'molecular_weight',
                      'oh_value', 'glass_transition', 'min_limit', 'max_limit', 'unit_price']
        },
        'pigment': {
            'sections': ['basic', 'physical', 'limits', 'pigment', 'cost'],
            'fields': ['name', 'category', 'code', 'density', 'ph',
                      'oil_absorption', 'particle_size', 'min_limit', 'max_limit', 'unit_price']
        },
        'filler': {
            'sections': ['basic', 'physical', 'limits', 'pigment', 'cost'],
            'fields': ['name', 'category', 'code', 'density', 'ph',
                      'oil_absorption', 'particle_size', 'min_limit', 'max_limit', 'unit_price']
        },
        'solvent': {
            'sections': ['basic', 'physical', 'solvent', 'cost'],
            'fields': ['name', 'category', 'code', 'density',
                      'boiling_point', 'evaporation_rate', 'voc_g_l', 'unit_price']
        },
        'additive': {
            'sections': ['basic', 'physical', 'chemical', 'limits', 'cost'],
            'fields': ['name', 'category', 'code', 'density', 'ph', 'solid_content',
                      'min_limit', 'max_limit', 'unit_price']
        },
        # Default for other categories
        'default': {
            'sections': ['basic', 'physical', 'chemical', 'limits', 'cost'],
            'fields': ['name', 'category', 'code', 'density', 'solid_content', 'ph',
                      'min_limit', 'max_limit', 'unit_price']
        }
    }
    
    def __init__(self, parent, db_manager, on_material_change: Callable = None):
        """
        Args:
            parent: Üst widget
            db_manager: LocalDBManager instance
            on_material_change: Malzeme değişikliği callback'i
        """
        super().__init__(parent)
        
        self.db_manager = db_manager
        self.on_material_change = on_material_change
        self.current_material_id = None
        self.materials = []
        
        self.setup_i18n()
        
        # Track form field frames for dynamic visibility
        self.field_frames = {}  # field_name -> frame widget
        self.section_header_labels = {} # section_id -> Label widget
        self.field_labels = {} # field_name -> Label widget
        self.section_frames = {}  # section_name -> (header_frame, separator)
        
        self._create_widgets()
        self._load_materials()
    
    def _create_widgets(self):
        """Widget'ları oluştur"""
        # Ana layout - sol liste, sağ detay
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # === Sol Panel - Malzeme Listesi ===
        self.left_frame = ttk.LabelFrame(main_paned, padding=5)
        main_paned.add(self.left_frame, weight=1)
        
        # Filtre alanı
        filter_frame = ttk.Frame(self.left_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_frame, text="🔍").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._filter_materials())
        ttk.Entry(filter_frame, textvariable=self.search_var, width=20).pack(side=tk.LEFT, padx=5)
        
        self.filter_cat_label = ttk.Label(filter_frame)
        self.filter_cat_label.pack(side=tk.LEFT, padx=(10, 0))
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var, 
                                       state='readonly', width=12)
        self.category_combo.pack(side=tk.LEFT, padx=5)
        self.category_combo.bind('<<ComboboxSelected>>', lambda e: self._filter_materials())
        
        # Malzeme listesi
        list_frame = ttk.Frame(self.left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('name', 'category', 'price')
        self.material_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        # Headings updated in _update_texts
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.material_tree.yview)
        self.material_tree.configure(yscrollcommand=scrollbar.set)
        
        self.material_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.material_tree.bind('<<TreeviewSelect>>', self._on_material_select)
        
        # Liste butonları - with themed styling
        btn_frame = ttk.Frame(self.left_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.new_btn = ttk.Button(btn_frame, command=self._new_material, width=10)
        self.new_btn.pack(side=tk.LEFT, padx=2)
        self.refresh_btn = ttk.Button(btn_frame, command=self._load_materials, width=10)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)
        self.import_btn = ttk.Button(btn_frame, command=self._import_materials, width=10)
        self.import_btn.pack(side=tk.LEFT, padx=2)
        
        # === Sağ Panel - Malzeme Detayları ===
        self.right_frame = ttk.LabelFrame(main_paned, padding=10)
        main_paned.add(self.right_frame, weight=2)
        
        # Scrollable form
        canvas = tk.Canvas(self.right_frame, highlightthickness=0)
        scrollbar_r = ttk.Scrollbar(self.right_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.form_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar_r.set)
        scrollbar_r.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        canvas_frame = canvas.create_window((0, 0), window=self.form_frame, anchor='nw')
        
        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox('all'))
            canvas.itemconfig(canvas_frame, width=event.width)
        
        self.form_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', configure_scroll)
        
        # Form alanları
        self.entries = {}
        
        # Temel bilgiler
        self._add_section("basic", "📋 Temel Bilgiler")
        self._add_entry("name", "Malzeme Adı *", width=30)
        self._add_combo("category", "Kategori *", self.CATEGORIES, width=15)
        self._add_entry("code", "Kod", width=15)
        
        # Fiziksel özellikler
        self._add_section("physical", "⚖️ Fiziksel Özellikler")
        self._add_entry("density", "Yoğunluk (g/cm³)", width=10)
        self._add_entry("solid_content", "Katı İçeriği (%)", width=10)
        self._add_entry("molecular_weight", "Mol. Ağırlık", width=10)
        
        # pH ve Kimyasal
        self._add_section("chemical", "🧪 Kimyasal Özellikler")
        self._add_entry("ph", "pH Değeri", width=10)
        self._add_entry("oh_value", "OH Değeri (mg KOH/g)", width=10)
        self._add_entry("glass_transition", "Cam Geçiş Sıcaklığı (Tg)", width=10)
        
        # Limitler
        self._add_section("limits", "⚠️ Kullanım Limitleri")
        self._add_entry("min_limit", "Min Kullanım (%)", width=10)
        self._add_entry("max_limit", "Max Kullanım (%)", width=10)
        
        # Pigment özellikleri
        self._add_section("pigment", "🎨 Pigment/Dolgu Özellikleri")
        self._add_entry("oil_absorption", "Yağ Absorpsiyonu", width=10)
        self._add_entry("particle_size", "Parçacık Boyutu (µm)", width=10)
        
        # Solvent özellikleri
        self._add_section("solvent", "💧 Çözücü Özellikleri")
        self._add_entry("boiling_point", "Kaynama Noktası (°C)", width=10)
        self._add_entry("evaporation_rate", "Buharlaşma Hızı", width=10)
        self._add_entry("voc_g_l", "VOC (g/L)", width=10)
        
        # Maliyet
        self._add_section("cost", "💰 Maliyet")
        self._add_entry("unit_price", "Birim Fiyat (TL/kg)", width=10)
        
        # Kaydet butonu - with themed styling
        save_frame = ttk.Frame(self.form_frame)
        save_frame.pack(fill=tk.X, pady=(20, 5))
        
        self.save_btn = ttk.Button(save_frame, command=self._save_material, 
                   style="Primary.TButton")
        self.save_btn.pack(side=tk.LEFT, padx=5)
        self.delete_btn = ttk.Button(save_frame, command=self._delete_material,
                   style="Danger.TButton")
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        self.clear_btn = ttk.Button(save_frame, command=self._clear_form)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        self._update_texts()
    
    def _update_texts(self):
        """Update UI texts for i18n"""
        self.left_frame.config(text=t(TK.NAV_MATERIALS))
        self.right_frame.config(text=t(TK.MAT_TITLE))
        
        self.filter_cat_label.config(text=t(TK.MAT_CATEGORY))
        current_filter = self.category_var.get()
        filter_vals = [t(TK.MAT_FILTER_ALL)] + self.CATEGORIES
        self.category_combo.config(values=filter_vals)
        if not current_filter or current_filter == "Tümü" or current_filter == "All":
             self.category_var.set(t(TK.MAT_FILTER_ALL))

        # Headings
        self.material_tree.heading('name', text=t(TK.MAT_NAME).strip('*: '))
        self.material_tree.heading('category', text=t(TK.MAT_CATEGORY).strip(': '))
        self.material_tree.heading('price', text=t(TK.MAT_UNIT_PRICE).strip(': '))
        
        # Buttons
        self.new_btn.config(text=f"{ICONS['add']} " + t(TK.common_add if hasattr(TK, 'common_add') else TK.ADD)) # Fix if TK.common_add is used
        self.refresh_btn.config(text=f"{ICONS['refresh']} " + t(TK.REFRESH))
        self.import_btn.config(text=f"{ICONS['import']} " + t(TK.FORM_IMPORT))
        self.save_btn.config(text=f"{ICONS['save']} " + t(TK.SAVE))
        self.delete_btn.config(text=f"{ICONS['delete']} " + t(TK.DELETE))
        self.clear_btn.config(text=f"{ICONS['clear'] if 'clear' in ICONS else ''} " + t(TK.FORM_CLEAN))

        # Section Headers
        section_titles = {
            "basic": TK.MAT_BASIC_INFO,
            "physical": TK.MAT_PHYSICAL_PROP,
            "chemical": TK.MAT_CHEMICAL_PROP,
            "limits": TK.MAT_LIMITS,
            "pigment": TK.MAT_PIGMENT_PROP,
            "solvent": TK.MAT_SOLVENT_PROP,
            "cost": TK.MAT_COST
        }
        for sid, label in self.section_header_labels.items():
             label.config(text=t(section_titles.get(sid, sid)))

        # Field Labels
        field_keys = {
            "name": TK.MAT_NAME,
            "category": TK.MAT_CATEGORY,
            "code": TK.MAT_CODE,
            "density": TK.MAT_DENSITY,
            "solid_content": TK.MAT_SOLID_CONTENT,
            "molecular_weight": TK.MAT_MOL_WEIGHT,
            "ph": TK.MAT_PH,
            "oh_value": TK.MAT_OH_VALUE,
            "glass_transition": TK.MAT_TG,
            "min_limit": TK.MAT_MIN_LIMIT,
            "max_limit": TK.MAT_MAX_LIMIT,
            "oil_absorption": TK.MAT_OIL_ABSORPTION,
            "particle_size": TK.MAT_PARTICLE_SIZE,
            "boiling_point": TK.MAT_BOILING_POINT,
            "evaporation_rate": TK.MAT_EVAPORATION_RATE,
            "voc_g_l": TK.MAT_VOC,
            "unit_price": TK.MAT_UNIT_PRICE
        }
        for fname, label in self.field_labels.items():
             label.config(text=t(field_keys.get(fname, fname)))
    
    def _add_section(self, section_id: str, title: str):
        """Bölüm başlığı ekle - with tracking for visibility"""
        header_frame = ttk.Frame(self.form_frame)
        header_frame.pack(fill=tk.X, pady=(15, 5))
        lbl = ttk.Label(header_frame, text=title, font=('Segoe UI', 10, 'bold'))
        lbl.pack(anchor='w')
        self.section_header_labels[section_id] = lbl
        
        separator = ttk.Separator(self.form_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=2)
        
        # Store reference for dynamic visibility
        self.section_frames[section_id] = (header_frame, separator)
    
    def _add_entry(self, name: str, label: str, width: int = 20, tooltip: str = None):
        """Giriş alanı ekle - with tracking for visibility"""
        frame = ttk.Frame(self.form_frame)
        frame.pack(fill=tk.X, pady=2)
        
        lbl_text = f"{label}:" if tooltip is None else f"{label} ({tooltip}):"
        lbl = ttk.Label(frame, text=lbl_text, width=25)
        lbl.pack(side=tk.LEFT)
        self.field_labels[name] = lbl
        
        var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=var, width=width)
        entry.pack(side=tk.LEFT, padx=5)
        
        self.entries[name] = var
        self.field_frames[name] = frame  # Track frame for visibility
    
    def _add_combo(self, name: str, label: str, values: List[str], width: int = 15):
        """Combo box ekle - with event binding for category"""
        frame = ttk.Frame(self.form_frame)
        frame.pack(fill=tk.X, pady=2)
        
        lbl = ttk.Label(frame, width=25)
        lbl.pack(side=tk.LEFT)
        self.field_labels[name] = lbl
        
        var = tk.StringVar()
        combo = ttk.Combobox(frame, textvariable=var, values=values, width=width, state='readonly')
        combo.pack(side=tk.LEFT, padx=5)
        
        # Bind category change event
        if name == 'category':
            combo.bind('<<ComboboxSelected>>', self._on_category_changed)
            self.category_combo = combo
        
        self.entries[name] = var
        self.field_frames[name] = frame  # Track frame for visibility
    
    def _on_category_changed(self, event=None):
        """Handle category selection change - update visible fields"""
        selected_category = self.entries.get('category', tk.StringVar()).get()
        self._update_form_fields(selected_category)
    
    def _update_form_fields(self, category: str):
        """
        Update form field visibility based on selected category.
        Uses pack_forget() and pack() to toggle visibility.
        
        Args:
            category: Selected material category
        """
        # Get field configuration for this category
        config = self.CATEGORY_FIELDS.get(category, self.CATEGORY_FIELDS['default'])
        visible_sections = config.get('sections', [])
        visible_fields = config.get('fields', [])
        
        # Update section visibility
        for section_id, (header_frame, separator) in self.section_frames.items():
            if section_id in visible_sections:
                # Show section
                header_frame.pack(fill=tk.X, pady=(15, 5))
                separator.pack(fill=tk.X, pady=2)
            else:
                # Hide section
                header_frame.pack_forget()
                separator.pack_forget()
        
        # Update field visibility
        for field_name, frame in self.field_frames.items():
            if field_name in visible_fields:
                # Show field
                frame.pack(fill=tk.X, pady=2)
            else:
                # Hide field
                frame.pack_forget()
        
        # Re-pack elements in correct order
        self._reorder_form_elements(visible_sections, visible_fields)
    
    def _reorder_form_elements(self, visible_sections: List[str], visible_fields: List[str]):
        """
        Reorder form elements to maintain proper layout after visibility changes.
        """
        # Define the order of sections and their fields
        section_field_map = {
            'basic': ['name', 'category', 'code'],
            'physical': ['density', 'solid_content', 'molecular_weight'],
            'chemical': ['ph', 'oh_value', 'glass_transition'],
            'limits': ['min_limit', 'max_limit'],
            'pigment': ['oil_absorption', 'particle_size'],
            'solvent': ['boiling_point', 'evaporation_rate', 'voc_g_l'],
            'cost': ['unit_price']
        }
        
        section_order = ['basic', 'physical', 'chemical', 'limits', 'pigment', 'solvent', 'cost']
        
        # First, unpack everything
        for section_id, (header_frame, separator) in self.section_frames.items():
            header_frame.pack_forget()
            separator.pack_forget()
        
        for field_name, frame in self.field_frames.items():
            frame.pack_forget()
        
        # Then, repack in order (only visible ones)
        for section_id in section_order:
            if section_id in visible_sections and section_id in self.section_frames:
                header_frame, separator = self.section_frames[section_id]
                header_frame.pack(fill=tk.X, pady=(15, 5))
                separator.pack(fill=tk.X, pady=2)
                
                # Pack fields for this section
                for field_name in section_field_map.get(section_id, []):
                    if field_name in visible_fields and field_name in self.field_frames:
                        self.field_frames[field_name].pack(fill=tk.X, pady=2)
    
    def _load_materials(self):
        """Malzemeleri veritabanından yükle"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, category, 
                           density, solid_content, ph, min_limit, max_limit,
                           unit_price, oh_value, glass_transition, molecular_weight,
                           oil_absorption, particle_size, boiling_point, evaporation_rate,
                           voc_g_l, code
                    FROM materials
                    ORDER BY category, name
                ''')
                
                self.materials = []
                for row in cursor.fetchall():
                    self.materials.append({
                        'id': row[0],
                        'name': row[1],
                        'category': row[2],
                        'density': row[3],
                        'solid_content': row[4],
                        'ph': row[5],
                        'min_limit': row[6],
                        'max_limit': row[7],
                        'unit_price': row[8],
                        'oh_value': row[9],
                        'glass_transition': row[10],
                        'molecular_weight': row[11],
                        'oil_absorption': row[12],
                        'particle_size': row[13],
                        'boiling_point': row[14],
                        'evaporation_rate': row[15],
                        'voc_g_l': row[16],
                        'code': row[17]
                    })
            
            self._filter_materials()
            logger.info(f"{len(self.materials)} malzeme yüklendi")
            
        except Exception as e:
            logger.error(f"Malzeme yükleme hatası: {e}")
            messagebox.showerror("Hata", f"Malzemeler yüklenemedi: {e}")
    
    def _filter_materials(self):
        """Malzemeleri filtrele ve listeyi güncelle"""
        # Mevcut öğeleri temizle
        for item in self.material_tree.get_children():
            self.material_tree.delete(item)
        
        search = self.search_var.get().lower()
        category = self.category_var.get()
        
        for mat in self.materials:
            # Filtre kontrolü
            if search and search not in (mat['name'] or '').lower():
                continue
            if category != "Tümü" and mat['category'] != category:
                continue
            
            # Fiyat gösterimi
            price = f"{mat.get('unit_price', 0) or 0:.2f}" if mat.get('unit_price') else "-"
            
            self.material_tree.insert('', 'end', iid=mat['id'],
                                       values=(mat['name'], mat['category'] or '', price))
    
    def _on_material_select(self, event):
        """Malzeme seçildiğinde"""
        selection = self.material_tree.selection()
        if not selection:
            return
        
        material_id = int(selection[0])
        self.current_material_id = material_id
        
        # Malzeme verilerini bul
        material = next((m for m in self.materials if m['id'] == material_id), None)
        if not material:
            return
        
        # Formu doldur
        for key, var in self.entries.items():
            value = material.get(key)
            var.set(str(value) if value is not None else '')
        
        # Update form fields based on category
        category = material.get('category', '')
        if category:
            self._update_form_fields(category)
    
    def _save_material(self):
        """Malzemeyi kaydet"""
        name = self.entries['name'].get().strip()
        if not name:
            messagebox.showwarning("Uyarı", "Malzeme adı zorunludur.")
            return
        
        category = self.entries['category'].get()
        if not category:
            messagebox.showwarning("Uyarı", "Kategori seçimi zorunludur.")
            return
        
        try:
            # Değerleri topla
            data = {}
            for key, var in self.entries.items():
                value = var.get().strip()
                if value:
                    # Sayısal alanları dönüştür
                    if key in ['density', 'solid_content', 'ph', 'min_limit', 'max_limit', 'unit_price',
                               'oh_value', 'glass_transition', 'molecular_weight', 'oil_absorption',
                               'particle_size', 'boiling_point', 'evaporation_rate', 'voc_g_l']:
                        try:
                            data[key] = float(value)
                        except ValueError:
                            pass
                    else:
                        data[key] = value
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.current_material_id:
                    # Güncelle
                    set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
                    values = list(data.values()) + [self.current_material_id]
                    cursor.execute(f'UPDATE materials SET {set_clause} WHERE id = ?', values)
                    msg = f"'{name}' güncellendi."
                else:
                    # Yeni ekle
                    columns = ', '.join(data.keys())
                    placeholders = ', '.join(['?' for _ in data])
                    cursor.execute(f'INSERT INTO materials ({columns}) VALUES ({placeholders})', 
                                   list(data.values()))
                    self.current_material_id = cursor.lastrowid
                    msg = f"'{name}' eklendi."
                
                conn.commit()
            
            messagebox.showinfo("Başarılı", msg)
            self._load_materials()
            
            # Select the newly saved/updated material in the tree
            if self.current_material_id:
                try:
                    self.material_tree.selection_set(str(self.current_material_id))
                    self.material_tree.see(str(self.current_material_id))
                except (tk.TclError, ValueError):
                    pass  # Tree item may not exist yet
            
            # Callback
            if self.on_material_change:
                self.on_material_change()
            
        except Exception as e:
            logger.error(f"Malzeme kaydetme hatası: {e}")
            messagebox.showerror("Hata", f"Kaydetme başarısız: {e}")
    
    def _delete_material(self):
        """Malzemeyi sil"""
        if not self.current_material_id:
            messagebox.showwarning("Uyarı", "Silinecek malzeme seçilmedi.")
            return
        
        name = self.entries['name'].get()
        if not messagebox.askyesno(t(TK.common_confirm if hasattr(TK, 'common_confirm') else TK.CONFIRM), t(TK.MSG_DELETE_CONFIRM).replace('{item}', f"'{name}'")):
            return
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM materials WHERE id = ?', (self.current_material_id,))
                conn.commit()
            
            messagebox.showinfo("Başarılı", f"'{name}' silindi.")
            self._clear_form()
            self._load_materials()
            
            # Notify about material change for ML reindexing
            if self.on_material_change:
                self.on_material_change()
            
        except Exception as e:
            logger.error(f"Malzeme silme hatası: {e}")
            messagebox.showerror("Hata", f"Silme başarısız: {e}")
    
    def _new_material(self):
        """Yeni malzeme formu"""
        self._clear_form()
        self.current_material_id = None
    
    def _update_texts(self):
        """Update texts for i18n"""
        # Search label
        if hasattr(self, 'search_label'):
            self.search_label.config(text=t(TK.MAT_SEARCH))
        
        # Category filter labels
        if hasattr(self, 'cat_label'):
            self.cat_label.config(text=t(TK.MAT_CATEGORY))
        
        # All filter
        if hasattr(self, 'category_listbox'):
            # This is harder as it's a listbox, but we can update static labels
            pass

        # Treeview headers
        if hasattr(self, 'tree'):
            self.tree.heading("name", text=t(TK.MAT_NAME))
            self.tree.heading("code", text=t(TK.MAT_CODE))
            self.tree.heading("category", text=t(TK.MAT_CATEGORY))
            self.tree.heading("density", text=t(TK.MAT_DENSITY))
            self.tree.heading("solid", text=t(TK.MAT_SOLID_CONTENT))
            self.tree.heading("price", text=t(TK.MAT_COST))

        # Detail Panel Headers
        for key, widget in self.section_header_labels.items():
            # key is section identifier like 'basic', 'physical'
            # Map section name to TK key
            section_map = {
                'basic': TK.MAT_BASIC_INFO,
                'physical': TK.MAT_PHYSICAL_PROP,
                'chemical': TK.MAT_CHEMICAL_PROP,
                'limits': TK.MAT_LIMITS,
                'pigment': TK.MAT_PIGMENT_PROP,
                'solvent': TK.MAT_SOLVENT_PROP,
                'cost': TK.MAT_COST
            }
            if key in section_map:
                widget.config(text=t(section_map[key]))

        # Field Labels
        field_map = {
            'name': TK.MAT_NAME,
            'code': TK.MAT_CODE,
            'category': TK.MAT_CATEGORY,
            'density': TK.MAT_DENSITY,
            'solid_content': TK.MAT_SOLID_CONTENT,
            'unit_price': TK.MAT_UNIT_PRICE,
            'ph': TK.MAT_PH,
            'molecular_weight': TK.MAT_MOL_WEIGHT,
            'glass_transition': TK.MAT_TG,
            'oh_value': TK.MAT_OH_VALUE,
            'min_limit': TK.MAT_MIN_LIMIT,
            'max_limit': TK.MAT_MAX_LIMIT,
            'oil_absorption': TK.MAT_OIL_ABSORPTION,
            'particle_size': TK.MAT_PARTICLE_SIZE,
            'boiling_point': TK.MAT_BOILING_POINT,
            'evaporation_rate': TK.MAT_EVAPORATION_RATE,
            'voc_g_l': TK.MAT_VOC
        }
        for key, widget in self.field_labels.items():
            if key in field_map:
                widget.config(text=t(field_map[key]) + ":")

        # Buttons
        if hasattr(self, 'save_btn'):
            self.save_btn.config(text=t(TK.SAVE))
        if hasattr(self, 'delete_btn'):
            self.delete_btn.config(text=t(TK.DELETE))
        if hasattr(self, 'import_btn'):
            self.import_btn.config(text=f"{ICONS['import']} Excel {t(TK.FORM_IMPORT)}")
        if hasattr(self, 'export_btn'):
            self.export_btn.config(text=f"{ICONS['export']} Excel {t(TK.FORM_EXPORT)}")
    
    def _clear_form(self):
        """Formu temizle"""
        self.current_material_id = None
        for var in self.entries.values():
            var.set('')
        
        # Seçimi kaldır
        for item in self.material_tree.selection():
            self.material_tree.selection_remove(item)
    
    def _import_materials(self):
        """Excel/CSV'den malzeme import et"""
        file_path = filedialog.askopenfilename(
            title="Malzeme Dosyası Seç",
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            import pandas as pd
            
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Sütun eşleştirme
            column_mapping = {
                'name': ['name', 'malzeme', 'ad', 'material'],
                'category': ['category', 'kategori', 'type', 'tip'],
                'density': ['density', 'yoğunluk', 'özgül ağırlık'],
                'ph': ['ph'],
                'solid_content': ['solid_content', 'katı', 'solid'],
                'min_limit': ['min_limit', 'min', 'minimum'],
                'max_limit': ['max_limit', 'max', 'maximum'],
                'unit_price': ['unit_price', 'fiyat', 'price']
            }
            
            # Sütunları normalize et
            df.columns = df.columns.str.lower().str.strip()
            
            imported = 0
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                for _, row in df.iterrows():
                    data = {'name': None, 'category': 'additive'}
                    
                    for target, sources in column_mapping.items():
                        for src in sources:
                            if src in df.columns:
                                val = row.get(src)
                                if pd.notna(val):
                                    data[target] = val
                                break
                    
                    if not data.get('name'):
                        continue
                    
                    # Mevcut mu kontrol et
                    cursor.execute('SELECT id FROM materials WHERE name = ?', (data['name'],))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Güncelle
                        set_clause = ', '.join([f"{k} = ?" for k in data.keys() if k != 'name'])
                        values = [v for k, v in data.items() if k != 'name'] + [data['name']]
                        cursor.execute(f'UPDATE materials SET {set_clause} WHERE name = ?', values)
                    else:
                        # Ekle
                        columns = ', '.join(data.keys())
                        placeholders = ', '.join(['?' for _ in data])
                        cursor.execute(f'INSERT INTO materials ({columns}) VALUES ({placeholders})',
                                       list(data.values()))
                    
                    imported += 1
                
                conn.commit()
            
            messagebox.showinfo("Başarılı", f"{imported} malzeme import edildi.")
            self._load_materials()
            
        except ImportError:
            messagebox.showerror("Hata", "pandas kütüphanesi gerekli: pip install pandas openpyxl")
        except Exception as e:
            logger.error(f"Import hatası: {e}")
            messagebox.showerror("Hata", f"Import başarısız: {e}")
