# DESIGN SYSTEM — Visual Identity, Logo, Loading Animation

> Black & Gold Egyptian heritage aesthetic. Non-negotiable color palette.

---

## Color Palette (Locked)

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `--color-night` | `#0A0A0A` | 10, 10, 10 | Page background |
| `--color-surface` | `#141414` | 20, 20, 20 | Cards, sections |
| `--color-gold` | `#D4AF37` | 212, 175, 55 | Primary accent |
| `--color-gold-light` | `#E5C76B` | 229, 199, 107 | Hover states |
| `--color-gold-dark` | `#B8962E` | 184, 150, 46 | Active states |
| `--color-sand` | `#C4A265` | 196, 162, 101 | Muted text |
| `--color-ivory` | `#F5F0E8` | 245, 240, 232 | Primary text |
| `--color-dust` | `#8B7355` | 139, 115, 85 | Disabled text |

### Contrast Ratios (WCAG AA)
- Gold on Night: **8.2:1** ✓ (AAA)
- Ivory on Night: **16.4:1** ✓ (AAA)
- Sand on Night: **5.8:1** ✓ (AA)
- Dust on Night: **4.0:1** ✓ (AA large text)

---

## Typography

| Role | Font | Weights | Fallback |
|------|------|---------|----------|
| Headings | Playfair Display | 600, 700 | Georgia, serif |
| Body | Inter | 400, 500, 600 | system-ui, sans-serif |
| Hieroglyphs | Noto Sans Egyptian Hieroglyphs | 400 | serif |
| Monospace | JetBrains Mono | 400 | monospace |

---

## Logo Specification — W-as-Serpent

### Concept
The letter **W** formed by the body of an Egyptian **uraeus** (rearing cobra). The serpent's body creates the three strokes of the W, with the cobra's hood at one peak.

### Design References
| Brand | Quality to Borrow |
|-------|-------------------|
| Nike swoosh | Single-stroke simplicity, instant recognition |
| Chanel CC | Elegant interlocking, luxury feel |
| Apple | Clean geometry, works at any size |
| Versace Medusa | Mythological creature as logo, gold on dark |

### Logo Variants

| Variant | Background | Foreground | File |
|---------|-----------|------------|------|
| Primary | `#0A0A0A` | `#D4AF37` | `logo.svg` |
| Light | `#0A0A0A` | `#F5F0E8` | `logo-light.svg` |
| Reversed | `#D4AF37` | `#0A0A0A` | `logo-reversed.svg` |
| Mono | transparent | `#FFFFFF` | `logo-mono.svg` |

### Size Requirements

| Size | Usage | Notes |
|------|-------|-------|
| 16×16 | Favicon | Must be a recognizable W shape |
| 32×32 | Browser tab | Slightly more detail |
| 48×48 | App icon small | Serpent detail visible |
| 128×128 | Dashboard, about | Full detail |
| 180×180 | Apple touch icon | With safe area padding |
| 192×192 | Android PWA | With safe area padding |
| 512×512 | Splash screen | Full detail + subtle texture |
| 1200×630 | OpenGraph | Logo centered + "Wadjet" text |

### SVG Technical Requirements
- No embedded raster images
- No CSS `<style>` blocks (use inline attributes for compatibility)
- Viewbox: `0 0 512 512` (square, scalable)
- Paths use even-odd fill rule
- Stroke width: proportional (scales cleanly)
- Maximum 10 paths (simple geometry)
- File size: < 5KB

### Design Questions for User

> These must be answered before logo creation:

1. **Serpent style**: Geometric/abstract (like Versace) or organic/realistic (like a hieroglyph)?
2. **W formation**: Should the W be formed by one continuous serpent body, or two serpents mirroring?
3. **Detail level**: Minimal (2-3 strokes) or detailed (scales, hood, eye visible)?
4. **Additional element**: Include the Eye of Horus somewhere in the mark? Or pure W-serpent?
5. **Wordmark**: Should "WADJET" text accompany the mark, or is the symbol standalone?
6. **Motion reference**: Should the serpent appear coiled/static or in motion (striking pose)?

---

## Loading Animation Specification

### Sequence (Total: ~2.5 seconds)

```
0.0s ─── Logo SVG appears (opacity 0)
0.1s ─── Stroke begins drawing (dasharray animation)
0.1s-1.5s ─ Stroke completes path (ease-in-out)
1.5s ─── Fill fades in (gold gradient)
1.5s-1.8s ─ Gold particles shimmer around logo
1.8s ─── "WADJET" text fades up below logo
1.8s-2.2s ─ Text fully visible
2.2s ─── Check if page loaded
2.2s-2.5s ─ Overlay fades out + slight scale-up
2.5s ─── Content visible, overlay removed from DOM
```

### CSS Implementation

```css
/* Loading overlay */
.loading-overlay {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: var(--color-night);
    transition: opacity 0.3s ease, transform 0.3s ease;
}

.loading-overlay.done {
    opacity: 0;
    transform: scale(1.05);
    pointer-events: none;
}

/* SVG stroke animation */
.loading-logo path {
    stroke: var(--color-gold);
    stroke-width: 2;
    fill: transparent;
    stroke-dasharray: 1000;
    stroke-dashoffset: 1000;
    animation: draw-logo 1.4s ease-in-out forwards;
}

@keyframes draw-logo {
    to { stroke-dashoffset: 0; }
}

/* Fill fade-in after stroke */
.loading-logo path {
    animation: draw-logo 1.4s ease-in-out forwards,
               fill-gold 0.3s ease 1.4s forwards;
}

@keyframes fill-gold {
    to { fill: var(--color-gold); }
}

/* Text fade-up */
.loading-text {
    opacity: 0;
    transform: translateY(10px);
    animation: fade-up 0.4s ease 1.8s forwards;
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    color: var(--color-gold);
    letter-spacing: 0.3em;
}

/* Gold particles (pseudo-elements or small dots) */
.loading-particles {
    position: absolute;
    width: 200px;
    height: 200px;
    animation: shimmer-particles 1s ease 1.5s forwards;
}

@keyframes shimmer-particles {
    0% { opacity: 0; }
    50% { opacity: 0.8; }
    100% { opacity: 0; }
}
```

### Alpine.js Integration

```html
<!-- In base.html, before all other content -->
<div x-data="{ loaded: false }"
     x-init="setTimeout(() => { if(document.readyState === 'complete') loaded = true; else window.addEventListener('load', () => loaded = true) }, 2200)"
     x-show="!loaded"
     x-transition:leave="transition ease-in duration-300"
     x-transition:leave-start="opacity-100"
     x-transition:leave-end="opacity-0"
     class="loading-overlay">
    
    <!-- SVG Logo -->
    <div class="loading-logo">
        <!-- logo SVG paths here -->
    </div>
    
    <!-- Brand text -->
    <span class="loading-text">WADJET</span>
</div>

<!-- Fallback: hide overlay if JS disabled -->
<noscript>
    <style>.loading-overlay { display: none !important; }</style>
</noscript>
```

### Scan-Specific Loading States

```html
<!-- In scan.html, during processing -->
<div x-show="scanning" class="scan-progress">
    <div class="loading-logo loading-logo--small"><!-- mini logo --></div>
    <div class="scan-steps">
        <div :class="step >= 1 ? 'text-gold' : 'text-dust'">
            <span class="scan-step-icon">𓁹</span> Detecting hieroglyphs...
        </div>
        <div :class="step >= 2 ? 'text-gold' : 'text-dust'">
            <span class="scan-step-icon">𓊖</span> Classifying symbols...
        </div>
        <div :class="step >= 3 ? 'text-gold' : 'text-dust'">
            <span class="scan-step-icon">𓂀</span> Translating inscription...
        </div>
    </div>
</div>
```

---

## Existing CSS Animations (in `input.css`)

Already available — reuse these:

| Name | Effect | Where Used |
|------|--------|-----------|
| `shimmer` | Scanning line sweep | Scan page |
| `fade-up` | Element entry | General |
| `pulse-gold` | Gold glow pulse | CTAs |
| `btn-shimmer` | Button edge glow | Buttons |
| `gradient-sweep` | Animated gradient text | Headings |
| `border-beam` | Orbiting border light | Cards |
| `meteor` | Falling gold streaks | Landing |
| `dot-glow` | Pulsing dot | Status indicators |
| `shine` | Border sweep | Cards |

### New Animations Needed

| Name | Effect | Where Used |
|------|--------|-----------|
| `draw-logo` | SVG stroke-dashoffset → 0 | Loading screen |
| `fill-gold` | Transparent → gold fill | Loading screen |
| `shimmer-particles` | Gold particle burst | Loading screen |
| `scan-pulse` | Step-by-step pulse | Scan processing |

---

## Component Library Reference

### Existing Components (in `input.css @layer components`)

| Class | Description |
|-------|------------|
| `.btn-gold` | Primary gold CTA button |
| `.btn-ghost` | Ghost/outline button |
| `.card` | Dark surface card |
| `.card-glow` | Card with gold hover glow |
| `.badge-gold` | Gold badge |
| `.input` | Form input (gold focus ring) |
| `.text-gold-animated` | Animated gradient text |
| `.dot-pattern` | Background dot overlay |
| `.meteor` | Meteor streak element |
| `.border-beam` | Border beam animation |

### New Components Needed

| Class | Description | Phase |
|-------|------------|-------|
| `.loading-overlay` | Full-screen loading container | P7 |
| `.loading-logo` | SVG logo with stroke animation | P7 |
| `.loading-text` | Brand text fade-in | P7 |
| `.scan-progress` | Scan step-by-step progress | P3 |
| `.google-btn` | Google sign-in button styling | P2 |
| `.story-image` | Story illustration with frame | P4 |
