"""
Paint Formulation AI - Dashboard Panel
=======================================
İstatistikler ve grafikler içeren dashboard bileşeni
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DashboardPanel(ttk.LabelFrame):
    """
    Dashboard paneli - İstatistik kartları, grafikler ve içgörüler
    
    Matplotlib entegreli, tıklanabilir istatistik kartları içerir.
    """
    
    # Kart -> Sekme eşlemesi (0-indexed)
    # Tab order: 0=Dashboard, 1=hammaddeler, 2=Formülasyon, 3=Test Sonuçları, 4=ML Merkezi, 5=Karşılaştırma
    CARD_TAB_MAPPING = {
        "Toplam Formül": 2,      # Formülasyon sekmesi
        "Bu Ay Eklenen": 2,      # Formülasyon sekmesi
        "Test Bekleyen": 3,      # Test Sonuçları sekmesi
        "Başarılı": 4            # ML Merkezi sekmesi
    }
    
    def __init__(self, parent, on_navigate: Callable = None):
        """
        Args:
            parent: Üst widget
            on_navigate: Kart tıklandığında çağrılacak callback(card_label)
        """
        super().__init__(parent, text="📈 Dashboard", padding=10)
        
        self.on_navigate = on_navigate
        self.has_matplotlib = False
        
        self._create_stat_cards()
        self._create_content_area()
    
    def _create_stat_cards(self):
        """İstatistik kartlarını oluştur"""
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stat_cards = {}
        stats = [
            ("Toplam Formül", "0"),
            ("Bu Ay Eklenen", "0"),
            ("Test Bekleyen", "0"),
            ("Başarılı", "0")
        ]
        
        for i, (label, value) in enumerate(stats):
            card = self._create_stat_card(stats_frame, label, value)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            self.stat_cards[label] = card
            stats_frame.columnconfigure(i, weight=1)
    
    def _create_content_area(self):
        """Grafik ve içgörü alanını oluştur"""
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Track current layout mode
        self._current_layout = "horizontal"
        
        # Grafik alanı (Sol)
        self.chart_frame = ttk.LabelFrame(self.content_frame, text="📊 Grafikler", padding=5)
        self.chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self._setup_matplotlib()
        
        # İçgörü alanı (Sağ) - expand=True for responsive behavior
        self.insight_frame = ttk.LabelFrame(self.content_frame, text="💡 Akıllı İçgörüler", padding=5)
        self.insight_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, ipadx=10)
        self.insight_frame.configure(width=200)
        
        # Bind resize event for responsive layout
        self.content_frame.bind('<Configure>', self._on_content_resize)
        
        # İçgörü listesi (Scrollable)
        canvas = tk.Canvas(self.insight_frame, bg='#333333', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.insight_frame, orient="vertical", command=canvas.yview)
        self.insight_content = ttk.Frame(canvas, style='Card.TFrame')
        self.insight_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.insight_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # İlk mesaj
        ttk.Label(
            self.insight_content,
            text="Henüz içgörü yok.",
            foreground="#888"
        ).pack(pady=10, padx=10)
    
    def _on_content_resize(self, event):
        """Handle responsive layout on resize"""
        # Threshold for switching layouts
        threshold_width = 600
        
        # Get current width
        width = event.width
        
        # Determine needed layout
        new_layout = "vertical" if width < threshold_width else "horizontal"
        
        # Only repack if layout mode changed
        if new_layout != self._current_layout:
            self._current_layout = new_layout
            
            # Repack based on width
            self.chart_frame.pack_forget()
            self.insight_frame.pack_forget()
            
            if new_layout == "vertical":
                # Stack vertically for narrow screens
                self.chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 5))
                self.insight_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            else:
                # Side by side for wider screens
                self.chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
                self.insight_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, ipadx=10)

    
    def _setup_matplotlib(self):
        """Matplotlib grafiklerini oluştur"""
        try:
            import matplotlib
            matplotlib.use('TkAgg')
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            
            # Figure oluştur
            self.fig = Figure(figsize=(8, 3), dpi=80, facecolor='#2b2b2b')
            
            # İki grafik alanı
            self.ax1 = self.fig.add_subplot(121)
            self.ax2 = self.fig.add_subplot(122)
            
            # Stil ayarları
            for ax in [self.ax1, self.ax2]:
                ax.set_facecolor('#3c3c3c')
                ax.tick_params(colors='white')
                ax.xaxis.label.set_color('white')
                ax.yaxis.label.set_color('white')
                ax.title.set_color('white')
                for spine in ax.spines.values():
                    spine.set_color('#555')
            
            # Başlangıç grafikleri
            self._draw_initial_charts()
            
            # Canvas'ı ekle
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            self.has_matplotlib = True
            
        except ImportError:
            self.has_matplotlib = False
            placeholder = ttk.Label(
                self.chart_frame,
                text="📊 Grafik için matplotlib kurun:\npip install matplotlib",
                justify=tk.CENTER
            )
            placeholder.pack(expand=True)
    
    def _draw_initial_charts(self):
        """Başlangıç grafiklerini çiz"""
        # Sol grafik - Bar chart
        self.ax1.clear()
        months = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz']
        values = [0, 0, 0, 0, 0, 0]
        self.ax1.bar(months, values, color='#4CAF50', alpha=0.8)
        self.ax1.set_title('Aylık Formülasyon', fontsize=10, color='white')
        self.ax1.set_ylabel('Adet', fontsize=9, color='white')
        self.ax1.set_ylim(0, 10)
        
        # Sağ grafik - Pie chart
        self.ax2.clear()
        categories = ['Başarılı', 'Test Bekleyen', 'Taslak']
        sizes = [1, 1, 1]
        colors = ['#4CAF50', '#FFC107', '#9E9E9E']
        self.ax2.pie(
            sizes, labels=categories, colors=colors, autopct='%1.0f%%',
            textprops={'color': 'white', 'fontsize': 8}
        )
        self.ax2.set_title('Durum Dağılımı', fontsize=10, color='white')
        
        self.fig.tight_layout()
    
    def _create_stat_card(self, parent, label: str, value: str) -> ttk.Frame:
        """Tıklanabilir istatistik kartı oluştur"""
        card = ttk.Frame(parent, relief="raised", borderwidth=1, padding=10)
        
        value_label = ttk.Label(card, text=value, font=("Helvetica", 24, "bold"))
        value_label.pack()
        
        name_label = ttk.Label(card, text=label, font=("Helvetica", 10))
        name_label.pack()
        
        # Tıklama ve hover olayları
        def on_click(event):
            self._navigate_to(label)
        
        def on_enter(event):
            card.configure(relief="groove")
            for widget in card.winfo_children():
                widget.configure(cursor="hand2")
        
        def on_leave(event):
            card.configure(relief="raised")
            for widget in card.winfo_children():
                widget.configure(cursor="")
        
        # Event binding
        for widget in [card, value_label, name_label]:
            widget.bind("<Button-1>", on_click)
        
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        
        return card
    
    def _navigate_to(self, card_label: str):
        """Karta göre navigasyon yap"""
        if self.on_navigate:
            self.on_navigate(card_label)
    
    def update_stats(self, stats: Dict, monthly_data: List = None, insights: List = None):
        """
        İstatistikleri ve grafikleri güncelle
        
        Args:
            stats: İstatistik sözlüğü (label -> value)
            monthly_data: Aylık veri listesi [{'month': 'YYYY-MM', 'count': N}, ...]
            insights: İçgörü listesi [{'type': 'info', 'title': '...', 'message': '...'}, ...]
        """
        # Kartları güncelle
        for label, card in self.stat_cards.items():
            if label in stats:
                for widget in card.winfo_children():
                    if isinstance(widget, ttk.Label):
                        font = widget.cget('font')
                        if 'bold' in str(font):
                            widget.config(text=str(stats[label]))
                            break
        
        # Grafikleri güncelle
        if self.has_matplotlib:
            self._update_charts(stats, monthly_data)
        
        # İçgörüleri güncelle
        if insights is not None:
            self._update_insights(insights)
    
    def _update_insights(self, insights: List):
        """İçgörü panelini güncelle"""
        # Mevcut içgörüleri temizle
        for widget in self.insight_content.winfo_children():
            widget.destroy()
        
        if not insights:
            ttk.Label(
                self.insight_content,
                text="Şu an için yeni bir içgörü yok.",
                foreground="#888"
            ).pack(pady=10, padx=10)
            return
        
        # İçgörüleri kart olarak ekle
        for insight in insights:
            frame = ttk.Frame(
                self.insight_content,
                style='Card.TFrame',
                relief="groove",
                borderwidth=1,
                padding=5
            )
            frame.pack(fill=tk.X, padx=5, pady=5)
            
            # İkon ve Başlık
            icon_map = {
                'warning': '⚠️',
                'success': '✅',
                'tip': '💡',
                'info': 'ℹ️'
            }
            icon = icon_map.get(insight.get('type', 'info'), 'ℹ️')
            
            ttk.Label(
                frame,
                text=f"{icon} {insight.get('title', 'İçgörü')}",
                font=("Helvetica", 9, "bold")
            ).pack(anchor=tk.W)
            
            ttk.Label(
                frame,
                text=insight.get('message', ''),
                wraplength=200,
                justify=tk.LEFT
            ).pack(anchor=tk.W, pady=(2, 0))
    
    def _update_charts(self, stats: Dict, monthly_data: List = None):
        """Grafikleri gerçek verilerle güncelle"""
        try:
            # Sol grafik - Aylık formülasyon
            self.ax1.clear()
            
            if monthly_data and len(monthly_data) > 0:
                month_names = {
                    '01': 'Oca', '02': 'Şub', '03': 'Mar', '04': 'Nis',
                    '05': 'May', '06': 'Haz', '07': 'Tem', '08': 'Ağu',
                    '09': 'Eyl', '10': 'Eki', '11': 'Kas', '12': 'Ara'
                }
                months = []
                values = []
                for item in monthly_data:
                    month_num = item['month'].split('-')[1]
                    months.append(month_names.get(month_num, month_num))
                    values.append(item['count'])
            else:
                months = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz']
                total = int(stats.get('Toplam Formül', 0))
                values = [0] * 5 + [total]
            
            self.ax1.bar(months, values, color='#4CAF50', alpha=0.8)
            self.ax1.set_title('Aylık Formülasyon', fontsize=10, color='white')
            self.ax1.set_ylabel('Adet', fontsize=9, color='white')
            self.ax1.set_facecolor('#3c3c3c')
            self.ax1.tick_params(colors='white')
            
            # Sağ grafik - Durum dağılımı
            self.ax2.clear()
            tested = max(1, int(stats.get('Başarılı', 0) or 0))
            waiting = max(1, int(stats.get('Test Bekleyen', 0) or 0))
            total = int(stats.get('Toplam Formül', 0) or 0)
            draft = max(1, total - tested - waiting)
            
            sizes = [tested, waiting, draft]
            categories = ['Test Edildi', 'Bekleyen', 'Taslak']
            colors = ['#4CAF50', '#FFC107', '#9E9E9E']
            
            self.ax2.pie(
                sizes, labels=categories, colors=colors, autopct='%1.0f%%',
                textprops={'color': 'white', 'fontsize': 8}
            )
            self.ax2.set_title('Durum Dağılımı', fontsize=10, color='white')
            
            self.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            logger.warning(f"Grafik güncelleme hatası: {e}")
