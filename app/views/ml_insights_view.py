"""
Paint Formulation AI - Passive ML Panel
========================================
Insight-based ML Dashboard replacing manual control panel.

Features:
- AI Engine status indicator (passive, no manual buttons)
- Project Coach: Live suggestions for current project
- Global Trends: Feature importance chart and learned rules
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class PassiveMLPanel(ttk.Frame):
    """
    Passive Assistant ML Panel.
    
    Displays ML insights and suggestions without manual training controls.
    Automatically updates when background learning completes.
    """
    
    def __init__(
        self,
        parent,
        db_manager=None,
        on_get_project_suggestions: Callable = None,
        on_get_global_trends: Callable = None
    ):
        super().__init__(parent)
        
        self.db_manager = db_manager
        self.on_get_project_suggestions = on_get_project_suggestions
        self.on_get_global_trends = on_get_global_trends
        
        self.current_project_id = None
        self.current_project_name = None
        self._is_learning = False
        self._feature_importance = {}
        self._learned_rules = []
        
        self._create_ui()
        
        # Initial refresh
        self.after(1000, self._refresh_insights)
    
    def _create_ui(self):
        """Create the passive assistant UI"""
        # === HEADER with Status Indicator ===
        header = ttk.Frame(self)
        header.pack(fill=tk.X, pady=(0, 15))
        
        # Title
        ttk.Label(
            header,
            text="🧠 Makine Öğrenmesi Merkezi",
            font=('Segoe UI', 16, 'bold')
        ).pack(side=tk.LEFT)
        
        # AI Status Indicator (Right side)
        self.status_frame = ttk.Frame(header)
        self.status_frame.pack(side=tk.RIGHT)
        
        self.status_icon = ttk.Label(
            self.status_frame,
            text="🟢",
            font=('Segoe UI', 14)
        )
        self.status_icon.pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="AI Engine: Hazır",
            font=('Segoe UI', 10)
        )
        self.status_label.pack(side=tk.LEFT)
        
        # === Main Content (Two Columns) ===
        content = ttk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        
        # === LEFT COLUMN: Project Coach ===
        left_frame = ttk.LabelFrame(content, text="🎯 Proje Koçu", padding=15)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Project selector (minimal)
        proj_row = ttk.Frame(left_frame)
        proj_row.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(proj_row, text="Aktif Proje:", font=('Segoe UI', 9)).pack(side=tk.LEFT)
        self.project_combo = ttk.Combobox(proj_row, state='readonly', width=25)
        self.project_combo.pack(side=tk.LEFT, padx=10)
        self.project_combo.bind('<<ComboboxSelected>>', self._on_project_changed)
        
        # Suggestions container (scrollable)
        suggestions_container = ttk.Frame(left_frame)
        suggestions_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for scrolling
        self.suggestions_canvas = tk.Canvas(
            suggestions_container,
            bg='#1E1E1E',
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(
            suggestions_container,
            orient="vertical",
            command=self.suggestions_canvas.yview
        )
        self.suggestions_frame = ttk.Frame(self.suggestions_canvas)
        
        self.suggestions_frame.bind(
            "<Configure>",
            lambda e: self.suggestions_canvas.configure(scrollregion=self.suggestions_canvas.bbox("all"))
        )
        
        self.suggestions_canvas.create_window((0, 0), window=self.suggestions_frame, anchor="nw")
        self.suggestions_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.suggestions_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Mouse wheel scroll
        self.suggestions_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Initial empty state
        self._show_suggestions_empty_state()
        
        # === RIGHT COLUMN: Global Trends ===
        right_frame = ttk.LabelFrame(content, text="📊 Global Trendler", padding=15)
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        # Feature Importance Chart
        chart_header = ttk.Frame(right_frame)
        chart_header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            chart_header,
            text="Özellik Önemi",
            font=('Segoe UI', 11, 'bold')
        ).pack(side=tk.LEFT)
        
        # Canvas for bar chart
        self.chart_canvas = tk.Canvas(
            right_frame,
            height=200,
            bg='#2D2D2D',
            highlightthickness=1,
            highlightbackground='#3D3D3D'
        )
        self.chart_canvas.pack(fill=tk.X, pady=(0, 15))
        
        # Learned Rules Section
        rules_header = ttk.Frame(right_frame)
        rules_header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(
            rules_header,
            text="📚 Öğrenilen Kurallar",
            font=('Segoe UI', 11, 'bold')
        ).pack(side=tk.LEFT)
        
        # Rules text area
        self.rules_text = tk.Text(
            right_frame,
            wrap=tk.WORD,
            state='disabled',
            bg='#1E1E1E',
            fg='#A0A0A0',
            font=('Consolas', 10),
            height=10,
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.rules_text.pack(fill=tk.BOTH, expand=True)
        
        # Initial empty state
        self._draw_empty_chart()
        self._show_rules_empty_state()
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scroll"""
        self.suggestions_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _on_project_changed(self, event=None):
        """Handle project selection change"""
        selection = self.project_combo.get()
        if hasattr(self, '_project_list'):
            for p in self._project_list:
                if p.get('name') == selection:
                    self.current_project_id = p.get('id')
                    self.current_project_name = selection
                    break
        
        # Refresh suggestions for new project
        self._refresh_suggestions()
    
    # === Public Methods ===
    
    def load_projects(self, projects: list):
        """Load projects into dropdown"""
        self._project_list = projects
        project_names = [p.get('name', '') for p in projects if p.get('name')]
        self.project_combo['values'] = project_names
        if project_names:
            self.project_combo.current(0)
            self._on_project_changed()
    
    def set_learning_status(self, is_learning: bool):
        """Update the AI status indicator"""
        self._is_learning = is_learning
        
        if is_learning:
            self.status_icon.config(text="🔄")
            self.status_label.config(text="AI Engine: Öğreniyor...")
            self._animate_status()
        else:
            self.status_icon.config(text="🟢")
            self.status_label.config(text="AI Engine: Güncel")
    
    def _animate_status(self):
        """Animate status icon while learning"""
        if self._is_learning:
            current = self.status_icon.cget('text')
            icons = ['🔄', '⏳', '🔃', '⌛']
            idx = icons.index(current) if current in icons else 0
            self.status_icon.config(text=icons[(idx + 1) % len(icons)])
            self.after(500, self._animate_status)
    
    def update_insights(self, result):
        """Update panel with new learning results"""
        self.set_learning_status(False)
        
        # Update feature importance
        if result.global_metrics and result.global_metrics.get('feature_importance'):
            self._feature_importance = result.global_metrics['feature_importance']
            self._draw_feature_importance_chart()
        
        # Update suggestions
        if result.suggestions:
            self._display_suggestions(result.suggestions)
        
        # Generate learned rules from feature importance
        self._generate_learned_rules()
    
    def _refresh_insights(self):
        """Refresh all insights"""
        self._refresh_suggestions()
        self._refresh_global_trends()
    
    def _refresh_suggestions(self):
        """Refresh project-specific suggestions"""
        if self.on_get_project_suggestions and self.current_project_id:
            try:
                suggestions = self.on_get_project_suggestions(self.current_project_id)
                if suggestions:
                    self._display_suggestions(suggestions)
            except Exception as e:
                logger.warning(f"Failed to get suggestions: {e}")
    
    def _refresh_global_trends(self):
        """Refresh global trends"""
        if self.on_get_global_trends:
            try:
                trends = self.on_get_global_trends()
                if trends:
                    self._feature_importance = trends.get('feature_importance', {})
                    self._learned_rules = trends.get('rules', [])
                    self._draw_feature_importance_chart()
                    self._display_learned_rules()
            except Exception as e:
                logger.warning(f"Failed to get trends: {e}")
    
    # === Suggestion Cards ===
    
    def _show_suggestions_empty_state(self):
        """Show empty state for suggestions"""
        for widget in self.suggestions_frame.winfo_children():
            widget.destroy()
        
        empty_card = ttk.Frame(self.suggestions_frame)
        empty_card.pack(fill=tk.X, pady=20, padx=10)
        
        ttk.Label(
            empty_card,
            text="💡",
            font=('Segoe UI', 24)
        ).pack()
        
        ttk.Label(
            empty_card,
            text="Proje verisi toplandıkça\nöneriler burada görünecek",
            font=('Segoe UI', 10),
            foreground='gray',
            justify=tk.CENTER
        ).pack(pady=10)
    
    def _display_suggestions(self, suggestions: List[str]):
        """Display suggestion cards"""
        for widget in self.suggestions_frame.winfo_children():
            widget.destroy()
        
        if not suggestions:
            self._show_suggestions_empty_state()
            return
        
        for i, suggestion in enumerate(suggestions):
            self._create_suggestion_card(suggestion, i)
    
    def _create_suggestion_card(self, suggestion: str, index: int):
        """Create a single suggestion card"""
        # Determine card type based on content
        if 'uyarı' in suggestion.lower() or 'dikkat' in suggestion.lower():
            icon = "⚠️"
            bg_color = "#3D2F00"
            border_color = "#FFB300"
        elif 'artır' in suggestion.lower() or 'iyi' in suggestion.lower():
            icon = "📈"
            bg_color = "#1B3A2F"
            border_color = "#00B894"
        else:
            icon = "💡"
            bg_color = "#1E2A4A"
            border_color = "#6C5CE7"
        
        card = tk.Frame(
            self.suggestions_frame,
            bg=bg_color,
            highlightbackground=border_color,
            highlightthickness=2,
            padx=12,
            pady=10
        )
        card.pack(fill=tk.X, pady=5, padx=5)
        
        # Icon and text
        content = tk.Frame(card, bg=bg_color)
        content.pack(fill=tk.X)
        
        tk.Label(
            content,
            text=icon,
            font=('Segoe UI', 14),
            bg=bg_color,
            fg='white'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(
            content,
            text=suggestion,
            font=('Segoe UI', 10),
            bg=bg_color,
            fg='#E0E0E0',
            wraplength=280,
            justify=tk.LEFT
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # === Feature Importance Chart ===
    
    def _draw_empty_chart(self):
        """Draw placeholder chart"""
        self.chart_canvas.delete("all")
        
        width = self.chart_canvas.winfo_width() or 400
        height = 200
        
        # Empty state message
        self.chart_canvas.create_text(
            width // 2, height // 2,
            text="Model eğitildiğinde\nözellik önemi grafiği burada görünecek",
            fill='#666666',
            font=('Segoe UI', 10),
            justify=tk.CENTER
        )
    
    def _draw_feature_importance_chart(self):
        """Draw horizontal bar chart for feature importance"""
        self.chart_canvas.delete("all")
        
        if not self._feature_importance:
            self._draw_empty_chart()
            return
        
        # Get first target's importance (usually quality_score)
        first_target = next(iter(self._feature_importance.values()), {})
        if not first_target:
            self._draw_empty_chart()
            return
        
        # Sort by importance and take top 8
        sorted_features = sorted(
            first_target.items(),
            key=lambda x: x[1],
            reverse=True
        )[:8]
        
        if not sorted_features:
            self._draw_empty_chart()
            return
        
        # Chart dimensions
        self.chart_canvas.update_idletasks()
        width = max(self.chart_canvas.winfo_width(), 400)
        height = 200
        padding = 10
        label_width = 120
        bar_height = 18
        bar_spacing = 4
        max_bar_width = width - label_width - padding * 3
        
        # Find max importance for scaling
        max_importance = max(v for _, v in sorted_features)
        
        # Draw bars
        y = padding
        colors = ['#6C5CE7', '#00B894', '#0984E3', '#FDCB6E', '#E17055', '#00CEC9', '#B2BEC3', '#636E72']
        
        for i, (feature, importance) in enumerate(sorted_features):
            # Feature label
            label = self._format_feature_name(feature)
            self.chart_canvas.create_text(
                padding, y + bar_height // 2,
                text=label,
                fill='#A0A0A0',
                font=('Segoe UI', 9),
                anchor='w'
            )
            
            # Bar
            bar_width = (importance / max_importance) * max_bar_width if max_importance > 0 else 0
            color = colors[i % len(colors)]
            
            self.chart_canvas.create_rectangle(
                label_width, y,
                label_width + bar_width, y + bar_height,
                fill=color,
                outline=''
            )
            
            # Value label
            self.chart_canvas.create_text(
                label_width + bar_width + 5, y + bar_height // 2,
                text=f"{importance:.1%}",
                fill='#E0E0E0',
                font=('Segoe UI', 8),
                anchor='w'
            )
            
            y += bar_height + bar_spacing
    
    def _format_feature_name(self, name: str) -> str:
        """Format feature name for display"""
        translations = {
            'viscosity': 'Viskozite',
            'ph': 'pH',
            'density': 'Yoğunluk',
            'coating_thickness': 'Kaplama Kal.',
            'binder_ratio': 'Binder %',
            'pigment_ratio': 'Pigment %',
            'solvent_ratio': 'Solvent %',
            'additive_ratio': 'Katkı %',
            'total_solids': 'Katı Madde',
            'pvc': 'PVC'
        }
        return translations.get(name, name[:15])
    
    # === Learned Rules ===
    
    def _show_rules_empty_state(self):
        """Show empty state for rules"""
        self.rules_text.config(state='normal')
        self.rules_text.delete(1.0, tk.END)
        self.rules_text.insert(tk.END, 
            "Henüz öğrenilen kural yok.\n\n"
            "Daha fazla formülasyon ve test sonucu\n"
            "eklendikçe AI kuralları öğrenecek."
        )
        self.rules_text.config(state='disabled')
    
    def _generate_learned_rules(self):
        """Generate learned rules from feature importance"""
        if not self._feature_importance:
            self._show_rules_empty_state()
            return
        
        rules = []
        
        # Analyze each target
        target_names = {
            'quality_score': 'Kalite Skoru',
            'opacity': 'Örtücülük',
            'gloss': 'Parlaklık',
            'corrosion_resistance': 'Korozyon Direnci'
        }
        
        for target, importance_dict in self._feature_importance.items():
            if target not in target_names:
                continue
            
            target_tr = target_names[target]
            
            # Get top 2 features
            sorted_features = sorted(
                importance_dict.items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            
            for feature, importance in sorted_features:
                if importance > 0.1:
                    feature_tr = self._format_feature_name(feature)
                    rules.append(f"• {feature_tr} → {target_tr}'yi etkiler (%{importance*100:.0f})")
        
        self._learned_rules = rules
        self._display_learned_rules()
    
    def _display_learned_rules(self):
        """Display learned rules"""
        self.rules_text.config(state='normal')
        self.rules_text.delete(1.0, tk.END)
        
        if not self._learned_rules:
            self._show_rules_empty_state()
            return
        
        self.rules_text.insert(tk.END, "Tüm projelerden öğrenilen kalıplar:\n\n")
        
        for rule in self._learned_rules[:10]:
            self.rules_text.insert(tk.END, f"{rule}\n")
        
        self.rules_text.config(state='disabled')
