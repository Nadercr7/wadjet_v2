# Phase 7 — SEO & Social Sharing

## Goal
Make Wadjet visible to search engines and shareable on social media. Currently the app has zero SEO — no OG tags, no sitemap, no robots.txt, no structured data.

## Bugs Fixed
- **M5**: No Open Graph / Twitter Card tags → invisible on social shares
- **M6**: No `robots.txt` or `sitemap.xml`

## New Features
- Per-page OG + Twitter Card meta tags
- JSON-LD structured data (WebApplication + Organization)
- Dynamic `sitemap.xml` with all public routes
- `robots.txt` pointing to sitemap
- Canonical URLs on every page

## Files Created
- `app/templates/partials/seo.html` — reusable SEO partial

## Files Modified
- `app/templates/base.html` — include SEO partial, canonical URL
- `app/templates/landing.html` — page-specific OG tags
- `app/templates/scan.html` — page-specific OG tags
- `app/templates/explore.html` — page-specific OG tags
- `app/templates/chat.html` — page-specific OG tags
- `app/templates/dictionary.html` — page-specific OG tags
- `app/templates/write.html` — page-specific OG tags
- `app/templates/quiz.html` — page-specific OG tags (will become stories.html)
- `app/api/pages.py` — robots.txt + sitemap.xml routes

## Implementation Steps

### Step 1: Create SEO partial
```html
<!-- app/templates/partials/seo.html -->

<!-- Canonical URL -->
<link rel="canonical" href="{{ canonical_url }}">

<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:url" content="{{ canonical_url }}">
<meta property="og:title" content="{{ og_title | default('Wadjet — Egyptian Heritage AI') }}">
<meta property="og:description" content="{{ og_description | default('AI-powered hieroglyph recognition, landmark exploration, and interactive Egyptian stories') }}">
<meta property="og:image" content="{{ og_image | default('/static/images/og-default.png') }}">
<meta property="og:locale" content="{{ 'ar_EG' if lang == 'ar' else 'en_US' }}">
<meta property="og:site_name" content="Wadjet">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ og_title | default('Wadjet — Egyptian Heritage AI') }}">
<meta name="twitter:description" content="{{ og_description | default('AI-powered hieroglyph recognition, landmark exploration, and interactive Egyptian stories') }}">
<meta name="twitter:image" content="{{ og_image | default('/static/images/og-default.png') }}">

<!-- JSON-LD Structured Data -->
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": "Wadjet",
    "description": "AI-powered Egyptian heritage explorer — scan hieroglyphs, discover landmarks, learn through interactive stories",
    "url": "{{ base_url }}",
    "applicationCategory": "EducationalApplication",
    "operatingSystem": "Web",
    "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD"
    },
    "author": {
        "@type": "Organization",
        "name": "Wadjet"
    }
}
</script>
```

### Step 2: Update base.html
```html
<head>
    ...
    {% block seo %}
    {% include "partials/seo.html" %}
    {% endblock %}
    ...
</head>
```

### Step 3: Per-page SEO overrides
Each page template sets its own OG values:
```html
{% block seo %}
{% set og_title = "Scan Hieroglyphs — Wadjet" %}
{% set og_description = "Upload a photo of ancient Egyptian hieroglyphs and get instant AI-powered identification and translation" %}
{% set canonical_url = base_url + "/scan" %}
{% include "partials/seo.html" %}
{% endblock %}
```

### Step 4: robots.txt route
```python
# In app/api/pages.py:
@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return """User-agent: *
Allow: /
Sitemap: https://wadjet.app/sitemap.xml

User-agent: GPTBot
Disallow: /api/
"""
```

### Step 5: Dynamic sitemap
```python
@router.get("/sitemap.xml", response_class=Response)
async def sitemap():
    pages = [
        "/", "/hieroglyphs", "/scan", "/dictionary",
        "/landmarks", "/explore", "/write", "/chat", "/stories"
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        xml += f'  <url><loc>https://wadjet.app{page}</loc><changefreq>weekly</changefreq></url>\n'
    xml += '</urlset>'
    return Response(content=xml, media_type="application/xml")
```

### Step 6: Create default OG image
Create a 1200x630px OG image with:
- Black background (#0A0A0A)
- Gold 𓂀 eye symbol (large, centered)
- "Wadjet" in Playfair Display
- "Egyptian Heritage AI" subtitle
Save to `app/static/images/og-default.png`

## Testing Checklist
- [ ] Share any page URL on Twitter/Facebook → preview card appears
- [ ] Preview shows correct title, description, and image per page
- [ ] `/robots.txt` returns valid robots file
- [ ] `/sitemap.xml` returns valid XML with all public routes
- [ ] Google Rich Results Test → valid structured data
- [ ] Each page has a canonical URL in `<head>`
- [ ] Arabic pages: `og:locale` is `ar_EG`
- [ ] View page source → OG tags visible in `<head>`
- [ ] No duplicate title/description tags

## Git Commit
```
[Phase 7] SEO & social — OG tags, Twitter Cards, sitemap, robots.txt, JSON-LD structured data
```
