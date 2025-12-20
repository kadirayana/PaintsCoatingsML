"""
Paint Formulation AI - ML Router
=================================
Hibrit ML yönlendirici - İnternet durumuna göre API veya lokal model seçimi
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MLRouter:
    """
    Hibrit ML yönlendirici
    
    İnternet bağlantısı varsa API'ye, yoksa lokal modele yönlendirir.
    """
    
    def __init__(self, network_checker, local_model_path: str = None, api_endpoint: str = None):
        """
        Args:
            network_checker: NetworkChecker instance
            local_model_path: Lokal model dosya yolu
            api_endpoint: Online API endpoint
        """
        self.network_checker = network_checker
        self.local_model_path = local_model_path
        self.api_endpoint = api_endpoint
        
        self._local_model = None
        self._api_client = None
    
    def get_recommendation(self, data: List[Dict], mode: str = 'auto') -> str:
        """
        AI önerisi al
        
        Args:
            data: Formülasyon/deneme verileri
            mode: 'auto', 'local' veya 'online'
            
        Returns:
            Öneri metni
        """
        try:
            # Mod belirleme
            use_online = self._should_use_online(mode)
            
            if use_online:
                return self._get_online_recommendation(data)
            else:
                return self._get_local_recommendation(data)
                
        except Exception as e:
            logger.error(f"Öneri hatası: {e}")
            return f"Öneri alınırken hata oluştu: {str(e)}"
    
    def _should_use_online(self, mode: str) -> bool:
        """Online mod kullanılıp kullanılmayacağını belirle"""
        if mode == 'local':
            return False
        
        if mode == 'online':
            if not self.network_checker.check_connection():
                logger.warning("Online mod istendi ama internet yok, lokal moda düşülüyor")
                return False
            return True
        
        # Auto mod: internet varsa online, yoksa local
        return self.network_checker.check_connection()
    
    def _get_local_recommendation(self, data: List[Dict]) -> str:
        """Lokal model ile öneri al"""
        logger.info("Lokal ML modeli kullanılıyor")
        
        try:
            from src.ml_engine.local_models import LocalMLModel
            
            if self._local_model is None:
                self._local_model = LocalMLModel(self.local_model_path)
            
            result = self._local_model.predict(data)
            
            # Sonucu formatla
            return self._format_local_result(result, data)
            
        except ImportError as e:
            logger.warning(f"LocalMLModel import hatası: {e}")
            return self._get_fallback_recommendation(data)
        except Exception as e:
            logger.error(f"Lokal model hatası: {e}")
            return self._get_fallback_recommendation(data)
    
    def _get_online_recommendation(self, data: List[Dict]) -> str:
        """Online API ile öneri al"""
        logger.info("Online API kullanılıyor")
        
        try:
            from src.ml_engine.api_client import MLAPIClient
            
            if self._api_client is None:
                self._api_client = MLAPIClient(self.api_endpoint)
            
            result = self._api_client.get_recommendation(data)
            
            return self._format_online_result(result)
            
        except ImportError as e:
            logger.warning(f"MLAPIClient import hatası: {e}")
            # Fallback to local
            return self._get_local_recommendation(data)
        except Exception as e:
            logger.error(f"API hatası: {e}, lokal moda düşülüyor")
            return self._get_local_recommendation(data)
    
    def _get_fallback_recommendation(self, data: List[Dict]) -> str:
        """Basit kural tabanlı öneri (fallback)"""
        logger.info("Fallback öneri sistemi kullanılıyor")
        
        if not data:
            return "⚠️ Öneri üretmek için yeterli veri yok.\n\nLütfen önce formülasyon verileri girin."
        
        # Son kayıtları analiz et
        recommendations = []
        recommendations.append("🔬 **FORMÜLASYON ANALİZ RAPORU**")
        recommendations.append("=" * 40)
        recommendations.append("")
        
        # Viskozite analizi
        viscosities = [d.get('viscosity') for d in data if d.get('viscosity')]
        if viscosities:
            avg_visc = sum(viscosities) / len(viscosities)
            recommendations.append(f"📊 **Viskozite Analizi**")
            recommendations.append(f"   • Ortalama: {avg_visc:.1f} cP")
            recommendations.append(f"   • Min: {min(viscosities):.1f} cP")
            recommendations.append(f"   • Max: {max(viscosities):.1f} cP")
            
            if avg_visc < 1000:
                recommendations.append("   💡 Öneri: Viskozite düşük, koyulaştırıcı eklemeyi düşünün")
            elif avg_visc > 5000:
                recommendations.append("   💡 Öneri: Viskozite yüksek, seyreltici eklemeyi düşünün")
            else:
                recommendations.append("   ✅ Viskozite optimum aralıkta")
            recommendations.append("")
        
        # pH analizi
        ph_values = [d.get('ph') for d in data if d.get('ph')]
        if ph_values:
            avg_ph = sum(ph_values) / len(ph_values)
            recommendations.append(f"🧪 **pH Analizi**")
            recommendations.append(f"   • Ortalama: {avg_ph:.2f}")
            
            if avg_ph < 7:
                recommendations.append("   💡 Öneri: pH asidik, baz eklemeyi düşünün")
            elif avg_ph > 9:
                recommendations.append("   💡 Öneri: pH bazik, asit eklemeyi düşünün")
            else:
                recommendations.append("   ✅ pH optimum aralıkta (7-9)")
            recommendations.append("")
        
        # Yoğunluk analizi
        densities = [d.get('density') for d in data if d.get('density')]
        if densities:
            avg_dens = sum(densities) / len(densities)
            recommendations.append(f"⚖️ **Yoğunluk Analizi**")
            recommendations.append(f"   • Ortalama: {avg_dens:.3f} g/ml")
            recommendations.append("")
        
        # Örtücülük analizi
        opacities = [d.get('opacity') for d in data if d.get('opacity')]
        if opacities:
            avg_opacity = sum(opacities) / len(opacities)
            recommendations.append(f"🎨 **Örtücülük Analizi**")
            recommendations.append(f"   • Ortalama: %{avg_opacity:.1f}")
            
            if avg_opacity < 90:
                recommendations.append("   💡 Öneri: Örtücülük düşük, TiO2 oranını artırın")
            else:
                recommendations.append("   ✅ Örtücülük optimum seviyede")
            recommendations.append("")
        
        # Parlaklık analizi
        gloss_values = [d.get('gloss') for d in data if d.get('gloss')]
        if gloss_values:
            avg_gloss = sum(gloss_values) / len(gloss_values)
            recommendations.append(f"✨ **Parlaklık Analizi**")
            recommendations.append(f"   • Ortalama: {avg_gloss:.1f} GU")
            recommendations.append("")
        
        recommendations.append("=" * 40)
        recommendations.append(f"📝 Analiz edilen kayıt sayısı: {len(data)}")
        recommendations.append("⚙️ Mod: Offline (Lokal Algoritma)")
        
        return "\n".join(recommendations)
    
    def _format_local_result(self, result: Dict, data: List[Dict]) -> str:
        """Lokal model sonucunu formatla"""
        output = []
        output.append("🤖 **AI FORMÜLASYON ÖNERİSİ**")
        output.append("=" * 40)
        output.append("⚙️ Mod: Offline (Scikit-learn Model)")
        output.append("")
        
        if 'prediction' in result:
            output.append(f"📊 **Tahmin**: {result['prediction']}")
        
        if 'confidence' in result:
            output.append(f"📈 **Güven Skoru**: %{result['confidence']*100:.1f}")
        
        if 'recommendations' in result:
            output.append("")
            output.append("💡 **Öneriler**:")
            for i, rec in enumerate(result['recommendations'], 1):
                output.append(f"   {i}. {rec}")
        
        if 'feature_importance' in result:
            output.append("")
            output.append("📋 **Önemli Parametreler**:")
            for feature, importance in result['feature_importance'].items():
                bar = "█" * int(importance * 20)
                output.append(f"   • {feature}: {bar} ({importance*100:.1f}%)")
        
        output.append("")
        output.append("=" * 40)
        output.append(f"Analiz edilen kayıt: {len(data)}")
        
        return "\n".join(output)
    
    def _format_online_result(self, result: Dict) -> str:
        """Online API sonucunu formatla"""
        output = []
        output.append("🌐 **AI FORMÜLASYON ÖNERİSİ**")
        output.append("=" * 40)
        output.append("⚙️ Mod: Online (Bulut AI)")
        output.append("")
        
        if 'analysis' in result:
            output.append(result['analysis'])
        
        if 'suggestions' in result:
            output.append("")
            output.append("💡 **Öneriler**:")
            for suggestion in result['suggestions']:
                output.append(f"   • {suggestion}")
        
        return "\n".join(output)
    
    def get_mode_status(self) -> Dict:
        """Mevcut mod durumunu döndür"""
        is_online = self.network_checker.check_connection()
        
        return {
            'is_online': is_online,
            'available_modes': ['local'] + (['online'] if is_online else []),
            'recommended_mode': 'online' if is_online else 'local',
            'local_model_available': self.local_model_path and self._check_model_exists(),
            'api_configured': bool(self.api_endpoint)
        }
    
    def _check_model_exists(self) -> bool:
        """Lokal model dosyasının varlığını kontrol et"""
        import os
        return os.path.exists(self.local_model_path) if self.local_model_path else False
