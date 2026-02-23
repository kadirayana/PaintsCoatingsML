import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(os.getcwd())

from src.core.i18n import t, I18n, switch_language, I18nMixin
from src.core.translation_keys import TK

def test_i18n_basic():
    print("Testing basic i18n...")
    i18n = I18n()
    
    # Test TR
    switch_language("tr")
    print(f"Current Lang: {i18n.current_language}")
    assert t(TK.MENU_FILE) == "Dosya"
    print("TR: OK")
    
    # Test EN
    switch_language("en")
    print(f"Current Lang: {i18n.current_language}")
    assert t(TK.MENU_FILE) == "File"
    print("EN: OK")

class MockWidget(I18nMixin):
    def __init__(self):
        self.updated = False
        self.setup_i18n()
    def _update_texts(self):
        self.updated = True

def test_i18n_propagation():
    print("Testing i18n propagation...")
    widget = MockWidget()
    assert widget.updated == False
    
    switch_language("tr")
    assert widget.updated == True
    print("Propagation: OK")

if __name__ == "__main__":
    try:
        test_i18n_basic()
        test_i18n_propagation()
        print("\nALL I18N TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
