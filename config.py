"""
NEXUS PRIME - Konfigürasyon Dosyası
Tüm ayarları burada yapılandırın
"""

import os
import sys
from pathlib import Path
from typing import Optional


class AppConfig:
    """Uygulama yapılandırması (v18.0)"""
    
    # --- VERSIYON ---
    version = "18.0"
    
    # --- PENCERE AYARLARI ---
    window_geometry = "1100x750"
    overlay_geometry = "900x150+400+800"
    overlay_alpha = 0.95
    
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
    
    # --- TEMA AYARLARI (v18.0+) ---
    available_themes = {
        "neon": {
            "primary": "#00d2ff",
            "secondary": "#ff006e",
            "accent": "#ffbe0b",
            "bg": "#0a0a0a",
            "fg": "#00ff88"
        },
        "cyberpunk": {
            "primary": "#ff006e",
            "secondary": "#00d2ff",
            "accent": "#ffbe0b",
            "bg": "#0d0221",
            "fg": "#e0aaff"
        },
        "matrix": {
            "primary": "#00ff00",
            "secondary": "#00cc00",
            "accent": "#ffff00",
            "bg": "#000000",
            "fg": "#00ff00"
        },
        "synthwave": {
            "primary": "#ff006e",
            "secondary": "#00d2ff",
            "accent": "#ffd60a",
            "bg": "#0f0f1e",
            "fg": "#ffd60a"
        }
    }
    
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
