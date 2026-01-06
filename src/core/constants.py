"""
Paint Formulation AI - Sabitler
================================
Uygulama genelinde kullanılan sabitler ve enum değerleri
"""

from enum import Enum, auto


# ============================================================================
# Uygulama Sabitleri
# ============================================================================

APP_NAME = "Paint Formulation AI"
APP_VERSION = "1.2.0"
APP_AUTHOR = "Paint AI Team"

# Minimum gereksinimler
MIN_PYTHON_VERSION = (3, 9)
MIN_TRAINING_SAMPLES = 3


# ============================================================================
# Veritabanı Sabitleri
# ============================================================================

# Tablo isimleri
TABLE_PROJECTS = "projects"
TABLE_FORMULATIONS = "formulations"
TABLE_COMPONENTS = "formulation_components"
TABLE_TRIALS = "trials"
TABLE_MATERIALS = "materials"
TABLE_CUSTOM_TEST_METHODS = "custom_test_methods"

# Varsayılan değerler
DEFAULT_PROJECT_NAME = "Yeni Proje"
DEFAULT_FORMULATION_STATUS = "draft"
MAX_COMPONENTS_PER_FORMULATION = 50


# ============================================================================
# ML Sabitleri
# ============================================================================

class MLMode(Enum):
    """ML çalışma modları"""
    AUTO = auto()      # Otomatik (internet varsa online, yoksa offline)
    LOCAL = auto()     # Sadece lokal model
    ONLINE = auto()    # Sadece online API


# Varsayılan hedef parametreler
DEFAULT_TARGET_PARAMS = [
    'opacity',           # Örtücülük (%)
    'gloss',             # Parlaklık (GU)
    'film_thickness',    # Film kalınlığı (mikron)
    'hardness',          # Sertlik (König/Persoz sn)
    'adhesion',          # Yapışma (derece)
    'corrosion_resistance'  # Korozyon direnci (saat)
]

# Özellik isimleri (Türkçe)
PARAM_LABELS_TR = {
    'opacity': 'Örtücülük',
    'gloss': 'Parlaklık',
    'film_thickness': 'Film Kalınlığı',
    'hardness': 'Sertlik',
    'adhesion': 'Yapışma',
    'corrosion_resistance': 'Korozyon Direnci',
    'viscosity': 'Viskozite',
    'density': 'Yoğunluk',
    'solid_content': 'Katı Madde',
    'drying_time': 'Kuruma Süresi'
}


# ============================================================================
# UI Sabitleri
# ============================================================================

class Theme(Enum):
    """UI temaları"""
    DARK = "dark"
    LIGHT = "light"


# Pencere boyutları
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800

# Renkler (Hex)
COLORS = {
    'primary': '#2196F3',        # Mavi
    'secondary': '#FF9800',      # Turuncu
    'success': '#4CAF50',        # Yeşil
    'warning': '#FFC107',        # Sarı
    'error': '#F44336',          # Kırmızı
    'info': '#00BCD4',           # Cyan
    'dark_bg': '#1E1E1E',        # Koyu arka plan
    'light_bg': '#FFFFFF',       # Açık arka plan
    'dark_text': '#FFFFFF',      # Koyu tema metin
    'light_text': '#212121'      # Açık tema metin
}

# Fontlar
FONTS = {
    'default': ('Segoe UI', 10),
    'heading': ('Segoe UI', 14, 'bold'),
    'subheading': ('Segoe UI', 12, 'bold'),
    'small': ('Segoe UI', 9),
    'monospace': ('Consolas', 10)
}


# ============================================================================
# Excel Sabitleri
# ============================================================================

# Excel sütun eşleştirmeleri
EXCEL_COLUMN_MAPPING = {
    # Hammadde bilgileri
    'material_code': ['Hammadde Kodu', 'Kod', 'Material Code', 'Code'],
    'material_name': ['Hammadde Adı', 'Hammadde', 'Material Name', 'Name'],
    'amount': ['Miktar', 'Miktar (kg)', 'Amount', 'Quantity'],
    'percentage': ['Yüzde', '%', 'Percentage', 'Percent'],
    'solid_content': ['Katı Oranı', 'Katı %', 'Solid Content', 'Solids'],
    'unit_price': ['Birim Fiyat', 'Fiyat', 'Unit Price', 'Price'],
    
    # Test sonuçları
    'opacity': ['Örtücülük', 'Opacity'],
    'gloss_60': ['Parlaklık 60°', 'Gloss 60', 'Gloss'],
    'film_thickness': ['Film Kalınlığı', 'DFT', 'Dry Film Thickness'],
    'hardness': ['Sertlik', 'Hardness', 'König'],
    'adhesion': ['Yapışma', 'Adhesion'],
}

# Template dosya isimleri
TEMPLATE_FORMULATION = "formulation_template.xlsx"
TEMPLATE_TEST_RESULTS = "test_results_template.xlsx"


# ============================================================================
# Dosya Uzantıları
# ============================================================================

SUPPORTED_EXCEL_EXTENSIONS = ('.xlsx', '.xls', '.xlsm')
SUPPORTED_CSV_EXTENSIONS = ('.csv', '.tsv')
BACKUP_EXTENSION = '.sqlite'
LOG_EXTENSION = '.log'


# ============================================================================
# Zaman Sabitleri
# ============================================================================

# Saniye cinsinden
NETWORK_CHECK_TIMEOUT = 5
API_DEFAULT_TIMEOUT = 10
UI_REFRESH_INTERVAL = 1000      # ms
AUTOSAVE_INTERVAL = 300         # 5 dakika
BACKUP_INTERVAL_DEFAULT = 1800  # 30 dakika


# ============================================================================
# Hata Mesajları (Türkçe)
# ============================================================================

ERROR_MESSAGES = {
    'db_connection': 'Veritabanına bağlanılamadı',
    'db_query': 'Veritabanı sorgusu başarısız',
    'file_not_found': 'Dosya bulunamadı',
    'permission_denied': 'Erişim izni yok',
    'invalid_format': 'Geçersiz dosya formatı',
    'network_error': 'Ağ bağlantısı hatası',
    'api_error': 'API isteği başarısız',
    'model_error': 'Model yüklenemedi',
    'validation_error': 'Doğrulama hatası',
    'insufficient_data': 'Yetersiz veri'
}

SUCCESS_MESSAGES = {
    'save': 'Başarıyla kaydedildi',
    'delete': 'Başarıyla silindi',
    'import': 'İçe aktarma tamamlandı',
    'export': 'Dışa aktarma tamamlandı',
    'backup': 'Yedekleme tamamlandı',
    'restore': 'Geri yükleme tamamlandı'
}
