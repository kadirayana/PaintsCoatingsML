"""
Paint Formulation AI - Prediction Panel
========================================
ML tahmin sonuçları gösterim bileşeni
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional
import threading
import logging

logger = logging.getLogger(__name__)


class PredictionPanel(ttk.LabelFrame):
    """
    ML Tahmin Sonuçları Paneli
    
    Formülasyon verilerine göre beklenen test sonuçlarını tahmin eder
    ve kullanıcıya gösterir.
    """
    
    def __init__(self, parent, on_predict: Callable = None):
        """
        Args:
            parent: Üst widget
            on_predict: Tahmin callback'i (formulation_data) -> Dict
        """
        super().__init__(parent, text="🔮 Muhtemel Test Sonuçları (Tahmin)", padding=10)
        
        self.on_predict = on_predict
        self.is_predicting = False
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Widget'ları oluştur"""
        # Üst kısım - Kontroller
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(control_frame, text="Kaplama Kalınlığı (µm):").pack(side=tk.LEFT)
        
        self.thickness_var = tk.StringVar(value="50")
        self.thickness_entry = ttk.Entry(control_frame, textvariable=self.thickness_var, width=8)
        self.thickness_entry.pack(side=tk.LEFT, padx=5)
        
        self.predict_btn = ttk.Button(
            control_frame,
            text="🔮 Tahmin Yap",
            command=self._do_predict
        )
        self.predict_btn.pack(side=tk.LEFT, padx=10)
        
        # Durum göstergesi
        self.status_label = ttk.Label(control_frame, text="", foreground="gray")
        self.status_label.pack(side=tk.RIGHT)
        
        # Sonuç alanı
        result_frame = ttk.Frame(self)
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = tk.Text(
            result_frame,
            height=6,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="white"
        )
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        # Başlangıç mesajı
        self._set_result("ℹ️ Formülasyon hammaddelerine göre muhtemel test sonuçlarını tahmin eder.\n\n"
                        "Tahmin yapmak için 'Tahmin Yap' butonuna tıklayın.")
    
    def _do_predict(self):
        """Tahmin işlemini başlat"""
        if self.is_predicting:
            return
        
        if not self.on_predict:
            self._set_result("⚠️ Tahmin servisi yapılandırılmamış.")
            return
        
        self.is_predicting = True
        self._set_status("processing")
        self._set_result("⏳ Tahmin hesaplanıyor...")
        
        # Arka planda çalıştır
        threading.Thread(
            target=self._run_prediction,
            daemon=True
        ).start()
    
    def _run_prediction(self):
        """Arka planda tahmin yap"""
        try:
            thickness = float(self.thickness_var.get() or 50)
            result = self.on_predict(thickness)
            
            # Ana thread'de güncelle
            self.after(0, lambda: self._on_prediction_complete(result, thickness))
            
        except ValueError:
            self.after(0, lambda: self._on_prediction_error("Geçersiz kalınlık değeri"))
        except Exception as e:
            logger.error(f"Tahmin hatası: {e}")
            self.after(0, lambda: self._on_prediction_error(str(e)))
    
    def _on_prediction_complete(self, result: Dict, thickness: float):
        """Tahmin tamamlandığında"""
        self.is_predicting = False
        self._set_status("success")
        self._display_results(result, thickness)
    
    def _on_prediction_error(self, error: str):
        """Tahmin hata verdiğinde"""
        self.is_predicting = False
        self._set_status("error")
        self._set_result(f"❌ Hata: {error}")
    
    def _display_results(self, result: Dict, thickness: float):
        """Tahmin sonuçlarını formatla ve göster"""
        if not result:
            self._set_result("⚠️ Tahmin sonucu alınamadı.")
            return
        
        lines = []
        lines.append(f"📊 Kaplama Kalınlığı: {thickness} µm\n")
        lines.append("=" * 40)
        lines.append("")
        
        # Güven bilgisi (en üstte göster)
        confidence_info = result.get('confidence', {})
        if confidence_info:
            overall_conf = confidence_info.get('overall', 0)
            conf_message = confidence_info.get('message', '')
            sample_count = confidence_info.get('sample_count', 0)
            
            # Güven bar'ı oluştur
            bar_length = 20
            filled = int(overall_conf / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            lines.append(f"📈 Güven: [{bar}] {overall_conf:.0f}%")
            lines.append(f"   {conf_message}")
            lines.append(f"   (Eğitim verisi: {sample_count} kayıt)")
            lines.append("")
            lines.append("-" * 40)
            lines.append("")
        
        # Temel tahminler
        predictions = result.get('predictions', result)
        
        if 'film_thickness' in predictions:
            lines.append(f"🎯 Film Kalınlığı: {predictions['film_thickness']:.1f} µm")
        
        if 'opacity' in predictions:
            lines.append(f"🎨 Örtücülük: {predictions['opacity']:.1f}%")
        
        if 'gloss' in predictions:
            lines.append(f"✨ Parlaklık: {predictions['gloss']:.1f} GU")
        elif 'gloss_60' in predictions:
            lines.append(f"✨ Parlaklık (60°): {predictions['gloss_60']:.1f} GU")
        
        if 'hardness' in predictions:
            lines.append(f"💎 Sertlik: {predictions['hardness']:.1f}")
        
        if 'adhesion' in predictions:
            lines.append(f"🔗 Yapışma: {predictions['adhesion']:.1f}/5")
        
        if 'corrosion_resistance' in predictions:
            lines.append(f"🛡️ Korozyon Direnci: {predictions['corrosion_resistance']:.1f}")
        
        # Detaylı güven bilgisi (her hedef için)
        if confidence_info and confidence_info.get('details'):
            lines.append("")
            lines.append("-" * 40)
            lines.append("📐 Güven Aralıkları:")
            for target, info in confidence_info.get('details', {}).items():
                pred_val = predictions.get(target)
                if pred_val is not None:
                    lower = info.get('lower', pred_val)
                    upper = info.get('upper', pred_val)
                    conf = info.get('confidence', 0)
                    lines.append(f"   {target}: {lower:.1f} - {upper:.1f} (%{conf:.0f})")
        
        # Model bilgisi
        if 'model' in result:
            lines.append(f"🤖 Model: {result['model']}")
        
        # Öneriler
        if 'recommendations' in result:
            lines.append("")
            lines.append("💡 Öneriler:")
            for rec in result['recommendations']:
                lines.append(f"  • {rec}")
        
        self._set_result('\n'.join(lines))
    
    def _set_result(self, text: str):
        """Sonuç alanını güncelle"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)
    
    def _set_status(self, status: str):
        """Durum göstergesini ayarla"""
        status_map = {
            "ready": ("", "gray"),
            "processing": ("⏳ İşleniyor...", "orange"),
            "success": ("✅ Tamamlandı", "green"),
            "error": ("❌ Hata", "red")
        }
        
        text, color = status_map.get(status, ("", "gray"))
        self.status_label.config(text=text, foreground=color)
    
    def set_enabled(self, enabled: bool = True):
        """Panel durumunu ayarla"""
        state = 'normal' if enabled else 'disabled'
        self.predict_btn.config(state=state)
        self.thickness_entry.config(state=state)
    
    def clear(self):
        """Sonuçları temizle"""
        self._set_result("ℹ️ Formülasyon hammaddelerine göre muhtemel test sonuçlarını tahmin eder.")
        self._set_status("ready")
