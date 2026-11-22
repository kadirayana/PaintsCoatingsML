"""
Çeviri anahtarı tutarlılığı: tanımsız TK sabitleri çalışma anında AttributeError
verir (ör. dashboard kartına tıklama, proje oluşturma mesajı).
"""
import glob
import json
import os
import re

from src.core.translation_keys import TK

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lookup(data, dotted):
    for part in dotted.split('.'):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


def test_every_referenced_tk_constant_is_defined():
    missing = {}
    for path in glob.glob(os.path.join(ROOT, 'app', '**', '*.py'), recursive=True) + \
            glob.glob(os.path.join(ROOT, 'src', '**', '*.py'), recursive=True):
        source = open(path, encoding='utf-8').read()
        guarded = set(re.findall(r"hasattr\(TK,\s*'([A-Za-z_0-9]+)'\)", source))
        for name in re.findall(r'\bTK\.([A-Z][A-Z_0-9]*)\b', source):
            if not hasattr(TK, name) and name not in guarded:
                missing.setdefault(name, set()).add(os.path.relpath(path, ROOT))
    assert not missing, missing


def test_every_tk_constant_has_text_in_both_languages():
    for lang in ('tr', 'en'):
        data = json.load(open(os.path.join(ROOT, 'lang', f'{lang}.json'), encoding='utf-8'))
        unresolved = [name for name, key in vars(TK).items()
                      if name.isupper() and name != 'COMMON' and isinstance(key, str)
                      and not isinstance(_lookup(data, key), str)]
        assert not unresolved, (lang, unresolved)
