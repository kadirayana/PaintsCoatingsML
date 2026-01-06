"""
Paint Formulation AI - Custom Exception Sınıfları
==================================================
Uygulama genelinde kullanılan özelleştirilmiş hata sınıfları
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class PaintAIException(Exception):
    """
    Tüm uygulama hatalarının temel sınıfı
    
    Attributes:
        message: Teknik hata mesajı (log için)
        user_message: Kullanıcı dostu Türkçe mesaj (UI için)
    """
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        self.message = message
        self.user_message = user_message or self._get_default_user_message()
        super().__init__(self.message)
        self._log()
    
    def _get_default_user_message(self) -> str:
        """Varsayılan kullanıcı mesajı"""
        return "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin."
    
    def _log(self):
        """Hatayı logla"""
        logger.error(f"{self.__class__.__name__}: {self.message}")


# ============================================================================
# Veritabanı Hataları
# ============================================================================

class DatabaseException(PaintAIException):
    """Veritabanı işlemlerinde oluşan hatalar"""
    
    def __init__(self, message: str, query: Optional[str] = None, 
                 params: Optional[tuple] = None, user_message: Optional[str] = None):
        self.query = query
        self.params = params
        super().__init__(message, user_message)
    
    def _get_default_user_message(self) -> str:
        return "Veritabanı işlemi başarısız oldu. Verileriniz kaydedilmemiş olabilir."
    
    def _log(self):
        logger.error(f"{self.__class__.__name__}: {self.message}")
        if self.query:
            logger.debug(f"Query: {self.query}")
        if self.params:
            logger.debug(f"Params: {self.params}")


class ConnectionError(DatabaseException):
    """Veritabanı bağlantı hataları"""
    
    def __init__(self, db_path: str, message: Optional[str] = None):
        self.db_path = db_path
        msg = message or f"Veritabanına bağlanılamadı: {db_path}"
        super().__init__(msg)
    
    def _get_default_user_message(self) -> str:
        return "Veritabanı dosyasına erişilemiyor. Lütfen dosya yolunu kontrol edin."


class IntegrityError(DatabaseException):
    """Veritabanı bütünlük hataları (unique constraint, foreign key vb.)"""
    
    def __init__(self, constraint: str, message: Optional[str] = None):
        self.constraint = constraint
        msg = message or f"Veritabanı bütünlük hatası: {constraint}"
        super().__init__(msg)
    
    def _get_default_user_message(self) -> str:
        if "unique" in self.constraint.lower():
            return "Bu kayıt zaten mevcut. Lütfen farklı bir değer girin."
        elif "foreign" in self.constraint.lower():
            return "İlişkili kayıt bulunamadı. Lütfen seçiminizi kontrol edin."
        return "Veri bütünlüğü hatası oluştu."


class RecordNotFoundError(DatabaseException):
    """Kayıt bulunamadı hatası"""
    
    def __init__(self, entity: str, identifier: Any):
        self.entity = entity
        self.identifier = identifier
        msg = f"{entity} bulunamadı: {identifier}"
        super().__init__(msg)
    
    def _get_default_user_message(self) -> str:
        return f"Aradığınız {self.entity} kaydı bulunamadı."


# ============================================================================
# Doğrulama Hataları
# ============================================================================

class ValidationError(PaintAIException):
    """Veri doğrulama hataları"""
    
    def __init__(self, field: str, value: Any, expected: str, 
                 message: Optional[str] = None):
        self.field = field
        self.value = value
        self.expected = expected
        msg = message or f"Geçersiz değer - Alan: {field}, Değer: {value}, Beklenen: {expected}"
        super().__init__(msg)
    
    def _get_default_user_message(self) -> str:
        return f"'{self.field}' alanındaki değer geçersiz. {self.expected}"


class RequiredFieldError(ValidationError):
    """Zorunlu alan hatası"""
    
    def __init__(self, field: str):
        super().__init__(field, None, "Bu alan zorunludur")
    
    def _get_default_user_message(self) -> str:
        return f"'{self.field}' alanı boş bırakılamaz."


class InvalidFormatError(ValidationError):
    """Format hatası"""
    
    def __init__(self, field: str, value: Any, expected_format: str):
        super().__init__(field, value, f"Beklenen format: {expected_format}")
    
    def _get_default_user_message(self) -> str:
        return f"'{self.field}' alanı geçersiz formatta. {self.expected}"


# ============================================================================
# ML Hataları
# ============================================================================

class MLException(PaintAIException):
    """Makine öğrenimi işlemlerinde oluşan hatalar"""
    
    def __init__(self, model_name: str, message: str, user_message: Optional[str] = None):
        self.model_name = model_name
        super().__init__(f"[{model_name}] {message}", user_message)
    
    def _get_default_user_message(self) -> str:
        return "AI analizi şu anda kullanılamıyor. Lütfen daha sonra tekrar deneyin."


class ModelNotFoundError(MLException):
    """Model dosyası bulunamadı"""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        super().__init__("LocalModel", f"Model dosyası bulunamadı: {model_path}")
    
    def _get_default_user_message(self) -> str:
        return "AI modeli yüklenemedi. Offline mod kullanılacak."


class InsufficientDataError(MLException):
    """Yetersiz veri hatası"""
    
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(
            "Training",
            f"Yetersiz veri: {available}/{required} kayıt mevcut"
        )
    
    def _get_default_user_message(self) -> str:
        return f"AI eğitimi için en az {self.required} kayıt gerekli. Şu anda {self.available} kayıt var."


class PredictionError(MLException):
    """Tahmin hatası"""
    
    def __init__(self, message: str):
        super().__init__("Prediction", message)
    
    def _get_default_user_message(self) -> str:
        return "Tahmin yapılamadı. Girdi verilerini kontrol edin."


# ============================================================================
# Ağ Hataları
# ============================================================================

class NetworkException(PaintAIException):
    """Ağ bağlantı hataları"""
    
    def __init__(self, endpoint: str, message: str, 
                 status_code: Optional[int] = None):
        self.endpoint = endpoint
        self.status_code = status_code
        super().__init__(f"[{endpoint}] {message} (Status: {status_code})")
    
    def _get_default_user_message(self) -> str:
        return "Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol edin."


class APIError(NetworkException):
    """API çağrı hatası"""
    
    def __init__(self, endpoint: str, status_code: int, response: Optional[str] = None):
        self.response = response
        super().__init__(endpoint, f"API hatası: {response or 'Bilinmeyen hata'}", status_code)
    
    def _get_default_user_message(self) -> str:
        if self.status_code == 401:
            return "API yetkilendirme hatası. Lütfen ayarlarınızı kontrol edin."
        elif self.status_code == 429:
            return "Çok fazla istek gönderildi. Lütfen biraz bekleyin."
        elif self.status_code >= 500:
            return "Sunucu hatası. Lütfen daha sonra tekrar deneyin."
        return "API isteği başarısız oldu."


class TimeoutError(NetworkException):
    """Zaman aşımı hatası"""
    
    def __init__(self, endpoint: str, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        super().__init__(endpoint, f"İstek zaman aşımına uğradı ({timeout_seconds}s)")
    
    def _get_default_user_message(self) -> str:
        return "İstek zaman aşımına uğradı. İnternet bağlantınız yavaş olabilir."


# ============================================================================
# Dosya İşlem Hataları
# ============================================================================

class FileOperationError(PaintAIException):
    """Dosya işlem hataları"""
    
    def __init__(self, file_path: str, operation: str, message: Optional[str] = None):
        self.file_path = file_path
        self.operation = operation
        msg = message or f"Dosya işlemi başarısız - {operation}: {file_path}"
        super().__init__(msg)
    
    def _get_default_user_message(self) -> str:
        return f"Dosya işlemi başarısız oldu: {self.operation}"


class ExcelImportError(FileOperationError):
    """Excel import hatası"""
    
    def __init__(self, file_path: str, message: str, row: Optional[int] = None):
        self.row = row
        row_info = f" (Satır: {row})" if row else ""
        super().__init__(file_path, "Excel Import", f"{message}{row_info}")
    
    def _get_default_user_message(self) -> str:
        if self.row:
            return f"Excel dosyası okunamadı. Satır {self.row}'de hata var."
        return "Excel dosyası okunamadı. Dosya formatını kontrol edin."


class ExcelExportError(FileOperationError):
    """Excel export hatası"""
    
    def __init__(self, file_path: str, message: str):
        super().__init__(file_path, "Excel Export", message)
    
    def _get_default_user_message(self) -> str:
        return "Excel dosyası oluşturulamadı. Dosya yolunu kontrol edin."


class BackupError(FileOperationError):
    """Yedekleme hatası"""
    
    def __init__(self, file_path: str, message: str):
        super().__init__(file_path, "Backup", message)
    
    def _get_default_user_message(self) -> str:
        return "Yedekleme başarısız oldu. Disk alanını kontrol edin."


# ============================================================================
# Konfigürasyon Hataları
# ============================================================================

class ConfigurationError(PaintAIException):
    """Konfigürasyon hataları"""
    
    def __init__(self, key: str, message: Optional[str] = None):
        self.key = key
        msg = message or f"Geçersiz konfigürasyon: {key}"
        super().__init__(msg)
    
    def _get_default_user_message(self) -> str:
        return "Uygulama ayarlarında bir sorun var. config.ini dosyasını kontrol edin."
