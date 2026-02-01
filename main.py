"""
NEXUS PRIME v17.0 - Akıllı Ekran Okuma ve Çeviri Aracı
Geliştirilmiş versiyon: Yeni arayüz, hotkeys, istatistikler, gelişmiş ayarlar
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import time
import os
import sys
import logging
import json
from typing import Optional, Tuple, List, Dict
from pathlib import Path
from datetime import datetime
import keyboard

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


class TranslationHistory:
    """Çeviri geçmişi yönetimi"""
    
    def __init__(self, history_file: str = "translation_history.json"):
        self.history_file = history_file
        self.history: List[Dict] = []
        self.stats = {"total_translations": 0, "total_characters": 0}
        self.load()
    
    def add(self, original: str, translated: str, language_pair: str) -> None:
        """Çeviriye geçmişe ekle"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "original": original,
            "translated": translated,
            "language_pair": language_pair
        }
        self.history.append(entry)
        self.stats["total_translations"] += 1
        self.stats["total_characters"] += len(original)
        self.save()
    
    def save(self) -> None:
        """Geçmişi kaydet"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({"history": self.history, "stats": self.stats}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Geçmiş kaydetme hatası: {e}")
    
    def load(self) -> None:
        """Geçmişi yükle"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get("history", [])
                    self.stats = data.get("stats", {"total_translations": 0, "total_characters": 0})
        except Exception as e:
            logger.error(f"Geçmiş yükleme hatası: {e}")
    
    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Son çevirileri getir"""
        return self.history[-limit:]


class NexusSentenceMode(ctk.CTk):
    """Ana uygulama penceresi"""
    
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.history = TranslationHistory()
        self._setup_variables()
        self._setup_window()
        self._setup_ui()
        self._initialize_components()
        self._setup_hotkeys()
        logger.info("NEXUS PRIME v17.0 başlatıldı")
    
    def _setup_variables(self) -> None:
        """Uygulama değişkenlerini başlat"""
        self.running = False
        self.selected_region: Optional[Tuple[int, int, int, int]] = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Ayarlar
        self.settings = {
            "source_language": self.config.source_language,
            "target_language": self.config.target_language,
            "theme": "dark",
            "ocr_interval": self.config.ocr_interval,
            "contrast": self.config.contrast_level,
            "enable_sound": True,
            "auto_copy": False
        }
        
        # Bileşenleri başlat
        self.tesseract_mgr = TesseractManager(self.config)
        self.image_processor = ImageProcessor()
        
        try:
            self.translator = GoogleTranslator(
                source=self.settings["source_language"],
                target=self.settings["target_language"]
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
        ).pack(pady=20)
        
        # Sekme buttonları
        self.tab_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        self.tab_frame.pack(fill="x", padx=10, pady=10)
        
        self.tab_buttons = {}
        for tab_name in ["Ana", "Ayarlar", "Geçmiş"]:
            btn = ctk.CTkButton(
                self.tab_frame,
                text=tab_name,
                fg_color="#1a1a2e",
                border_width=2,
                border_color=self.config.neon_color,
                command=lambda t=tab_name: self._switch_tab(t)
            )
            btn.pack(fill="x", pady=5)
            self.tab_buttons[tab_name] = btn
        
        # İçerik alanı
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(side="right", fill="both", expand=True, padx=30, pady=30)
        
        # Sekmeler
        self.tabs = {}
        self._create_main_tab()
        self._create_settings_tab()
        self._create_history_tab()
        
        # Ana sekmesini göster
        self._switch_tab("Ana")
    
    def _switch_tab(self, tab_name: str) -> None:
        """Sekmeleri değiştir"""
        # Tüm sekmeler gizle
        for tab in self.tabs.values():
            tab.pack_forget()
        
        # Seçili sekmeyi göster
        self.tabs[tab_name].pack(fill="both", expand=True)
        
        # Button rengini güncelle
        for name, btn in self.tab_buttons.items():
            if name == tab_name:
                btn.configure(fg_color=self.config.neon_color, text_color="#000")
            else:
                btn.configure(fg_color="#1a1a2e", text_color="white")
    
    def _create_main_tab(self) -> None:
        """Ana sekmeyi oluştur"""
        main_tab = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.tabs["Ana"] = main_tab
        
        # Başlık
        ctk.CTkLabel(main_tab, text="AKILLI ÇEVİRİ MOTORU", font=("Roboto", 24, "bold")).pack(pady=20)
        
        # Pencere seçici
        ctk.CTkLabel(main_tab, text="Hedef Pencere:", font=("Roboto", 12)).pack(anchor="w", padx=10)
        windows = self._get_windows()
        self.window_combo = ctk.CTkComboBox(
            main_tab, width=400, height=40,
            values=windows if windows else ["Pencere bulunamadı"]
        )
        self.window_combo.pack(fill="x", pady=10)
        
        # Bölge seçme butonu
        self.btn_region = ctk.CTkButton(
            main_tab, text="🎯 ALTYAZI ALANINI BELİRLE", height=60,
            fg_color="#1a1a2e", border_width=2, border_color=self.config.neon_color,
            command=self.select_region, font=("Roboto", 14, "bold")
        )
        self.btn_region.pack(fill="x", pady=15)
        
        # Başlat butonu
        self.btn_start = ctk.CTkButton(
            main_tab, text="▶ BAŞLAT", height=80,
            fg_color=self.config.neon_color, text_color="#000",
            command=self.toggle_translation, font=("Roboto", 18, "bold")
        )
        self.btn_start.pack(fill="x", pady=15)
        
        # Terminal
        ctk.CTkLabel(main_tab, text="Aktivite Logu:", font=("Roboto", 12, "bold")).pack(anchor="w", padx=10, pady=(20, 5))
        self.terminal = ctk.CTkTextbox(main_tab, fg_color="#08080a", text_color="#00ff88", font=("Consolas", 11))
        self.terminal.pack(fill="both", expand=True, pady=10)
        self.terminal.insert("0.0", ">>> NEXUS PRIME v17.0 Başlatıldı\n>>> Hazır")
        self.terminal.configure(state="disabled")
    
    def _create_settings_tab(self) -> None:
        """Ayarlar sekmesini oluştur"""
        settings_tab = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.tabs["Ayarlar"] = settings_tab
        
        # Başlık
        ctk.CTkLabel(settings_tab, text="AYARLAR", font=("Roboto", 20, "bold")).pack(pady=20)
        
        # Scroll frame
        scroll_frame = ctk.CTkScrollableFrame(settings_tab, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)
        
        # Dil Ayarları
        ctk.CTkLabel(scroll_frame, text="DİL AYARLARI", font=("Roboto", 14, "bold")).pack(anchor="w", padx=10, pady=(20, 10))
        
        ctk.CTkLabel(scroll_frame, text="Kaynak Dil:", font=("Roboto", 12)).pack(anchor="w", padx=20)
        self.source_lang = ctk.CTkComboBox(scroll_frame, values=["en", "tr", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"])
        self.source_lang.set("en")
        self.source_lang.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(scroll_frame, text="Hedef Dil:", font=("Roboto", 12)).pack(anchor="w", padx=20, pady=(15, 0))
        self.target_lang = ctk.CTkComboBox(scroll_frame, values=["tr", "en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"])
        self.target_lang.set("tr")
        self.target_lang.pack(fill="x", padx=20, pady=5)
        
        # OCR Ayarları
        ctk.CTkLabel(scroll_frame, text="OCR AYARLARI", font=("Roboto", 14, "bold")).pack(anchor="w", padx=10, pady=(25, 10))
        
        ctk.CTkLabel(scroll_frame, text=f"Kontras Seviyesi: {self.config.contrast_level}", font=("Roboto", 12)).pack(anchor="w", padx=20)
        self.contrast_slider = ctk.CTkSlider(scroll_frame, from_=1.0, to=5.0, number_of_steps=40)
        self.contrast_slider.set(self.config.contrast_level)
        self.contrast_slider.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(scroll_frame, text=f"Tarama Aralığı: {self.config.ocr_interval}s", font=("Roboto", 12)).pack(anchor="w", padx=20, pady=(15, 0))
        self.interval_slider = ctk.CTkSlider(scroll_frame, from_=0.1, to=1.0, number_of_steps=90)
        self.interval_slider.set(self.config.ocr_interval)
        self.interval_slider.pack(fill="x", padx=20, pady=5)
        
        # Özellikler
        ctk.CTkLabel(scroll_frame, text="ÖZELLİKLER", font=("Roboto", 14, "bold")).pack(anchor="w", padx=10, pady=(25, 10))
        
        self.auto_copy_check = ctk.CTkCheckBox(scroll_frame, text="Otomatik Kopyala", font=("Roboto", 12))
        self.auto_copy_check.pack(anchor="w", padx=20, pady=5)
        
        self.sound_check = ctk.CTkCheckBox(scroll_frame, text="Ses Bildirimi Aç", font=("Roboto", 12))
        self.sound_check.pack(anchor="w", padx=20, pady=5)
        
        # Kaydet butonu
        ctk.CTkButton(scroll_frame, text="💾 KAYDET", height=50, command=self._save_settings).pack(fill="x", padx=20, pady=20)
    
    def _create_history_tab(self) -> None:
        """Geçmiş sekmesini oluştur"""
        history_tab = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.tabs["Geçmiş"] = history_tab
        
        # Başlık
        ctk.CTkLabel(history_tab, text="ÇEVİRİ GEÇMİŞİ", font=("Roboto", 20, "bold")).pack(pady=20)
        
        # İstatistikler
        stats_frame = ctk.CTkFrame(history_tab, fg_color="#1a1a2e", corner_radius=10)
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        total = self.history.stats.get("total_translations", 0)
        chars = self.history.stats.get("total_characters", 0)
        
        ctk.CTkLabel(stats_frame, text=f"📊 Toplam Çeviri: {total}", font=("Roboto", 12)).pack(anchor="w", padx=15, pady=10)
        ctk.CTkLabel(stats_frame, text=f"📝 Toplam Karakter: {chars}", font=("Roboto", 12)).pack(anchor="w", padx=15, pady=10)
        
        # Geçmiş listesi
        ctk.CTkLabel(history_tab, text="Son Çeviriler:", font=("Roboto", 12, "bold")).pack(anchor="w", padx=10, pady=(15, 5))
        
        history_scroll = ctk.CTkScrollableFrame(history_tab, fg_color="#0a0a0a", corner_radius=10)
        history_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        recent = self.history.get_recent(20)
        if recent:
            for item in reversed(recent):
                entry_frame = ctk.CTkFrame(history_scroll, fg_color="#1a1a2e", corner_radius=8)
                entry_frame.pack(fill="x", padx=5, pady=5)
                
                ctk.CTkLabel(entry_frame, text=f"📌 {item['original'][:50]}...", font=("Roboto", 10), text_color="#00ff88").pack(anchor="w", padx=10, pady=(5, 0))
                ctk.CTkLabel(entry_frame, text=f"✓ {item['translated'][:50]}...", font=("Roboto", 10), text_color="#00d2ff").pack(anchor="w", padx=10, pady=(0, 5))
        else:
            ctk.CTkLabel(history_scroll, text="Geçmiş boş", font=("Roboto", 12)).pack(pady=20)
        
        # Temizle butonu
        ctk.CTkButton(history_tab, text="🗑️ GEÇMİŞİ TEMİZLE", height=40, fg_color="#ff4b4b", command=self._clear_history).pack(fill="x", padx=10, pady=10)
    
    def _save_settings(self) -> None:
        """Ayarları kaydet"""
        self.settings["source_language"] = self.source_lang.get()
        self.settings["target_language"] = self.target_lang.get()
        self.settings["contrast"] = self.contrast_slider.get()
        self.settings["ocr_interval"] = self.interval_slider.get()
        self.settings["auto_copy"] = self.auto_copy_check.get()
        self.settings["enable_sound"] = self.sound_check.get()
        
        # Çeviriciyi yeniden başlat
        try:
            self.translator = GoogleTranslator(
                source=self.settings["source_language"],
                target=self.settings["target_language"]
            )
        except:
            pass
        
        self._log("[AYARLAR] Ayarlar kaydedildi")
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi!")
    
    def _clear_history(self) -> None:
        """Geçmişi temizle"""
        if messagebox.askyesno("Onayla", "Geçmiş silinecek, emin misin?"):
            self.history.history = []
            self.history.stats = {"total_translations": 0, "total_characters": 0}
            self.history.save()
            self._log("[GEÇMİŞ] Geçmiş temizlendi")
            self._switch_tab("Geçmiş")
    
    def _setup_hotkeys(self) -> None:
        """Sistem hotkeys'ini ayarla"""
        try:
            keyboard.add_hotkey('ctrl+shift+s', self.toggle_translation)
            keyboard.add_hotkey('ctrl+shift+r', self.select_region)
            logger.info("Hotkeys bağlandı: Ctrl+Shift+S (Başlat), Ctrl+Shift+R (Bölge seç)")
        except Exception as e:
            logger.warning(f"Hotkey kurulamadı: {e}")
    
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
                text="⏹ DURDUR",
                fg_color="#ff4b4b",
                text_color="#fff"
            )
            self._log("[BAŞLAT] Çeviri motoru başlatıldı 🎯")
            threading.Thread(target=self._process_loop, daemon=True).start()
        else:
            self.running = False
            if self.overlay:
                self.overlay.destroy()
            self.btn_start.configure(
                text="▶ BAŞLAT",
                fg_color=self.config.neon_color,
                text_color="#000"
            )
            self._log("[DURDUR] Çeviri motoru durduruldu ⏹")
    
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
                
                # Kontrast ayarını uygula
                enhancer = ImageEnhance.Contrast(processed)
                processed = enhancer.enhance(self.settings["contrast"])
                
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
                            self._log(f"[✓] {translated}")
                            self.history.add(accumulated_text, translated, f"{self.settings['source_language']}->{self.settings['target_language']}")
                            
                            # Otomatik kopyala
                            if self.settings["auto_copy"]:
                                pyautogui.write(translated, interval=0.01)
                    except Exception as e:
                        logger.error(f"Çeviri hatası: {e}")
                    
                    accumulated_text = ""
                
                time.sleep(self.settings["ocr_interval"])
                
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
