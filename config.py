"""
NEXUS PRIME - Konfigürasyon Dosyası
Tüm ayarları burada yapılandırın
"""

import os
import sys
from pathlib import Path
from typing import Optional


class AppConfig:
    """Uygulama yapılandırması"""
    
    # --- VERSIYON ---
    version = "16.1"
    
    # --- PENCERE AYARLARI ---
    window_geometry = "1000x700"
    overlay_geometry = "900x130+400+820"
    overlay_alpha = 0.9
    
    # --- RENKLER (Neon Tema) ---
    bg_color = "#050505"
    neon_color = "#00d2ff"
    text_color = "white"
    wrap_length = 850
    
    # --- FONT AYARLARI ---
    font_name = "Segoe UI"
    font_size = 20
    
    # --- OCR AYARLARI ---
    ocr_interval = 0.3  # Saniye cinsinden
    sentence_pause_threshold = 1.0  # Cümle bitişi için bekleme süresi
    contrast_level = 2.5
    brightness_level = 1.0
    
    # --- ÇEVİRİ AYARLARI ---
    source_language = 'en'
    target_language = 'tr'
    
    @staticmethod
    def get_tesseract_path() -> Optional[str]:
        """
        İşletim sistemine göre Tesseract yolunu belirle
        
        Windows: C:\\Program Files\\Tesseract-OCR\\tesseract.exe
        Linux: /usr/bin/tesseract
        macOS: /usr/local/bin/tesseract
        """
        system = sys.platform
        
        if system == "win32":
            # Windows
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
            ]
        elif system == "linux":
            # Linux
            common_paths = [
                "/usr/bin/tesseract",
                "/usr/local/bin/tesseract",
                os.path.expanduser("~/tesseract/bin/tesseract"),
            ]
        elif system == "darwin":
            # macOS
            common_paths = [
                "/usr/local/bin/tesseract",
                "/opt/homebrew/bin/tesseract",
            ]
        else:
            return None
        
        # İlk var olan yolu döndür
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # Hiçbiri bulunamadıysa None döndür
        return None
    
    @staticmethod
    def get_project_root() -> Path:
        """Proje kök dizinini döndür"""
        return Path(__file__).parent
    
    @staticmethod
    def get_log_path() -> Path:
        """Log dosyasının yolunu döndür"""
        log_dir = AppConfig.get_project_root() / "logs"
        log_dir.mkdir(exist_ok=True)
        return log_dir / "nexus.log"
