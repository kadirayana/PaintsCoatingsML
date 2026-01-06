"""
Paint Formulation AI - Turkish Messages
========================================
Türkçe hata mesajları ve kullanıcı bildirimleri
"""

from enum import Enum
from typing import Dict, Optional


class MessageCategory(Enum):
    """Mesaj kategorileri"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    CONFIRM = "confirm"


class Messages:
    """
    Türkçe mesaj yöneticisi
    
    Tüm kullanıcı arayüzü mesajlarını merkezi olarak yönetir.
    """
    
    # =========================================================================
    # BAŞARI MESAJLARI
    # =========================================================================
    SUCCESS = {
        # Genel
        "operation_complete": "İşlem başarıyla tamamlandı.",
        "saved": "Kayıt başarıyla oluşturuldu.",
        "updated": "Güncelleme başarıyla yapıldı.",
        "deleted": "Silme işlemi tamamlandı.",
        
        # Proje
        "project_created": "Proje başarıyla oluşturuldu: {name}",
        "project_updated": "Proje güncellendi: {name}",
        "project_deleted": "Proje silindi: {name}",
        
        # Formülasyon
        "formulation_saved": "Formülasyon kaydedildi: {code}",
        "formulation_updated": "Formülasyon güncellendi: {code}",
        "formulation_deleted": "Formülasyon silindi: {code}",
        
        # Test Sonuçları
        "trial_saved": "Test sonucu kaydedildi.",
        "trial_updated": "Test sonucu güncellendi.",
        "trial_deleted": "Test sonucu silindi.",
        
        # Excel
        "excel_imported": "{count} satır başarıyla içe aktarıldı.",
        "excel_exported": "Dosya kaydedildi: {path}",
        "template_created": "Excel şablonu oluşturuldu.",
        
        # Yedekleme
        "backup_created": "Yedek oluşturuldu: {filename}",
        "backup_restored": "Yedek başarıyla geri yüklendi.",
        "backup_deleted": "Yedek silindi.",
        
        # ML
        "model_trained": "ML modeli eğitildi. Örnek sayısı: {count}",
        "prediction_complete": "Tahmin tamamlandı.",
        "optimization_complete": "Optimizasyon tamamlandı.",
    }
    
    # =========================================================================
    # HATA MESAJLARI
    # =========================================================================
    ERROR = {
        # Genel
        "unexpected": "Beklenmeyen bir hata oluştu: {error}",
        "operation_failed": "İşlem başarısız oldu.",
        "connection_lost": "Bağlantı koptu. Lütfen tekrar deneyin.",
        
        # Doğrulama
        "required_field": "{field} alanı zorunludur.",
        "invalid_value": "Geçersiz değer: {field}",
        "already_exists": "{item} zaten mevcut.",
        "not_found": "{item} bulunamadı.",
        "duplicate_name": "Bu isim zaten kullanılıyor: {name}",
        
        # Veritabanı
        "db_connection": "Veritabanı bağlantısı kurulamadı.",
        "db_query": "Veritabanı sorgu hatası: {error}",
        "db_integrity": "Veri bütünlüğü hatası.",
        "db_locked": "Veritabanı kilitli. Lütfen bekleyin.",
        
        # Dosya
        "file_not_found": "Dosya bulunamadı: {path}",
        "file_read": "Dosya okunamadı: {error}",
        "file_write": "Dosya yazılamadı: {error}",
        "file_permission": "Dosya erişim izni reddedildi.",
        "invalid_format": "Geçersiz dosya formatı.",
        
        # Excel
        "excel_read": "Excel dosyası okunamadı: {error}",
        "excel_write": "Excel dosyası yazılamadı: {error}",
        "excel_no_data": "Excel dosyasında veri bulunamadı.",
        "excel_invalid_columns": "Excel sütunları tanınamadı.",
        
        # ML
        "ml_not_trained": "ML modeli henüz eğitilmedi.",
        "ml_insufficient_data": "Yetersiz eğitim verisi. En az {min} örnek gerekli.",
        "ml_prediction_failed": "Tahmin yapılamadı: {error}",
        "ml_training_failed": "Model eğitimi başarısız: {error}",
        
        # Ağ
        "network_unavailable": "İnternet bağlantısı yok.",
        "api_error": "API hatası: {error}",
        "timeout": "Zaman aşımı. Lütfen tekrar deneyin.",
        
        # Yedekleme
        "backup_failed": "Yedekleme başarısız: {error}",
        "restore_failed": "Geri yükleme başarısız: {error}",
        "backup_not_found": "Yedek dosyası bulunamadı.",
        
        # Konfigürasyon
        "config_load": "Yapılandırma dosyası yüklenemedi.",
        "config_save": "Yapılandırma kaydedilemedi.",
        "config_invalid": "Geçersiz yapılandırma değeri: {key}",
    }
    
    # =========================================================================
    # UYARI MESAJLARI
    # =========================================================================
    WARNING = {
        # Genel
        "unsaved_changes": "Kaydedilmemiş değişiklikler var. Devam etmek istiyor musunuz?",
        "no_selection": "Lütfen bir öğe seçin.",
        "empty_data": "Veri bulunamadı.",
        
        # Proje
        "no_project": "Önce bir proje seçin.",
        "project_has_data": "Bu projede formülasyonlar var. Yine de silmek istiyor musunuz?",
        
        # Formülasyon
        "no_formulation": "Önce bir formülasyon seçin.",
        "incomplete_formulation": "Formülasyon eksik. Toplam % kontrol edin.",
        "low_percentage": "Toplam yüzde 100'den düşük: {value}%",
        
        # ML
        "low_confidence": "Düşük güven skoru: {score}%. Sonuçları dikkatli değerlendirin.",
        "outdated_model": "ML modeli güncellenmeli. Son eğitim: {date}",
        
        # Yedekleme
        "no_backups": "Mevcut yedek bulunamadı.",
        "old_backup": "Son yedek {days} gün önce alınmış.",
    }
    
    # =========================================================================
    # BİLGİ MESAJLARI
    # =========================================================================
    INFO = {
        # Genel
        "loading": "Yükleniyor...",
        "processing": "İşleniyor...",
        "please_wait": "Lütfen bekleyin...",
        
        # ML
        "ml_training": "Model eğitiliyor. Bu işlem birkaç dakika sürebilir.",
        "ml_predicting": "Tahmin hesaplanıyor...",
        "ml_optimizing": "Optimizasyon çalışıyor...",
        
        # Yedekleme
        "backup_in_progress": "Yedekleme devam ediyor...",
        "restore_in_progress": "Geri yükleme devam ediyor...",
        
        # Uygulama
        "app_starting": "Uygulama başlatılıyor...",
        "db_initializing": "Veritabanı hazırlanıyor...",
        "ready": "Hazır",
    }
    
    # =========================================================================
    # ONAY MESAJLARI
    # =========================================================================
    CONFIRM = {
        "delete": "{item} silmek istediğinizden emin misiniz?",
        "delete_all": "Tüm {items} silmek istediğinizden emin misiniz?",
        "overwrite": "{item} zaten mevcut. Üzerine yazmak istiyor musunuz?",
        "restore": "Veritabanı geri yüklenecek. Mevcut veriler değiştirilecek. Devam?",
        "exit": "Uygulamadan çıkmak istediğinizden emin misiniz?",
        "reset": "Tüm ayarları varsayılana döndürmek istiyor musunuz?",
    }
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    @classmethod
    def get(cls, category: str, key: str, **kwargs) -> str:
        """
        Mesaj al ve parametrelerle formatla
        
        Args:
            category: Mesaj kategorisi (success, error, warning, info, confirm)
            key: Mesaj anahtarı
            **kwargs: Format parametreleri
            
        Returns:
            str: Formatlanmış mesaj
        """
        category_map = {
            "success": cls.SUCCESS,
            "error": cls.ERROR,
            "warning": cls.WARNING,
            "info": cls.INFO,
            "confirm": cls.CONFIRM,
        }
        
        messages = category_map.get(category.lower(), {})
        template = messages.get(key, f"[{category}:{key}]")
        
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    
    @classmethod
    def success(cls, key: str, **kwargs) -> str:
        """Başarı mesajı al"""
        return cls.get("success", key, **kwargs)
    
    @classmethod
    def error(cls, key: str, **kwargs) -> str:
        """Hata mesajı al"""
        return cls.get("error", key, **kwargs)
    
    @classmethod
    def warning(cls, key: str, **kwargs) -> str:
        """Uyarı mesajı al"""
        return cls.get("warning", key, **kwargs)
    
    @classmethod
    def info(cls, key: str, **kwargs) -> str:
        """Bilgi mesajı al"""
        return cls.get("info", key, **kwargs)
    
    @classmethod
    def confirm(cls, key: str, **kwargs) -> str:
        """Onay mesajı al"""
        return cls.get("confirm", key, **kwargs)


# Kısa erişim için alias
msg = Messages
