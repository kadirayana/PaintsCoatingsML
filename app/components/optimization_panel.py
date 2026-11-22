"""
Paint Formulation AI - Reçete Optimizasyonu Paneli
==================================================
Hedef özellikleri alır, Genetik Algoritma (MLOptimizer) ile reçete önerir.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable
import threading


class RecipeOptimizationPanel(ttk.LabelFrame):
    """
    Çoklu Hedef Optimizasyonu Paneli
    Genetik Algoritma kullanarak hedeflenen özellikleri sağlayan reçeteyi bulur.
    """
    
    def __init__(self, parent, on_generate_recipe: Callable = None, on_apply_recipe: Callable = None):
        """
        Args:
            parent: Ebeveyn widget
            on_apply_recipe: Önerilen reçeteyi uygulama callback'i
            on_generate_recipe: Yeni Reçete Üretme (Genetik Algoritma) callback'i
        """
        super().__init__(parent, text="🎯 Reçete Optimizasyonu (AI)", padding=10)
        
        self.on_apply_recipe = on_apply_recipe
        self.on_generate_recipe = on_generate_recipe 
        
        self._create_ui()
    
    def _create_ui(self):
        # Üst Panel: Hedefler
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Açıklama
        ttk.Label(
            top_frame,
            text="İstenen özellikleri girin, Makine öğrenmesi en uygun reçeteyi bulsun.",
            font=('Helvetica', 9, 'italic'),
            wraplength=400
        ).pack(anchor=tk.W, pady=(0, 5))
        
        # Model status warning label
        self.model_status_label = ttk.Label(
            top_frame,
            text="⚠️ Önce ML modelini eğitmeniz gerekiyor",
            foreground="orange",
            font=('Helvetica', 9, 'bold')
        )
        self.model_status_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Hedef Ekleme Paneli
        target_frame = ttk.LabelFrame(top_frame, text="Hedefler", padding=5)
        target_frame.pack(fill=tk.X, expand=True)
        
        # Hedef Giriş Alanları
        self.targets = {}
        
        # Grid layout
        grid_frame = ttk.Frame(target_frame)
        grid_frame.pack(fill=tk.X)
        
        common_targets = [
            ('gloss', 'Parlaklık (GU)', '85'),
            ('corrosion_resistance', 'Korozyon (h)', '500'),
            ('total_cost', 'Maliyet (TL)', '50'),
            ('opacity', 'Örtücülük (%)', '98'),
            ('hardness', 'Sertlik (H)', '2'),
            ('adhesion', 'Yapışma (0-5)', '5')
        ]
        
        for i, (key, label, default) in enumerate(common_targets):
            row = i // 2
            col = i % 2
            
            f = ttk.Frame(grid_frame)
            f.grid(row=row, column=col, padx=10, pady=5, sticky='w')
            
            # Checkbox (Aktif/Pasif)
            var_active = tk.BooleanVar(value=False)
            ttk.Checkbutton(f, variable=var_active).pack(side=tk.LEFT)
            
            ttk.Label(f, text=label).pack(side=tk.LEFT, padx=2)
            
            var_val = tk.StringVar(value=default)
            entry = ttk.Entry(f, textvariable=var_val, width=6)
            entry.pack(side=tk.LEFT, padx=2)
            
            self.targets[key] = {'active': var_active, 'value': var_val}

        # Aksiyon Butonları
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, pady=10)
        
        self.generate_btn = ttk.Button(
            action_frame, 
            text="🧬 Reçete Oluştur (Genetik Algoritma)", 
            command=self._generate_recipe,
            style='Accent.TButton'
        )
        self.generate_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        # Sonuç Alanı
        self.result_frame = ttk.LabelFrame(self, text="Önerilen Reçeteler", padding=5)
        self.result_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tab (Sekme) yapısı
        self.notebook = ttk.Notebook(self.result_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self._add_empty_message()

    def _add_empty_message(self):
        f = ttk.Frame(self.notebook)
        self.notebook.add(f, text="Bilgi")
        
        # More informative empty state message
        info_text = """
📋 Reçete Optimizasyonu Kullanım Kılavuzu:

1. ✅ Formülasyon ekleyin ("Formülasyon" sekmesi)
2. ✅ Test sonuçlarını kaydedin ("Test Sonuçları" sekmesi)
3. ✅ En az 3 test sonucu girin (model arka planda otomatik eğitilir)
4. 🎯 Yukarıdan hedefleri seçin
5. 🧬 "Reçete Oluştur" butonuna basın

⚠️ Model eğitilmeden reçete oluşturulamaz!
        """
        ttk.Label(f, text=info_text, justify=tk.LEFT, wraplength=350).pack(padx=20, pady=10)

    def update_model_status(self, is_trained: bool, sample_count: int = 0):
        """Update the model status indicator
        
        Args:
            is_trained: Whether the model is trained
            sample_count: Number of training samples
        """
        if is_trained:
            self.model_status_label.config(
                text=f"✅ Model hazır ({sample_count} veri ile eğitildi)",
                foreground="green"
            )
        elif sample_count > 0:
            self.model_status_label.config(
                text=f"⚠️ Veri mevcut ({sample_count} kayıt), model eğitilmedi",
                foreground="orange"
            )
        else:
            self.model_status_label.config(
                text="❌ Veri yok - önce formülasyon ve test sonuçları girin",
                foreground="red"
            )


    def _generate_recipe(self):
        """Optimizasyonu başlat"""
        optimization_targets = {}
        for key, data in self.targets.items():
            if data['active'].get():
                try:
                    val = float(data['value'].get())
                    optimization_targets[key] = val
                except ValueError:
                    messagebox.showwarning("Uyarı", f"{key} için geçerli bir sayı girin.")
                    return
        
        if not optimization_targets:
            messagebox.showwarning("Uyarı", "En az bir hedef seçmelisiniz.")
            return

        self.config(cursor="wait")
        threading.Thread(target=self._run_optimization, args=(optimization_targets,), daemon=True).start()

    def _run_optimization(self, targets):
        try:
            if self.on_generate_recipe:
                result = self.on_generate_recipe(targets)
                self.after(0, lambda: self._show_results(result))
            else:
                 self.after(0, lambda: messagebox.showerror("Hata", "Optimizasyon fonksiyonu bağlı değil."))
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: messagebox.showerror("Hata", msg))
        finally:
            self.after(0, lambda: self.config(cursor=""))

    def _show_results(self, result):
        """Sonuçları göster"""
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
            
        if not result.get('success'):
            messagebox.showerror("Başarısız", result.get('message', 'Bilinmeyen hata'))
            self._add_empty_message()
            return
            
        suggestions = result.get('suggestions', [])
        if not suggestions:
            messagebox.showinfo("Sonuç", "Hedeflere uygun reçete bulunamadı.")
            self._add_empty_message()
            return
            
        for i, item in enumerate(suggestions):
            score = item.get('score', 0)
            recipe = item.get('recipe', [])
            prediction = item.get('prediction', {})
            
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=f"Öneri {i+1}")
            
            paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
            paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Reçete
            recipe_frame = ttk.LabelFrame(paned, text="Reçete")
            paned.add(recipe_frame, weight=1)
            
            tree = ttk.Treeview(recipe_frame, columns=('code', 'name', 'amount'), show='headings', height=8)
            tree.heading('code', text='Kod')
            tree.heading('name', text='Ad')
            tree.heading('amount', text='Miktar (%)')
            tree.column('code', width=60)
            tree.column('name', width=120)
            tree.column('amount', width=60)
            tree.pack(fill=tk.BOTH, expand=True)
            
            for comp in recipe:
                tree.insert('', tk.END, values=(
                    comp.get('code', '?'),
                    comp.get('name', '?'),
                    f"{comp.get('amount', 0):.2f}"
                ))
            
            ttk.Button(
                recipe_frame, 
                text="📝 Bu Reçeteyi Uygula",
                command=lambda r=recipe: self._apply_recipe(r)
            ).pack(pady=5)
            
            # Tahmin
            pred_frame = ttk.LabelFrame(paned, text="Tahmin Edilen Özellikler")
            paned.add(pred_frame, weight=1)
            
            ptree = ttk.Treeview(pred_frame, columns=('prop', 'val'), show='headings', height=8)
            ptree.heading('prop', text='Özellik')
            ptree.heading('val', text='Değer')
            ptree.pack(fill=tk.BOTH, expand=True)
            
            for k, v in prediction.items():
                if isinstance(v, (int, float)):
                    val_str = f"{v:.2f}"
                else:
                    val_str = str(v)
                ptree.insert('', tk.END, values=(k, val_str))

    def _apply_recipe(self, recipe):
        if self.on_apply_recipe:
            self.on_apply_recipe(recipe)
