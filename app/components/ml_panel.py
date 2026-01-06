"""
Paint Formulation AI - ML Recommendation Panel
===============================================
Makine öğrenimi öneri paneli bileşeni
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
import threading
import logging

logger = logging.getLogger(__name__)


class MLRecommendationPanel(ttk.LabelFrame):
    """
    ML Öneri paneli
    
    Formülasyon optimizasyonu için ML tabanlı öneriler sunar.
    """
    
    def __init__(self, parent, on_get_recommendation: Callable = None):
        """
        Args:
            parent: Üst widget
            on_get_recommendation: Öneri callback'i (mode) -> str
        """
        super().__init__(parent, text="🤖 ML Öneri Sistemi", padding=10)
        
        self.on_get_recommendation = on_get_recommendation
        self.is_processing = False
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Widget'ları oluştur"""
        # Mod seçimi
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(mode_frame, text="Mod:").pack(side=tk.LEFT)
        
        self.mode_var = tk.StringVar(value="auto")
        modes = [
            ("Otomatik", "auto"),
            ("Lokal", "local"),
            ("Online", "online")
        ]
        
        for text, value in modes:
            ttk.Radiobutton(
                mode_frame,
                text=text,
                variable=self.mode_var,
                value=value
            ).pack(side=tk.LEFT, padx=10)
        
        # Durum göstergesi
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="⚪ Hazır",
            foreground="gray"
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Model durumu
        self.model_status_label = ttk.Label(
            self.status_frame,
            text="",
            foreground="gray"
        )
        self.model_status_label.pack(side=tk.RIGHT)
        
        # Öneri butonu
        self.recommend_btn = ttk.Button(
            self,
            text="🔮 ML Öneri Al",
            command=self._get_recommendation
        )
        self.recommend_btn.pack(fill=tk.X, pady=10)
        
        # Sonuç alanı
        result_frame = ttk.Frame(self)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(result_frame, text="Öneriler:").pack(anchor=tk.W)
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(result_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = tk.Text(
            text_frame,
            height=10,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="white"
        )
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(
            text_frame,
            orient=tk.VERTICAL,
            command=self.result_text.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        # Başlangıç mesajı
        self.result_text.insert(tk.END, "ML önerileri burada görüntülenecek...\n\n")
        self.result_text.insert(tk.END, "Formülasyon verilerinize göre:\n")
        self.result_text.insert(tk.END, "• Optimum parametre tahminleri\n")
        self.result_text.insert(tk.END, "• İyileştirme önerileri\n")
        self.result_text.insert(tk.END, "• Benzer formülasyon karşılaştırmaları\n")
        self.result_text.config(state=tk.DISABLED)
        
        # Alt butonlar
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            btn_frame,
            text="📋 Kopyala",
            command=self._copy_result
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="🗑️ Temizle",
            command=self._clear_result
        ).pack(side=tk.LEFT, padx=2)
    
    def _get_recommendation(self):
        """ML önerisi al"""
        if self.is_processing:
            return
        
        if not self.on_get_recommendation:
            self._display_result("Öneri servisi yapılandırılmamış.")
            return
        
        self.is_processing = True
        self._set_status("processing")
        
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "⏳ Öneri hesaplanıyor...\n")
        self.result_text.config(state=tk.DISABLED)
        
        # Arka planda çalıştır
        mode = self.mode_var.get()
        threading.Thread(
            target=self._fetch_recommendation,
            args=(mode,),
            daemon=True
        ).start()
    
    def _fetch_recommendation(self, mode: str):
        """Arka planda öneri al"""
        try:
            result = self.on_get_recommendation(mode)
            self.after(0, lambda: self._on_recommendation_complete(result))
        except Exception as e:
            logger.error(f"ML öneri hatası: {e}")
            self.after(0, lambda: self._on_recommendation_error(str(e)))
    
    def _on_recommendation_complete(self, result: str):
        """Öneri tamamlandığında"""
        self.is_processing = False
        self._set_status("success")
        self._display_result(result)
    
    def _on_recommendation_error(self, error: str):
        """Öneri hata verdiğinde"""
        self.is_processing = False
        self._set_status("error")
        self._display_result(f"❌ Hata: {error}")
    
    def _display_result(self, result: str):
        """Sonucu göster"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result)
        self.result_text.config(state=tk.DISABLED)
    
    def _set_status(self, status: str):
        """Durum göstergesini ayarla"""
        status_map = {
            "ready": ("⚪ Hazır", "gray"),
            "processing": ("🔄 İşleniyor...", "orange"),
            "success": ("✅ Tamamlandı", "green"),
            "error": ("❌ Hata", "red"),
            "offline": ("🔴 Offline", "red"),
            "online": ("🟢 Online", "green")
        }
        
        text, color = status_map.get(status, ("⚪ Hazır", "gray"))
        self.status_label.config(text=text, foreground=color)
    
    def set_model_status(self, status: str):
        """Model durumunu göster"""
        self.model_status_label.config(text=status)
    
    def _copy_result(self):
        """Sonucu panoya kopyala"""
        self.result_text.config(state=tk.NORMAL)
        text = self.result_text.get(1.0, tk.END).strip()
        self.result_text.config(state=tk.DISABLED)
        
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
    
    def _clear_result(self):
        """Sonucu temizle"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "ML önerileri burada görüntülenecek...")
        self.result_text.config(state=tk.DISABLED)
        self._set_status("ready")
    
    def set_enabled(self, enabled: bool = True):
        """Panel durumunu ayarla"""
        state = 'normal' if enabled else 'disabled'
        self.recommend_btn.config(state=state)
