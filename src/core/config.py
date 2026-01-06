"""
Paint Formulation AI - Merkezi Konfigürasyon Yöneticisi
========================================================
config.ini dosyasını okur ve uygulama genelinde erişim sağlar
"""

import os
import logging
from configparser import ConfigParser
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Singleton instance
_config_instance: Optional['ConfigManager'] = None


def get_config() -> 'ConfigManager':
    """
    Global ConfigManager instance'ını döndürür (Singleton pattern)
    
    Returns:
        ConfigManager instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


class ConfigManager:
    """
    Merkezi konfigürasyon yöneticisi
    
    Özellikler:
    - config.ini dosyasını okur
    - Environment variable desteği
    - Varsayılan değerler
    - Type-safe erişim metodları
    """
    
    # Varsayılan değerler
    DEFAULTS = {
        'Application': {
            'name': 'Paint Formulation AI',
            'version': '1.2.0',
            'language': 'tr'
        },
        'Database': {
            'db_file': 'db.sqlite',
            'backup_interval': '30',
            'max_backups': '5'
        },
        'ML': {
            'local_model': 'assets/models/local_model_v1.pkl',
            'api_endpoint': '',
            'api_timeout': '10',
            'default_mode': 'auto',
            'min_training_samples': '3'
        },
        'UI': {
            'theme': 'dark',
            'window_width': '1200',
            'window_height': '800'
        },
        'Logging': {
            'level': 'INFO',
            'max_size': '10',
            'backup_count': '5'
        }
    }
    
    def __init__(self, config_path: Optional[str] = None, app_dir: Optional[str] = None):
        """
        Args:
            config_path: config.ini dosya yolu (opsiyonel)
            app_dir: Uygulama kök dizini (opsiyonel)
        """
        self._config = ConfigParser()
        self._app_dir = app_dir or self._detect_app_dir()
        self._config_path = config_path or os.path.join(self._app_dir, 'config.ini')
        
        # Varsayılanları yükle
        self._load_defaults()
        
        # config.ini'yi oku
        self._load_config_file()
        
        logger.info(f"Konfigürasyon yüklendi: {self._config_path}")
    
    def _detect_app_dir(self) -> str:
        """Uygulama kök dizinini tespit et"""
        import sys
        if getattr(sys, 'frozen', False):
            # PyInstaller EXE
            return os.path.dirname(sys.executable)
        else:
            # Normal Python - src/core/config.py'den 3 seviye yukarı
            return str(Path(__file__).parent.parent.parent.parent)
    
    def _load_defaults(self):
        """Varsayılan değerleri yükle"""
        for section, values in self.DEFAULTS.items():
            if not self._config.has_section(section):
                self._config.add_section(section)
            for key, value in values.items():
                self._config.set(section, key, value)
    
    def _load_config_file(self):
        """config.ini dosyasını oku"""
        if os.path.exists(self._config_path):
            try:
                self._config.read(self._config_path, encoding='utf-8')
            except Exception as e:
                logger.warning(f"config.ini okunamadı, varsayılanlar kullanılıyor: {e}")
    
    # =========================================================================
    # Generic Accessors
    # =========================================================================
    
    def get(self, section: str, key: str, fallback: Any = None) -> str:
        """
        Değer oku (environment variable öncelikli)
        
        Args:
            section: Bölüm adı
            key: Anahtar
            fallback: Varsayılan değer
            
        Returns:
            Değer (str)
        """
        # Environment variable kontrolü (PREFIX_SECTION_KEY formatında)
        env_key = f"PAINTAI_{section.upper()}_{key.upper()}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value
        
        return self._config.get(section, key, fallback=fallback)
    
    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """Integer değer oku"""
        try:
            return int(self.get(section, key, str(fallback)))
        except ValueError:
            return fallback
    
    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Float değer oku"""
        try:
            return float(self.get(section, key, str(fallback)))
        except ValueError:
            return fallback
    
    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """Boolean değer oku"""
        value = self.get(section, key, str(fallback)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def get_path(self, section: str, key: str, fallback: str = '') -> str:
        """Dosya yolu oku (app_dir'e göreceli yolları mutlak yola çevir)"""
        path = self.get(section, key, fallback)
        if path and not os.path.isabs(path):
            path = os.path.join(self._app_dir, path)
        return path
    
    # =========================================================================
    # Typed Accessors (Kolaylık metodları)
    # =========================================================================
    
    @property
    def app_dir(self) -> str:
        """Uygulama kök dizini"""
        return self._app_dir
    
    @property
    def app_name(self) -> str:
        """Uygulama adı"""
        return self.get('Application', 'name')
    
    @property
    def app_version(self) -> str:
        """Uygulama versiyonu"""
        return self.get('Application', 'version')
    
    @property
    def language(self) -> str:
        """Dil"""
        return self.get('Application', 'language')
    
    @property
    def db_path(self) -> str:
        """Veritabanı tam yolu"""
        db_file = self.get('Database', 'db_file')
        return os.path.join(self._app_dir, 'data_storage', db_file)
    
    @property
    def backup_interval(self) -> int:
        """Yedekleme aralığı (dakika)"""
        return self.get_int('Database', 'backup_interval', 30)
    
    @property
    def max_backups(self) -> int:
        """Maksimum yedek sayısı"""
        return self.get_int('Database', 'max_backups', 5)
    
    @property
    def local_model_path(self) -> str:
        """Lokal ML model yolu"""
        return self.get_path('ML', 'local_model')
    
    @property
    def api_endpoint(self) -> str:
        """API endpoint"""
        return self.get('ML', 'api_endpoint', '')
    
    @property
    def api_timeout(self) -> int:
        """API zaman aşımı (saniye)"""
        return self.get_int('ML', 'api_timeout', 10)
    
    @property
    def ml_mode(self) -> str:
        """ML modu: auto, local, online"""
        return self.get('ML', 'default_mode', 'auto')
    
    @property
    def min_training_samples(self) -> int:
        """Minimum eğitim örneği sayısı"""
        return self.get_int('ML', 'min_training_samples', 3)
    
    @property
    def ui_theme(self) -> str:
        """UI teması: dark, light"""
        return self.get('UI', 'theme', 'dark')
    
    @property
    def window_width(self) -> int:
        """Pencere genişliği"""
        return self.get_int('UI', 'window_width', 1200)
    
    @property
    def window_height(self) -> int:
        """Pencere yüksekliği"""
        return self.get_int('UI', 'window_height', 800)
    
    @property
    def log_level(self) -> str:
        """Log seviyesi"""
        return self.get('Logging', 'level', 'INFO')
    
    @property
    def log_max_size(self) -> int:
        """Maksimum log dosyası boyutu (MB)"""
        return self.get_int('Logging', 'max_size', 10)
    
    @property
    def log_backup_count(self) -> int:
        """Saklanacak log dosyası sayısı"""
        return self.get_int('Logging', 'backup_count', 5)
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def save(self):
        """Konfigürasyonu dosyaya kaydet"""
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                self._config.write(f)
            logger.info(f"Konfigürasyon kaydedildi: {self._config_path}")
        except Exception as e:
            logger.error(f"Konfigürasyon kaydedilemedi: {e}")
            raise
    
    def set(self, section: str, key: str, value: Any):
        """Değer ayarla"""
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, str(value))
    
    def reload(self):
        """Konfigürasyonu yeniden yükle"""
        self._load_defaults()
        self._load_config_file()
        logger.info("Konfigürasyon yeniden yüklendi")
    
    def to_dict(self) -> dict:
        """Tüm konfigürasyonu sözlük olarak döndür"""
        result = {}
        for section in self._config.sections():
            result[section] = dict(self._config.items(section))
        return result
