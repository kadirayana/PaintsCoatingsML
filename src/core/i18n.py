import json
import logging
from pathlib import Path
from typing import Dict, List, Callable, Optional, Any

logger = logging.getLogger(__name__)

class I18nMixin:
    """
    Mixin for UI components that need to respond to language changes.
    """
    def setup_i18n(self):
        """Register listener for language change events."""
        get_i18n().add_listener(self._on_language_changed)

    def _on_language_changed(self):
        """Callback triggered when language switches. Should be overridden."""
        if hasattr(self, '_update_texts'):
            self._update_texts()

    def unbind_i18n(self):
        """Cleanup listener to prevent memory leaks."""
        get_i18n().remove_listener(self._on_language_changed)

class I18n:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._lang = "tr"  # Default
        self._strings: Dict = {}
        self._listeners: List[Callable[[], None]] = []
        self._lang_dir = self._find_lang_dir()
        
        # Load default
        self.load(self._lang)
        self._initialized = True
    
    def _find_lang_dir(self) -> Path:
        """Find translation directory."""
        candidates = [
            Path(__file__).parent.parent.parent / "lang",
            Path.cwd() / "lang",
            Path(__file__).absolute().parent.parent.parent / "lang"
        ]
        for p in candidates:
            if p.exists() and p.is_dir():
                return p
        return Path.cwd() / "lang"

    def load(self, lang: str) -> bool:
        """Load strings from JSON file."""
        file_path = self._lang_dir / f"{lang}.json"
        if not file_path.exists():
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self._strings = json.load(f)
            self._lang = lang
            return True
        except Exception as e:
            logger.error(f"i18n load error ({lang}): {e}")
            return False

    def switch(self, lang: str) -> bool:
        """Switch language and notify listeners."""
        if lang == self._lang: return True
        if self.load(lang):
            self._notify_listeners()
            return True
        return False

    def _notify_listeners(self):
        """Notify all listeners to refresh their texts."""
        for callback in self._listeners:
            try:
                callback()
            except Exception as e:
                logger.error(f"Listener error: {e}")

    def add_listener(self, callback: Callable[[], None]):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[], None]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def t(self, key: str, default: str = None, **kwargs) -> str:
        """Translate key with dot-notation support and variable interpolation."""
        parts = key.split('.')
        val = self._strings
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return default if default is not None else key
        
        if not isinstance(val, str):
            return key
            
        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val

    @property
    def current_language(self) -> str:
        return self._lang

# Singleton Access
_i18n = I18n()

def t(key: str, default: str = None, **kwargs) -> str:
    return _i18n.t(key, default, **kwargs)

def get_i18n() -> I18n:
    return _i18n

def switch_language(lang: str) -> bool:
    return _i18n.switch(lang)
