# NEXUS PRIME v16.1 - Akıllı Ekran Okuma ve Çeviri Aracı

## 🎯 Nedir?

NEXUS PRIME, real-time ekran okuma (OCR) ve otomatik çeviri yapan gelişmiş bir Python uygulamasıdır. Özellikle oyunlar, filmler veya video oynatıcılardan altyazıları okumuş olarak anında Türkçeye çevirebilir.

## ✨ Özellikler

- 🎮 **Oyun Uyumlu**: Neon tema ve overlay penceresi
- 🔤 **OCR**: Tesseract kullanarak metin okuma
- 🌍 **Otomatik Çeviri**: Google Translate ile desteklenen her dile çeviri
- 📊 **Cümle Modu**: Cümle bitene kadar bekleyip toplu çeviri
- 🖥️ **Platform Uyumlu**: Windows, Linux, macOS
- 📝 **Logging**: Detaylı log ve hata izlemesi
- ⚙️ **Yapılandırılabilir**: `config.py` ile tam kontrol

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

### Adımlar
1. **Pencere Seç**: Açılır listeden okumak istediğiniz pencereyi seçin
2. **Bölge Tanımla**: "ALTYAZI ALANINI BELİRLE" butonuna tıklayın
3. **Sürükleme**: Fare ile altyazı alanını seçin (çapraz sürükle)
4. **Başlat**: "AKILLI ÇEVİRİYİ BAŞLAT" butonuna tıklayın
5. **Sonuç**: Çeviriler overlay penceresinde görüntülenecek

## ⚙️ Yapılandırma

`config.py` dosyasında değiştirebileceğiniz ayarlar:

```python
# OCR Ayarları
ocr_interval = 0.3  # Kontrol aralığı (saniye)
sentence_pause_threshold = 1.0  # Cümle bitişi süresi

# Çeviri
source_language = 'en'  # Kaynak dil
target_language = 'tr'  # Hedef dil

# Tema
neon_color = "#00d2ff"  # Ana renk
```

## 🎨 Tema Özelleştirmesi

`config.py` dosyasında renkleri değiştirin:

```python
bg_color = "#050505"        # Arka plan
neon_color = "#00d2ff"      # Neon renk (tuşlar, sınırlar)
text_color = "white"        # Yazı rengi
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
- Contrast ve brightness ayarlarını artırın

### Çeviri hataları
- İnternet bağlantısını kontrol edin
- Deep-translator kütüphanesini güncelleyin: `pip install --upgrade deep-translator`

## 📝 Loglar

Tüm işlemler `nexus.log` dosyasına kaydedilir:
```
2026-02-01 12:00:00 - INFO - Tesseract başarıyla başlatıldı
2026-02-01 12:00:05 - INFO - Çeviri motoru başlatıldı
```

## 🔧 Geliştirme İçin İpuçları

### Hata Ayıklamayı Etkinleştir
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Modu (Screenshot kaydet)
```python
screenshot.save(f"debug_{int(time.time())}.png")
```

## 📊 İyileştirmeler (v16.0 → v16.1)

| Özellik | Eski | Yeni |
|---------|------|------|
| Platform Desteği | Sadece Windows | Windows/Linux/macOS |
| Hata Yönetimi | Zayıf (pass) | Kapsamlı logging |
| Kod Organizasyonu | Monolitik | Modüler sınıflar |
| Type Hints | Yok | Tam kapsam |
| Yapılandırma | Hardcoded | Merkezileştirilmiş |
| Docstrings | Yok | İngilizce + Türkçe |

## 📜 Lisans

MIT License - Özgürce kullanın ve değiştirin

## 🤝 Katkı

Hataları veya iyileştirmeleri GitHub Issues'de raporlayın.

---

**Geliştirici**: 00yusuf0912  
**Son Güncelleme**: Şubat 2026  
**Versiyon**: 16.1