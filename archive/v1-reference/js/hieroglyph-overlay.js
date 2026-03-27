/**
 * ═══════════════════════════════════════════════════════════════
 *  Wadjet AI — Hieroglyph Overlay Renderer
 *  H6.7: Real-time bounding box overlay + live results
 * ═══════════════════════════════════════════════════════════════
 *
 *  Renders detection results on a canvas overlay:
 *    - Bounding boxes with confidence
 *    - Gardiner code + transliteration labels
 *    - Reading order numbers
 *    - Translation panel
 *
 *  Public API:
 *    new HieroglyphOverlay(canvas)
 *    .render(result)   → void  — draw pipeline result
 *    .clear()          → void  — clear overlay
 *    .setStyle(opts)   → void  — customize colors/fonts
 *
 *  Globals exposed:
 *    window.HieroglyphOverlay
 */

'use strict';

/**
 * @param {HTMLCanvasElement} canvas — overlay canvas (must be sized to match source)
 * @param {Object} [opts]
 * @param {string} [opts.boxColor]   — bounding box color (default: '#00e5ff')
 * @param {string} [opts.textColor]  — label text color (default: '#ffffff')
 * @param {string} [opts.bgColor]    — label background (default: 'rgba(0,0,0,0.7)')
 * @param {string} [opts.font]       — label font (default: '12px monospace')
 * @param {number} [opts.lineWidth]  — box stroke width (default: 2)
 */
function HieroglyphOverlay(canvas, opts) {
    this._canvas = canvas;
    this._ctx = canvas.getContext('2d');
    opts = opts || {};

    this._boxColor  = opts.boxColor  || '#00e5ff';
    this._textColor = opts.textColor || '#ffffff';
    this._bgColor   = opts.bgColor   || 'rgba(0,0,0,0.7)';
    this._font       = opts.font      || '12px monospace';
    this._lineWidth  = opts.lineWidth || 2;
}

/**
 * Render pipeline result onto the overlay canvas.
 * @param {Object} result — from HieroglyphPipeline.processImage()
 * @param {Object} [opts]
 * @param {boolean} [opts.showConfidence=true]   — show confidence %
 * @param {boolean} [opts.showGardiner=true]     — show Gardiner code
 * @param {boolean} [opts.showTransliteration=true] — show transliteration
 * @param {boolean} [opts.showOrder=true]        — show reading order number
 */
HieroglyphOverlay.prototype.render = function(result, opts) {
    opts = opts || {};
    var showConf    = opts.showConfidence !== false;
    var showGard    = opts.showGardiner !== false;
    var showTranslit = opts.showTransliteration !== false;
    var showOrder   = opts.showOrder !== false;

    var ctx = this._ctx;
    this.clear();

    if (!result || !result.glyphs || !result.glyphs.length) return;

    ctx.lineWidth = this._lineWidth;
    ctx.font = this._font;

    var glyphs = result.glyphs;

    for (var i = 0; i < glyphs.length; i++) {
        var g = glyphs[i];
        var x1 = g.x1, y1 = g.y1, x2 = g.x2, y2 = g.y2;
        var w = x2 - x1, h = y2 - y1;

        // Draw bounding box
        ctx.strokeStyle = this._boxColor;
        ctx.strokeRect(x1, y1, w, h);

        // Build label
        var parts = [];
        if (showOrder) parts.push('#' + (i + 1));
        if (showGard) parts.push(g.gardinerCode || g.gardiner_code);
        if (showConf) {
            var conf = g.classConfidence || g.class_confidence || g.confidence;
            parts.push(Math.round(conf * 100) + '%');
        }
        var label = parts.join(' ');

        // Draw label background
        var metrics = ctx.measureText(label);
        var labelH = 16;
        var labelY = y1 - labelH - 2;
        if (labelY < 0) labelY = y2 + 2; // below box if above is clipped

        ctx.fillStyle = this._bgColor;
        ctx.fillRect(x1, labelY, metrics.width + 8, labelH);

        // Draw label text
        ctx.fillStyle = this._textColor;
        ctx.fillText(label, x1 + 4, labelY + 12);
    }

    // Draw transliteration summary below image
    if (showTranslit && result.transliteration) {
        var summaryY = this._canvas.height - 40;
        ctx.fillStyle = 'rgba(0,0,0,0.8)';
        ctx.fillRect(0, summaryY, this._canvas.width, 40);

        ctx.fillStyle = '#00e5ff';
        ctx.font = '14px monospace';
        ctx.fillText(
            'MdC: ' + result.transliteration.substring(0, 80),
            10, summaryY + 16
        );

        // Translation if available
        if (result.translationEn) {
            ctx.fillStyle = '#ffffff';
            ctx.font = '12px sans-serif';
            ctx.fillText(
                'EN: ' + result.translationEn.substring(0, 80),
                10, summaryY + 32
            );
        }
    }
};

/**
 * Clear the overlay canvas.
 */
HieroglyphOverlay.prototype.clear = function() {
    this._ctx.clearRect(0, 0, this._canvas.width, this._canvas.height);
};

/**
 * Update overlay style.
 */
HieroglyphOverlay.prototype.setStyle = function(opts) {
    if (opts.boxColor) this._boxColor = opts.boxColor;
    if (opts.textColor) this._textColor = opts.textColor;
    if (opts.bgColor) this._bgColor = opts.bgColor;
    if (opts.font) this._font = opts.font;
    if (opts.lineWidth) this._lineWidth = opts.lineWidth;
};

/* ── Expose globally ────────────────────────────────── */
window.HieroglyphOverlay = HieroglyphOverlay;
