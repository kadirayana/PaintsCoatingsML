"""
Paint Formulation AI - Network Checker
=======================================
İnternet bağlantısı kontrolü
"""

import socket
import logging
from typing import Tuple, Optional
from urllib.request import urlopen
from urllib.error import URLError
import threading
import time

logger = logging.getLogger(__name__)


class NetworkChecker:
    """
    İnternet bağlantısı kontrolcüsü
    
    Ping atarak veya HTTP isteği yaparak internet durumunu kontrol eder.
    """
    
    # Kontrol için kullanılacak sunucular
    CHECK_HOSTS = [
        ("8.8.8.8", 53),           # Google DNS
        ("1.1.1.1", 53),           # Cloudflare DNS
        ("208.67.222.222", 53),    # OpenDNS
    ]
    
    CHECK_URLS = [
        "https://www.google.com",
        "https://www.cloudflare.com",
        "https://www.microsoft.com",
    ]
    
    def __init__(self, timeout: float = 3.0, cache_duration: float = 30.0):
        """
        Args:
            timeout: Bağlantı zaman aşımı (saniye)
            cache_duration: Önbellek süresi (saniye)
        """
        self.timeout = timeout
        self.cache_duration = cache_duration
        
        self._last_check_time = 0
        self._last_result = None
        self._lock = threading.Lock()
    
    def check_connection(self, force: bool = False) -> bool:
        """
        İnternet bağlantısını kontrol et
        
        Args:
            force: Önbelleği yoksay
            
        Returns:
            Bağlantı var mı?
        """
        with self._lock:
            current_time = time.time()
            
            # Önbellek geçerli mi?
            if not force and self._last_result is not None:
                if current_time - self._last_check_time < self.cache_duration:
                    return self._last_result
            
            # Yeni kontrol yap
            result = self._do_check()
            
            self._last_check_time = current_time
            self._last_result = result
            
            return result
    
    def _do_check(self) -> bool:
        """Gerçek bağlantı kontrolü"""
        # Önce socket ile dene (hızlı)
        if self._check_socket():
            logger.debug("Socket kontrolü başarılı - internet var")
            return True
        
        # HTTP ile dene (daha güvenilir)
        if self._check_http():
            logger.debug("HTTP kontrolü başarılı - internet var")
            return True
        
        logger.info("İnternet bağlantısı bulunamadı")
        return False
    
    def _check_socket(self) -> bool:
        """Socket ile bağlantı kontrolü (hızlı)"""
        for host, port in self.CHECK_HOSTS:
            try:
                socket.setdefaulttimeout(self.timeout)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    return True
                    
            except (socket.error, OSError) as e:
                logger.debug(f"Socket kontrolü başarısız {host}:{port} - {e}")
                continue
        
        return False
    
    def _check_http(self) -> bool:
        """HTTP ile bağlantı kontrolü (güvenilir)"""
        for url in self.CHECK_URLS:
            try:
                response = urlopen(url, timeout=self.timeout)
                response.close()
                return True
                
            except URLError as e:
                logger.debug(f"HTTP kontrolü başarısız {url} - {e}")
                continue
            except Exception as e:
                logger.debug(f"HTTP hatası {url} - {e}")
                continue
        
        return False
    
    def get_connection_info(self) -> dict:
        """
        Detaylı bağlantı bilgisi döndür
        
        Returns:
            Bağlantı detayları
        """
        is_connected = self.check_connection(force=True)
        
        info = {
            'connected': is_connected,
            'last_check': self._last_check_time,
            'local_ip': self._get_local_ip(),
            'dns_reachable': [],
            'http_reachable': []
        }
        
        # DNS sunucularını kontrol et
        for host, port in self.CHECK_HOSTS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    info['dns_reachable'].append(host)
            except (socket.error, OSError):
                pass  # DNS check failed - expected in offline mode
        
        return info
    
    def _get_local_ip(self) -> Optional[str]:
        """Yerel IP adresini al"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except (socket.error, OSError):
            return None  # Could not determine local IP
    
    def wait_for_connection(self, max_wait: float = 60.0, check_interval: float = 5.0) -> bool:
        """
        İnternet bağlantısı için bekle
        
        Args:
            max_wait: Maksimum bekleme süresi (saniye)
            check_interval: Kontrol aralığı (saniye)
            
        Returns:
            Bağlantı sağlandı mı?
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self.check_connection(force=True):
                return True
            
            logger.info(f"İnternet bekleniyor... ({int(time.time() - start_time)}s)")
            time.sleep(check_interval)
        
        return False
    
    def ping(self, host: str) -> Tuple[bool, float]:
        """
        Belirli bir sunucuya ping at
        
        Args:
            host: Hedef sunucu adresi
            
        Returns:
            (başarılı mı, gecikme ms)
        """
        try:
            start = time.time()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, 80))
            sock.close()
            
            latency = (time.time() - start) * 1000  # ms
            
            if result == 0:
                return True, latency
            else:
                return False, 0
                
        except Exception as e:
            logger.debug(f"Ping hatası {host}: {e}")
            return False, 0
    
    def test_api_endpoint(self, endpoint: str) -> dict:
        """
        API endpoint erişilebilirliğini test et
        
        Args:
            endpoint: API URL
            
        Returns:
            Test sonuçları
        """
        result = {
            'reachable': False,
            'latency_ms': 0,
            'status_code': None,
            'error': None
        }
        
        try:
            start = time.time()
            
            response = urlopen(endpoint, timeout=self.timeout)
            
            result['latency_ms'] = (time.time() - start) * 1000
            result['status_code'] = response.getcode()
            result['reachable'] = True
            
            response.close()
            
        except URLError as e:
            result['error'] = str(e.reason)
        except Exception as e:
            result['error'] = str(e)
        
        return result


# Singleton instance
_network_checker = None


def get_network_checker() -> NetworkChecker:
    """Global NetworkChecker instance'ı döndür"""
    global _network_checker
    
    if _network_checker is None:
        _network_checker = NetworkChecker()
    
    return _network_checker
