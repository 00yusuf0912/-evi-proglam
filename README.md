# NEXUS PRIME v17.0 - Akıllı Ekran Okuma ve Çeviri Aracı

## 🎯 Nedir?

NEXUS PRIME, real-time ekran okuma (OCR) ve otomatik çeviri yapan gelişmiş bir Python uygulamasıdır. Özellikle oyunlar, filmler veya video oynatıcılardan altyazıları okumuş olarak anında Türkçeye çevirebilir.

## ✨ Yeni Özellikler (v17.0)

- 🎮 **Sekme Arayüzü**: Ana, Ayarlar, Geçmiş sekmelerine ayrılmış modern UI
- ⌨️ **Sistem Hotkeys**: `Ctrl+Shift+S` (Başlat), `Ctrl+Shift+R` (Bölge Seç)
- 📊 **Çeviri Geçmişi**: Tüm çevirileri JSON'da kaydet, istatistikleri görüntüle
- 🌍 **10+ Dil Desteği**: Ayarlardan dil seçimi
- 🎚️ **İleri OCR Kontrolü**: Kontrast, tarama aralığı ayarları
- 📋 **Otomatik Kopyala**: Çevirilen metni otomatik olarak yapıştır
- 🔔 **Ses Bildirimi**: Çeviri tamamlandığında bildir (konfigüre edilebilir)

## 📋 Gereksinimler

### Yazılım Bağımlılıkları

```bash
pip install -r requirements.txt
```

### Sistem Bağımlılıkları

#### Windows
1. [Tesseract-OCR](https://github.com/UB-Mannheim/tesseract/wiki) indir
2. Varsayılan konuma kur (`C:\Program Files\Tesseract-OCR\`)

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get install tesseract-ocr
```

#### macOS
```bash
brew install tesseract
```

## 🚀 Kullanım

### Temel Çalıştırma
```bash
python main.py
```

### Sekmeler

#### Ana Sekme
- Hedef pencere seçimi
- Altyazı bölgesi tanımlama
- Çeviri başlatma/durdurma
- Aktivite logu

#### Ayarlar Sekme
- **Dil Ayarları**: Kaynak ve hedef dil seçimi
- **OCR Ayarları**: Kontrast, tarama aralığı
- **Özellikler**: Otomatik kopyala, ses bildirimi

#### Geçmiş Sekme
- Tüm çevirilerin listesi
- Toplam çeviri ve karakter istatistikleri
- Geçmiş temizleme seçeneği

### Hotkeys
- `Ctrl+Shift+S`: Çeviriyi başlat/durdur
- `Ctrl+Shift+R`: Altyazı bölgesini seç

## ⚙️ Yapılandırma

`config.py` dosyasında değiştirebileceğiniz ayarlar:

```python
# Versiyon
version = "17.0"

# OCR Ayarları
ocr_interval = 0.3  # Kontrol aralığı (saniye)
sentence_pause_threshold = 1.0  # Cümle bitişi süresi
contrast_level = 2.5  # Varsayılan kontrast

# Çeviri
source_language = 'en'  # Kaynak dil
target_language = 'tr'  # Hedef dil
```

## 🎨 Tema Özelleştirmesi

`config.py` dosyasında renkleri değiştirin:

```python
bg_color = "#050505"        # Arka plan
neon_color = "#00d2ff"      # Neon renk (tuşlar, sınırlar)
text_color = "white"        # Yazı rengi
```

## 📊 Çeviri Geçmişi

Tüm çeviriler `translation_history.json` dosyasına otomatik kaydedilir:

```json
{
  "history": [
    {
      "timestamp": "2026-02-01T12:00:00",
      "original": "Hello world",
      "translated": "Merhaba dünya",
      "language_pair": "en->tr"
    }
  ],
  "stats": {
    "total_translations": 42,
    "total_characters": 1337
  }
}
```

## 🐛 Sorun Giderme

### "Tesseract not found" hatası
```bash
# Windows: Tesseract-OCR'ı yükleyin
# Linux: sudo apt-get install tesseract-ocr
# macOS: brew install tesseract
```

### OCR çalışmıyor
- Tesseract başarıyla yüklendiğini kontrol edin
- `nexus.log` dosyasını kontrol edin
- Contrast ayarını artırın

### Hotkeys çalışmıyor
- Linux'ta `sudo` izni gerekebilir: `sudo python main.py`
- Windows'ta izin isteyebilir

### Çeviri hataları
- İnternet bağlantısını kontrol edin
- Deep-translator kütüphanesini güncelleyin: `pip install --upgrade deep-translator`

## 📝 Loglar

Tüm işlemler `nexus.log` dosyasına kaydedilir:
```
2026-02-01 12:00:00 - INFO - NEXUS PRIME v17.0 başlatıldı
2026-02-01 12:00:05 - INFO - Hotkeys bağlandı: Ctrl+Shift+S (Başlat), Ctrl+Shift+R (Bölge seç)
2026-02-01 12:00:10 - INFO - Çeviri motoru başlatıldı
```

## 🔧 Geliştiriciler için

### Debug Modu
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### İstatistikleri Temizle
```python
from main import TranslationHistory
h = TranslationHistory()
h.history = []
h.stats = {"total_translations": 0, "total_characters": 0}
h.save()
```

## 📊 İyileştirmeler (v16.1 → v17.0)

| Özellik | v16.1 | v17.0 |
|---------|-------|-------|
| Arayüz | Tek ekran | Sekme sistemi |
| Hotkeys | Yok | Ctrl+Shift+S/R |
| Geçmiş | Yok | JSON kayıt + İstatistik |
| Ayarlar | Hardcoded | GUI'dan değiştirilebilir |
| Dil Seçimi | Sabit | Dinamik seçim |
| OCR Kontrol | Sabit | Slider kontrolü |

## 📜 Lisans

MIT License - Özgürce kullanın ve değiştirin

## 🤝 Katkı

Hataları veya iyileştirmeleri GitHub Issues'de raporlayın.

---

**Geliştirici**: 00yusuf0912  
**Son Güncelleme**: Şubat 2026  
**Versiyon**: 17.0