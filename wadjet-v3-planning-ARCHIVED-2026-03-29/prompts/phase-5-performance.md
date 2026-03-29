# Phase 5 — Performance Optimization

## Goal
Optimize caching, loading, and rendering so the app is fast on slow networks and doesn't re-download 42MB of ML models unnecessarily.

## Bugs Fixed
- **H8**: Model cache uses network-first (re-downloads 42MB when online)
- **M7**: No `loading="lazy"` on images
- **M9**: 260 explore cards load all at once (no pagination)

## Files Modified
- `app/static/sw.js` — cache-first for models
- `app/templates/explore.html` — HTMX infinite scroll
- `app/templates/scan.html` — lazy images
- `app/templates/landing.html` — lazy images
- `app/templates/landmarks.html` — lazy images
- `app/api/explore.py` — add pagination endpoint

## Implementation Steps

### Step 1: Fix H8 — Cache-first for ML models
Already partially done in Phase 2. Verify `sw.js` uses `cacheFirst()` for model paths:
```javascript
if (isModel) {
    event.respondWith(cacheFirst(event.request, MODEL_CACHE));
    return;
}
```

### Step 2: Fix M7 — Lazy loading images
Add `loading="lazy"` to all `<img>` tags that are below the fold:
```html
<!-- Every image except the hero/above-fold: -->
<img src="..." loading="lazy" alt="...">
```

Templates to update:
- `explore.html` — all landmark card images
- `landmarks.html` — all landmark images
- `landing.html` — images below first viewport
- `scan.html` — result images
- `dictionary.html` — glyph images if any

### Step 3: Fix M9 — Paginate explore cards
Instead of loading all 260 landmarks at once, load 20 initially with HTMX infinite scroll.

**Backend** — `app/api/explore.py`:
```python
@router.get("/api/explore/cards")
async def explore_cards(page: int = 1, per_page: int = 20, q: str = ""):
    """Return paginated landmark cards as HTML partial."""
    sites = load_sites()  # existing function
    if q:
        sites = [s for s in sites if q.lower() in s['name'].lower()]

    start = (page - 1) * per_page
    end = start + per_page
    page_sites = sites[start:end]
    has_more = end < len(sites)

    return templates.TemplateResponse("partials/explore_cards.html", {
        "request": request,
        "sites": page_sites,
        "next_page": page + 1 if has_more else None,
    })
```

**Frontend** — `explore.html`:
```html
<!-- Initial cards container -->
<div id="cards-container">
    {% include "partials/explore_cards.html" %}
</div>
```

**Partial** — `partials/explore_cards.html`:
```html
{% for site in sites %}
<div class="card ...">
    <img src="{{ site.image }}" loading="lazy" alt="{{ site.name }}">
    <h3>{{ site.name }}</h3>
    ...
</div>
{% endfor %}

{% if next_page %}
<!-- Infinite scroll trigger -->
<div hx-get="/api/explore/cards?page={{ next_page }}"
     hx-trigger="revealed"
     hx-swap="afterend"
     hx-target="this"
     class="h-20 flex items-center justify-center">
    <div class="animate-spin w-6 h-6 border-2 border-gold border-t-transparent rounded-full"></div>
</div>
{% endif %}
```

### Step 4: Preload critical fonts
Add preload for the fonts used above the fold:
```html
<link rel="preload" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap" as="style">
```

## Testing Checklist
- [ ] Network tab: ML models NOT re-fetched when page loads online (cache-first)
- [ ] First load: models download and cache correctly
- [ ] Subsequent loads: models served from cache (0ms network)
- [ ] Explore page: only ~20 cards initially visible
- [ ] Scroll to bottom → next 20 cards load automatically (HTMX trigger)
- [ ] Continue scrolling → cards keep loading until all 260 shown
- [ ] Search + scroll: filtered results also paginate
- [ ] Images below fold: `loading="lazy"` attribute present in HTML
- [ ] Network tab: below-fold images don't load until scrolled into view
- [ ] Lighthouse Performance score > 85
- [ ] No layout shifts from lazy-loaded images (use width/height or aspect-ratio)

## Git Commit
```
[Phase 5] Performance — cache-first models, lazy loading, HTMX infinite scroll pagination
```
