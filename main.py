"""
NEXUS PRIME v16.1 - Akıllı Ekran Okuma ve Çeviri Aracı
Geliştirilmiş versiyon: Hata yönetimi, logging ve platform uyumluluğu iyileştirildi.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import time
import os
import sys
import logging
from typing import Optional, Tuple, List
from pathlib import Path

import pyautogui
import pygetwindow as gw
from PIL import Image, ImageOps, ImageEnhance
from deep_translator import GoogleTranslator

try:
    import pytesseract
except ImportError:
    pytesseract = None

from config import AppConfig

# --- LOGGING KURULUMU ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nexus.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TesseractManager:
    """Tesseract OCR yönetimi (platform uyumlu)"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.available = False
        self.initialize()
    
    def initialize(self) -> bool:
        """Tesseract'ı yapılandır ve kontrol et"""
        try:
            if not pytesseract:
                logger.warning("pytesseract yüklenmemiş")
                return False
            
            # Tesseract yolunu set et
            tesseract_path = self.config.get_tesseract_path()
            if tesseract_path and os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                logger.info(f"Tesseract yolu: {tesseract_path}")
            
            # Tesseract'ı test et
            pytesseract.get_tesseract_version()
            self.available = True
            logger.info("Tesseract başarıyla başlatıldı")
            return True
            
        except Exception as e:
            logger.error(f"Tesseract başlatma hatası: {e}")
            return False
    
    def extract_text(self, image: Image.Image, language: str = 'eng') -> str:
        """Görüntüden metin çıkart"""
        if not self.available:
            logger.warning("Tesseract kullanılamıyor")
            return ""
        
        try:
            return pytesseract.image_to_string(image, lang=language).strip()
        except Exception as e:
            logger.error(f"OCR hatası: {e}")
            return ""


class ImageProcessor:
    """Görüntü işleme işlemleri"""
    
    @staticmethod
    def prepare_for_ocr(image: Image.Image, config: AppConfig) -> Image.Image:
        """OCR için görüntüyü optimize et"""
        try:
            # Gri tonlamaya dönüştür ve ters çevir
            image = ImageOps.invert(ImageOps.grayscale(image))
            
            # Kontrastı artır
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(config.contrast_level)
            
            # Parlaklığı ayarla
            brightness_enhancer = ImageEnhance.Brightness(image)
            image = brightness_enhancer.enhance(config.brightness_level)
            
            return image
        except Exception as e:
            logger.error(f"Görüntü işleme hatası: {e}")
            return image


class SubtitleOverlay(tk.Toplevel):
    """Çeviri sonuçlarını gösteren overlay penceresi"""
    
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self._setup_window()
        self._setup_ui()
        self._bind_events()
    
    def _setup_window(self) -> None:
        """Pencere özelliklerini yapılandır"""
        self.overrideredirect(True)
        self.attributes("-topmost", True, "-alpha", self.config.overlay_alpha)
        self.config_window(bg=self.config.bg_color)
        self.geometry(self.config.overlay_geometry)
    
    def _setup_ui(self) -> None:
        """UI öğelerini oluştur"""
        # Neon sınır
        self.border = tk.Frame(self, bg=self.config.neon_color, padx=2, pady=2)
        self.border.pack(expand=True, fill="both")
        
        # İç çerçeve
        self.inner = tk.Frame(self.border, bg=self.config.bg_color)
        self.inner.pack(expand=True, fill="both")
        
        # Metin etiketi
        self.label = tk.Label(
            self.inner,
            text="NEXUS AI: Konuşma Bekleniyor...",
            font=(self.config.font_name, self.config.font_size, "bold"),
            fg=self.config.text_color,
            bg=self.config.bg_color,
            wraplength=self.config.wrap_length,
            justify="center"
        )
        self.label.pack(expand=True, fill="both", padx=15)
    
    def _bind_events(self) -> None:
        """Olay bağlantılarını ayarla (sürükleme)"""
        self.bind("<Button-1>", self._start_drag)
        self.bind("<B1-Motion>", self._drag)
    
    def _start_drag(self, event) -> None:
        """Sürükleme başlat"""
        self.drag_x = event.x
        self.drag_y = event.y
    
    def _drag(self, event) -> None:
        """Pencereyi sürükle"""
        new_x = self.winfo_x() + (event.x - self.drag_x)
        new_y = self.winfo_y() + (event.y - self.drag_y)
        self.geometry(f"+{new_x}+{new_y}")
    
    def update_text(self, text: str) -> None:
        """Gösterilen metni güncelle"""
        self.label.config(text=text)
        self.update()


class NexusSentenceMode(ctk.CTk):
    """Ana uygulama penceresi"""
    
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self._setup_variables()
        self._setup_window()
        self._setup_ui()
        self._initialize_components()
        logger.info("NEXUS PRIME başlatıldı")
    
    def _setup_variables(self) -> None:
        """Uygulama değişkenlerini başlat"""
        self.running = False
        self.selected_region: Optional[Tuple[int, int, int, int]] = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Bileşenleri başlat
        self.tesseract_mgr = TesseractManager(self.config)
        self.image_processor = ImageProcessor()
        
        try:
            self.translator = GoogleTranslator(
                source=self.config.source_language,
                target=self.config.target_language
            )
        except Exception as e:
            logger.error(f"Çevirmen başlatma hatası: {e}")
            self.translator = None
        
        self.overlay: Optional[SubtitleOverlay] = None
    
    def _setup_window(self) -> None:
        """Ana pencereyi yapılandır"""
        self.title(f"NEXUS PRIME v{self.config.version}")
        self.geometry(self.config.window_geometry)
        ctk.set_appearance_mode("dark")
    
    def _setup_ui(self) -> None:
        """Kullanıcı arayüzünü oluştur"""
        self.configure(fg_color=self.config.bg_color)
        
        # Sol panel
        left_panel = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color="#0a0a0a")
        left_panel.pack(side="left", fill="y")
        
        ctk.CTkLabel(
            left_panel,
            text="NEXUS",
            font=("Orbitron", 40, "bold"),
            text_color=self.config.neon_color
        ).pack(pady=50)
        
        # Sağ panel (içerik)
        content_panel = ctk.CTkFrame(self, fg_color="transparent")
        content_panel.pack(side="right", fill="both", expand=True, padx=30, pady=30)
        
        # Pencere seçici
        windows = self._get_windows()
        self.window_combo = ctk.CTkComboBox(
            content_panel,
            width=500,
            height=45,
            values=windows if windows else ["Pencere bulunamadı"]
        )
        self.window_combo.pack(pady=10)
        
        # Bölge seçme butonu
        self.btn_region = ctk.CTkButton(
            content_panel,
            text="ALTYAZI ALANINI BELİRLE",
            height=65,
            fg_color="#1a1a2e",
            border_width=1,
            border_color=self.config.neon_color,
            command=self.select_region
        )
        self.btn_region.pack(fill="x", pady=10)
        
        # Başlat butonu
        self.btn_start = ctk.CTkButton(
            content_panel,
            text="AKILLI ÇEVİRİYİ BAŞLAT",
            height=75,
            fg_color=self.config.neon_color,
            text_color="#000",
            font=("Roboto", 18, "bold"),
            command=self.toggle_translation
        )
        self.btn_start.pack(fill="x", pady=10)
        
        # Terminal (log alanı)
        self.terminal = ctk.CTkTextbox(
            content_panel,
            fg_color="#08080a",
            text_color="#00ff88",
            font=("Consolas", 14)
        )
        self.terminal.pack(fill="both", expand=True, pady=15)
        
        # İlk mesaj
        initial_msg = (
            ">>> Akıllı Cümle Modu Aktif.\n"
            ">>> Program cümlenin bitmesini bekleyip çevirecek.\n"
            ">>> Tesseract: " + ("✓ Aktif" if self.tesseract_mgr.available else "✗ Hata")
        )
        self.terminal.insert("0.0", initial_msg)
        self.terminal.configure(state="disabled")
    
    def _initialize_components(self) -> None:
        """Bileşenleri başlat"""
        if not self.tesseract_mgr.available:
            messagebox.showwarning(
                "Uyarı",
                "Tesseract yüklenmiş değil. OCR çalışmayabilir."
            )
    
    def _get_windows(self) -> List[str]:
        """Açık pencereleri listele"""
        try:
            return [w.title for w in gw.getAllWindows() if w.title]
        except Exception as e:
            logger.error(f"Pencere listesi hatası: {e}")
            return []
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """Terminal ve log dosyasına yaz"""
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(message)
        
        self.terminal.configure(state="normal")
        self.terminal.insert("end", f"\n>>> {message}")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")
    
    def select_region(self) -> None:
        """Altyazı bölgesini seç"""
        self.withdraw()
        time.sleep(0.5)
        
        selection_window = tk.Toplevel()
        selection_window.attributes("-alpha", 0.4, "-fullscreen", True, "-topmost", True)
        selection_window.config(cursor="cross")
        
        canvas = tk.Canvas(selection_window, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        def on_press(event):
            self.drag_start_x = event.x
            self.drag_start_y = event.y
        
        def on_drag(event):
            canvas.delete("selection_box")
            canvas.create_rectangle(
                self.drag_start_x, self.drag_start_y,
                event.x, event.y,
                outline=self.config.neon_color,
                width=3,
                tags="selection_box"
            )
        
        def on_release(event):
            self.selected_region = (
                min(self.drag_start_x, event.x),
                min(self.drag_start_y, event.y),
                abs(event.x - self.drag_start_x),
                abs(event.y - self.drag_start_y)
            )
            selection_window.destroy()
            self.deiconify()
            self._log(f"[BÖLGE] Altyazı bölgesi kilitlendi: {self.selected_region}")
        
        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
    
    def toggle_translation(self) -> None:
        """Çeviri motorunu aç/kapat"""
        if not self.selected_region:
            messagebox.showwarning(
                "Hata",
                "Lütfen önce altyazı bölgesini seçiniz!"
            )
            return
        
        if not self.running:
            self.running = True
            self.overlay = SubtitleOverlay(self.config)
            self.btn_start.configure(
                text="DURDUR",
                fg_color="#ff4b4b",
                text_color="#fff"
            )
            self._log("[BAŞLAT] Çeviri motoru başlatıldı")
            threading.Thread(target=self._process_loop, daemon=True).start()
        else:
            self.running = False
            if self.overlay:
                self.overlay.destroy()
            self.btn_start.configure(
                text="AKILLI ÇEVİRİYİ BAŞLAT",
                fg_color=self.config.neon_color,
                text_color="#000"
            )
            self._log("[DURDUR] Çeviri motoru durduruldu")
    
    def _process_loop(self) -> None:
        """Ana işleme döngüsü"""
        accumulated_text = ""
        last_update_time = time.time()
        
        while self.running:
            try:
                # Ekran görüntüsünü yakala
                screenshot = pyautogui.screenshot(region=self.selected_region)
                
                # Görüntüyü OCR için hazırla
                processed = self.image_processor.prepare_for_ocr(screenshot, self.config)
                
                # Metin çıkart
                current_text = self.tesseract_mgr.extract_text(processed)
                
                # Metin değişti mi?
                if len(current_text) > 1 and current_text != accumulated_text:
                    accumulated_text = current_text
                    last_update_time = time.time()
                
                # Cümle bitti mi? (1 saniye metin değişmedi mi)
                elapsed = time.time() - last_update_time
                if accumulated_text and elapsed > self.config.sentence_pause_threshold:
                    try:
                        if self.translator:
                            translated = self.translator.translate(accumulated_text)
                            if self.overlay:
                                self.overlay.update_text(translated)
                            self._log(f"[ÇEVİRİ] {translated}")
                    except Exception as e:
                        logger.error(f"Çeviri hatası: {e}")
                    
                    accumulated_text = ""
                
                time.sleep(self.config.ocr_interval)
                
            except Exception as e:
                logger.error(f"İşleme hatası: {e}")
                time.sleep(0.5)


def main():
    """Uygulamayı çalıştır"""
    try:
        app = NexusSentenceMode()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Uygulama hatası: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
