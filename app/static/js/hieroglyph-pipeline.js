/**
 * ═══════════════════════════════════════════════════════════════
 *  Wadjet AI — Hieroglyph Browser Pipeline (ONNX-Unified)
 *  All browser ML via ONNX Runtime Web — ZERO TF.js dependency
 * ═══════════════════════════════════════════════════════════════
 *
 *  Stages (all client-side except translation):
 *    1. Detection:        ONNX Runtime Web → bounding boxes (YOLOv8, NCHW)
 *    2. Classification:   ONNX Runtime Web → Gardiner codes (MobileNetV3, NCHW)
 *    3. Transliteration:  JS → MdC notation
 *    4. Translation:      Server API (POST /api/scan)
 *
 *  Dependencies:
 *    - onnxruntime-web >= 1.18.0 (single runtime for ALL models)
 *
 *  Globals exposed:
 *    window.HieroglyphPipeline
 *    window.HieroglyphPipelineState
 */

'use strict';

/* ── States ─────────────────────────────────────────── */

var HieroglyphPipelineState = Object.freeze({
    IDLE:       'idle',
    LOADING:    'loading',
    READY:      'ready',
    PROCESSING: 'processing',
    ERROR:      'error'
});

/* ── HieroglyphPipeline ─────────────────────────────── */

/**
 * @param {Object} opts
 * @param {string} [opts.detectorUrl]      — glyph_detector_uint8.onnx URL
 * @param {string} [opts.classifierUrl]    — hieroglyph_classifier_uint8.onnx URL (ONNX)
 * @param {string} [opts.labelMapUrl]      — label_mapping.json URL
 * @param {string} [opts.translationApi]   — Server endpoint for translation
 * @param {number} [opts.detConfThreshold] — Detection confidence (default: 0.15)
 * @param {number} [opts.nmsIouThreshold]  — NMS IoU threshold (default: 0.45)
 * @param {number} [opts.classInputSize]   — Classification input size (default: 128)
 * @param {Function} [opts.onStateChange]  — State change callback
 * @param {Function} [opts.onProgress]     — Loading progress callback (0–1)
 */
function HieroglyphPipeline(opts) {
    opts = opts || {};

    // URLs (v2 paths — models served at /models/ mount)
    this._detectorUrl    = opts.detectorUrl    || '/models/hieroglyph/detector/glyph_detector_uint8.onnx';
    this._classifierUrl  = opts.classifierUrl  || '/models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx';
    this._labelMapUrl    = opts.labelMapUrl    || '/models/hieroglyph/label_mapping.json';
    this._translationApi = opts.translationApi || '/api/scan';

    // Config
    this._detConf    = opts.detConfThreshold || 0.15;
    this._nmsIou     = opts.nmsIouThreshold  || 0.45;
    this._classSize  = opts.classInputSize   || 128;
    this._detSize    = 640;

    // Callbacks
    this._onStateChange = opts.onStateChange || function() {};
    this._onProgress    = opts.onProgress    || function() {};

    // Internal state
    this._state             = HieroglyphPipelineState.IDLE;
    this._detectorSession   = null;  // ONNX detector (NCHW)
    this._classifierSession = null;  // ONNX classifier (NCHW)
    this._labelMap          = null;  // { idx_to_gardiner: {0: 'A55', ...} }
    this._gardinerMap       = null;  // gardiner_code → transliteration info
    this._cameraRunning     = false;

    // Build static Gardiner mapping for transliteration
    this._buildGardinerMap();
}

/* ── State management ───────────────────────────────── */

HieroglyphPipeline.prototype._setState = function(state) {
    var prev = this._state;
    this._state = state;
    this._onStateChange(state, prev);
};

HieroglyphPipeline.prototype.getState = function() {
    return this._state;
};

/* ── Initialization ─────────────────────────────────── */

HieroglyphPipeline.prototype.init = async function() {
    this._setState(HieroglyphPipelineState.LOADING);

    try {
        // 1. Load label mapping
        this._onProgress(0);
        var resp = await fetch(this._labelMapUrl);
        if (!resp.ok) throw new Error('Failed to load label mapping: ' + resp.status);
        this._labelMap = await resp.json();
        this._onProgress(0.1);

        // 2. Load ONNX detection model
        if (typeof ort === 'undefined') {
            throw new Error('ONNX Runtime Web not loaded. Add onnxruntime-web CDN.');
        }
        this._detectorSession = await ort.InferenceSession.create(this._detectorUrl, {
            executionProviders: ['wasm'],
            graphOptimizationLevel: 'all'
        });
        this._onProgress(0.5);

        // 3. Load ONNX classification model
        this._classifierSession = await ort.InferenceSession.create(this._classifierUrl, {
            executionProviders: ['wasm'],
            graphOptimizationLevel: 'all'
        });
        this._onProgress(0.9);

        // 4. Warm up both models
        await this._warmup();
        this._onProgress(1.0);

        this._setState(HieroglyphPipelineState.READY);
    } catch (err) {
        this._setState(HieroglyphPipelineState.ERROR);
        throw err;
    }
};

HieroglyphPipeline.prototype._warmup = async function() {
    // Warmup detector (NCHW)
    var dummyDet = new ort.Tensor('float32', new Float32Array(1 * 3 * 640 * 640), [1, 3, 640, 640]);
    var detFeeds = {};
    detFeeds[this._detectorSession.inputNames[0]] = dummyDet;
    await this._detectorSession.run(detFeeds);

    // Warmup classifier (NCHW)
    var s = this._classSize;
    var dummyCls = new ort.Tensor('float32', new Float32Array(1 * 3 * s * s), [1, 3, s, s]);
    var clsFeeds = {};
    clsFeeds[this._classifierSession.inputNames[0]] = dummyCls;
    await this._classifierSession.run(clsFeeds);
};

/* ── Stage 1: Detection (ONNX NCHW) ────────────────── */

HieroglyphPipeline.prototype.detect = async function(source) {
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');
    var srcW, srcH;

    if (source instanceof HTMLVideoElement) {
        srcW = source.videoWidth;
        srcH = source.videoHeight;
    } else {
        srcW = source.naturalWidth || source.width;
        srcH = source.naturalHeight || source.height;
    }

    // Letterbox resize to 640×640
    var scale = Math.min(this._detSize / srcW, this._detSize / srcH);
    var newW = Math.round(srcW * scale);
    var newH = Math.round(srcH * scale);
    var padX = (this._detSize - newW) / 2;
    var padY = (this._detSize - newH) / 2;

    canvas.width = this._detSize;
    canvas.height = this._detSize;
    ctx.fillStyle = '#808080';
    ctx.fillRect(0, 0, this._detSize, this._detSize);
    ctx.drawImage(source, padX, padY, newW, newH);

    // Convert to NCHW float32 tensor (for YOLOv8)
    var imgData = ctx.getImageData(0, 0, this._detSize, this._detSize).data;
    var floats = new Float32Array(3 * this._detSize * this._detSize);
    var pixelCount = this._detSize * this._detSize;
    for (var i = 0; i < pixelCount; i++) {
        floats[i]                  = imgData[i * 4]     / 255.0;
        floats[pixelCount + i]     = imgData[i * 4 + 1] / 255.0;
        floats[2 * pixelCount + i] = imgData[i * 4 + 2] / 255.0;
    }

    var inputTensor = new ort.Tensor('float32', floats, [1, 3, this._detSize, this._detSize]);
    var feeds = {};
    feeds[this._detectorSession.inputNames[0]] = inputTensor;
    var output = await this._detectorSession.run(feeds);
    var rawOutput = output[this._detectorSession.outputNames[0]];

    // Parse YOLO output: [1, 5, 8400]
    var data = rawOutput.data;
    var numBoxes = rawOutput.dims[2];
    var boxes = [];

    for (var b = 0; b < numBoxes; b++) {
        var conf = data[4 * numBoxes + b];
        if (conf < this._detConf) continue;

        var cx = data[0 * numBoxes + b];
        var cy = data[1 * numBoxes + b];
        var bw = data[2 * numBoxes + b];
        var bh = data[3 * numBoxes + b];

        var x1 = ((cx - bw / 2) - padX) / scale;
        var y1 = ((cy - bh / 2) - padY) / scale;
        var x2 = ((cx + bw / 2) - padX) / scale;
        var y2 = ((cy + bh / 2) - padY) / scale;

        x1 = Math.max(0, Math.min(srcW, x1));
        y1 = Math.max(0, Math.min(srcH, y1));
        x2 = Math.max(0, Math.min(srcW, x2));
        y2 = Math.max(0, Math.min(srcH, y2));

        if (x2 - x1 < 5 || y2 - y1 < 5) continue;
        boxes.push({ x1: x1, y1: y1, x2: x2, y2: y2, confidence: conf });
    }

    boxes = this._nms(boxes, this._nmsIou);

    return {
        boxes: boxes,
        preprocessInfo: { scale: scale, padX: padX, padY: padY, srcW: srcW, srcH: srcH }
    };
};

HieroglyphPipeline.prototype._nms = function(boxes, iouThreshold) {
    boxes.sort(function(a, b) { return b.confidence - a.confidence; });
    var keep = [];
    var suppressed = new Set();

    for (var i = 0; i < boxes.length; i++) {
        if (suppressed.has(i)) continue;
        keep.push(boxes[i]);
        for (var j = i + 1; j < boxes.length; j++) {
            if (suppressed.has(j)) continue;
            if (this._iou(boxes[i], boxes[j]) > iouThreshold) {
                suppressed.add(j);
            }
        }
    }
    return keep;
};

HieroglyphPipeline.prototype._iou = function(a, b) {
    var x1 = Math.max(a.x1, b.x1);
    var y1 = Math.max(a.y1, b.y1);
    var x2 = Math.min(a.x2, b.x2);
    var y2 = Math.min(a.y2, b.y2);
    var inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
    var areaA = (a.x2 - a.x1) * (a.y2 - a.y1);
    var areaB = (b.x2 - b.x1) * (b.y2 - b.y1);
    return inter / (areaA + areaB - inter + 1e-6);
};

/* ── Stage 2: Classification (ONNX NCHW) ───────────── */

HieroglyphPipeline.prototype.classify = async function(source, boxes) {
    if (!boxes.length) return [];

    var size = this._classSize;
    var results = [];
    var i2g = this._labelMap.idx_to_gardiner || this._labelMap;
    var inputName = this._classifierSession.inputNames[0];

    // Process each crop through ONNX classifier
    for (var i = 0; i < boxes.length; i++) {
        var box = boxes[i];
        var cropCanvas = document.createElement('canvas');
        cropCanvas.width = size;
        cropCanvas.height = size;
        var ctx = cropCanvas.getContext('2d');

        // Draw cropped region resized to classifier input
        ctx.drawImage(source,
            box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1,
            0, 0, size, size
        );

        // Convert to NCHW float32 (PyTorch-origin ONNX model)
        var imgData = ctx.getImageData(0, 0, size, size).data;
        var floats = new Float32Array(3 * size * size);
        var pixelCount = size * size;
        for (var p = 0; p < pixelCount; p++) {
            floats[p]                    = imgData[p * 4]     / 255.0;  // R plane
            floats[pixelCount + p]       = imgData[p * 4 + 1] / 255.0;  // G plane
            floats[2 * pixelCount + p]   = imgData[p * 4 + 2] / 255.0;  // B plane
        }

        var inputTensor = new ort.Tensor('float32', floats, [1, 3, size, size]);
        var feeds = {};
        feeds[inputName] = inputTensor;
        var output = await this._classifierSession.run(feeds);
        var probs = output[this._classifierSession.outputNames[0]].data;

        // Find argmax
        var maxIdx = 0;
        var maxProb = probs[0];
        for (var j = 1; j < probs.length; j++) {
            if (probs[j] > maxProb) {
                maxProb = probs[j];
                maxIdx = j;
            }
        }

        var gardiner = i2g[String(maxIdx)] || ('UNK_' + maxIdx);
        results.push({
            x1: box.x1, y1: box.y1, x2: box.x2, y2: box.y2,
            confidence: box.confidence,
            classId: maxIdx,
            gardinerCode: gardiner,
            classConfidence: maxProb
        });
    }

    return results;
};

/* ── Stage 3: Transliteration ───────────────────────── */

HieroglyphPipeline.prototype.transliterate = function(glyphs) {
    if (!glyphs.length) {
        return { transliteration: '', gardinerSequence: '', direction: 'RTL' };
    }

    var lines = this._clusterIntoLines(glyphs);
    var direction = 'RTL';
    var mdc_parts = [];
    var gardiner_parts = [];

    for (var li = 0; li < lines.length; li++) {
        var line = lines[li];
        line.sort(function(a, b) { return b.x1 - a.x1; });

        var lineTranslit = [];
        var lineGardiner = [];
        for (var gi = 0; gi < line.length; gi++) {
            var g = line[gi];
            var code = g.gardinerCode;
            var info = this._gardinerMap[code];
            if (info) {
                if (info.isDeterminative) {
                    lineTranslit.push('<' + (info.detClass || code) + '>');
                } else {
                    lineTranslit.push(info.transliteration || code);
                }
            } else {
                lineTranslit.push('[' + code + ']');
            }
            lineGardiner.push(code);
        }
        mdc_parts.push(lineTranslit.join('-'));
        gardiner_parts.push(lineGardiner.join('-'));
    }

    return {
        transliteration: mdc_parts.join(' '),
        gardinerSequence: gardiner_parts.join(' '),
        direction: direction,
        numLines: lines.length,
        numGlyphs: glyphs.length
    };
};

HieroglyphPipeline.prototype._clusterIntoLines = function(glyphs) {
    if (!glyphs.length) return [];

    var sorted = glyphs.slice().sort(function(a, b) {
        return ((a.y1 + a.y2) / 2) - ((b.y1 + b.y2) / 2);
    });

    var lines = [[sorted[0]]];
    for (var i = 1; i < sorted.length; i++) {
        var glyph = sorted[i];
        var lastLine = lines[lines.length - 1];
        var lastGlyph = lastLine[lastLine.length - 1];

        var overlapY = Math.min(glyph.y2, lastGlyph.y2) - Math.max(glyph.y1, lastGlyph.y1);
        var minH = Math.min(glyph.y2 - glyph.y1, lastGlyph.y2 - lastGlyph.y1);
        if (overlapY > minH * 0.3) {
            lastLine.push(glyph);
        } else {
            lines.push([glyph]);
        }
    }
    return lines;
};

/* ── Stage 4: Translation (Server API) ──────────────── */

HieroglyphPipeline.prototype.translate = async function(mdc) {
    if (!mdc) return { english: '', arabic: '', error: '' };

    try {
        var resp = await fetch(this._translationApi, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transliteration: mdc })
        });
        if (!resp.ok) throw new Error('Translation API error: ' + resp.status);
        return await resp.json();
    } catch (err) {
        return { english: '', arabic: '', error: err.message };
    }
};

/* ── Full Pipeline ──────────────────────────────────── */

HieroglyphPipeline.prototype.processImage = async function(source, opts) {
    opts = opts || {};
    var doTranslate = opts.translate || false;
    this._setState(HieroglyphPipelineState.PROCESSING);

    var result = {
        numDetections: 0,
        glyphs: [],
        transliteration: '',
        gardinerSequence: '',
        readingDirection: 'RTL',
        translationEn: '',
        translationAr: '',
        translationError: '',
        timing: { detectionMs: 0, classificationMs: 0, transliterationMs: 0, translationMs: 0, totalMs: 0 }
    };

    var tTotal = performance.now();

    // Stage 1: Detection
    var t0 = performance.now();
    var detResult = await this.detect(source);
    result.timing.detectionMs = performance.now() - t0;
    result.numDetections = detResult.boxes.length;

    if (!detResult.boxes.length) {
        result.timing.totalMs = performance.now() - tTotal;
        this._setState(HieroglyphPipelineState.READY);
        return result;
    }

    // Stage 2: Classification
    t0 = performance.now();
    result.glyphs = await this.classify(source, detResult.boxes);
    result.timing.classificationMs = performance.now() - t0;

    // Stage 3: Transliteration
    t0 = performance.now();
    var translit = this.transliterate(result.glyphs);
    result.timing.transliterationMs = performance.now() - t0;
    result.transliteration = translit.transliteration;
    result.gardinerSequence = translit.gardinerSequence;
    result.readingDirection = translit.direction;

    // Stage 4: Translation (optional, server-side)
    if (doTranslate && result.transliteration) {
        t0 = performance.now();
        var trans = await this.translate(result.transliteration);
        result.timing.translationMs = performance.now() - t0;
        result.translationEn = trans.english || '';
        result.translationAr = trans.arabic || '';
        result.translationError = trans.error || '';
    }

    result.timing.totalMs = performance.now() - tTotal;
    this._setState(HieroglyphPipelineState.READY);
    return result;
};

/* ── Real-Time Camera Support ───────────────────────── */

/**
 * Start continuous detection on a video element.
 * Uses setTimeout pattern from face-api.js (not requestAnimationFrame).
 * @param {HTMLVideoElement} video
 * @param {HTMLCanvasElement} overlayCanvas
 * @param {Object} opts
 * @param {Function} opts.onDetections — callback(boxes) after each frame
 * @param {Function} opts.onError — callback(error)
 */
HieroglyphPipeline.prototype.startCameraLoop = function(video, overlayCanvas, opts) {
    opts = opts || {};
    var self = this;
    this._cameraRunning = true;

    var ctx = overlayCanvas.getContext('2d');

    async function onPlay() {
        if (!self._cameraRunning) return;
        if (video.paused || video.ended) return setTimeout(onPlay, 100);

        try {
            var detResult = await self.detect(video);
            var boxes = detResult.boxes;

            overlayCanvas.width = video.videoWidth;
            overlayCanvas.height = video.videoHeight;
            ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

            ctx.strokeStyle = '#D4AF37';
            ctx.lineWidth = 2;
            ctx.font = '12px Inter, sans-serif';
            ctx.fillStyle = '#D4AF37';

            for (var i = 0; i < boxes.length; i++) {
                var b = boxes[i];
                ctx.strokeRect(b.x1, b.y1, b.x2 - b.x1, b.y2 - b.y1);
                ctx.fillText(Math.round(b.confidence * 100) + '%', b.x1, b.y1 - 4);
            }

            if (opts.onDetections) opts.onDetections(boxes);
        } catch (err) {
            if (opts.onError) opts.onError(err);
        }

        setTimeout(onPlay);
    }

    setTimeout(onPlay);
};

HieroglyphPipeline.prototype.stopCameraLoop = function() {
    this._cameraRunning = false;
};

/**
 * Capture current video frame and run full classification pipeline.
 */
HieroglyphPipeline.prototype.captureAndClassify = async function(video) {
    var canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    // Use canvas directly as source for processImage
    return this.processImage(canvas);
};

/* ── Cleanup ────────────────────────────────────────── */

HieroglyphPipeline.prototype.dispose = function() {
    this._cameraRunning = false;
    this._detectorSession = null;
    this._classifierSession = null;
    this._setState(HieroglyphPipelineState.IDLE);
};

/* ── Gardiner Mapping (Transliteration Data) ────────── */

HieroglyphPipeline.prototype._buildGardinerMap = function() {
    var m = {};

    // Uniliterals (single consonant signs)
    var uni = {
        'G1':'A','M17':'i','M18':'y','D36':'a','G43':'w',
        'D58':'b','Q3':'p','I9':'f','G17':'m','N35':'n',
        'D21':'r','O4':'h','V28':'H','Aa1':'x',
        'S29':'s','N37':'S','D46':'d','I10':'D','X1':'t',
        'V13':'T','V31':'k','W11':'g','O34':'s'
    };
    for (var code in uni) {
        m[code] = { transliteration: uni[code], isDeterminative: false };
    }

    // Biliterals
    var bi = {
        'D4':'ir','D28':'kA','D34':'aS','D35':'nw','D39':'mH',
        'D52':'mt','D53':'mw','D56':'rd','D62':'mt',
        'E34':'SA','F4':'kA','F13':'wp','F16':'db','F18':'ns',
        'F22':'Hw','F26':'Hn','F30':'sD','F31':'ms','F32':'xm','F34':'ib','F40':'Aw',
        'G10':'tA','G21':'nH','G25':'Ax','G26':'bA','G29':'bA',
        'G35':'aq','G36':'wr','G39':'sA','G40':'pA',
        'M1':'xt','M3':'Ht','M8':'SA','M12':'xA','M16':'HA',
        'M20':'sw','M23':'sw','M40':'is','M42':'sn','M44':'sp',
        'N1':'pt','N18':'iw','N19':'iw','N26':'Dw','N29':'qA','N36':'mr','N41':'Hm',
        'O1':'pr','O11':'aH','O29':'aA',
        'P1':'dp','Q1':'st',
        'T21':'Hq','T22':'Ss','T30':'nm',
        'U1':'mA','U7':'mr','U15':'tm','U28':'DA','U33':'ti',
        'V4':'wA','V6':'Ss','V16':'sA','V22':'mn','V24':'wD','V30':'nb',
        'W14':'Hz','W19':'mi','W22':'ab','W24':'nw',
        'X8':'di','Y3':'sS','Y5':'mn',
        'Aa27':'nD','Aa28':'qd'
    };
    for (var code in bi) {
        m[code] = { transliteration: bi[code], isDeterminative: false };
    }

    // Triliterals
    var tri = {
        'D10':'wDAt','D19':'fnD','D60':'wab',
        'E9':'sAb','E17':'mAi','E23':'rwD',
        'F9':'nSm','F12':'wsr','F21':'sDm','F23':'xnt','F29':'sti','F35':'nfr',
        'G4':'tyw','G14':'mwt','G37':'nDs','G50':'pAq',
        'H6':'mAat','I5':'Hfn',
        'L1':'xpr',
        'M4':'rnp','M26':'Sma','M29':'nDm','M41':'Hsa',
        'N14':'sbA','N24':'spAt','N25':'xAst','N30':'Dba','N31':'wAt',
        'O28':'iwn','O31':'Htp','O50':'Ssp',
        'P6':'mxnt','P8':'xAw','P13':'xrw',
        'Q7':'snTr',
        'R4':'Htp','R8':'nTr',
        'S24':'TAw','S28':'Dba','S34':'anx','S42':'wAs',
        'T14':'qmA','T20':'nmt','T28':'sfx',
        'U35':'nmt',
        'V7':'snT','V25':'wAD',
        'W15':'iab','W18':'kAb','W25':'ini',
        'X6':'pAt',
        'Y1':'mDAt','Y2':'mnhd',
        'Z11':'imi',
        'Aa15':'wDa'
    };
    for (var code in tri) {
        m[code] = { transliteration: tri[code], isDeterminative: false };
    }

    // Logograms
    var logo = {
        'E1':'kA','G5':'Hr','N5':'ra','N16':'tA','N17':'tA',
        'O49':'niwt','O51':'niwt','Z1':'|'
    };
    for (var code in logo) {
        if (!m[code]) m[code] = { transliteration: logo[code], isDeterminative: false };
    }

    // Determinatives
    var det = {
        'D54':'walking','G7':'divine','N2':'sky','Z7':'W'
    };
    for (var code in det) {
        m[code] = { transliteration: '', isDeterminative: true, detClass: det[code] };
    }

    // Uncertain/rare signs
    var uncertain = ['A55','D156','M195','P98','Aa26'];
    for (var u = 0; u < uncertain.length; u++) {
        if (!m[uncertain[u]]) {
            m[uncertain[u]] = { transliteration: uncertain[u], isDeterminative: false };
        }
    }

    this._gardinerMap = m;
};

/* ── Static helpers ─────────────────────────────────── */

HieroglyphPipeline.isAvailable = function() {
    return typeof ort !== 'undefined';
};

/* ── Expose globally ────────────────────────────────── */
window.HieroglyphPipeline = HieroglyphPipeline;
window.HieroglyphPipelineState = HieroglyphPipelineState;
