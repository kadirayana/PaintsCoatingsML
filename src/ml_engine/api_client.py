"""
Paint Formulation AI - ML API İstemcisi
========================================
Online ML servisine güvenli bağlantı
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class MLAPIClient:
    """
    Online ML API istemcisi
    
    Bulut tabanlı ML servislerine bağlantı sağlar.
    """
    
    def __init__(self, endpoint: str, api_key: str = None, timeout: int = 30):
        """
        Args:
            endpoint: API endpoint URL
            api_key: API anahtarı (opsiyonel)
            timeout: İstek zaman aşımı (saniye)
        """
        self.endpoint = endpoint
        self.api_key = api_key or os.environ.get('ML_API_KEY', '')
        self.timeout = timeout
    
    def get_recommendation(self, data: List[Dict]) -> Dict:
        """
        API'den öneri al
        
        Args:
            data: Formülasyon verileri
            
        Returns:
            API yanıtı
        """
        if not self.endpoint:
            raise ValueError("API endpoint tanımlanmamış")
        
        try:
            # İstek hazırla
            payload = {
                'data': data,
                'request_type': 'recommendation',
                'language': 'tr'
            }
            
            response = self._make_request('POST', '/recommend', payload)
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"API isteği başarısız: {e}")
            raise
    
    def analyze_formulation(self, formulation: Dict) -> Dict:
        """
        Formülasyon analizi yap
        
        Args:
            formulation: Formülasyon verileri
            
        Returns:
            Analiz sonuçları
        """
        try:
            payload = {
                'formulation': formulation,
                'request_type': 'analysis'
            }
            
            response = self._make_request('POST', '/analyze', payload)
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Analiz isteği başarısız: {e}")
            raise
    
    def optimize_formulation(self, formulation: Dict, constraints: Dict = None) -> Dict:
        """
        Formülasyon optimizasyonu
        
        Args:
            formulation: Mevcut formülasyon
            constraints: Kısıtlamalar (maks maliyet, hedef özellikler vb.)
            
        Returns:
            Optimizasyon önerileri
        """
        try:
            payload = {
                'formulation': formulation,
                'constraints': constraints or {},
                'request_type': 'optimize'
            }
            
            response = self._make_request('POST', '/optimize', payload)
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Optimizasyon isteği başarısız: {e}")
            raise
    
    def predict_properties(self, components: List[Dict]) -> Dict:
        """
        Bileşenlerden özellikleri tahmin et
        
        Args:
            components: Bileşen listesi
            
        Returns:
            Tahmin edilen özellikler
        """
        try:
            payload = {
                'components': components,
                'request_type': 'predict'
            }
            
            response = self._make_request('POST', '/predict', payload)
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"Tahmin isteği başarısız: {e}")
            raise
    
    def _make_request(self, method: str, path: str, data: Dict = None) -> str:
        """
        HTTP isteği yap
        
        Args:
            method: HTTP metodu (GET, POST)
            path: API yolu
            data: İstek verisi
            
        Returns:
            Yanıt içeriği
        """
        url = f"{self.endpoint.rstrip('/')}{path}"
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'PaintFormulationAI/1.1.0'
        }
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        try:
            if method == 'GET':
                if data:
                    url = f"{url}?{urlencode(data)}"
                req = Request(url, headers=headers, method='GET')
            else:
                body = json.dumps(data).encode('utf-8') if data else None
                req = Request(url, data=body, headers=headers, method=method)
            
            with urlopen(req, timeout=self.timeout) as response:
                return response.read().decode('utf-8')
                
        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            logger.error(f"HTTP Hatası {e.code}: {error_body}")
            raise Exception(f"API hatası ({e.code}): {e.reason}")
            
        except URLError as e:
            logger.error(f"URL Hatası: {e.reason}")
            raise Exception(f"Bağlantı hatası: {e.reason}")
            
        except Exception as e:
            logger.error(f"İstek hatası: {e}")
            raise
    
    def _parse_response(self, response_text: str) -> Dict:
        """
        API yanıtını parse et
        
        Args:
            response_text: JSON yanıt metni
            
        Returns:
            Parse edilmiş yanıt
        """
        try:
            data = json.loads(response_text)
            
            # Hata kontrolü
            if 'error' in data:
                raise Exception(data['error'])
            
            return data
            
        except json.JSONDecodeError:
            logger.error(f"JSON parse hatası: {response_text[:200]}")
            raise Exception("Geçersiz API yanıtı")
    
    def check_health(self) -> bool:
        """
        API sağlık kontrolü
        
        Returns:
            API erişilebilir mi?
        """
        try:
            response = self._make_request('GET', '/health')
            data = json.loads(response)
            return data.get('status') == 'healthy'
        except Exception:
            return False
    
    def get_model_info(self) -> Dict:
        """
        Uzak model bilgilerini al
        
        Returns:
            Model bilgileri
        """
        try:
            response = self._make_request('GET', '/model/info')
            return json.loads(response)
        except Exception as e:
            logger.error(f"Model bilgisi alınamadı: {e}")
            return {}


class MockMLAPIClient(MLAPIClient):
    """
    Test ve demo amaçlı sahte API istemcisi
    
    Gerçek API olmadan öneri simülasyonu yapar.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__('http://mock-api', *args, **kwargs)
    
    def get_recommendation(self, data: List[Dict]) -> Dict:
        """Sahte öneri döndür"""
        logger.info("MockMLAPIClient: Sahte öneri üretiliyor")
        
        return {
            'status': 'success',
            'mode': 'mock',
            'analysis': self._generate_mock_analysis(data),
            'suggestions': self._generate_mock_suggestions(data),
            'confidence': 0.85,
            'model_version': '1.0-mock'
        }
    
    def _generate_mock_analysis(self, data: List[Dict]) -> str:
        """Sahte analiz üret"""
        if not data:
            return "Veri yetersiz, analiz yapılamadı."
        
        analysis = []
        analysis.append("🔬 **Formülasyon Analizi** (Demo Mod)")
        analysis.append("")
        analysis.append(f"Toplam {len(data)} kayıt analiz edildi.")
        analysis.append("")
        analysis.append("**Genel Değerlendirme:**")
        analysis.append("Formülasyon parametreleri genel olarak kabul edilebilir sınırlar içinde.")
        analysis.append("Optimizasyon için bazı ince ayarlar önerilmektedir.")
        
        return "\n".join(analysis)
    
    def _generate_mock_suggestions(self, data: List[Dict]) -> List[str]:
        """Sahte öneriler üret"""
        return [
            "TiO2 oranını %0.5 artırarak örtücülüğü iyileştirin",
            "Koyulaştırıcı dozajını kontrol edin",
            "pH stabilizasyonu için tampon sistem ekleyin",
            "Dispersiyon süresini 5 dakika uzatmayı deneyin"
        ]
    
    def check_health(self) -> bool:
        """Mock her zaman sağlıklı"""
        return True
