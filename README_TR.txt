================================================================================
                    PAINT FORMULATION AI - PORTABLE EDITION
                         Boya Formülasyonu Yönetim Sistemi
                                   Sürüm 1.1.0
================================================================================

HAKKINDA
--------
Paint Formulation AI, boya formülasyonlarınızı yönetmenizi, analiz etmenizi ve
yapay zeka destekli öneriler almanızı sağlayan bir masaüstü uygulamasıdır.

Uygulama, internet bağlantısı olmadan da tam fonksiyonel çalışabilir (Hibrit Mod).


KURULUM
-------
Kurulum gerektirmez! PaintFormulationAI.exe dosyasını çift tıklayarak 
uygulamayı başlatabilirsiniz.


KULLANIM
--------
1. PaintFormulationAI.exe dosyasına çift tıklayın
2. Uygulama açıldığında yeni bir proje oluşturun veya mevcut projeyi açın
3. Excel dosyanızı sürükleyip bırakarak verileri import edin
4. Dashboard üzerinde grafikler ve analizleri inceleyin
5. "AI Öneri Al" butonuna basarak formülasyon önerileri alın


DOSYA YAPISI
------------
PaintFormulationAI.exe  - Ana uygulama dosyası
config.ini              - Konfigürasyon ayarları
data_storage/           - Veritabanı ve veri dosyaları
  └── db.sqlite         - SQLite veritabanı
logs/                   - Log dosyaları
README_TR.txt           - Bu dosya
LISANS.txt              - Lisans bilgileri


OFFLINE MOD
-----------
Uygulama internet bağlantısı olmadan şu özellikleri sunar:
- Veri girişi ve düzenleme
- Excel import/export
- Dashboard ve grafikler
- Temel ML önerileri (Scikit-learn tabanlı)

İnternet bağlantısı varsa gelişmiş AI önerileri için bulut API kullanılır.


TEKNİK BİLGİLER
---------------
- Python 3.9 (Gömülü)
- SQLite veritabanı
- Hibrit ML motoru (Offline: Scikit-learn, Online: API)


DESTEK
------
Sorularınız için: support@example.com


================================================================================
                          © 2024 Paint Formulation AI
================================================================================
