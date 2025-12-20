"""
Paint Formulation AI - Offline Yardımcı Fonksiyonlar
=====================================================
Offline mod için yardımcı fonksiyonlar ve araçlar
"""

import os
import shutil
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def setup_directories(app_dir: str) -> None:
    """
    Uygulama dizinlerini oluştur ve kontrol et
    
    Args:
        app_dir: Uygulama kök dizini
    """
    directories = [
        'data_storage',
        'logs',
        'assets',
        'assets/models',
        'assets/templates',
        'exports'
    ]
    
    for dir_name in directories:
        dir_path = os.path.join(app_dir, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"Dizin oluşturuldu: {dir_path}")


def backup_database(db_path: str, backup_dir: str) -> Optional[str]:
    """
    Veritabanı yedeği al
    
    Args:
        db_path: Veritabanı dosya yolu
        backup_dir: Yedek dizini
        
    Returns:
        Yedek dosya yolu veya None
    """
    if not os.path.exists(db_path):
        logger.warning(f"Veritabanı bulunamadı: {db_path}")
        return None
    
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"db_backup_{timestamp}.sqlite"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"Veritabanı yedeklendi: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Yedekleme hatası: {e}")
        return None


def cleanup_old_backups(backup_dir: str, keep_count: int = 10) -> None:
    """
    Eski yedekleri temizle
    
    Args:
        backup_dir: Yedek dizini
        keep_count: Saklanacak yedek sayısı
    """
    if not os.path.exists(backup_dir):
        return
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.startswith("db_backup_") and filename.endswith(".sqlite"):
            filepath = os.path.join(backup_dir, filename)
            backups.append((filepath, os.path.getmtime(filepath)))
    
    # Tarihe göre sırala (en yeni en başta)
    backups.sort(key=lambda x: x[1], reverse=True)
    
    # Eski yedekleri sil
    for filepath, _ in backups[keep_count:]:
        try:
            os.remove(filepath)
            logger.info(f"Eski yedek silindi: {filepath}")
        except Exception as e:
            logger.error(f"Yedek silme hatası: {e}")


def get_file_size_formatted(file_path: str) -> str:
    """
    Dosya boyutunu okunabilir formatta döndür
    
    Args:
        file_path: Dosya yolu
        
    Returns:
        Formatlanmış boyut string'i
    """
    if not os.path.exists(file_path):
        return "0 B"
    
    size = os.path.getsize(file_path)
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    
    return f"{size:.1f} TB"


def validate_excel_structure(file_path: str, required_columns: List[str]) -> Dict:
    """
    Excel dosyası yapısını doğrula
    
    Args:
        file_path: Dosya yolu
        required_columns: Gerekli sütunlar
        
    Returns:
        Doğrulama sonucu
    """
    result = {
        'valid': False,
        'message': '',
        'missing_columns': [],
        'found_columns': []
    }
    
    try:
        import openpyxl
        
        wb = openpyxl.load_workbook(file_path, read_only=True)
        ws = wb.active
        
        # İlk satırdan sütun isimlerini al
        headers = [cell.value for cell in ws[1] if cell.value]
        result['found_columns'] = headers
        
        # Eksik sütunları bul
        missing = [col for col in required_columns if col not in headers]
        result['missing_columns'] = missing
        
        if not missing:
            result['valid'] = True
            result['message'] = "Dosya yapısı geçerli"
        else:
            result['message'] = f"Eksik sütunlar: {', '.join(missing)}"
        
        wb.close()
        
    except ImportError:
        result['message'] = "openpyxl kütüphanesi bulunamadı"
    except Exception as e:
        result['message'] = f"Dosya okuma hatası: {str(e)}"
    
    return result


def export_to_csv(data: List[Dict], output_path: str) -> bool:
    """
    Verileri CSV dosyasına aktar
    
    Args:
        data: Dışa aktarılacak veriler
        output_path: Çıktı dosya yolu
        
    Returns:
        Başarı durumu
    """
    if not data:
        logger.warning("Dışa aktarılacak veri yok")
        return False
    
    try:
        import csv
        
        # Sütun isimlerini al
        fieldnames = list(data[0].keys())
        
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"CSV dışa aktarıldı: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"CSV dışa aktarma hatası: {e}")
        return False


def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """
    Tarih/saat formatlama
    
    Args:
        dt: Datetime nesnesi
        format_str: Format string'i
        
    Returns:
        Formatlanmış tarih string'i
    """
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except:
            return dt
    
    return dt.strftime(format_str)


def calculate_stats(values: List[float]) -> Dict:
    """
    Temel istatistikleri hesapla
    
    Args:
        values: Sayısal değerler listesi
        
    Returns:
        İstatistik sözlüğü
    """
    if not values:
        return {
            'count': 0,
            'min': None,
            'max': None,
            'mean': None,
            'std': None
        }
    
    import statistics
    
    n = len(values)
    mean_val = statistics.mean(values)
    
    return {
        'count': n,
        'min': min(values),
        'max': max(values),
        'mean': round(mean_val, 2),
        'std': round(statistics.stdev(values), 2) if n > 1 else 0
    }


def sanitize_filename(filename: str) -> str:
    """
    Dosya adını güvenli hale getir
    
    Args:
        filename: Orijinal dosya adı
        
    Returns:
        Güvenli dosya adı
    """
    # Windows'ta geçersiz karakterler
    invalid_chars = '<>:"/\\|?*'
    
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Başındaki ve sonundaki boşlukları kaldır
    filename = filename.strip()
    
    # Boş ise varsayılan isim
    if not filename:
        filename = "unnamed"
    
    return filename
