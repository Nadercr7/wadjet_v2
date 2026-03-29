# Phase 6 — Arabic i18n

## Goal
Make Wadjet fully bilingual (English/Arabic) with proper RTL layout, Arabic translations for all UI strings, and Arabic data rendering. Arabic is a first-class citizen — not an afterthought.

## Bugs Fixed
- **M1**: Zero RTL CSS for Arabic text
- **M2**: Arabic names in data but never rendered (260 landmarks have `name_ar`)
- **M3**: Smart Write says "English or Arabic" but only shows English examples
- **M4**: Translation corpus has no Arabic translations

## New Features
- Language toggle (🌐) in nav
- Full RTL layout via Tailwind `rtl:` prefix
- Cairo font for Arabic text
- `i18n/en.json` + `i18n/ar.json` translation files
- Jinja2 template macro `{{ t('key') }}`
- Language persisted in cookie + user preference (if logged in)

## Files Created
- `app/i18n/en.json` — all English UI strings
- `app/i18n/ar.json` — all Arabic UI strings
- `app/i18n/__init__.py` — translation loader + Jinja2 integration
- `app/static/fonts/Cairo-Variable.woff2` — Arabic font (self-hosted)

## Files Modified
- `app/templates/base.html` — add RTL support, lang attribute, Cairo font
- `app/templates/partials/nav.html` — language toggle button
- `app/templates/explore.html` — render `name_ar` alongside English
- `app/templates/dictionary.html` — render Arabic sign names
- `app/templates/write.html` — add Arabic examples
- `app/templates/landing.html` — bilingual content
- `app/templates/chat.html` — bilingual UI strings
- `app/templates/scan.html` — bilingual UI strings
- `app/static/css/input.css` — RTL utilities
- `app/api/pages.py` — language detection, pass to templates
- `app/main.py` — register i18n in Jinja2 globals

## Implementation Steps

### Step 1: Create i18n system
```python
# app/i18n/__init__.py
import json
from pathlib import Path
from functools import lru_cache

I18N_DIR = Path(__file__).parent

@lru_cache(maxsize=4)
def load_translations(lang: str) -> dict:
    path = I18N_DIR / f"{lang}.json"
    if not path.exists():
        path = I18N_DIR / "en.json"
    return json.loads(path.read_text(encoding="utf-8"))

def t(key: str, lang: str = "en") -> str:
    """Get translation for key in given language."""
    translations = load_translations(lang)
    # Support nested keys: "nav.home" → translations["nav"]["home"]
    parts = key.split(".")
    value = translations
    for part in parts:
        value = value.get(part, key)
        if isinstance(value, str):
            return value
    return key
```

### Step 2: English translation file (partial — key structure)
```json
{
    "app": { "name": "Wadjet", "tagline": "Egyptian Heritage AI" },
    "nav": {
        "hieroglyphs": "Hieroglyphs", "scan": "Scan", "dictionary": "Dictionary",
        "landmarks": "Landmarks", "explore": "Explore", "write": "Write",
        "quiz": "Stories", "chat": "Thoth", "sign_in": "Sign In", "sign_up": "Sign Up"
    },
    "landing": {
        "hero_title": "Decode Ancient Egypt",
        "hero_subtitle": "AI-powered hieroglyph recognition, landmark exploration, and interactive stories",
        "cta": "Start Scanning"
    },
    "scan": {
        "title": "Scan Hieroglyphs",
        "upload": "Upload an image",
        "drop": "or drag and drop",
        "formats": "JPEG, PNG, or WebP up to 10MB",
        "scanning": "Analyzing...",
        "confidence": "confidence"
    },
    "common": {
        "loading": "Loading...", "error": "Something went wrong",
        "offline": "You are offline", "back": "Back", "next": "Next"
    }
}
```

### Step 3: Arabic translation file
```json
{
    "app": { "name": "واجت", "tagline": "التراث المصري بالذكاء الاصطناعي" },
    "nav": {
        "hieroglyphs": "الهيروغليفية", "scan": "مسح", "dictionary": "القاموس",
        "landmarks": "المعالم", "explore": "استكشاف", "write": "اكتب",
        "quiz": "حكايات", "chat": "تحوت", "sign_in": "تسجيل الدخول", "sign_up": "إنشاء حساب"
    },
    "landing": {
        "hero_title": "فك رموز مصر القديمة",
        "hero_subtitle": "تعرف على الهيروغليفية والمعالم الأثرية وحكايات النيل التفاعلية بالذكاء الاصطناعي",
        "cta": "ابدأ المسح"
    },
    "scan": {
        "title": "مسح الهيروغليفية",
        "upload": "ارفع صورة",
        "drop": "أو اسحب وأفلت",
        "formats": "JPEG أو PNG أو WebP حتى 10 ميجابايت",
        "scanning": "جاري التحليل...",
        "confidence": "دقة"
    },
    "common": {
        "loading": "جاري التحميل...", "error": "حدث خطأ",
        "offline": "أنت غير متصل", "back": "رجوع", "next": "التالي"
    }
}
```

### Step 4: Register i18n in Jinja2
```python
# In app/main.py (during app setup):
from app.i18n import t as translate_fn

# After templates are initialized:
app.state.templates.env.globals["t"] = translate_fn

# In each page handler, determine language:
def get_lang(request: Request) -> str:
    # Priority: 1) query param ?lang=ar  2) cookie  3) Accept-Language  4) 'en'
    lang = request.query_params.get("lang")
    if not lang:
        lang = request.cookies.get("wadjet_lang")
    if not lang:
        accept = request.headers.get("accept-language", "")
        lang = "ar" if "ar" in accept else "en"
    return lang if lang in ("en", "ar") else "en"
```

### Step 5: Update base.html for RTL
```html
<!-- Dynamic lang + dir -->
<html lang="{{ lang }}" dir="{{ 'rtl' if lang == 'ar' else 'ltr' }}" class="scroll-smooth">

<!-- Add Cairo font for Arabic -->
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">

<!-- Or self-host: -->
<link rel="stylesheet" href="/static/fonts/cairo.css">
```

### Step 6: Tailwind RTL utilities
Tailwind v4 has built-in RTL support. Use `rtl:` prefix:
```html
<!-- Padding that flips in RTL: -->
<div class="pl-4 rtl:pr-4 rtl:pl-0">

<!-- Text alignment: -->
<p class="text-left rtl:text-right">

<!-- Margin direction: -->
<span class="ml-2 rtl:mr-2 rtl:ml-0">
```

### Step 7: Language toggle in nav
```html
<!-- In nav.html, after the CTA button: -->
<button @click="toggleLang()" class="p-2 rounded-lg text-text-muted hover:text-text hover:bg-surface-alt transition-colors" aria-label="Switch language">
    <span x-text="document.documentElement.lang === 'ar' ? 'EN' : 'عر'" class="text-sm font-medium"></span>
</button>

<script>
function toggleLang() {
    const current = document.documentElement.lang;
    const next = current === 'ar' ? 'en' : 'ar';
    document.cookie = `wadjet_lang=${next};path=/;max-age=31536000`;
    window.location.reload();
}
</script>
```

### Step 8: Render Arabic names in explore
```html
<!-- In explore cards: -->
<h3 class="font-display text-lg">{{ site.name }}</h3>
{% if lang == 'ar' and site.name_ar %}
<p class="text-sm text-text-muted font-arabic">{{ site.name_ar }}</p>
{% endif %}
```

### Step 9: Arabic examples in Write
Add bilingual placeholder examples:
```html
<div class="flex flex-col gap-2">
    <button @click="input = 'The sun rises over Egypt'" class="text-left rtl:text-right text-sm text-text-muted hover:text-gold">
        "The sun rises over Egypt"
    </button>
    <button @click="input = 'الشمس تشرق على مصر'" class="text-right text-sm text-text-muted hover:text-gold font-arabic" dir="rtl">
        "الشمس تشرق على مصر"
    </button>
</div>
```

## Testing Checklist
- [ ] Toggle language → page reloads in Arabic
- [ ] Arabic UI: all nav items, buttons, headings in Arabic
- [ ] RTL layout: nav, cards, text alignment all mirror correctly
- [ ] Arabic font (Cairo) loads and renders
- [ ] Explore page: Arabic landmark names shown alongside English
- [ ] Dictionary: Arabic sign names displayed
- [ ] Write page: Arabic examples appear
- [ ] Language persists across pages (cookie)
- [ ] Logged-in user: language saved to profile preference
- [ ] Mixed content: Arabic UI with English glyph data renders without breaking
- [ ] Toggle back to English → everything returns to LTR
- [ ] Mobile: RTL works on small screens
- [ ] Offline: language toggle works (no server needed, cookie-based)

## Git Commit
```
[Phase 6] Arabic i18n — RTL layout, bilingual UI, language toggle, Cairo font, Arabic data rendering
```
