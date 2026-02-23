"""
Paint Formulation AI - Test Sonuçları Paneli V2 (Decision Support)
===================================================================
Karar destek odaklı test sonuçları ekranı:
- Renkli durum kartları
- Gruplandırılmış açılır/kapanır test panelleri
- ML entegrasyonu ve yorumlar
- Geçmiş karşılaştırma
"""

import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, List, Optional, Callable, Any

from src.core.i18n import t, I18nMixin
from src.core.translation_keys import TK

# Theme colors
try:
    from app.theme import COLORS, FONTS, ICONS
except ImportError:
    # Fallback colors
    COLORS = {
        'bg_main': '#1E1E1E',
        'bg_panel': '#252526',
        'bg_secondary': '#2D2D2D',
        'bg_input': '#3C3C3C',
        'text_primary': '#CCCCCC',
        'text_secondary': '#858585',
        'accent_primary': '#007ACC',
        'accent_success': '#4EC9B0',
        'accent_danger': '#F14C4C',
        'accent_warning': '#CCA700',
        'border_default': '#3C3C3C',
    }
    FONTS = {'default': ('Segoe UI', 10), 'heading': ('Segoe UI', 12, 'bold')}
    ICONS = {}


# Status threshold configuration (domain knowledge)
TEST_THRESHOLDS = {
    # Mekanik Testler
    'hardness_konig': {'good': 100, 'medium': 60, 'unit': 'sn', 'higher_is_better': True},
    'hardness_pencil': {'good': 'H', 'medium': 'HB', 'unit': '', 'higher_is_better': True},
    'flexibility_erichsen': {'good': 8, 'medium': 5, 'unit': 'mm', 'higher_is_better': True},
    'impact_resistance': {'good': 50, 'medium': 30, 'unit': 'kg.cm', 'higher_is_better': True},
    'adhesion': {'good': 4, 'medium': 2, 'unit': '0-5', 'higher_is_better': True},
    
    # Optik Testler
    'gloss_60': {'good': 85, 'medium': 60, 'unit': 'GU', 'higher_is_better': True},
    'gloss_20': {'good': 70, 'medium': 40, 'unit': 'GU', 'higher_is_better': True},
    'opacity': {'good': 95, 'medium': 85, 'unit': '%', 'higher_is_better': True},
    'color_delta_e': {'good': 1, 'medium': 3, 'unit': 'ΔE', 'higher_is_better': False},
    
    # Kimyasal Testler
    'acid_resistance': {'good': 4, 'medium': 2, 'unit': '0-5', 'higher_is_better': True},
    'alkali_resistance': {'good': 4, 'medium': 2, 'unit': '0-5', 'higher_is_better': True},
    'solvent_resistance': {'good': 100, 'medium': 50, 'unit': 'DRC', 'higher_is_better': True},
    'chemical_resistance': {'good': 4, 'medium': 2, 'unit': '0-5', 'higher_is_better': True},
    
    # Dayanım Testleri
    'corrosion_resistance': {'good': 500, 'medium': 250, 'unit': 'saat', 'higher_is_better': True},
    'uv_resistance': {'good': 500, 'medium': 200, 'unit': 'saat', 'higher_is_better': True},
    'water_resistance': {'good': 500, 'medium': 200, 'unit': 'saat', 'higher_is_better': True},
    'humidity_resistance': {'good': 500, 'medium': 200, 'unit': 'saat', 'higher_is_better': True},
    
    # Uygulama Özellikleri
    'drying_time': {'good': 30, 'medium': 60, 'unit': 'dk', 'higher_is_better': False},
    'pot_life': {'good': 60, 'medium': 30, 'unit': 'dk', 'higher_is_better': True},
}

# Test categories - Dynamic Keys
TEST_CATEGORIES = {
    'mechanical': {
        'name_key': TK.TEST_MECH,
        'icon': '🔧',
        'tests': ['hardness_konig', 'hardness_pencil', 'flexibility_erichsen', 'impact_resistance', 'adhesion'],
        'labels': {
            'hardness_konig': TK.TEST_HARDNESS_KONIG,
            'hardness_pencil': TK.TEST_HARDNESS_PENCIL,
            'flexibility_erichsen': TK.TEST_FLEXIBILITY,
            'impact_resistance': TK.TEST_IMPACT,
            'adhesion': TK.TEST_ADHESION,
        }
    },
    'optical': {
        'name_key': TK.TEST_OPTICAL,
        'icon': '✨',
        'tests': ['gloss_60', 'gloss_20', 'opacity', 'color_delta_e'],
        'labels': {
            'gloss_60': TK.TEST_GLOSS60,
            'gloss_20': TK.TEST_GLOSS20,
            'opacity': TK.TEST_OPACITY,
            'color_delta_e': TK.TEST_DE,
        }
    },
    'chemical': {
        'name_key': TK.TEST_CHEMICAL,
        'icon': '🧪',
        'tests': ['acid_resistance', 'alkali_resistance', 'solvent_resistance', 'chemical_resistance'],
        'labels': {
            'acid_resistance': TK.TEST_ACID,
            'alkali_resistance': TK.TEST_ALKALI,
            'solvent_resistance': TK.TEST_SOLVENT,
            'chemical_resistance': TK.TEST_CHEMICAL_RES,
        }
    },
    'durability': {
        'name_key': TK.TEST_DURABILITY,
        'icon': '🛡️',
        'tests': ['corrosion_resistance', 'uv_resistance', 'water_resistance', 'humidity_resistance'],
        'labels': {
            'corrosion_resistance': TK.TEST_CORROSION,
            'uv_resistance': TK.TEST_UV,
            'water_resistance': TK.TEST_WATER,
            'humidity_resistance': TK.TEST_HUMIDITY,
        }
    },
}


class StatusCard(tk.Frame, I18nMixin):
    """
    Renkli durum kartı - özet skor gösterimi
    """
    
    def __init__(self, parent, category_key: str, title_key: str, icon: str = '', **kwargs):
        super().__init__(parent, **kwargs)
        
        self.category_key = category_key
        self.title_key = title_key
        self._score = 0
        self._status = 'neutral'
        
        self.configure(
            bg=COLORS['bg_secondary'],
            highlightbackground=COLORS['border_default'],
            highlightthickness=1,
            padx=10,
            pady=8
        )
        self.setup_i18n()
        self._create_widgets(icon)
        self._update_texts()

    def _create_widgets(self, icon):
        # Icon + Title
        title_frame = tk.Frame(self, bg=COLORS['bg_secondary'])
        title_frame.pack(fill=tk.X)
        
        self.icon_label = tk.Label(
            title_frame,
            text=icon,
            font=('Segoe UI Emoji', 16),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary']
        )
        self.icon_label.pack(side=tk.LEFT)
        
        self.title_label = tk.Label(
            title_frame,
            font=FONTS['heading'],
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary']
        )
        self.title_label.pack(side=tk.LEFT, padx=5)
        
        # Score
        self.score_label = tk.Label(
            self,
            text='0',
            font=('Segoe UI', 24, 'bold'),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_secondary']
        )
        self.score_label.pack(pady=5)
        
        # Status
        self.status_label = tk.Label(
            self,
            font=('Segoe UI', 9),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_secondary']
        )
        self.status_label.pack()
        
        # Click to expand
        self.bind('<Button-1>', self._on_click)
        for child in self.winfo_children():
            child.bind('<Button-1>', self._on_click)
    
    def set_status(self, status: str, score: float):
        """Update card status: 'good', 'medium', 'bad', or 'neutral'"""
        self._status = status
        self._score = score
        
        status_config = {
            'good': {'text': t(TK.TEST_STATUS_GOOD), 'color': '#10B981', 'border': '#059669'},
            'medium': {'text': t(TK.TEST_STATUS_MEDIUM), 'color': '#F59E0B', 'border': '#D97706'},
            'bad': {'text': t(TK.TEST_STATUS_BAD), 'color': '#EF4444', 'border': '#DC2626'},
            'neutral': {'text': '—', 'color': COLORS['text_secondary'], 'border': COLORS['border_default']},
        }
        
        config = status_config.get(status, status_config['neutral'])
        
        self.status_label.configure(text=config['text'], fg=config['color'])
        self.score_label.configure(text=f'{int(score)}/100' if score > 0 else '—/100')
        self.configure(highlightbackground=config['border'])
    
    def _update_texts(self):
        """Update texts on language change"""
        self.title_label.config(text=t(self.title_key))
        self.set_status(self._status, self._score)
    
    def _on_click(self, event=None):
        """Emit click event for parent to handle"""
        self.event_generate('<<StatusCardClick>>')


class CollapsibleTestGroup(ttk.Frame, I18nMixin):
    """
    Açılır/kapanır test grubu paneli
    """
    
    def __init__(self, parent, category_key: str, title_key: str, icon: str,
                 tests: List[str], label_keys: Dict[str, str], on_value_change: Callable = None):
        super().__init__(parent)
        
        self.category_key = category_key
        self.title_key = title_key
        self.icon = icon
        self.tests = tests
        self.label_keys = label_keys
        self.on_value_change = on_value_change
        self.entries: Dict[str, ttk.Entry] = {}
        self.status_labels: Dict[str, tk.Label] = {}
        self.test_labels_widgets: Dict[str, tk.Label] = {}
        self._is_expanded = False
        
        self.setup_i18n()
        
        # Header (toggle button)
        self.header = tk.Frame(self, bg=COLORS['bg_secondary'], cursor='hand2')
        self.header.pack(fill=tk.X)
        
        self.toggle_icon = tk.Label(
            self.header,
            text='▶',
            font=('Segoe UI', 10),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary'],
            width=2
        )
        self.toggle_icon.pack(side=tk.LEFT, padx=5, pady=8)
        
        self.header_label = tk.Label(
            self.header,
            text=f'{self.icon} {t(self.title_key)}',
            font=FONTS.get('heading', ('Segoe UI', 12, 'bold')),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_primary']
        )
        self.header_label.pack(side=tk.LEFT, pady=8)
        
        # Status indicator on right
        self.header_status = tk.Label(
            self.header,
            text='',
            font=('Segoe UI', 9),
            bg=COLORS['bg_secondary'],
            fg=COLORS['text_secondary']
        )
        self.header_status.pack(side=tk.RIGHT, padx=10)
        
        # Content (hidden initially)
        self.content = tk.Frame(self, bg=COLORS['bg_panel'])
        
        # Bind toggle
        self.header.bind('<Button-1>', self._toggle)
        self.toggle_icon.bind('<Button-1>', self._toggle)
        self.header_label.bind('<Button-1>', self._toggle)
        
        # Build test inputs
        self._build_test_inputs()
    
    def _build_test_inputs(self):
        """Build test input fields"""
        for i, test_key in enumerate(self.tests):
            row = tk.Frame(self.content, bg=COLORS['bg_panel'])
            row.pack(fill=tk.X, padx=20, pady=3)
            
            # Label
            label_text = t(self.label_keys.get(test_key, test_key))
            threshold = TEST_THRESHOLDS.get(test_key, {})
            unit = threshold.get('unit', '')
            
            label = tk.Label(
                row,
                text=f'{label_text} ({unit}):' if unit else f'{label_text}:',
                font=FONTS.get('default', ('Segoe UI', 10)),
                bg=COLORS['bg_panel'],
                fg=COLORS['text_primary'],
                width=25,
                anchor='w'
            )
            label.pack(side=tk.LEFT)
            self.test_labels_widgets[test_key] = label
            
            # Entry
            entry = ttk.Entry(row, width=10)
            entry.pack(side=tk.LEFT, padx=5)
            entry.bind('<FocusOut>', lambda e, k=test_key: self._on_entry_change(k))
            entry.bind('<Return>', lambda e, k=test_key: self._on_entry_change(k))
            self.entries[test_key] = entry
            
            # Unit label
            if unit:
                unit_label = tk.Label(
                    row,
                    text=unit,
                    font=('Segoe UI', 9),
                    bg=COLORS['bg_panel'],
                    fg=COLORS['text_secondary'],
                    width=6
                )
                unit_label.pack(side=tk.LEFT)
            
            # Status badge
            status_badge = tk.Label(
                row,
                text='',
                font=('Segoe UI', 9, 'bold'),
                bg=COLORS['bg_panel'],
                fg=COLORS['text_muted'],
                width=8
            )
            status_badge.pack(side=tk.LEFT, padx=10)
            self.status_labels[test_key] = status_badge
            
            # Help tooltip
            help_btn = tk.Label(
                row,
                text='?',
                font=('Segoe UI', 9),
                bg=COLORS['bg_panel'],
                fg=COLORS['text_muted'],
                cursor='question_arrow'
            )
            help_btn.pack(side=tk.LEFT)
            help_btn.bind('<Enter>', lambda e, k=test_key: self._show_tooltip(e, k))
    
    def _update_texts(self):
        """Update texts on language change"""
        self.header_label.config(text=f'{self.icon} {t(self.title_key)}')
        for test_key, label in self.test_labels_widgets.items():
            threshold = TEST_THRESHOLDS.get(test_key, {})
            unit = threshold.get('unit', '')
            label_text = t(self.label_keys.get(test_key, test_key))
            label.config(text=f'{label_text} ({unit}):' if unit else f'{label_text}:')
            
            val = self.entries[test_key].get().strip()
            self._update_status_badge(test_key, val)
    
    def _toggle(self, event=None):
        """Toggle expand/collapse"""
        self._is_expanded = not self._is_expanded
        
        if self._is_expanded:
            self.content.pack(fill=tk.X, pady=(0, 10))
            self.toggle_icon.configure(text='▼')
        else:
            self.content.pack_forget()
            self.toggle_icon.configure(text='▶')
    
    def expand(self):
        """Force expand"""
        if not self._is_expanded:
            self._toggle()
    
    def collapse(self):
        """Force collapse"""
        if self._is_expanded:
            self._toggle()
    
    def _on_entry_change(self, test_key: str):
        """Handle value change"""
        value = self.entries[test_key].get().strip()
        self._update_status_badge(test_key, value)
        
        if self.on_value_change:
            self.on_value_change(self.category_key, test_key, value)
    
    def _update_status_badge(self, test_key: str, value: str):
        """Update status badge for a test"""
        threshold = TEST_THRESHOLDS.get(test_key)
        badge = self.status_labels.get(test_key)
        
        if not threshold or not badge:
            return
        
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            badge.configure(text='', fg=COLORS['text_muted'])
            return
        
        good = threshold.get('good', 0)
        medium = threshold.get('medium', 0)
        higher_is_better = threshold.get('higher_is_better', True)
        
        if higher_is_better:
            if num_value >= good:
                badge.configure(text=t(TK.TEST_STATUS_GOOD), fg='#10B981')
            elif num_value >= medium:
                badge.configure(text=t(TK.TEST_STATUS_MEDIUM), fg='#F59E0B')
            else:
                badge.configure(text=t(TK.TEST_STATUS_BAD), fg='#EF4444')
        else:
            if num_value <= good:
                badge.configure(text=t(TK.TEST_STATUS_GOOD), fg='#10B981')
            elif num_value <= medium:
                badge.configure(text=t(TK.TEST_STATUS_MEDIUM), fg='#F59E0B')
            else:
                badge.configure(text=t(TK.TEST_STATUS_BAD), fg='#EF4444')
    
    def _show_tooltip(self, event, test_key: str):
        """Show help tooltip"""
        threshold = TEST_THRESHOLDS.get(test_key, {})
        good = threshold.get('good', '?')
        medium = threshold.get('medium', '?')
        unit = threshold.get('unit', '')
        
        # Could implement proper tooltip, for now just show in status
        pass
    
    def get_values(self) -> Dict[str, Any]:
        """Get all values in this group"""
        values = {}
        for key, entry in self.entries.items():
            val = entry.get().strip()
            if val:
                try:
                    values[key] = float(val)
                except ValueError:
                    values[key] = val
        return values
    
    def set_values(self, values: Dict[str, Any]):
        """Set values from dict"""
        for key, entry in self.entries.items():
            entry.delete(0, tk.END)
            if key in values and values[key] is not None:
                entry.insert(0, str(values[key]))
                self._update_status_badge(key, str(values[key]))
    
    def clear(self):
        """Clear all values"""
        for key, entry in self.entries.items():
            entry.delete(0, tk.END)
            self.status_labels[key].configure(text='', fg=COLORS['text_muted'])
    
    def calculate_category_score(self) -> tuple:
        """Calculate overall category score and status"""
        values = self.get_values()
        if not values:
            return 'neutral', 0
        
        scores = []
        for key, val in values.items():
            threshold = TEST_THRESHOLDS.get(key)
            if not threshold:
                continue
            
            try:
                num_val = float(val)
            except (ValueError, TypeError):
                continue
            
            good = threshold.get('good', 0)
            medium = threshold.get('medium', 0)
            higher_is_better = threshold.get('higher_is_better', True)
            
            # Normalize to 0-100 score
            if higher_is_better:
                if num_val >= good:
                    score = 100
                elif num_val >= medium:
                    score = 60 + 40 * (num_val - medium) / (good - medium)
                elif medium > 0:
                    score = 60 * num_val / medium
                else:
                    score = 0
            else:
                if num_val <= good:
                    score = 100
                elif num_val <= medium:
                    score = 60 + 40 * (medium - num_val) / (medium - good)
                else:
                    score = max(0, 60 - (num_val - medium) * 2)
            
            scores.append(min(100, max(0, score)))
        
        if not scores:
            return 'neutral', 0
        
        avg_score = sum(scores) / len(scores)
        
        if avg_score >= 70:
            status = 'good'
        elif avg_score >= 50:
            status = 'medium'
        else:
            status = 'bad'
        
        return status, avg_score


class MLIntegrationPanel(tk.Frame, I18nMixin):
    """
    ML entegrasyon paneli - model durumu, yorumlar, karşılaştırma
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(bg=COLORS['bg_panel'])
        self.setup_i18n()
        
        # Model Status Section
        self.status_frame = tk.LabelFrame(
            self,
            font=FONTS.get('heading', ('Segoe UI', 11, 'bold')),
            bg=COLORS['bg_panel'],
            fg=COLORS['text_primary'],
            padx=10,
            pady=5
        )
        self.status_frame.pack(fill=tk.X, pady=5)
        
        # Include in ML checkbox
        self.include_in_ml_var = tk.BooleanVar(value=True)
        self.include_check = tk.Checkbutton(
            self.status_frame,
            variable=self.include_in_ml_var,
            bg=COLORS['bg_panel'],
            fg=COLORS['text_primary'],
            activebackground=COLORS['bg_panel'],
            selectcolor=COLORS['bg_input']
        )
        self.include_check.pack(anchor='w')
        
        # Confidence score
        conf_frame = tk.Frame(self.status_frame, bg=COLORS['bg_panel'])
        conf_frame.pack(fill=tk.X, pady=5)
        
        self.confidence_header = tk.Label(
            conf_frame,
            font=('Segoe UI', 9),
            bg=COLORS['bg_panel'],
            fg=COLORS['text_secondary']
        )
        self.confidence_header.pack(side=tk.LEFT)
        
        self.confidence_bar = ttk.Progressbar(
            conf_frame,
            length=100,
            mode='determinate',
            value=0
        )
        self.confidence_bar.pack(side=tk.LEFT, padx=5)
        
        self.confidence_label = tk.Label(
            conf_frame,
            text='—%',
            font=('Segoe UI', 9),
            bg=COLORS['bg_panel'],
            fg=COLORS['text_primary']
        )
        self.confidence_label.pack(side=tk.LEFT)
        
        # Last training info
        self.training_label = tk.Label(
            self.status_frame,
            font=('Segoe UI', 9),
            bg=COLORS['bg_panel'],
            fg=COLORS['text_secondary']
        )
        self.training_label.pack(anchor='w')
        
        # ML Comments Section
        self.comments_frame = tk.LabelFrame(
            self,
            font=FONTS.get('heading', ('Segoe UI', 11, 'bold')),
            bg=COLORS['bg_panel'],
            fg=COLORS['text_primary'],
            padx=10,
            pady=5
        )
        self.comments_frame.pack(fill=tk.X, pady=5)
        
        self.comments_text = tk.Text(
            self.comments_frame,
            height=5,
            bg=COLORS['bg_input'],
            fg=COLORS['text_primary'],
            font=('Segoe UI', 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            relief='flat'
        )
        self.comments_text.pack(fill=tk.X)
        
        # Comparison Section
        self.compare_frame = tk.LabelFrame(
            self,
            font=FONTS.get('heading', ('Segoe UI', 11, 'bold')),
            bg=COLORS['bg_panel'],
            fg=COLORS['text_primary'],
            padx=10,
            pady=5
        )
        self.compare_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Comparison selector
        self.compare_combo = ttk.Combobox(
            self.compare_frame,
            state='readonly',
            width=25
        )
        self.compare_combo.pack(fill=tk.X, pady=5)
        # updated in _update_texts
        
        # Comparison results treeview
        self.compare_tree = ttk.Treeview(
            self.compare_frame,
            columns=('param', 'current', 'previous', 'delta'),
            show='headings',
            height=5
        )
        # Headings updated in _update_texts
        
        self.compare_tree.column('param', width=100)
        self.compare_tree.column('current', width=60)
        self.compare_tree.column('previous', width=60)
        self.compare_tree.column('delta', width=60)
        
        self.compare_tree.pack(fill=tk.BOTH, expand=True)
        self._update_texts()
    
    def _update_texts(self):
        """Update texts on language change"""
        self.status_frame.config(text=t(TK.NAV_ML_CENTER))
        self.include_check.config(text=t(TK.TEST_MESSAGES_ML_INCLUDE))
        self.confidence_header.config(text=t(TK.TEST_MESSAGES_CONFIDENCE))
        self.comments_frame.config(text=t(TK.TEST_MESSAGES_COMMENTS))
        self.compare_frame.config(text=t(TK.TEST_MESSAGES_COMPARE))
        
        self.compare_combo.config(values=[
            t(TK.TEST_MESSAGES_COMPARE) + " (Last 3)", 
            t(TK.TEST_MESSAGES_COMPARE) + " (Prev)", 
            t(TK.TEST_MESSAGES_COMPARE) + " (Avg)"
        ])
        
        self.compare_tree.heading('param', text=t(TK.TEST_COMPARE_PARAM))
        self.compare_tree.heading('current', text=t(TK.TEST_COMPARE_NOW))
        self.compare_tree.heading('previous', text=t(TK.TEST_COMPARE_PREV))
        self.compare_tree.heading('delta', text=t(TK.TEST_COMPARE_DELTA))
        
        # Refresh training info if already set
        if hasattr(self, '_last_training_data'):
            self.set_training_info(*self._last_training_data)

    def set_confidence(self, score: float):
        """Set confidence score (0-100)"""
        self.confidence_bar['value'] = score
        self.confidence_label.configure(text=f'{int(score)}%')
    
    def set_training_info(self, last_trained: str, sample_count: int):
        """Set last training info"""
        self._last_training_data = (last_trained, sample_count)
        label_text = f"{t(TK.TEST_MESSAGES_LAST_TRAINING)} {last_trained} ({sample_count} {t(getattr(TK, 'common_all', 'Tümü')).lower()})"
        self.training_label.configure(text=label_text)
    
    def set_comments(self, comments: List[str]):
        """Set ML comments"""
        self.comments_text.configure(state=tk.NORMAL)
        self.comments_text.delete(1.0, tk.END)
        for comment in comments:
            self.comments_text.insert(tk.END, f'• {comment}\n')
        self.comments_text.configure(state=tk.DISABLED)
    
    def set_comparison_data(self, data: List[Dict]):
        """Set comparison data: [{'param': 'Sertlik', 'current': 120, 'previous': 115, 'delta': '+5%'}]"""
        for item in self.compare_tree.get_children():
            self.compare_tree.delete(item)
        
        for row in data:
            tags = ()
            delta = row.get('delta', '')
            if delta.startswith('+'):
                tags = ('positive',)
            elif delta.startswith('-'):
                tags = ('negative',)
            
            self.compare_tree.insert('', tk.END, values=(
                row.get('param', ''),
                row.get('current', ''),
                row.get('previous', ''),
                delta
            ), tags=tags)
        
        # Configure tags
        self.compare_tree.tag_configure('positive', foreground='#10B981')
        self.compare_tree.tag_configure('negative', foreground='#EF4444')


class TestResultsPanelV2(ttk.Frame, I18nMixin):
    """
    Test Sonuçları Paneli V2 - Karar Destek Odaklı
    """
    
    def __init__(self, parent, on_save: Callable = None, on_load_formulations: Callable = None,
                 on_load_trial: Callable = None, db_manager=None):
        super().__init__(parent)
        self.on_save = on_save
        self.on_load_formulations = on_load_formulations
        self.on_load_trial = on_load_trial
        self.db = db_manager
        
        self.current_formulation_code = None
        self.current_trial_id = None
        self.ml_panel = None
        
        self.setup_i18n()
        self.test_groups: Dict[str, CollapsibleTestGroup] = {}
        self.status_cards: Dict[str, StatusCard] = {}
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the main UI"""
        
        # Configure grid weights
        self.columnconfigure(0, weight=6)  # Left panel (60%)
        self.columnconfigure(1, weight=4)  # Right panel (40%)
        self.rowconfigure(2, weight=1)
        
        # =====================================================================
        # TOP BAR - Formulation Selector
        # =====================================================================
        top_bar = tk.Frame(self, bg=COLORS['bg_panel'])
        top_bar.grid(row=0, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
        
        self.main_title = tk.Label(
            top_bar,
            font=('Segoe UI', 14, 'bold'),
            bg=COLORS['bg_panel'],
            fg=COLORS['text_primary']
        )
        self.main_title.pack(side=tk.LEFT)
        
        # Formulation selector (right side)
        selector_frame = tk.Frame(top_bar, bg=COLORS['bg_panel'])
        selector_frame.pack(side=tk.RIGHT)
        
        self.label_formulation = tk.Label(
            selector_frame,
            bg=COLORS['bg_panel'],
            fg=COLORS['text_secondary']
        )
        self.label_formulation.pack(side=tk.LEFT, padx=5)
        
        self.formulation_combo = ttk.Combobox(selector_frame, width=25, state='readonly')
        self.formulation_combo.pack(side=tk.LEFT, padx=5)
        self.formulation_combo.bind('<<ComboboxSelected>>', self._on_formulation_selected)
        
        self.label_date = tk.Label(
            selector_frame,
            bg=COLORS['bg_panel'],
            fg=COLORS['text_secondary']
        )
        self.label_date.pack(side=tk.LEFT, padx=(20, 5))
        
        self.date_entry = ttk.Entry(selector_frame, width=12)
        self.date_entry.pack(side=tk.LEFT)
        self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        # =====================================================================
        # STATUS CARDS BANNER
        # =====================================================================
        cards_frame = tk.Frame(self, bg=COLORS['bg_main'])
        cards_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=10, pady=5)
        
        # Overall card
        overall_card = StatusCard(cards_frame, 'overall', TK.TEST_OVERALL, '📊')
        overall_card.pack(side=tk.LEFT, padx=5)
        self.status_cards['overall'] = overall_card
        
        # Category cards
        for cat_key, cat_info in TEST_CATEGORIES.items():
            card = StatusCard(cards_frame, cat_key, cat_info['name_key'], cat_info['icon'])
            card.pack(side=tk.LEFT, padx=5)
            card.bind('<<StatusCardClick>>', lambda e, k=cat_key: self._expand_category(k))
            self.status_cards[cat_key] = card
        
        # =====================================================================
        # LEFT PANEL - Test Input Groups
        # =====================================================================
        left_panel = tk.Frame(self, bg=COLORS['bg_panel'])
        left_panel.grid(row=2, column=0, sticky='nsew', padx=(10, 5), pady=5)
        
        # Scrollable container
        canvas = tk.Canvas(left_panel, bg=COLORS['bg_panel'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_panel, orient='vertical', command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=COLORS['bg_panel'])
        
        self.scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Build collapsible test groups
        for cat_key, cat_info in TEST_CATEGORIES.items():
            group = CollapsibleTestGroup(
                self.scroll_frame,
                cat_key,
                cat_info['name_key'],
                cat_info['icon'],
                cat_info['tests'],
                cat_info['labels'],
                on_value_change=self._on_test_value_change
            )
            group.pack(fill=tk.X, pady=2)
            self.test_groups[cat_key] = group
        
        # Notes section
        self.notes_frame = tk.LabelFrame(
            self.scroll_frame,
            font=FONTS.get('heading', ('Segoe UI', 11, 'bold')),
            bg=COLORS['bg_panel'],
            fg=COLORS['text_primary'],
            padx=10,
            pady=5
        )
        self.notes_frame.pack(fill=tk.X, pady=10)
        
        self.notes_text = tk.Text(
            self.notes_frame,
            height=3,
            bg=COLORS['bg_input'],
            fg=COLORS['text_primary'],
            font=FONTS.get('default', ('Segoe UI', 10)),
            wrap=tk.WORD,
            relief='flat'
        )
        self.notes_text.pack(fill=tk.X)
        
        # Action buttons
        btn_frame = tk.Frame(self.scroll_frame, bg=COLORS['bg_panel'])
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.save_btn = ttk.Button(btn_frame, style='Primary.TButton', command=self._save, text=t(TK.SAVE))
        self.save_btn.pack(side=tk.LEFT, padx=2)
        self.ml_btn = ttk.Button(btn_frame, style='Success.TButton', command=self._save_to_ml, text=t(TK.TEST_ADD_TO_ML))
        self.ml_btn.pack(side=tk.LEFT, padx=2)
        self.clear_btn = ttk.Button(btn_frame, command=self._clear, text=t(TK.FORM_CLEAN))
        self.clear_btn.pack(side=tk.LEFT, padx=2)
        self.copy_btn = ttk.Button(btn_frame, command=self._copy_from_previous, text=t(TK.TEST_COPY_PREVIOUS))
        self.copy_btn.pack(side=tk.LEFT, padx=2)
        
        # =====================================================================
        # RIGHT PANEL - ML Integration
        # =====================================================================
        self.ml_panel = MLIntegrationPanel(self)
        self.ml_panel.grid(row=2, column=1, sticky='nsew', padx=(5, 10), pady=5)
        
        # Set initial ML data
        self._update_ml_panel()
        self._update_texts()
    
    def _on_formulation_selected(self, event=None):
        """Handle formulation selection"""
        formulation = self.formulation_combo.get()
        if not formulation:
            return
        
        if self.on_load_trial:
            trial_data = self.on_load_trial(formulation)
            if trial_data:
                self._load_trial_data(trial_data)
    
    def _load_trial_data(self, data: Dict):
        """Load trial data into form"""
        for cat_key, group in self.test_groups.items():
            group.set_values(data)
        
        if 'notes' in data:
            self.notes_text.delete(1.0, tk.END)
            self.notes_text.insert(tk.END, data['notes'])
        
        self._update_status_cards()
    
    def _on_test_value_change(self, category_key: str, test_key: str, value: str):
        """Handle test value change"""
        self._update_status_cards()
        self._generate_ml_comments()
    
    def _update_status_cards(self):
        """Update all status cards"""
        all_scores = []
        
        for cat_key, group in self.test_groups.items():
            status, score = group.calculate_category_score()
            self.status_cards[cat_key].set_status(status, score)
            
            if score > 0:
                all_scores.append(score)
        
        # Overall score
        if all_scores:
            overall_score = sum(all_scores) / len(all_scores)
            if overall_score >= 70:
                overall_status = 'good'
            elif overall_score >= 50:
                overall_status = 'medium'
            else:
                overall_status = 'bad'
            self.status_cards['overall'].set_status(overall_status, overall_score)
        else:
            self.status_cards['overall'].set_status('neutral', 0)
    
    def _expand_category(self, category_key: str):
        """Expand specific category group"""
        for key, group in self.test_groups.items():
            if key == category_key:
                group.expand()
            else:
                group.collapse()
    
    def _generate_ml_comments(self):
        """Generate ML comments based on current values"""
        comments = []
        
        for cat_key, group in self.test_groups.items():
            values = group.get_values()
            for test_key, value in values.items():
                threshold = TEST_THRESHOLDS.get(test_key)
                if not threshold:
                    continue
                
                try:
                    num_val = float(value)
                except (ValueError, TypeError):
                    continue
                
                good = threshold.get('good', 0)
                label = TEST_CATEGORIES.get(cat_key, {}).get('labels', {}).get(test_key, test_key)
                higher_is_better = threshold.get('higher_is_better', True)
                
                if higher_is_better:
                    if num_val > good * 1.1:
                        pct = int((num_val/good - 1) * 100)
                        comments.append(t(TK.ML_COMMENT_ABOVE, label=label, pct=pct))
                    elif num_val < good * 0.5:
                        comments.append(t(TK.ML_COMMENT_BELOW_CRITICAL, label=label))
                else:
                    if num_val < good * 0.9:
                        comments.append(t(TK.ML_COMMENT_BELOW_GOOD, label=label))
                    elif num_val > good * 2:
                        comments.append(t(TK.ML_COMMENT_OUT_OF_TOLERANCE, label=label))
        
        if not comments:
            comments = [t(TK.DASHBOARD_NO_INSIGHTS)] # Reuse or use generic one
        
        self.ml_panel.set_comments(comments[:5])  # Max 5 comments
    
    def _update_ml_panel(self):
        """Update ML panel with current model info"""
        # Try to get model status
        try:
            from src.ml_engine.incremental_learner import IncrementalLearner
            learner = IncrementalLearner()
            status = learner.get_status()
            
            # Find first active model
            for target, info in status.items():
                if info.get('has_model'):
                    self.ml_panel.set_confidence(info.get('r2_score', 0) * 100)
                    self.ml_panel.set_training_info(
                        info.get('last_trained', '—')[:10] if info.get('last_trained') else '—',
                        info.get('samples', 0)
                    )
                    break
        except Exception:
            self.ml_panel.set_confidence(0)
            self.ml_panel.set_training_info('—', 0)
        # Default empty state
        self.ml_panel.set_comments([t(TK.ML_EMPTY_SUGGESTIONS)])
    
    def _save(self):
        """Save test results to database"""
        data = self.get_test_data()
        
        if not self.formulation_combo.get():
            messagebox.showwarning(t(TK.common_warning if hasattr(TK, 'common_warning') else TK.WARNING), t(TK.MSG_CHOOSE_FORMULATION))
            return
        
        if self.on_save:
            self.on_save(data)
            messagebox.showinfo(t(TK.common_success if hasattr(TK, 'common_success') else TK.SUCCESS), f"✅ {t(TK.MSG_SAVED)}")
    
    def _save_to_ml(self):
        """Save and add to ML training queue"""
        data = self.get_test_data()
        data['include_in_ml'] = True
        
        if self.on_save:
            self.on_save(data)
            messagebox.showinfo(
                t(TK.ML_CENTER_TITLE),
                f"✅ {t(TK.MSG_SAVED)}\n\n" + t(TK.MSG_AUTO_ADD_MATERIALS) # Reusing info key or similar
            )
    
    def _clear(self):
        """Clear all form values"""
        for group in self.test_groups.values():
            group.clear()
        
        self.notes_text.delete(1.0, tk.END)
        self._update_status_cards()
        self.ml_panel.set_comments([t(TK.ML_EMPTY_SUGGESTIONS)])
    
    def _copy_from_previous(self):
        """Copy values from previous test"""
        formulation = self.formulation_combo.get()
        if not formulation:
            messagebox.showwarning(t(TK.common_warning if hasattr(TK, 'common_warning') else TK.WARNING), t(TK.MSG_CHOOSE_FORMULATION))
            return
        
        if self.on_load_trial:
            trial_data = self.on_load_trial(formulation)
            if trial_data:
                self._load_trial_data(trial_data)
                messagebox.showinfo(t(TK.common_info if hasattr(TK, 'common_info') else TK.INFO), t(TK.MSG_PREV_TEST_COPIED))
            else:
                messagebox.showinfo(t(TK.common_info if hasattr(TK, 'common_info') else TK.INFO), t(TK.MSG_NO_PREV_TEST))
    
    def get_test_data(self) -> Dict:
        """Get all test data as dictionary"""
        data = {
            'formulation': self.formulation_combo.get(),
            'date': self.date_entry.get(),
            'notes': self.notes_text.get(1.0, tk.END).strip(),
            'include_in_ml': self.ml_panel.include_in_ml_var.get(),
            'results': {},
        }
        
        for group in self.test_groups.values():
            data['results'].update(group.get_values())
        
        return data
    
    def load_formulations(self, formulations: List):
        """Load formulations into dropdown"""
        if not formulations:
            self.formulation_combo['values'] = []
            return
            
        names = [f.get('formula_code', '') or f.get('name', '') for f in formulations if f]
        # Filter out empty/None values
        names = [n for n in names if n]
        self.formulation_combo['values'] = names
    
    def load_projects(self, projects: List):
        """Load projects (for compatibility)"""
        pass  # Projects are handled at parent level
    
    def load_history(self, trials: List):
        """
        Load trial history data.
        
        Args:
            trials: List of trial dicts (can be None or empty)
        """
        # Handle None/empty safely
        if not trials:
            self._clear()
            return
        
        # Filter valid trials
        valid_trials = [t for t in trials if t and isinstance(t, dict)]
        if not valid_trials:
            return
        
        # Load most recent trial into form
        latest = valid_trials[0]
        self._load_trial_data(latest)
        
        # Update comparison panel with previous trials
        if len(valid_trials) > 1:
            comparison_data = []
            current = valid_trials[0]
            previous = valid_trials[1]
            
            # Compare key metrics
            metrics = [
                ('hardness_konig', t(TK.TEST_HARDNESS_KONIG)),
                ('gloss_60', t(TK.TEST_GLOSS60)),
                ('adhesion', t(TK.TEST_ADHESION)),
                ('corrosion_resistance', t(TK.TEST_CORROSION)),
            ]
            
            for key, label in metrics:
                curr_val = current.get(key)
                prev_val = previous.get(key)
                
                if curr_val is not None and prev_val is not None:
                    try:
                        curr_num = float(curr_val)
                        prev_num = float(prev_val)
                        if prev_num != 0:
                            delta = ((curr_num - prev_num) / prev_num) * 100
                            delta_str = f'+{delta:.0f}%' if delta >= 0 else f'{delta:.0f}%'
                        else:
                            delta_str = '—'
                        
                        comparison_data.append({
                            'param': label,
                            'current': f'{curr_num:.1f}',
                            'previous': f'{prev_num:.1f}',
                            'delta': delta_str
                        })
                    except (ValueError, TypeError):
                        pass
            
            if comparison_data:
                self.ml_panel.set_comparison_data(comparison_data)

    def _update_texts(self):
        """Update overall panel texts"""
        self.main_title.config(text=t(TK.TEST_RESULTS_TITLE))
        self.label_formulation.config(text=t(TK.FORM_SAVED_FORMULAS) + ":")
        self.label_date.config(text=t(TK.TEST_DATE))
        self.notes_frame.config(text=t(TK.TEST_NOTES))
        
        # Update sub-panels
        for card in self.status_cards.values():
            card._update_texts()
            
        for group in self.test_groups.values():
            group._update_texts()
            
        if self.ml_panel:
            self.ml_panel._update_texts()
            
        # Update Action Buttons
        self.save_btn.config(text=t(TK.SAVE))
        self.ml_btn.config(text=t(TK.TEST_ADD_TO_ML))
        self.clear_btn.config(text=t(TK.FORM_CLEAN))
        self.copy_btn.config(text=t(TK.TEST_COPY_PREVIOUS))
            
        # Refresh current charts/insights if data exists
        if self.current_formulation_code:
            self._update_charts(self.current_formulation_code)
