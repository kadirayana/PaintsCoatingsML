"""
Paint Formulation AI - Input Validation (Girdi Doğrulama)
=========================================================
UI ve API için girdi doğrulama fonksiyonları
"""

import re
from typing import Tuple, Optional, Any


def validate_material_code(code: str) -> Tuple[bool, str]:
    """
    hammadde kodu validasyonu
    
    Args:
        code: Kontrol edilecek hammadde kodu
        
    Returns:
        (geçerli_mi, hata_mesajı) tuple'ı
    """
    if not code:
        return False, "hammadde kodu boş olamaz"
    
    code = code.strip()
    
    if len(code) > 50:
        return False, "hammadde kodu 50 karakteri geçemez"
    
    if not re.match(r'^[A-Za-z0-9\-_\.]+$', code):
        return False, "hammadde kodu sadece harf, rakam, -, _ ve . içerebilir"
    
    return True, ""


def validate_percentage(value: Any) -> Tuple[bool, Optional[float], str]:
    """
    Yüzde değeri validasyonu
    
    Args:
        value: Kontrol edilecek yüzde değeri (string veya sayı)
        
    Returns:
        (geçerli_mi, dönüştürülmüş_değer, hata_mesajı) tuple'ı
    """
    if value is None or value == '':
        return False, None, "Yüzde değeri boş olamaz"
    
    try:
        # String ise temizle
        if isinstance(value, str):
            value = value.strip().replace(',', '.').replace('%', '')
        
        num = float(value)
        
        if num < 0:
            return False, None, "Yüzde negatif olamaz"
        if num > 100:
            return False, None, "Yüzde 100'den büyük olamaz"
            
        return True, num, ""
    except (ValueError, TypeError):
        return False, None, "Geçerli bir sayı girin"


def validate_positive_number(value: Any, field_name: str = "Değer") -> Tuple[bool, Optional[float], str]:
    """
    Pozitif sayı validasyonu (miktar, fiyat vb.)
    
    Args:
        value: Kontrol edilecek değer
        field_name: Hata mesajında kullanılacak alan adı
        
    Returns:
        (geçerli_mi, dönüştürülmüş_değer, hata_mesajı) tuple'ı
    """
    if value is None or value == '':
        return True, None, ""  # Boş değer bazı alanlar için kabul edilebilir
    
    try:
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
        
        num = float(value)
        
        if num < 0:
            return False, None, f"{field_name} negatif olamaz"
            
        return True, num, ""
    except (ValueError, TypeError):
        return False, None, f"{field_name} geçerli bir sayı olmalı"


def validate_project_name(name: str) -> Tuple[bool, str]:
    """
    Proje adı validasyonu
    
    Args:
        name: Kontrol edilecek proje adı
        
    Returns:
        (geçerli_mi, hata_mesajı) tuple'ı
    """
    if not name:
        return False, "Proje adı boş olamaz"
    
    name = name.strip()
    
    if len(name) < 2:
        return False, "Proje adı en az 2 karakter olmalı"
    
    if len(name) > 100:
        return False, "Proje adı 100 karakteri geçemez"
    
    # Tehlikeli karakterleri kontrol et
    dangerous_chars = ['<', '>', '"', "'", ';', '--', '/*', '*/']
    for char in dangerous_chars:
        if char in name:
            return False, f"Proje adı '{char}' karakteri içeremez"
    
    return True, ""


def validate_formula_code(code: str) -> Tuple[bool, str]:
    """
    Formül kodu validasyonu
    
    Args:
        code: Kontrol edilecek formül kodu
        
    Returns:
        (geçerli_mi, hata_mesajı) tuple'ı
    """
    if not code:
        return False, "Formül kodu boş olamaz"
    
    code = code.strip()
    
    if len(code) > 50:
        return False, "Formül kodu 50 karakteri geçemez"
    
    if not re.match(r'^[A-Za-z0-9\-_\.\/]+$', code):
        return False, "Formül kodu sadece harf, rakam, -, _, . ve / içerebilir"
    
    return True, ""


def validate_ph(value: Any) -> Tuple[bool, Optional[float], str]:
    """
    pH değeri validasyonu (0-14 arası)
    
    Args:
        value: Kontrol edilecek pH değeri
        
    Returns:
        (geçerli_mi, dönüştürülmüş_değer, hata_mesajı) tuple'ı
    """
    if value is None or value == '':
        return True, None, ""
    
    try:
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
        
        num = float(value)
        
        if num < 0 or num > 14:
            return False, None, "pH değeri 0-14 arasında olmalı"
            
        return True, num, ""
    except (ValueError, TypeError):
        return False, None, "pH geçerli bir sayı olmalı"


def validate_temperature(value: Any, min_val: float = -50, max_val: float = 500) -> Tuple[bool, Optional[float], str]:
    """
    Sıcaklık değeri validasyonu
    
    Args:
        value: Kontrol edilecek sıcaklık değeri (°C)
        min_val: Minimum kabul edilebilir değer
        max_val: Maximum kabul edilebilir değer
        
    Returns:
        (geçerli_mi, dönüştürülmüş_değer, hata_mesajı) tuple'ı
    """
    if value is None or value == '':
        return True, None, ""
    
    try:
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
        
        num = float(value)
        
        if num < min_val or num > max_val:
            return False, None, f"Sıcaklık {min_val}°C - {max_val}°C arasında olmalı"
            
        return True, num, ""
    except (ValueError, TypeError):
        return False, None, "Sıcaklık geçerli bir sayı olmalı"


def sanitize_string(text: str, max_length: int = 500) -> str:
    """
    String temizleme ve güvenli hale getirme
    
    Args:
        text: Temizlenecek metin
        max_length: Maximum uzunluk
        
    Returns:
        Temizlenmiş metin
    """
    if not text:
        return ""
    
    # Başta ve sonda boşlukları kaldır
    text = text.strip()
    
    # Maximum uzunluğu uygula
    if len(text) > max_length:
        text = text[:max_length]
    
    # Tehlikeli HTML karakterlerini escape et
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    
    return text


def validate_email(email: str) -> Tuple[bool, str]:
    """
    E-posta adresi validasyonu
    
    Args:
        email: Kontrol edilecek e-posta
        
    Returns:
        (geçerli_mi, hata_mesajı) tuple'ı
    """
    if not email:
        return True, ""  # E-posta opsiyonel olabilir
    
    email = email.strip()
    
    # Basit regex kontrolü
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Geçerli bir e-posta adresi girin"
    
    return True, ""
