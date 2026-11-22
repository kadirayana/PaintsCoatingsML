"""
Paint Formulation AI - Ana Uygulama Modülü
==========================================
Boya formülasyonu yönetimi ve hibrit ML öneri sistemi

Bu dosya uygulamanın ana giriş noktasıdır.
"""

import os
import sys
import logging
from datetime import datetime
from configparser import ConfigParser

# Uygulama kök dizinini belirle
if getattr(sys, 'frozen', False):
    # PyInstaller ile paketlenmiş EXE içinde çalışıyoruz
    APP_DIR = os.path.dirname(sys.executable)
else:
    # Normal Python script olarak çalışıyoruz
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Modül yollarını ekle
sys.path.insert(0, APP_DIR)
# Göreli yollar (ör. 'assets/models') her zaman uygulama dizinine göre çözülsün
os.chdir(APP_DIR)

# Yerel modülleri import et
from app.ui_components import PaintFormulationApp
from app.offline_utils import setup_directories
from src.data_handlers.local_db_manager import LocalDBManager
from src.utils.network_checker import NetworkChecker


def configure_windows() -> None:
    """Windows'a özgü ayarlar (diğer platformlarda hiçbir şey yapmaz).

    - DPI farkındalığı: olmazsa yüksek çözünürlüklü/ölçekli ekranlarda arayüz bulanık görünür.
      Tk penceresi oluşturulmadan ÖNCE çağrılmalıdır.
    - AppUserModelID: görev çubuğunda uygulamanın python.exe yerine kendi adıyla gruplanması.
    """
    if sys.platform != 'win32':
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Windows 8.1+
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # Windows 7/8
        except Exception:
            pass
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('PaintFormulationAI.Desktop')
    except Exception:
        pass


def setup_logging(config: ConfigParser) -> logging.Logger:
    """Loglama sistemini yapılandır"""
    log_dir = os.path.join(APP_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_level = config.get('Logging', 'level', fallback='INFO')
    log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')
    
    handlers = [logging.FileHandler(log_file, encoding='utf-8')]
    # Konsolsuz (windowed) EXE'de sys.stderr None'dır. Windows konsolu (cp857/cp1254)
    # emoji yazamaz; karakter hatası log satırını düşürmesin diye 'replace' kullan.
    if sys.stderr is not None:
        if hasattr(sys.stderr, 'reconfigure'):
            try:
                sys.stderr.reconfigure(errors='replace')
            except Exception:
                pass
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    return logging.getLogger('PaintFormulationAI')


def load_config() -> ConfigParser:
    """Konfigürasyon dosyasını yükle"""
    config = ConfigParser()
    config_path = os.path.join(APP_DIR, 'config.ini')
    
    if os.path.exists(config_path):
        config.read(config_path, encoding='utf-8')
    else:
        # Varsayılan değerler
        config['Application'] = {
            'name': 'Paint Formulation AI',
            'version': '1.1.0-offline',
            'language': 'tr'
        }
        config['Database'] = {
            'db_file': 'db.sqlite'
        }
        config['ML'] = {
            'default_mode': 'auto'
        }
        config['UI'] = {
            'theme': 'dark',
            'window_width': '1200',
            'window_height': '800'
        }
        config['Logging'] = {
            'level': 'INFO'
        }
    
    return config


def initialize_database(config: ConfigParser, logger: logging.Logger) -> LocalDBManager:
    """Veritabanını başlat"""
    data_dir = os.path.join(APP_DIR, 'data_storage')
    os.makedirs(data_dir, exist_ok=True)
    
    db_file = config.get('Database', 'db_file', fallback='db.sqlite')
    db_path = os.path.join(data_dir, db_file)
    
    logger.info(f"Veritabanı başlatılıyor: {db_path}")
    
    db_manager = LocalDBManager(db_path)
    db_manager.initialize()
    
    return db_manager


def main():
    """Ana uygulama fonksiyonu"""
    # Konfigürasyon yükle
    config = load_config()
    
    # Loglama başlat
    logger = setup_logging(config)
    logger.info("=" * 50)
    logger.info("Paint Formulation AI başlatılıyor...")
    logger.info(f"Sürüm: {config.get('Application', 'version', fallback='1.0.0')}")
    logger.info("=" * 50)
    
    configure_windows()

    try:
        # Dizinleri kontrol et/oluştur
        setup_directories(APP_DIR)
        
        # Veritabanını başlat
        db_manager = initialize_database(config, logger)
        
        # İnternet durumunu kontrol et
        network_checker = NetworkChecker()
        is_online = network_checker.check_connection()
        
        if is_online:
            logger.info("İnternet bağlantısı mevcut - Hibrit mod aktif")
        else:
            logger.info("İnternet bağlantısı yok - Offline mod aktif")
        
        # UI'ı başlat
        logger.info("Kullanıcı arayüzü başlatılıyor...")
        app = PaintFormulationApp(
            config=config,
            db_manager=db_manager,
            network_checker=network_checker,
            app_dir=APP_DIR
        )
        
        # Arayüz geri çağrılarındaki hatalar varsayılan olarak stderr'e yazılır; konsolsuz
        # EXE'de kaybolmasınlar diye log dosyasına yönlendir.
        app.root.report_callback_exception = lambda exc, val, tb: logger.error(
            f"Arayüz hatası: {val}", exc_info=(exc, val, tb))

        # Uygulamayı çalıştır
        app.run()
        
    except Exception as e:
        logger.error(f"Kritik hata: {str(e)}", exc_info=True)
        # Konsolsuz EXE'de kullanıcı aksi halde hiçbir şey görmeden uygulama kapanır
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Paint Formulation AI",
                f"Uygulama başlatılamadı:\n\n{e}\n\nAyrıntılar: {os.path.join(APP_DIR, 'logs')}")
        except Exception:
            pass
        raise
    finally:
        logger.info("Uygulama kapatılıyor...")


if __name__ == "__main__":
    main()
