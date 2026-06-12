import json
import os

def load_texts():
    fa_path = os.path.join(os.path.dirname(__file__), 'fa.json')
    en_path = os.path.join(os.path.dirname(__file__), 'en.json')
    
    with open(fa_path, 'r', encoding='utf-8') as f:
        fa = json.load(f)
    with open(en_path, 'r', encoding='utf-8') as f:
        en = json.load(f)
    
    return {'fa': fa, 'en': en}

TEXTS = load_texts()

def get_text(user_id, key, **kwargs):
    # Simplified - in production, get language from DB
    lang = 'fa'
    text = TEXTS.get(lang, TEXTS['fa']).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text
