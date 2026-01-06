"""
Paint Formulation AI - Progress Dialog (İlerleme Diyaloğu)
=========================================================
Uzun süren işlemler için ilerleme göstergesi
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
import threading


class ProgressDialog(tk.Toplevel):
    """
    Uzun süren işlemler için progress dialog
    
    Kullanım:
        with ProgressDialog(parent, "İşleniyor...") as dialog:
            for i in range(100):
                dialog.update_progress(i, 100, f"Adım {i+1}/100")
                # İşlem yap...
    """
    
    def __init__(self, parent, title: str = "İşleniyor...", 
                 determinate: bool = False, cancelable: bool = False):
        """
        Args:
            parent: Üst pencere
            title: Dialog başlığı
            determinate: True ise yüzde göstergesi, False ise indeterminate
            cancelable: True ise iptal butonu gösterir
        """
        super().__init__(parent)
        
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        
        self._cancelled = False
        self._determinate = determinate
        
        # Modal pencere
        self.grab_set()
        
        # Ana frame
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Durum etiketi
        self.status_label = ttk.Label(main_frame, text="Lütfen bekleyin...", 
                                       font=('Segoe UI', 10))
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        mode = 'determinate' if determinate else 'indeterminate'
        self.progress = ttk.Progressbar(main_frame, length=300, mode=mode)
        self.progress.pack(pady=10)
        
        if not determinate:
            self.progress.start(10)  # Animasyonu başlat
        
        # Yüzde etiketi (determinate modda)
        if determinate:
            self.percent_label = ttk.Label(main_frame, text="0%", 
                                           font=('Segoe UI', 9))
            self.percent_label.pack(pady=(5, 0))
        
        # İptal butonu
        if cancelable:
            self.cancel_btn = ttk.Button(main_frame, text="İptal", 
                                         command=self._on_cancel)
            self.cancel_btn.pack(pady=(10, 0))
        
        # Pencereyi ortala
        self._center_window()
        
        # Kapatma tuşunu devre dışı bırak
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.update()
    
    def _center_window(self):
        """Pencereyi ekranın ortasına konumlandır"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')
    
    def update_status(self, message: str):
        """
        Durum mesajını güncelle
        
        Args:
            message: Gösterilecek mesaj
        """
        self.status_label.config(text=message)
        self.update()
    
    def update_progress(self, current: int, total: int, message: str = None):
        """
        İlerlemeyi güncelle (sadece determinate modda)
        
        Args:
            current: Mevcut değer
            total: Toplam değer
            message: Opsiyonel durum mesajı
        """
        if not self._determinate:
            return
        
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress['value'] = percentage
        
        if hasattr(self, 'percent_label'):
            self.percent_label.config(text=f"{percentage}%")
        
        if message:
            self.status_label.config(text=message)
        
        self.update()
    
    def is_cancelled(self) -> bool:
        """İptal edildi mi kontrol et"""
        return self._cancelled
    
    def _on_cancel(self):
        """İptal butonuna basıldığında"""
        self._cancelled = True
        self.update_status("İptal ediliyor...")
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.config(state='disabled')
    
    def _on_close(self):
        """Pencere kapatılmaya çalışıldığında"""
        # İşlem devam ederken kapatmayı engelle
        pass
    
    def close(self):
        """Dialogu kapat"""
        if hasattr(self, 'progress') and not self._determinate:
            self.progress.stop()
        self.grab_release()
        self.destroy()
    
    def __enter__(self):
        """Context manager girişi"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager çıkışı"""
        self.close()
        return False


class TaskRunner:
    """
    Arka plan görevi çalıştırıcı - UI donmasını önler
    
    Kullanım:
        def long_task():
            # Uzun süren işlem
            return result
        
        def on_complete(result):
            print(f"Tamamlandı: {result}")
        
        TaskRunner.run(parent, long_task, on_complete, "İşleniyor...")
    """
    
    @staticmethod
    def run(parent, task_func, on_complete=None, on_error=None, 
            title: str = "İşleniyor...", show_progress: bool = True):
        """
        Arka planda görev çalıştır
        
        Args:
            parent: Üst pencere
            task_func: Çalıştırılacak fonksiyon
            on_complete: Başarılı tamamlandığında çağrılacak callback(result)
            on_error: Hata olduğunda çağrılacak callback(exception)
            title: Progress dialog başlığı
            show_progress: Progress dialog gösterilsin mi
        """
        result = [None]
        error = [None]
        
        # Progress dialog
        dialog = None
        if show_progress:
            dialog = ProgressDialog(parent, title)
        
        def worker():
            try:
                result[0] = task_func()
            except Exception as e:
                error[0] = e
        
        def check_thread():
            if thread.is_alive():
                parent.after(100, check_thread)
            else:
                if dialog:
                    dialog.close()
                
                if error[0]:
                    if on_error:
                        on_error(error[0])
                else:
                    if on_complete:
                        on_complete(result[0])
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        
        parent.after(100, check_thread)


# Test için
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Progress Test")
    root.geometry("300x150")
    
    def test_indeterminate():
        dialog = ProgressDialog(root, "Yükleniyor...")
        root.after(3000, dialog.close)
    
    def test_determinate():
        dialog = ProgressDialog(root, "İşleniyor...", determinate=True)
        
        def update(i=0):
            if i <= 100:
                dialog.update_progress(i, 100, f"Adım {i}/100")
                root.after(50, lambda: update(i+1))
            else:
                dialog.close()
        
        update()
    
    ttk.Button(root, text="Indeterminate Test", command=test_indeterminate).pack(pady=10)
    ttk.Button(root, text="Determinate Test", command=test_determinate).pack(pady=10)
    
    root.mainloop()
