"""
NEXUS PRIME v18.0 - Akıllı Ekran Okuma ve Çeviri Aracı
Geliştirilmiş versiyon: Animasyonlu arayüz, renkli temalar, live istatistikler
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
import random

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
        logging.FileHandler('nexus.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AnimationManager:
    """Arayüz animasyonları yönetimi"""
    
    @staticmethod
    def pulse_color(color_start: str, color_end: str, step: int) -> str:
        """İki renk arasında pulse animasyonu"""
        colors = [
            "#00d2ff", "#00c4ff", "#00b6ff", "#00a8ff",
            "#009aff", "#008cff", "#007fff", "#0071ff"
        ]
        return colors[step % len(colors)]
    
    @staticmethod
    def get_theme_colors(theme: str) -> Dict[str, str]:
        """Tema renklerini döndür"""
        themes = {
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
        return themes.get(theme, themes["neon"])


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
    """Çeviri sonuçlarını gösteren overlay penceresi (animasyonlu)"""
    
    def __init__(self, config: AppConfig, theme: str = "neon"):
        super().__init__()
        self.config = config
        self.theme = theme
        self.colors = AnimationManager.get_theme_colors(theme)
        self.pulse_step = 0
        self._setup_window()
        self._setup_ui()
        self._bind_events()
        self._start_pulse_animation()
    
    def _setup_window(self) -> None:
        """Pencere özelliklerini yapılandır"""
        self.overrideredirect(True)
        self.attributes("-topmost", True, "-alpha", self.config.overlay_alpha)
        self.configure(bg=self.colors["bg"])
        self.geometry(self.config.overlay_geometry)
    
    def _setup_ui(self) -> None:
        """UI öğelerini oluştur (animasyonlu sınır)"""
        # Animasyonlu neon sınır
        self.border = tk.Frame(self, bg=self.colors["primary"], padx=2, pady=2)
        self.border.pack(expand=True, fill="both")
        
        # İç çerçeve
        self.inner = tk.Frame(self.border, bg=self.colors["bg"])
        self.inner.pack(expand=True, fill="both")
        
        # Durum etiketi
        self.status = tk.Label(
            self.inner,
            text="◉ HAZIR",
            font=("Roboto", 10, "bold"),
            fg=self.colors["accent"],
            bg=self.colors["bg"]
        )
        self.status.pack(anchor="ne", padx=10, pady=5)
        
        # Metin etiketi (ana)
        self.label = tk.Label(
            self.inner,
            text="NEXUS AI: Konuşma Bekleniyor...",
            font=(self.config.font_name, self.config.font_size, "bold"),
            fg=self.colors["fg"],
            bg=self.colors["bg"],
            wraplength=self.config.wrap_length,
            justify="center"
        )
        self.label.pack(expand=True, fill="both", padx=15, pady=15)
        
        # Alt bilgi
        self.info = tk.Label(
            self.inner,
            text="Sürükle: Pencereyi taşı",
            font=("Roboto", 8),
            fg=self.colors["secondary"],
            bg=self.colors["bg"]
        )
        self.info.pack(anchor="s", padx=5, pady=5)
    
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
    
    def _start_pulse_animation(self) -> None:
        """Pulse animasyonunu başlat"""
        self._animate_pulse()
    
    def _animate_pulse(self) -> None:
        """Sınırı animasyonlu renk döngüsüne sok"""
        try:
            if not self.winfo_exists():
                return
            
            colors_seq = [
                self.colors["primary"],
                self.colors["secondary"],
                self.colors["accent"],
                self.colors["primary"]
            ]
            color = colors_seq[self.pulse_step % len(colors_seq)]
            self.border.configure(bg=color)
            
            self.pulse_step += 1
            self.after(300, self._animate_pulse)
        except Exception as e:
            logger.warning(f"Animation hatası: {e}")
    
    def update_text(self, text: str) -> None:
        """Gösterilen metni güncelle"""
        try:
            self.label.config(text=text, fg=self.colors["fg"])
            self.status.config(text="✓ ÇEVRILI", fg=self.colors["accent"])
            self.update()
        except Exception as e:
            logger.warning(f"Text update hatası: {e}")


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
        self.animation_step = 0
        self.current_theme = "neon"
        self._setup_variables()
        self._setup_window()
        self._setup_ui()
        self._initialize_components()
        self._setup_hotkeys()
        self._start_ui_animation()
        logger.info("NEXUS PRIME v18.0 başlatıldı")
    
    def _start_ui_animation(self) -> None:
        """UI animasyonunu başlat"""
        self._animate_ui()
    
    def _animate_ui(self) -> None:
        """Başlık animasyonunu güncelle"""
        try:
            if not self.winfo_exists():
                return
            
            colors = ["#00d2ff", "#ff006e", "#ffbe0b", "#00ff88"]
            color = colors[self.animation_step % len(colors)]
            self.title_label.configure(text_color=color)
            
            self.animation_step += 1
            self.after(500, self._animate_ui)
        except Exception as e:
            logger.warning(f"UI animation hatası: {e}")
    
    def _setup_variables(self) -> None:
        """Uygulama değişkenlerini başlat"""
        self.running = False
        self.selected_region: Optional[Tuple[int, int, int, int]] = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.translation_count = 0
        self.char_count = 0
        
        # Temalar
        self.available_themes = ["neon", "cyberpunk", "matrix", "synthwave"]
        self.current_theme = "neon"
        
        # Ayarlar
        self.settings = {
            "source_language": self.config.source_language,
            "target_language": self.config.target_language,
            "theme": "neon",
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
        """Kullanıcı arayüzünü oluştur (geliştirilmiş animasyonlu)"""
        self.configure(fg_color=self.config.bg_color)
        
        # Sol panel
        left_panel = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#0a0a0a")
        left_panel.pack(side="left", fill="y")
        
        # Animasyonlu başlık
        self.title_label = ctk.CTkLabel(
            left_panel,
            text="❯ NEXUS ◾",
            font=("Orbitron", 38, "bold"),
            text_color="#00d2ff"
        )
        self.title_label.pack(pady=15)
        
        # Versiyon ve durumu
        status_frame = ctk.CTkFrame(left_panel, fg_color="#1a1a2e", corner_radius=8)
        status_frame.pack(padx=10, pady=5, fill="x")
        
        ctk.CTkLabel(status_frame, text="v18.0", font=("Roboto", 9), text_color="#00ff88").pack(padx=10, pady=5)
        self.status_label = ctk.CTkLabel(status_frame, text="🟢 İDLE", font=("Roboto", 9), text_color="#00ff88")
        self.status_label.pack(padx=10, pady=5)
        
        # Sekme buttonları (geliştirilmiş stil)
        self.tab_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        self.tab_frame.pack(fill="x", padx=8, pady=15)
        
        self.tab_buttons = {}
        tab_icons = ["📊 Ana", "⚙️ Ayarlar", "📜 Geçmiş"]
        for i, tab_name in enumerate(["Ana", "Ayarlar", "Geçmiş"]):
            btn = ctk.CTkButton(
                self.tab_frame,
                text=tab_icons[i],
                fg_color="#1a1a2e",
                border_width=2,
                border_color="#00d2ff",
                command=lambda t=tab_name: self._switch_tab(t),
                font=("Roboto", 11, "bold")
            )
            btn.pack(fill="x", pady=6)
            self.tab_buttons[tab_name] = btn
        
        # İstatistikler paneli
        stats_panel = ctk.CTkFrame(left_panel, fg_color="#0d1b2a", corner_radius=8)
        stats_panel.pack(padx=10, pady=10, fill="x")
        
        ctk.CTkLabel(stats_panel, text="📈 İSTATİSTİKLER", font=("Roboto", 10, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.stats_translations = ctk.CTkLabel(stats_panel, text="Çeviri: 0", font=("Roboto", 9), text_color="#00ff88")
        self.stats_translations.pack(anchor="w", padx=15, pady=2)
        self.stats_characters = ctk.CTkLabel(stats_panel, text="Karakter: 0", font=("Roboto", 9), text_color="#00d2ff")
        self.stats_characters.pack(anchor="w", padx=15, pady=(2, 5))
        
        # Tema seçici
        theme_panel = ctk.CTkFrame(left_panel, fg_color="#1a1a2e", corner_radius=8)
        theme_panel.pack(padx=10, pady=10, fill="x")
        ctk.CTkLabel(theme_panel, text="🎨 TEMA", font=("Roboto", 10, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.theme_combo = ctk.CTkComboBox(
            theme_panel,
            values=self.available_themes,
            command=self._change_theme,
            font=("Roboto", 10)
        )
        self.theme_combo.set("neon")
        self.theme_combo.pack(fill="x", padx=10, pady=(0, 5))
        
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
                btn.configure(fg_color="#00d2ff", text_color="#000")
            else:
                btn.configure(fg_color="#1a1a2e", text_color="white")
    
    def _change_theme(self, theme: str) -> None:
        """Tema değiştir"""
        self.current_theme = theme
        self.settings["theme"] = theme
        self._log(f"[TEMA] {theme.upper()} temaya geçildi")
        messagebox.showinfo("Başarılı", f"Tema: {theme.upper()}")
    
    def _update_stats_display(self) -> None:
        """İstatistikleri güncelle"""
        try:
            total = self.history.stats.get("total_translations", 0)
            chars = self.history.stats.get("total_characters", 0)
            self.stats_translations.configure(text=f"Çeviri: {total}")
            self.stats_characters.configure(text=f"Karakter: {chars}")
        except Exception as e:
            logger.warning(f"Stats update hatası: {e}")
    
    def _create_main_tab(self) -> None:
        """Ana sekmeyi oluştur (geliştirilmiş)"""
        main_tab = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.tabs["Ana"] = main_tab
        
        # Başlık
        title_frame = ctk.CTkFrame(main_tab, fg_color="#1a1a2e", corner_radius=10)
        title_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(
            title_frame,
            text="🚀 AKILLI ÇEVİRİ MOTORU",
            font=("Roboto", 22, "bold"),
            text_color="#00d2ff"
        ).pack(pady=15)
        
        # Pencere seçici (geliştirilmiş)
        window_frame = ctk.CTkFrame(main_tab, fg_color="#0d1b2a", corner_radius=8)
        window_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(window_frame, text="🪟 Hedef Pencere:", font=("Roboto", 12, "bold"), text_color="#00ff88").pack(anchor="w", padx=15, pady=(10, 0))
        windows = self._get_windows()
        self.window_combo = ctk.CTkComboBox(
            window_frame, width=400, height=40,
            values=windows if windows else ["Pencere bulunamadı"],
            font=("Roboto", 11)
        )
        self.window_combo.pack(fill="x", padx=15, pady=(0, 10))
        
        # Bölge seçme butonu (geliştirilmiş)
        self.btn_region = ctk.CTkButton(
            main_tab, text="🎯 ALTYAZI ALANINI BELİRLE", height=50,
            fg_color="#00d2ff", text_color="#000",
            command=self.select_region, font=("Roboto", 13, "bold"),
            border_width=3, border_color="#ff006e"
        )
        self.btn_region.pack(fill="x", pady=12)
        
        # Başlat/Durdur butonu (büyük ve dikkat çekici)
        self.btn_start = ctk.CTkButton(
            main_tab, text="▶ BAŞLAT", height=90,
            fg_color="#ff006e", text_color="#fff",
            command=self.toggle_translation, font=("Roboto", 20, "bold"),
            border_width=4, border_color="#ffbe0b"
        )
        self.btn_start.pack(fill="x", pady=15)
        
        # Terminal (geliştirilmiş tema)
        terminal_frame = ctk.CTkFrame(main_tab, fg_color="#0a0a0a", corner_radius=8)
        terminal_frame.pack(fill="both", expand=True, pady=10)
        
        ctk.CTkLabel(terminal_frame, text="📡 Aktivite Logu:", font=("Roboto", 11, "bold"), text_color="#ffbe0b").pack(anchor="w", padx=10, pady=(10, 5))
        self.terminal = ctk.CTkTextbox(terminal_frame, fg_color="#08080a", text_color="#00ff88", font=("Consolas", 10))
        self.terminal.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.terminal.insert("0.0", ">>> NEXUS PRIME v18.0 Başlatıldı\n>>> Tema: NEON\n>>> Hazır...")
        self.terminal.configure(state="disabled")
    
    def _create_settings_tab(self) -> None:
        """Ayarlar sekmesini oluştur (geliştirilmiş)"""
        settings_tab = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.tabs["Ayarlar"] = settings_tab
        
        # Başlık
        ctk.CTkLabel(settings_tab, text="⚙️ AYARLAR", font=("Roboto", 22, "bold"), text_color="#ff006e").pack(pady=20)
        
        # Scroll frame
        scroll_frame = ctk.CTkScrollableFrame(settings_tab, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)
        
        # Dil Ayarları (geliştirilmiş)
        lang_frame = ctk.CTkFrame(scroll_frame, fg_color="#0d1b2a", corner_radius=8)
        lang_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(lang_frame, text="🌐 DİL AYARLARI", font=("Roboto", 13, "bold"), text_color="#00d2ff").pack(anchor="w", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(lang_frame, text="Kaynak Dil:", font=("Roboto", 11)).pack(anchor="w", padx=25)
        self.source_lang = ctk.CTkComboBox(lang_frame, values=["en", "tr", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"], font=("Roboto", 10))
        self.source_lang.set("en")
        self.source_lang.pack(fill="x", padx=25, pady=5)
        
        ctk.CTkLabel(lang_frame, text="Hedef Dil:", font=("Roboto", 11)).pack(anchor="w", padx=25, pady=(10, 0))
        self.target_lang = ctk.CTkComboBox(lang_frame, values=["tr", "en", "fr", "de", "es", "it", "pt", "ru", "ja", "ko", "zh"], font=("Roboto", 10))
        self.target_lang.set("tr")
        self.target_lang.pack(fill="x", padx=25, pady=(0, 10))
        
        # OCR Ayarları (geliştirilmiş)
        ocr_frame = ctk.CTkFrame(scroll_frame, fg_color="#0d1b2a", corner_radius=8)
        ocr_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(ocr_frame, text="🔍 OCR AYARLARI", font=("Roboto", 13, "bold"), text_color="#00ff88").pack(anchor="w", padx=15, pady=(10, 5))
        
        # Kontrast slider (görsel göstergeli)
        contrast_label = ctk.CTkLabel(ocr_frame, text=f"Kontras: {self.config.contrast_level:.1f}", font=("Roboto", 10))
        contrast_label.pack(anchor="w", padx=25)
        self.contrast_slider = ctk.CTkSlider(ocr_frame, from_=1.0, to=5.0, number_of_steps=40, command=lambda v: contrast_label.configure(text=f"Kontras: {float(v):.1f}"))
        self.contrast_slider.set(self.config.contrast_level)
        self.contrast_slider.pack(fill="x", padx=25, pady=5)
        
        # Tarama aralığı slider
        interval_label = ctk.CTkLabel(ocr_frame, text=f"Tarama Aralığı: {self.config.ocr_interval:.2f}s", font=("Roboto", 10))
        interval_label.pack(anchor="w", padx=25, pady=(10, 0))
        self.interval_slider = ctk.CTkSlider(ocr_frame, from_=0.1, to=1.0, number_of_steps=90, command=lambda v: interval_label.configure(text=f"Tarama Aralığı: {float(v):.2f}s"))
        self.interval_slider.set(self.config.ocr_interval)
        self.interval_slider.pack(fill="x", padx=25, pady=(0, 10))
        
        # Özellikler (geliştirilmiş)
        features_frame = ctk.CTkFrame(scroll_frame, fg_color="#0d1b2a", corner_radius=8)
        features_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(features_frame, text="⚡ ÖZELLİKLER", font=("Roboto", 13, "bold"), text_color="#ffbe0b").pack(anchor="w", padx=15, pady=(10, 5))
        
        self.auto_copy_check = ctk.CTkCheckBox(features_frame, text="📋 Otomatik Kopyala", font=("Roboto", 11))
        self.auto_copy_check.pack(anchor="w", padx=25, pady=5)
        
        self.sound_check = ctk.CTkCheckBox(features_frame, text="🔊 Ses Bildirimi", font=("Roboto", 11))
        self.sound_check.pack(anchor="w", padx=25, pady=(5, 10))
        
        # Kaydet butonu (geliştirilmiş)
        ctk.CTkButton(
            scroll_frame, text="💾 KAYDET",
            height=50,
            fg_color="#00d2ff",
            text_color="#000",
            font=("Roboto", 12, "bold"),
            command=self._save_settings
        ).pack(fill="x", padx=10, pady=20)
    
    def _create_history_tab(self) -> None:
        """Geçmiş sekmesini oluştur (geliştirilmiş istatistikler)"""
        history_tab = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.tabs["Geçmiş"] = history_tab
        
        # Başlık
        ctk.CTkLabel(history_tab, text="📜 ÇEVİRİ GEÇMİŞİ", font=("Roboto", 22, "bold"), text_color="#00d2ff").pack(pady=20)
        
        # İstatistikler Dashboard (geliştirilmiş)
        stats_frame = ctk.CTkFrame(history_tab, fg_color="#0d1b2a", corner_radius=10, border_width=2, border_color="#ff006e")
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        # İstatistikler başlığı
        ctk.CTkLabel(stats_frame, text="📊 İSTATİSTİK ÖZETI", font=("Roboto", 13, "bold"), text_color="#ffbe0b").pack(anchor="w", padx=15, pady=(10, 5))
        
        # 3 kolon istatistikler
        col_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        col_frame.pack(fill="x", padx=15, pady=10)
        
        # Toplam çeviriler
        col1 = ctk.CTkFrame(col_frame, fg_color="#1a1a2e", corner_radius=8)
        col1.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(col1, text="📝 Çeviri", font=("Roboto", 10), text_color="#00ff88").pack(padx=10, pady=5)
        self.stats_total = ctk.CTkLabel(col1, text="0", font=("Roboto", 20, "bold"), text_color="#00ff88")
        self.stats_total.pack(padx=10, pady=(0, 5))
        
        # Toplam karakterler
        col2 = ctk.CTkFrame(col_frame, fg_color="#1a1a2e", corner_radius=8)
        col2.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(col2, text="📄 Karakter", font=("Roboto", 10), text_color="#00d2ff").pack(padx=10, pady=5)
        self.stats_chars = ctk.CTkLabel(col2, text="0", font=("Roboto", 20, "bold"), text_color="#00d2ff")
        self.stats_chars.pack(padx=10, pady=(0, 5))
        
        # Ortalama
        col3 = ctk.CTkFrame(col_frame, fg_color="#1a1a2e", corner_radius=8)
        col3.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(col3, text="📈 Ortalama", font=("Roboto", 10), text_color="#ffbe0b").pack(padx=10, pady=5)
        self.stats_avg = ctk.CTkLabel(col3, text="0", font=("Roboto", 20, "bold"), text_color="#ffbe0b")
        self.stats_avg.pack(padx=10, pady=(0, 5))
        
        # Geçmiş listesi
        ctk.CTkLabel(history_tab, text="🕐 Son Çeviriler:", font=("Roboto", 12, "bold"), text_color="#00ff88").pack(anchor="w", padx=15, pady=(15, 5))
        
        history_scroll = ctk.CTkScrollableFrame(history_tab, fg_color="#0a0a0a", corner_radius=10)
        history_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        recent = self.history.get_recent(20)
        if recent:
            for item in reversed(recent):
                entry_frame = ctk.CTkFrame(history_scroll, fg_color="#1a1a2e", corner_radius=8, border_width=1, border_color="#00d2ff")
                entry_frame.pack(fill="x", padx=5, pady=5)
                
                # Zaman
                time_label = ctk.CTkLabel(entry_frame, text=f"⏰ {item['timestamp'][-8:-3]}", font=("Roboto", 9), text_color="#ffbe0b")
                time_label.pack(anchor="e", padx=10, pady=3)
                
                # Özgün metin
                ctk.CTkLabel(entry_frame, text=f"📌 {item['original'][:60]}{'...' if len(item['original']) > 60 else ''}", font=("Roboto", 10), text_color="#00ff88").pack(anchor="w", padx=15, pady=2)
                
                # Çeviri
                ctk.CTkLabel(entry_frame, text=f"✓ {item['translated'][:60]}{'...' if len(item['translated']) > 60 else ''}", font=("Roboto", 10), text_color="#00d2ff").pack(anchor="w", padx=15, pady=(0, 5))
        else:
            ctk.CTkLabel(history_scroll, text="📭 Geçmiş boş", font=("Roboto", 12), text_color="#ffbe0b").pack(pady=30)
        
        # Temizle butonu (geliştirilmiş)
        ctk.CTkButton(
            history_tab,
            text="🗑️ GEÇMİŞİ TEMİZLE",
            height=45,
            fg_color="#ff4b4b",
            text_color="#fff",
            font=("Roboto", 12, "bold"),
            command=self._clear_history
        ).pack(fill="x", padx=10, pady=10)
    
    def _save_settings(self) -> None:
        """Ayarları kaydet ve istatistikleri güncelle"""
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
        
        self._log("[⚙️] Ayarlar kaydedildi")
        self._update_stats_display()
        messagebox.showinfo("✓ Başarılı", "Ayarlar kaydedildi!")
    
    def _clear_history(self) -> None:
        """Geçmişi temizle"""
        if messagebox.askyesno("Onayla", "Geçmiş silinecek, emin misin?"):
            self.history.history = []
            self.history.stats = {"total_translations": 0, "total_characters": 0}
            self.history.save()
            self._log("[🗑️] Geçmiş temizlendi")
            self._update_stats_display()
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
        
        try:
            self.terminal.configure(state="normal")
            self.terminal.insert("end", f"\n{message}")
            self.terminal.see("end")
            self.terminal.configure(state="disabled")
        except Exception as e:
            logger.warning(f"Log hatası: {e}")
    
    def select_region(self) -> None:
        """Altyazı bölgesini seç (geliştirilmiş)"""
        self.withdraw()
        time.sleep(0.5)
        
        selection_window = tk.Toplevel()
        selection_window.attributes("-alpha", 0.3, "-fullscreen", True, "-topmost", True)
        selection_window.config(cursor="crosshair")
        
        canvas = tk.Canvas(selection_window, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        # Bilgi etiketi
        info_label = tk.Label(
            selection_window,
            text="🎯 Altyazı bölgesini belirle | Sürükle ve bırak",
            font=("Arial", 14, "bold"),
            fg="#00d2ff",
            bg="#0a0a0a"
        )
        info_label.pack(side="top", pady=20)
        
        def on_press(event):
            self.drag_start_x = event.x
            self.drag_start_y = event.y
        
        def on_drag(event):
            canvas.delete("selection_box")
            canvas.create_rectangle(
                self.drag_start_x, self.drag_start_y,
                event.x, event.y,
                outline="#00d2ff",
                width=4,
                tags="selection_box"
            )
            # Çerçeve rengi pulsing
            colors = ["#00d2ff", "#ff006e", "#ffbe0b"]
            canvas.create_rectangle(
                self.drag_start_x, self.drag_start_y,
                event.x, event.y,
                outline=colors[random.randint(0, 2)],
                width=2,
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
            self._log(f"[🎯] Bölge kilitlendi: {self.selected_region}")
        
        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
    
    def toggle_translation(self) -> None:
        """Çeviri motorunu aç/kapat (geliştirilmiş)"""
        try:
            if not self.selected_region:
                messagebox.showwarning(
                    "⚠️ Hata",
                    "Lütfen önce altyazı bölgesini seçiniz!"
                )
                return
            
            if not self.running:
                self.running = True
                try:
                    self.overlay = SubtitleOverlay(self.config, self.current_theme)
                    logger.info("Overlay penceresi açıldı")
                except Exception as e:
                    logger.error(f"Overlay açma hatası: {e}", exc_info=True)
                    self.running = False
                    messagebox.showerror("❌ Hata", f"Overlay açılamadı: {e}")
                    return
                
                self.btn_start.configure(
                    text="⏹ DURDUR",
                    fg_color="#ff4b4b",
                    text_color="#fff",
                    border_color="#ff006e"
                )
                self.status_label.configure(text="🔴 ÇALIŞIYOR", text_color="#ff006e")
                self._log("[▶️] Çeviri motoru başlatıldı")
                threading.Thread(target=self._process_loop, daemon=True).start()
            else:
                self.running = False
                if self.overlay:
                    try:
                        self.overlay.destroy()
                    except:
                        pass
                self.btn_start.configure(
                    text="▶ BAŞLAT",
                    fg_color="#ff006e",
                    text_color="#fff",
                    border_color="#ffbe0b"
                )
                self.status_label.configure(text="🟢 İDLE", text_color="#00ff88")
                self._log("[⏹️] Çeviri motoru durduruldu")
                self._update_stats_display()
        except Exception as e:
            logger.error(f"Toggle translation hatası: {e}", exc_info=True)
    
    def _process_loop(self) -> None:
        """Ana işleme döngüsü (geliştirilmiş)"""
        accumulated_text = ""
        last_update_time = time.time()
        error_count = 0
        
        try:
            logger.info("İşleme döngüsü başladı")
            
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
                                if self.overlay and self.running:
                                    self.overlay.update_text(translated)
                                self._log(f"✓ {translated}")
                                self.history.add(accumulated_text, translated, f"{self.settings['source_language']}->{self.settings['target_language']}")
                                self._update_stats_display()
                                
                                # Otomatik kopyala
                                if self.settings["auto_copy"]:
                                    try:
                                        pyautogui.write(translated, interval=0.01)
                                    except Exception as e:
                                        logger.warning(f"Otomatik kopyala hatası: {e}")
                        except Exception as e:
                            logger.error(f"Çeviri hatası: {e}", exc_info=True)
                            error_count += 1
                        
                        accumulated_text = ""
                    
                    time.sleep(self.settings["ocr_interval"])
                    error_count = 0  # Başarılı olursa counter sıfırla
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"İşleme hatası ({error_count}): {e}", exc_info=True)
                    
                    if error_count > 10:
                        logger.error("Çok fazla hata, işleme durduruldu")
                        self.running = False
                        break
                    
                    time.sleep(1)
        
        except Exception as e:
            logger.error(f"Process loop kritik hatası: {e}", exc_info=True)
        finally:
            logger.info("İşleme döngüsü sona erdi")


def main():
    """Uygulamayı çalıştır"""
    try:
        logger.info("=" * 50)
        logger.info("NEXUS PRIME v17.0 Başlatılıyor...")
        logger.info("=" * 50)
        app = NexusSentenceMode()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Uygulama kritik hatası: {e}", exc_info=True)
        print(f"\n❌ KRİTİK HATA: {e}")
        print("Detaylar için nexus.log dosyasını kontrol edin")
        sys.exit(1)
    finally:
        logger.info("=" * 50)
        logger.info("NEXUS PRIME Kapatıldı")
        logger.info("=" * 50)


if __name__ == "__main__":
    main()
