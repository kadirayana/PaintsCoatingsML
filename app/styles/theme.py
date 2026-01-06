"""
Paint Formulation AI - Modern Dark Theme
========================================
Centralized theme configuration for the application.
VS Code Dark+ inspired color palette with Data Science focus.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional, Callable
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# COLOR PALETTE
# =============================================================================

COLORS = {
    # Backgrounds
    'bg_main': '#1E1E1E',        # Main window background
    'bg_panel': '#252526',       # Panels and cards
    'bg_secondary': '#2D2D2D',   # Secondary areas, table rows
    'bg_input': '#3C3C3C',       # Input fields
    'bg_hover': '#404040',       # Hover states
    'bg_selected': '#094771',    # Selected items (darker blue)
    
    # Accents
    'accent_primary': '#007ACC',  # Primary buttons, active states
    'accent_success': '#4EC9B0',  # Success, confirm actions
    'accent_danger': '#F14C4C',   # Delete, danger actions
    'accent_warning': '#CCA700',  # Warning states
    'accent_info': '#3794FF',     # Info, links
    
    # Text
    'text_primary': '#CCCCCC',    # Main text (off-white)
    'text_secondary': '#858585',  # Secondary text
    'text_muted': '#6A6A6A',      # Disabled, muted text
    'text_inverse': '#FFFFFF',    # Text on accent backgrounds
    
    # Borders
    'border_default': '#3C3C3C',  # Default borders
    'border_focus': '#007ACC',    # Focus state borders
    'border_subtle': '#2D2D2D',   # Subtle borders
    
    # Status colors
    'status_online': '#89D185',   # Online/Connected
    'status_offline': '#F14C4C',  # Offline/Disconnected
    'status_warning': '#CCA700',  # Warning state
}

# =============================================================================
# ICON MAPPING (Unicode/Emoji)
# =============================================================================

ICONS = {
    # Actions
    'save': '💾',
    'delete': '🗑️',
    'add': '➕',
    'edit': '✏️',
    'refresh': '🔄',
    'clear': '🧹',
    'close': '✕',
    
    # Navigation
    'home': '🏠',
    'back': '◀',
    'forward': '▶',
    'up': '▲',
    'down': '▼',
    
    # Data Science / ML
    'calculate': '📊',
    'ml': '🧠',
    'ml_predict': '🔮',
    'ml_train': '🧠',
    'optimize': '⚡',
    'chart': '📈',
    'data': '📋',
    
    # File operations
    'export': '📤',
    'import': '📥',
    'folder': '📁',
    'folder_open': '📂',
    'file': '📄',
    'excel': '📊',
    
    # Domain specific
    'materials': '🧪',
    'formula': '📋',
    'test': '🧫',
    'project': '📁',
    'settings': '⚙️',
    
    # Status
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'loading': '⏳',
}

# =============================================================================
# FONTS
# =============================================================================

FONTS = {
    'default': ('Segoe UI', 10),
    'small': ('Segoe UI', 9),
    'heading': ('Segoe UI', 12, 'bold'),
    'title': ('Segoe UI', 14, 'bold'),
    'mono': ('Consolas', 10),
    'icon': ('Segoe UI Emoji', 14),
    'icon_large': ('Segoe UI Emoji', 18),
}

# =============================================================================
# SPACING
# =============================================================================

SPACING = {
    'xs': 2,
    'sm': 5,
    'md': 10,
    'lg': 15,
    'xl': 20,
}

# =============================================================================
# THEME APPLICATION
# =============================================================================

def apply_dark_theme(root: tk.Tk) -> ttk.Style:
    """
    Apply modern dark theme to the entire application.
    
    Args:
        root: The root Tk window
        
    Returns:
        Configured ttk.Style object
    """
    # Configure root window
    root.configure(bg=COLORS['bg_main'])
    
    # Option database for tk widgets
    root.option_add('*Background', COLORS['bg_panel'])
    root.option_add('*Foreground', COLORS['text_primary'])
    root.option_add('*Font', FONTS['default'])
    
    # Create and configure style
    style = ttk.Style()
    
    # Use 'clam' as base theme (most customizable)
    try:
        style.theme_use('clam')
    except tk.TclError:
        style.theme_use('default')
    
    # ---------------------------------------------------------------------
    # GLOBAL STYLES
    # ---------------------------------------------------------------------
    style.configure('.',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        fieldbackground=COLORS['bg_input'],
        bordercolor=COLORS['border_default'],
        darkcolor=COLORS['bg_secondary'],
        lightcolor=COLORS['bg_hover'],
        troughcolor=COLORS['bg_secondary'],
        selectbackground=COLORS['accent_primary'],
        selectforeground=COLORS['text_inverse'],
        font=FONTS['default'],
    )
    
    # ---------------------------------------------------------------------
    # FRAME STYLES
    # ---------------------------------------------------------------------
    style.configure('TFrame', 
        background=COLORS['bg_panel']
    )
    style.configure('Dark.TFrame', 
        background=COLORS['bg_main']
    )
    style.configure('Card.TFrame',
        background=COLORS['bg_secondary'],
        relief='flat'
    )
    
    # ---------------------------------------------------------------------
    # LABEL STYLES
    # ---------------------------------------------------------------------
    style.configure('TLabel',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        font=FONTS['default']
    )
    style.configure('Header.TLabel',
        font=FONTS['heading'],
        foreground=COLORS['text_primary']
    )
    style.configure('Title.TLabel',
        font=FONTS['title'],
        foreground=COLORS['text_primary']
    )
    style.configure('Muted.TLabel',
        foreground=COLORS['text_muted']
    )
    style.configure('Success.TLabel',
        foreground=COLORS['accent_success']
    )
    style.configure('Danger.TLabel',
        foreground=COLORS['accent_danger']
    )
    style.configure('Accent.TLabel',
        foreground=COLORS['accent_primary']
    )
    
    # ---------------------------------------------------------------------
    # LABELFRAME STYLES
    # ---------------------------------------------------------------------
    style.configure('TLabelframe',
        background=COLORS['bg_panel'],
        bordercolor=COLORS['border_default'],
        relief='groove'
    )
    style.configure('TLabelframe.Label',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        font=FONTS['heading']
    )
    
    # ---------------------------------------------------------------------
    # BUTTON STYLES
    # ---------------------------------------------------------------------
    style.configure('TButton',
        background=COLORS['bg_secondary'],
        foreground=COLORS['text_primary'],
        bordercolor=COLORS['border_default'],
        focuscolor=COLORS['accent_primary'],
        font=FONTS['default'],
        padding=(12, 6)
    )
    style.map('TButton',
        background=[
            ('active', COLORS['bg_hover']),
            ('pressed', COLORS['accent_primary']),
            ('disabled', COLORS['bg_secondary'])
        ],
        foreground=[
            ('pressed', COLORS['text_inverse']),
            ('disabled', COLORS['text_muted'])
        ]
    )
    
    # Primary Button (Blue)
    style.configure('Primary.TButton',
        background=COLORS['accent_primary'],
        foreground=COLORS['text_inverse'],
        bordercolor=COLORS['accent_primary']
    )
    style.map('Primary.TButton',
        background=[
            ('active', '#005A9E'),
            ('pressed', '#004578'),
            ('disabled', COLORS['bg_secondary'])
        ]
    )
    
    # Success Button (Green)
    style.configure('Success.TButton',
        background=COLORS['accent_success'],
        foreground=COLORS['bg_main'],
        bordercolor=COLORS['accent_success']
    )
    style.map('Success.TButton',
        background=[
            ('active', '#3DAA9A'),
            ('pressed', '#2D8A7A')
        ]
    )
    
    # Danger Button (Red)
    style.configure('Danger.TButton',
        background=COLORS['accent_danger'],
        foreground=COLORS['text_inverse'],
        bordercolor=COLORS['accent_danger']
    )
    style.map('Danger.TButton',
        background=[
            ('active', '#D13438'),
            ('pressed', '#A80000')
        ]
    )
    
    # Sidebar Button (Icon-only)
    style.configure('Sidebar.TButton',
        background=COLORS['bg_main'],
        foreground=COLORS['text_primary'],
        borderwidth=0,
        padding=(8, 12),
        font=FONTS['icon_large']
    )
    style.map('Sidebar.TButton',
        background=[
            ('active', COLORS['bg_hover']),
            ('selected', COLORS['accent_primary'])
        ],
        foreground=[
            ('selected', COLORS['text_inverse'])
        ]
    )
    
    # ---------------------------------------------------------------------
    # ENTRY STYLES
    # ---------------------------------------------------------------------
    style.configure('TEntry',
        fieldbackground=COLORS['bg_input'],
        foreground=COLORS['text_primary'],
        bordercolor=COLORS['border_default'],
        insertcolor=COLORS['text_primary'],
        padding=6
    )
    style.map('TEntry',
        bordercolor=[
            ('focus', COLORS['border_focus']),
            ('invalid', COLORS['accent_danger'])
        ],
        fieldbackground=[
            ('disabled', COLORS['bg_secondary'])
        ]
    )
    
    # ---------------------------------------------------------------------
    # COMBOBOX STYLES
    # ---------------------------------------------------------------------
    style.configure('TCombobox',
        fieldbackground=COLORS['bg_input'],
        background=COLORS['bg_secondary'],
        foreground=COLORS['text_primary'],
        arrowcolor=COLORS['text_primary'],
        bordercolor=COLORS['border_default'],
        padding=6
    )
    style.map('TCombobox',
        fieldbackground=[
            ('readonly', COLORS['bg_input']),
            ('disabled', COLORS['bg_secondary'])
        ],
        bordercolor=[
            ('focus', COLORS['border_focus'])
        ]
    )
    
    # Configure dropdown list colors
    root.option_add('*TCombobox*Listbox.background', COLORS['bg_input'])
    root.option_add('*TCombobox*Listbox.foreground', COLORS['text_primary'])
    root.option_add('*TCombobox*Listbox.selectBackground', COLORS['accent_primary'])
    root.option_add('*TCombobox*Listbox.selectForeground', COLORS['text_inverse'])
    
    # ---------------------------------------------------------------------
    # TREEVIEW (DATA TABLE) STYLES
    # ---------------------------------------------------------------------
    style.configure('Treeview',
        background=COLORS['bg_secondary'],
        foreground=COLORS['text_primary'],
        fieldbackground=COLORS['bg_secondary'],
        borderwidth=0,
        rowheight=28,
        font=FONTS['default']
    )
    style.configure('Treeview.Heading',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        font=FONTS['heading'],
        borderwidth=0,
        relief='flat',
        padding=(8, 4)
    )
    style.map('Treeview',
        background=[
            ('selected', COLORS['bg_selected'])
        ],
        foreground=[
            ('selected', COLORS['text_inverse'])
        ]
    )
    style.map('Treeview.Heading',
        background=[
            ('active', COLORS['bg_hover'])
        ]
    )
    
    # ---------------------------------------------------------------------
    # NOTEBOOK (TABS) STYLES
    # ---------------------------------------------------------------------
    style.configure('TNotebook',
        background=COLORS['bg_main'],
        borderwidth=0,
        tabmargins=[0, 0, 0, 0]
    )
    style.configure('TNotebook.Tab',
        background=COLORS['bg_secondary'],
        foreground=COLORS['text_secondary'],
        padding=(16, 8),
        font=FONTS['default'],
        borderwidth=0
    )
    style.map('TNotebook.Tab',
        background=[
            ('selected', COLORS['bg_panel'])
        ],
        foreground=[
            ('selected', COLORS['accent_primary'])
        ],
        expand=[
            ('selected', [0, 0, 0, 2])
        ]
    )
    
    # ---------------------------------------------------------------------
    # SCROLLBAR STYLES
    # ---------------------------------------------------------------------
    style.configure('TScrollbar',
        background=COLORS['bg_secondary'],
        troughcolor=COLORS['bg_main'],
        arrowcolor=COLORS['text_muted'],
        borderwidth=0,
        width=12
    )
    style.map('TScrollbar',
        background=[
            ('active', COLORS['bg_hover'])
        ]
    )
    
    # Vertical scrollbar
    style.configure('Vertical.TScrollbar',
        arrowsize=12
    )
    
    # ---------------------------------------------------------------------
    # SEPARATOR STYLES
    # ---------------------------------------------------------------------
    style.configure('TSeparator',
        background=COLORS['border_default']
    )
    
    # ---------------------------------------------------------------------
    # PROGRESSBAR STYLES
    # ---------------------------------------------------------------------
    style.configure('TProgressbar',
        background=COLORS['accent_primary'],
        troughcolor=COLORS['bg_secondary'],
        borderwidth=0,
        thickness=6
    )
    style.configure('Success.Horizontal.TProgressbar',
        background=COLORS['accent_success']
    )
    
    # ---------------------------------------------------------------------
    # SCALE STYLES
    # ---------------------------------------------------------------------
    style.configure('TScale',
        background=COLORS['bg_panel'],
        troughcolor=COLORS['bg_secondary'],
        borderwidth=0
    )
    
    # ---------------------------------------------------------------------
    # CHECKBUTTON & RADIOBUTTON STYLES
    # ---------------------------------------------------------------------
    style.configure('TCheckbutton',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        font=FONTS['default']
    )
    style.map('TCheckbutton',
        background=[
            ('active', COLORS['bg_panel'])
        ]
    )
    
    style.configure('TRadiobutton',
        background=COLORS['bg_panel'],
        foreground=COLORS['text_primary'],
        font=FONTS['default']
    )
    style.map('TRadiobutton',
        background=[
            ('active', COLORS['bg_panel'])
        ]
    )
    
    # ---------------------------------------------------------------------
    # SPINBOX STYLES
    # ---------------------------------------------------------------------
    style.configure('TSpinbox',
        fieldbackground=COLORS['bg_input'],
        foreground=COLORS['text_primary'],
        bordercolor=COLORS['border_default'],
        arrowcolor=COLORS['text_primary'],
        padding=6
    )
    
    logger.info("Dark theme applied successfully")
    return style


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_icon_button(parent, icon_key: str, text: str = "", command: Callable = None, 
                       style: str = 'TButton', tooltip: str = None, **kwargs) -> ttk.Button:
    """
    Create a button with an icon and optional text.
    
    Args:
        parent: Parent widget
        icon_key: Key from ICONS dict
        text: Optional text label
        command: Button command
        style: ttk style name
        tooltip: Tooltip text (not implemented yet)
        **kwargs: Additional button options
    
    Returns:
        ttk.Button widget
    """
    icon = ICONS.get(icon_key, '')
    display_text = f"{icon} {text}".strip() if text else icon
    
    btn = ttk.Button(parent, text=display_text, command=command, style=style, **kwargs)
    
    # TODO: Add tooltip binding if needed
    
    return btn


def configure_treeview_tags(tree: ttk.Treeview):
    """
    Configure alternating row colors and other visual tags for a Treeview.
    
    Args:
        tree: Treeview widget to configure
    """
    tree.tag_configure('oddrow', background=COLORS['bg_secondary'])
    tree.tag_configure('evenrow', background='#2A2A2A')
    tree.tag_configure('selected', background=COLORS['bg_selected'])
    tree.tag_configure('success', foreground=COLORS['accent_success'])
    tree.tag_configure('danger', foreground=COLORS['accent_danger'])
    tree.tag_configure('warning', foreground=COLORS['accent_warning'])


def apply_focus_highlight(widget: tk.Widget):
    """
    Add focus highlighting effect to an entry-like widget.
    
    Args:
        widget: Widget to apply effect to
    """
    original_style = widget.cget('style') if hasattr(widget, 'cget') else 'TEntry'
    
    def on_focus_in(event):
        # Focus effect is handled by style map
        pass
    
    def on_focus_out(event):
        # Reset effect is handled by style map
        pass
    
    widget.bind('<FocusIn>', on_focus_in, add='+')
    widget.bind('<FocusOut>', on_focus_out, add='+')


class ThemedText(tk.Text):
    """Text widget with dark theme styling."""
    
    def __init__(self, parent, **kwargs):
        # Apply theme colors
        kwargs.setdefault('bg', COLORS['bg_input'])
        kwargs.setdefault('fg', COLORS['text_primary'])
        kwargs.setdefault('insertbackground', COLORS['text_primary'])
        kwargs.setdefault('selectbackground', COLORS['accent_primary'])
        kwargs.setdefault('selectforeground', COLORS['text_inverse'])
        kwargs.setdefault('relief', 'flat')
        kwargs.setdefault('borderwidth', 1)
        kwargs.setdefault('highlightthickness', 1)
        kwargs.setdefault('highlightcolor', COLORS['border_focus'])
        kwargs.setdefault('highlightbackground', COLORS['border_default'])
        kwargs.setdefault('font', FONTS['default'])
        
        super().__init__(parent, **kwargs)


class ThemedListbox(tk.Listbox):
    """Listbox widget with dark theme styling."""
    
    def __init__(self, parent, **kwargs):
        kwargs.setdefault('bg', COLORS['bg_input'])
        kwargs.setdefault('fg', COLORS['text_primary'])
        kwargs.setdefault('selectbackground', COLORS['accent_primary'])
        kwargs.setdefault('selectforeground', COLORS['text_inverse'])
        kwargs.setdefault('relief', 'flat')
        kwargs.setdefault('borderwidth', 1)
        kwargs.setdefault('highlightthickness', 1)
        kwargs.setdefault('highlightcolor', COLORS['border_focus'])
        kwargs.setdefault('highlightbackground', COLORS['border_default'])
        kwargs.setdefault('font', FONTS['default'])
        
        super().__init__(parent, **kwargs)
