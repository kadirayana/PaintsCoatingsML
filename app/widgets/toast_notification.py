"""
Paint Formulation AI - Toast Notification Widget
=================================================
Non-intrusive notification widget for background operations.

Features:
- Appears at bottom-right of window
- Auto-dismisses after configurable timeout
- Queue multiple toasts
- Customizable icons and colors
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class ToastNotification(tk.Toplevel):
    """
    Non-blocking toast notification widget.
    
    Appears at bottom-right of parent window and
    auto-dismisses after specified duration.
    """
    
    # Toast types and their styling
    TYPES = {
        'info': {'icon': 'ℹ️', 'bg': '#2D3436', 'fg': '#DFE6E9'},
        'success': {'icon': '✅', 'bg': '#00B894', 'fg': '#FFFFFF'},
        'warning': {'icon': '⚠️', 'bg': '#FDCB6E', 'fg': '#2D3436'},
        'error': {'icon': '❌', 'bg': '#D63031', 'fg': '#FFFFFF'},
        'ml': {'icon': '🤖', 'bg': '#6C5CE7', 'fg': '#FFFFFF'},
    }
    
    def __init__(
        self,
        parent,
        message: str,
        toast_type: str = 'info',
        duration: int = 5000,
        on_click: Optional[Callable] = None
    ):
        """
        Create a toast notification.
        
        Args:
            parent: Parent window
            message: Message to display
            toast_type: One of 'info', 'success', 'warning', 'error', 'ml'
            duration: Auto-dismiss time in milliseconds (0 = no auto-dismiss)
            on_click: Optional callback when toast is clicked
        """
        super().__init__(parent)
        
        self.parent = parent
        self.on_click = on_click
        self.duration = duration
        
        # Window setup
        self.overrideredirect(True)  # No window decorations
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.95)
        
        # Get styling
        style = self.TYPES.get(toast_type, self.TYPES['info'])
        
        # Configure window
        self.configure(bg=style['bg'])
        
        # Main frame
        frame = tk.Frame(self, bg=style['bg'], padx=15, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Icon
        icon_label = tk.Label(
            frame,
            text=style['icon'],
            font=('Segoe UI', 16),
            bg=style['bg'],
            fg=style['fg']
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Message
        msg_label = tk.Label(
            frame,
            text=message,
            font=('Segoe UI', 10),
            bg=style['bg'],
            fg=style['fg'],
            wraplength=300,
            justify=tk.LEFT
        )
        msg_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Close button
        close_btn = tk.Label(
            frame,
            text='✕',
            font=('Segoe UI', 10),
            bg=style['bg'],
            fg=style['fg'],
            cursor='hand2'
        )
        close_btn.pack(side=tk.RIGHT, padx=(10, 0))
        close_btn.bind('<Button-1>', lambda e: self._close())
        
        # Bind click to whole toast
        if on_click:
            for widget in [frame, icon_label, msg_label]:
                widget.bind('<Button-1>', lambda e: self._on_click())
                widget.configure(cursor='hand2')
        
        # Position toast
        self._position_toast()
        
        # Start fade-in animation
        self._fade_in()
        
        # Schedule auto-dismiss
        if duration > 0:
            self.after(duration, self._fade_out)
    
    def _position_toast(self):
        """Position toast at bottom-right of parent window"""
        self.update_idletasks()
        
        # Get parent window position
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Get toast dimensions
        toast_width = self.winfo_reqwidth()
        toast_height = self.winfo_reqheight()
        
        # Calculate position (bottom-right with padding)
        x = parent_x + parent_width - toast_width - 20
        y = parent_y + parent_height - toast_height - 40
        
        self.geometry(f'+{x}+{y}')
    
    def _fade_in(self):
        """Fade in animation"""
        alpha = 0.0
        
        def step():
            nonlocal alpha
            alpha += 0.1
            if alpha <= 0.95:
                self.attributes('-alpha', alpha)
                self.after(20, step)
            else:
                self.attributes('-alpha', 0.95)
        
        self.attributes('-alpha', 0)
        step()
    
    def _fade_out(self):
        """Fade out animation"""
        alpha = 0.95
        
        def step():
            nonlocal alpha
            alpha -= 0.1
            if alpha >= 0:
                self.attributes('-alpha', alpha)
                self.after(20, step)
            else:
                self._close()
        
        step()
    
    def _on_click(self):
        """Handle click on toast"""
        if self.on_click:
            self.on_click()
        self._close()
    
    def _close(self):
        """Close the toast"""
        try:
            self.destroy()
        except tk.TclError:
            pass


class ToastManager:
    """
    Manages a queue of toast notifications.
    
    Ensures toasts don't overlap and are shown sequentially.
    """
    
    def __init__(self, parent):
        self.parent = parent
        self._toast_queue = []
        self._current_toast = None
        self._offset = 0
    
    def show(
        self,
        message: str,
        toast_type: str = 'info',
        duration: int = 5000,
        on_click: Optional[Callable] = None
    ):
        """
        Show a toast notification.
        
        Args:
            message: Message to display
            toast_type: One of 'info', 'success', 'warning', 'error', 'ml'
            duration: Auto-dismiss time in milliseconds
            on_click: Optional callback when toast is clicked
        """
        toast = ToastNotification(
            self.parent,
            message=message,
            toast_type=toast_type,
            duration=duration,
            on_click=on_click
        )
        
        # Offset if multiple toasts
        if self._current_toast and self._current_toast.winfo_exists():
            self._offset += 70
            toast.geometry(f'+{toast.winfo_x()}+{toast.winfo_y() - self._offset}')
        else:
            self._offset = 0
        
        self._current_toast = toast
        return toast
    
    def show_ml_update(self, message: str = "AI Model updated with latest formulation"):
        """Convenience method for ML update notifications"""
        return self.show(message, toast_type='ml', duration=4000)
    
    def show_success(self, message: str):
        """Convenience method for success notifications"""
        return self.show(message, toast_type='success', duration=3000)
    
    def show_warning(self, message: str):
        """Convenience method for warning notifications"""
        return self.show(message, toast_type='warning', duration=5000)
