"""
Paint Formulation AI - Internationalization (i18n) Module
==========================================================
Çoklu dil desteği için singleton pattern ile string yönetimi.

Kullanım:
    from src.core.i18n import I18n, t
    
    # Singleton'ı al
    i18n = I18n()
    i18n.load("tr")  # veya "en"
    
    # String çevir
    label = t("buttons.save")  # → "Kaydet" veya "Save"
    
    # Dil değiştir (UI otomatik güncellenir)
    i18n.switch("en")
"""

import json
import os
import logging
from typing import Dict, List, Callable, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class I18n:
    """
    Internationalization singleton.
    
    Dil dosyalarını yükler ve string çevirileri sağlar.
    Observer pattern ile dil değişikliklerini UI'a bildirir.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._lang = "tr"  # Default language
        self._strings: Dict = {}
        self._listeners: List[Callable[[], None]] = []
        self._lang_dir = self._find_lang_dir()
        
        # Load default language
        self.load(self._lang)
        self._initialized = True
    
    def _find_lang_dir(self) -> Path:
        """Dil dosyaları dizinini bul"""
        # Try multiple locations
        candidates = [
            Path(__file__).parent.parent.parent / "lang",  # src/core -> lang
            Path.cwd() / "lang",
            Path(__file__).parent.parent.parent.parent / "lang",
        ]
        
        for path in candidates:
            if path.exists():
                return path
        
        # Create if not exists
        default_path = Path.cwd() / "lang"
        default_path.mkdir(exist_ok=True)
        return default_path
    
    @property
    def current_language(self) -> str:
        """Aktif dil kodu"""
        return self._lang
    
    @property
    def available_languages(self) -> List[str]:
        """Mevcut dil dosyaları"""
        return [f.stem for f in self._lang_dir.glob("*.json")]
    
    def load(self, lang: str) -> bool:
        """
        Dil dosyasını yükle.
        
        Args:
            lang: Dil kodu (örn: 'tr', 'en')
            
        Returns:
            Başarılı ise True
        """
        file_path = self._lang_dir / f"{lang}.json"
        
        if not file_path.exists():
            logger.warning(f"Language file not found: {file_path}")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self._strings = json.load(f)
            self._lang = lang
            logger.info(f"Loaded language: {lang}")
            return True
        except Exception as e:
            logger.error(f"Failed to load language {lang}: {e}")
            return False
    
    def switch(self, lang: str) -> bool:
        """
        Dili değiştir ve listener'ları bilgilendir.
        
        Args:
            lang: Yeni dil kodu
            
        Returns:
            Başarılı ise True
        """
        if lang == self._lang:
            return True
        
        if self.load(lang):
            self._notify_listeners()
            return True
        return False
    
    def t(self, key: str, default: str = None, **kwargs) -> str:
        """
        String çevir.
        
        Args:
            key: Nokta ile ayrılmış anahtar (örn: 'buttons.save')
            default: Bulunamazsa varsayılan değer
            **kwargs: Format parametreleri
            
        Returns:
            Çevrilmiş string
        """
        value = self._get_nested(key)
        
        if value is None:
            if default is not None:
                return default
            logger.debug(f"Missing translation: {key}")
            return key
        
        if kwargs:
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        
        return value
    
    def _get_nested(self, key: str) -> Optional[str]:
        """Nested dictionary'den değer al (örn: 'buttons.save')"""
        keys = key.split('.')
        value = self._strings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value if isinstance(value, str) else None
    
    def add_listener(self, callback: Callable[[], None]):
        """Dil değişikliği listener'ı ekle"""
        if callback not in self._listeners:
            self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[], None]):
        """Listener kaldır"""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self):
        """Tüm listener'ları bilgilendir"""
        for callback in self._listeners:
            try:
                callback()
            except Exception as e:
                logger.error(f"Listener error on language change: {e}")


# Global singleton erişimi
_i18n = I18n()


def t(key: str, default: str = None, **kwargs) -> str:
    """
    Kısayol fonksiyon: String çevir.
    
    Kullanım:
        from src.core.i18n import t
        label = t("buttons.save")  # → "Kaydet"
    """
    return _i18n.t(key, default, **kwargs)


def get_i18n() -> I18n:
    """I18n singleton'ını döndür"""
    return _i18n


def switch_language(lang: str) -> bool:
    """Dil değiştir"""
    return _i18n.switch(lang)


def current_language() -> str:
    """Aktif dil kodu"""
    return _i18n.current_language
