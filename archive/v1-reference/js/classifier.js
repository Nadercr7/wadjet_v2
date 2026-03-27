/**
 * ═══════════════════════════════════════════════════════════════
 *  Wadjet AI — TF.js Model Loader, Preprocessor & Classifier
 *  Phase 6.2: Load, cache, and warm up the EfficientNetV2-S model
 *  Phase 6.3: Browser preprocessing pipeline
 *  Phase 6.4: Browser inference pipeline
 *  Phase 6.12: Performance optimization (backend selection, memory profiling)
 * ═══════════════════════════════════════════════════════════════
 *
 *  Public API:
 *    new WadjetClassifier(options)
 *    .loadModel()           → Promise<boolean> — download / cache / warmup
 *    .preprocess(source)    → tf.Tensor4D       — [1, 384, 384, 3] float32
 *    .preprocessVideo(video)→ tf.Tensor4D       — optimized for video elements
 *    .classify(source)      → Promise<ClassifyResult> — full inference pipeline
 *    .classifyVideo(video)  → Promise<ClassifyResult|null> — video convenience
 *    .getClassName(index)   → string           — internal class key
 *    .getDisplayName(index) → string           — human-readable name
 *    .getMemoryInfo()       → { numTensors, numBytes, numMB }
 *    .getMemoryProfile()    → { baseline, current, delta, leaked }
 *    .startMemoryMonitor()  → void             — periodic leak check
 *    .stopMemoryMonitor()   → void
 *    .dispose()             → void             — free GPU / CPU memory
 *
 *  Static:
 *    WadjetClassifier.isAvailable()  → boolean (TF.js loaded?)
 *    WadjetClassifier.getBackend()   → Promise<string|null>
 *    WadjetClassifier.initBackend()  → Promise<string> — WebGL → WASM → CPU
 *
 *  Globals exposed:
 *    window.WadjetClassifier
 *    window.ClassifierState
 */

/* ── Classifier States ──────────────────────────────── */

var ClassifierState = Object.freeze({
    IDLE:     'idle',
    LOADING:  'loading',
    CACHING:  'caching',
    WARMING:  'warming',
    READY:    'ready',
    ERROR:    'error'
});

/* ── WadjetClassifier Class ─────────────────────────── */

/**
 * @param {Object} options
 * @param {string} [options.modelUrl]     — URL to model.json (default: /static/model/model.json)
 * @param {string} [options.metadataUrl]  — URL to model_metadata.json
 * @param {string} [options.cacheKey]     — IndexedDB cache identifier
 * @param {Function} [options.onProgress] — Called with fraction 0-1 during download
 * @param {Function} [options.onStateChange] — Called with ClassifierState value
 * @param {Function} [options.onError]    — Called with Error object
 */
function WadjetClassifier(options) {
    options = options || {};

    this._model       = null;
    this._metadata    = null;
    this._state       = ClassifierState.IDLE;
    this._modelUrl    = options.modelUrl    || '/static/model/model.json';
    this._metadataUrl = options.metadataUrl || '/static/model/model_metadata.json';
    this._cacheKey    = options.cacheKey    || 'wadjet-model-v3';
    this._onProgress    = options.onProgress    || null;
    this._onStateChange = options.onStateChange || null;
    this._onError       = options.onError       || null;

    // Timing stats
    this._loadTimeMs   = 0;
    this._warmupTimeMs = 0;
    this._cachedLoad   = false;

    // Inference stats (Phase 6.4)
    this._lastInferenceMs = 0;
    this._totalInferences = 0;
    this._inferenceRunning = false;

    // Model shape info (populated after load)
    this._inputShape  = null;
    this._numClasses  = null;

    // Memory profiling (Phase 6.12)
    this._baselineTensors = 0;
    this._baselineBytes   = 0;
    this._memoryMonitorId = null;
    this._peakTensors     = 0;
    this._leakWarnings    = 0;
}

/* ── Getters ────────────────────────────────────────── */

Object.defineProperties(WadjetClassifier.prototype, {
    state:            { get: function() { return this._state; } },
    isReady:          { get: function() { return this._state === ClassifierState.READY; } },
    isLoading:        { get: function() { return this._state === ClassifierState.LOADING || this._state === ClassifierState.CACHING || this._state === ClassifierState.WARMING; } },
    model:            { get: function() { return this._model; } },
    metadata:         { get: function() { return this._metadata; } },
    loadTimeMs:       { get: function() { return this._loadTimeMs; } },
    warmupTimeMs:     { get: function() { return this._warmupTimeMs; } },
    cachedLoad:       { get: function() { return this._cachedLoad; } },
    inputShape:       { get: function() { return this._inputShape; } },
    numClasses:       { get: function() { return this._numClasses; } },
    lastInferenceMs:  { get: function() { return this._lastInferenceMs; } },
    totalInferences:  { get: function() { return this._totalInferences; } },
    inferenceRunning: { get: function() { return this._inferenceRunning; } },
    baselineTensors:  { get: function() { return this._baselineTensors; } },
    peakTensors:      { get: function() { return this._peakTensors; } },
    leakWarnings:     { get: function() { return this._leakWarnings; } }
});

/* ── State Management ───────────────────────────────── */

WadjetClassifier.prototype._setState = function(state) {
    var prev = this._state;
    this._state = state;
    if (this._onStateChange) {
        try { this._onStateChange(state, prev); } catch (_) { /* swallow callback errors */ }
    }
};

/* ── Main Load Method ───────────────────────────────── */

/**
 * Load model: metadata → IndexedDB cache check → download → cache → warmup.
 * Resolves true when model is ready. Rejects on fatal error.
 *
 * @returns {Promise<boolean>}
 */
WadjetClassifier.prototype.loadModel = function() {
    var self = this;

    // Guard: already loading or ready
    if (this._state === ClassifierState.LOADING ||
        this._state === ClassifierState.CACHING ||
        this._state === ClassifierState.WARMING) {
        return Promise.resolve(false);
    }
    if (this._state === ClassifierState.READY && this._model) {
        return Promise.resolve(true);
    }

    // Pre-flight: TF.js must be available
    if (!WadjetClassifier.isAvailable()) {
        var err = new Error('TensorFlow.js is not loaded. Include the TF.js script before classifier.js.');
        this._setState(ClassifierState.ERROR);
        if (this._onError) this._onError(err);
        return Promise.reject(err);
    }

    this._setState(ClassifierState.LOADING);

    return this._loadMetadata()
        .then(function() {
            return self._tryLoadFromCache();
        })
        .then(function(cachedModel) {
            if (cachedModel) {
                self._cachedLoad = true;
                console.log('[Wadjet] Model loaded from IndexedDB cache');
                return cachedModel;
            }
            // Download from server
            return self._downloadModel().then(function(model) {
                self._setState(ClassifierState.CACHING);
                return self._saveToCache(model).then(function() {
                    return model;
                });
            });
        })
        .then(function(model) {
            self._model = model;
            // Graph models may expose inputs differently from layers models
            var inp0 = model.inputs && model.inputs[0];
            self._inputShape = (inp0 && inp0.shape && inp0.shape.length > 1)
                ? inp0.shape.slice(1)
                : [384, 384, 3];  // fallback for graph models
            var out0 = model.outputs && model.outputs[0];
            self._numClasses = (out0 && out0.shape) ? out0.shape[out0.shape.length - 1] : 52;
            self._setState(ClassifierState.WARMING);
            return self._warmup();
        })
        .then(function() {
            self._setState(ClassifierState.READY);

            // Capture memory baseline after warmup (Phase 6.12)
            if (WadjetClassifier.isAvailable()) {
                var mem = tf.memory();
                self._baselineTensors = mem.numTensors;
                self._baselineBytes   = mem.numBytes;
                self._peakTensors     = mem.numTensors;
            }

            console.log('[Wadjet] Classifier ready — ' +
                'input: [' + self._inputShape.join(', ') + '], ' +
                'classes: ' + self._numClasses + ', ' +
                'load: ' + self._loadTimeMs + 'ms, ' +
                'warmup: ' + self._warmupTimeMs + 'ms' +
                (self._cachedLoad ? ' (cached)' : '') +
                ', backend: ' + (WadjetClassifier.isAvailable() ? tf.getBackend() : 'N/A') +
                ', baseline tensors: ' + self._baselineTensors);
            return true;
        })
        .catch(function(error) {
            self._setState(ClassifierState.ERROR);
            if (self._onError) self._onError(error);
            throw error;
        });
};

/* ── Metadata Loading (with offline cache — Phase 6.11) ─ */

WadjetClassifier.prototype._loadMetadata = function() {
    var self = this;
    var CACHE_KEY = 'wadjet_model_metadata';

    return fetch(this._metadataUrl).then(function(resp) {
        if (!resp.ok) {
            throw new Error('Failed to load model metadata: HTTP ' + resp.status);
        }
        return resp.json();
    }).then(function(meta) {
        self._metadata = meta;
        // Cache metadata for offline use
        try { localStorage.setItem(CACHE_KEY, JSON.stringify(meta)); } catch (_) {}
        console.log('[Wadjet] Metadata loaded — ' + meta.num_classes + ' classes, v' + meta.version);
    }).catch(function(err) {
        // Offline fallback: try localStorage cache
        try {
            var cached = localStorage.getItem(CACHE_KEY);
            if (cached) {
                self._metadata = JSON.parse(cached);
                console.log('[Wadjet] Metadata loaded from offline cache — ' +
                    self._metadata.num_classes + ' classes, v' + self._metadata.version);
                return;
            }
        } catch (_) {}
        throw err;
    });
};

/* ── IndexedDB Cache ────────────────────────────────── */

WadjetClassifier.prototype._tryLoadFromCache = function() {
    var cacheKey = 'indexeddb://' + this._cacheKey;
    return tf.loadLayersModel(cacheKey).then(function(model) {
        return model;
    }).catch(function() {
        // Cache miss — expected on first load
        return null;
    });
};

WadjetClassifier.prototype._saveToCache = function(model) {
    var cacheKey = 'indexeddb://' + this._cacheKey;
    return model.save(cacheKey).then(function() {
        console.log('[Wadjet] Model cached to IndexedDB');
    }).catch(function(err) {
        // Non-fatal — model works, just not cached
        console.warn('[Wadjet] Cache save failed:', err.message);
    });
};

/* ── Model Download ─────────────────────────────────── */

WadjetClassifier.prototype._downloadModel = function() {
    var self = this;
    var t0 = performance.now();

    return tf.loadLayersModel(this._modelUrl, {
        onProgress: function(fraction) {
            if (self._onProgress) {
                try { self._onProgress(fraction); } catch (_) { /* swallow */ }
            }
        }
    }).then(function(model) {
        self._loadTimeMs = Math.round(performance.now() - t0);
        console.log('[Wadjet] Model downloaded in ' + self._loadTimeMs + 'ms');
        return model;
    }).catch(function(err) {
        // Enhance error messages for common failures
        if (err.message && err.message.indexOf('fetch') !== -1) {
            throw new Error('Model download failed — check network connection. (' + err.message + ')');
        }
        if (err.message && err.message.indexOf('memory') !== -1) {
            throw new Error('Insufficient memory to load model — try closing other tabs. (' + err.message + ')');
        }
        throw new Error('Model loading failed: ' + err.message);
    });
};

/* ── Warmup ─────────────────────────────────────────── */

/**
 * Run a dummy prediction to trigger JIT compilation / shader compilation.
 * Uses tf.tidy to guarantee tensor cleanup.
 */
WadjetClassifier.prototype._warmup = function() {
    var self = this;
    var t0 = performance.now();
    var shape = this._inputShape; // [384, 384, 3]

    return new Promise(function(resolve, reject) {
        try {
            var result = tf.tidy(function() {
                var dummy = tf.zeros([1, shape[0], shape[1], shape[2]]);
                return self._model.predict(dummy);
            });

            // Force execution by reading data
            result.data().then(function(data) {
                result.dispose();

                self._warmupTimeMs = Math.round(performance.now() - t0);

                // Validate output
                var sum = 0;
                for (var i = 0; i < data.length; i++) { sum += data[i]; }
                var softmaxOk = Math.abs(sum - 1.0) < 0.01;

                if (!softmaxOk) {
                    console.warn('[Wadjet] Warmup: softmax sum = ' + sum.toFixed(4) + ' (expected ~1.0)');
                }

                console.log('[Wadjet] Warmup prediction in ' + self._warmupTimeMs + 'ms — ' +
                    'output: [' + data.length + '], softmax sum: ' + sum.toFixed(4));
                resolve();
            }).catch(function(err) {
                reject(new Error('Warmup prediction failed: ' + err.message));
            });
        } catch (err) {
            reject(new Error('Warmup prediction failed: ' + err.message));
        }
    });
};

/* ── Preprocessing (Phase 6.3) ──────────────────────── */

/**
 * Preprocess an image source into a model-ready tensor.
 *
 * Accepts: HTMLCanvasElement, HTMLVideoElement, HTMLImageElement,
 *          ImageData, or an existing tf.Tensor3D (H, W, 3).
 *
 * Pipeline:
 *   1. tf.browser.fromPixels → int32 [H, W, 3] with values [0, 255]
 *   2. tf.image.resizeBilinear → [384, 384, 3]
 *   3. tf.cast → float32  (model has built-in imagenet preprocessing)
 *   4. tf.expandDims → [1, 384, 384, 3]
 *
 * NOTE: No manual normalization (/255). The exported EfficientNetV2-S
 * model includes a built-in preprocessing layer that expects raw
 * pixel values in [0, 255] and converts internally (see model_metadata.json).
 *
 * The returned tensor must be disposed by the caller (or use tf.tidy).
 *
 * @param {HTMLCanvasElement|HTMLVideoElement|HTMLImageElement|ImageData|tf.Tensor3D} source
 * @returns {tf.Tensor4D} — shape [1, 384, 384, 3], dtype float32
 * @throws {Error} if model not loaded or source invalid
 */
WadjetClassifier.prototype.preprocess = function(source) {
    if (!this._model || !this._inputShape) {
        throw new Error('[Wadjet] Cannot preprocess — model not loaded');
    }

    var targetH = this._inputShape[0]; // 384
    var targetW = this._inputShape[1]; // 384

    return tf.tidy(function() {
        var pixels;

        // Handle tf.Tensor input (already pixel data)
        if (source instanceof tf.Tensor) {
            pixels = source.rank === 3 ? source : source.squeeze();
        } else {
            // HTMLCanvasElement, HTMLVideoElement, HTMLImageElement, ImageData
            pixels = tf.browser.fromPixels(source); // int32 [H, W, 3]
        }

        // Resize to model input dimensions
        var resized = tf.image.resizeBilinear(
            pixels.expandDims(0),    // [1, H, W, 3] for resizeBilinear
            [targetH, targetW]
        ).squeeze(0);                // back to [384, 384, 3]

        // Cast to float32 — model expects [0, 255] float32 input
        // (model's built-in preprocessing layer handles normalization)
        var asFloat = resized.dtype === 'float32' ? resized : tf.cast(resized, 'float32');

        // Add batch dimension → [1, 384, 384, 3]
        return asFloat.expandDims(0);
    });
};

/**
 * Preprocess directly from an HTMLVideoElement — optimized for the
 * real-time detection loop. Captures the current video frame without
 * needing a separate canvas capture step.
 *
 * @param {HTMLVideoElement} videoEl
 * @returns {tf.Tensor4D|null} — shape [1, 384, 384, 3] or null if video not ready
 */
WadjetClassifier.prototype.preprocessVideo = function(videoEl) {
    if (!this._model || !this._inputShape) {
        return null;
    }
    if (!videoEl || videoEl.videoWidth === 0 || videoEl.videoHeight === 0) {
        return null;
    }
    return this.preprocess(videoEl);
};

/**
 * Preprocess from an HTMLCanvasElement (from WadjetCamera.captureFrameAsCanvas).
 *
 * @param {HTMLCanvasElement} canvas
 * @returns {tf.Tensor4D} — shape [1, 384, 384, 3]
 */
WadjetClassifier.prototype.preprocessCanvas = function(canvas) {
    return this.preprocess(canvas);
};

/**
 * Preprocess from raw ImageData (from WadjetCamera.captureFrame).
 *
 * @param {ImageData} imageData
 * @returns {tf.Tensor4D} — shape [1, 384, 384, 3]
 */
WadjetClassifier.prototype.preprocessImageData = function(imageData) {
    return this.preprocess(imageData);
};

/**
 * Validate the output tensor shape/type of a preprocessed tensor.
 * Useful for debugging.
 *
 * @param {tf.Tensor} tensor
 * @returns {{ valid: boolean, shape: number[], dtype: string, issues: string[] }}
 */
WadjetClassifier.prototype.validatePreprocessed = function(tensor) {
    var issues = [];
    var expectedShape = [1, this._inputShape[0], this._inputShape[1], this._inputShape[2]];

    if (tensor.rank !== 4) {
        issues.push('Expected rank 4, got ' + tensor.rank);
    }
    if (tensor.dtype !== 'float32') {
        issues.push('Expected dtype float32, got ' + tensor.dtype);
    }

    var shape = tensor.shape;
    if (shape[0] !== 1) {
        issues.push('Batch size should be 1, got ' + shape[0]);
    }
    if (shape[1] !== expectedShape[1] || shape[2] !== expectedShape[2]) {
        issues.push('Expected [' + expectedShape[1] + ', ' + expectedShape[2] + '], got [' + shape[1] + ', ' + shape[2] + ']');
    }
    if (shape[3] !== 3) {
        issues.push('Expected 3 channels, got ' + shape[3]);
    }

    return {
        valid:  issues.length === 0,
        shape:  shape,
        dtype:  tensor.dtype,
        issues: issues
    };
};

/* ── Inference Pipeline (Phase 6.4) ─────────────────── */

/**
 * Run full inference on an image source.
 *
 * Pipeline: preprocess → model.predict → decode top-5 → dispose tensors.
 *
 * Accepts the same source types as preprocess(): HTMLCanvasElement,
 * HTMLVideoElement, HTMLImageElement, ImageData, or tf.Tensor3D.
 *
 * @param {HTMLCanvasElement|HTMLVideoElement|HTMLImageElement|ImageData|tf.Tensor3D} source
 * @returns {Promise<{
 *   className:      string,
 *   displayName:    string,
 *   confidence:     number,
 *   top5:           Array<{ className: string, displayName: string, confidence: number, index: number }>,
 *   inferenceTimeMs: number,
 *   totalInferences: number
 * }>}
 * @throws {Error} if model not ready or source invalid
 */
WadjetClassifier.prototype.classify = function(source) {
    var self = this;

    // Guard: model must be ready
    if (this._state !== ClassifierState.READY || !this._model) {
        return Promise.reject(
            new Error('[Wadjet] Cannot classify — model not ready (state: ' + this._state + ')')
        );
    }

    // Guard: skip if previous inference still running (throttle)
    if (this._inferenceRunning) {
        return Promise.reject(
            new Error('[Wadjet] Inference already in progress — skipping frame')
        );
    }

    this._inferenceRunning = true;
    var t0 = performance.now();
    var preprocessed = null;
    var outputTensor = null;

    try {
        // Phase 6.12: Batch preprocess + predict inside tf.tidy to
        // guarantee all intermediate tensors are cleaned up automatically.
        // Only the final output tensor escapes the tidy scope.
        outputTensor = tf.tidy(function() {
            var pp = self.preprocess(source);
            var out = self._model.predict(pp);
            // pp is auto-disposed by tf.tidy since we return out
            return out;
        });
    } catch (err) {
        this._inferenceRunning = false;
        return Promise.reject(
            new Error('[Wadjet] Inference failed: ' + err.message)
        );
    }

    // Step 3: Read output data and decode
    return outputTensor.data().then(function(probabilities) {
        // Dispose output tensor immediately after reading data
        outputTensor.dispose();

        // Timing
        var elapsed = Math.round(performance.now() - t0);
        self._lastInferenceMs = elapsed;
        self._totalInferences++;
        self._inferenceRunning = false;

        // Track peak tensor count (Phase 6.12)
        if (WadjetClassifier.isAvailable()) {
            var currentTensors = tf.memory().numTensors;
            if (currentTensors > self._peakTensors) {
                self._peakTensors = currentTensors;
            }
        }

        // Decode output probabilities into result
        return self._decodeOutput(probabilities, elapsed);
    }).catch(function(err) {
        // Ensure cleanup on error
        if (outputTensor)  { try { outputTensor.dispose(); } catch (_) {} }
        self._inferenceRunning = false;
        throw new Error('[Wadjet] Inference decode failed: ' + err.message);
    });
};

/**
 * Classify directly from a video element — convenience for the
 * real-time detection loop. Returns null (resolves) if video is
 * not ready instead of rejecting.
 *
 * @param {HTMLVideoElement} videoEl
 * @returns {Promise<Object|null>} — ClassifyResult or null
 */
WadjetClassifier.prototype.classifyVideo = function(videoEl) {
    if (!videoEl || videoEl.videoWidth === 0 || videoEl.videoHeight === 0) {
        return Promise.resolve(null);
    }
    return this.classify(videoEl).catch(function(err) {
        // Swallow "already in progress" errors for detection loop
        if (err.message && err.message.indexOf('already in progress') !== -1) {
            return null;
        }
        throw err;
    });
};

/**
 * Decode raw softmax output probabilities into a structured result.
 *
 * @private
 * @param {Float32Array} probabilities — length numClasses softmax output
 * @param {number} elapsedMs — inference duration
 * @returns {Object} ClassifyResult
 */
WadjetClassifier.prototype._decodeOutput = function(probabilities, elapsedMs) {
    var numClasses = probabilities.length;

    // Build indexed array for sorting
    var indexed = new Array(numClasses);
    for (var i = 0; i < numClasses; i++) {
        indexed[i] = { index: i, prob: probabilities[i] };
    }

    // Sort descending by probability
    indexed.sort(function(a, b) { return b.prob - a.prob; });

    // Build top-5 results
    var top5 = [];
    var count = Math.min(5, numClasses);
    for (var j = 0; j < count; j++) {
        var entry = indexed[j];
        top5.push({
            className:   this.getClassName(entry.index),
            displayName: this.getDisplayName(entry.index),
            confidence:  Math.round(entry.prob * 10000) / 10000,  // 4 decimal places
            index:       entry.index
        });
    }

    // Top-1 result
    var best = indexed[0];

    return {
        className:       this.getClassName(best.index),
        displayName:     this.getDisplayName(best.index),
        confidence:      Math.round(best.prob * 10000) / 10000,
        index:           best.index,
        top5:            top5,
        inferenceTimeMs: elapsedMs,
        totalInferences: this._totalInferences
    };
};

/* ── Class Name Helpers ─────────────────────────────── */

/**
 * Get internal class key (e.g., "karnak_temple") by index.
 * @param {number} index — 0-based class index
 * @returns {string}
 */
WadjetClassifier.prototype.getClassName = function(index) {
    if (!this._metadata || !this._metadata.class_names) return 'class_' + index;
    return this._metadata.class_names[index] || 'class_' + index;
};

/**
 * Get human-readable display name (e.g., "Karnak Temple") by index.
 * @param {number} index — 0-based class index
 * @returns {string}
 */
WadjetClassifier.prototype.getDisplayName = function(index) {
    if (!this._metadata) return 'Class ' + index;
    var key = this._metadata.class_names[index];
    if (!key) return 'Class ' + index;
    return (this._metadata.display_names && this._metadata.display_names[key]) || key;
};

/**
 * Get all class names as an array.
 * @returns {string[]}
 */
WadjetClassifier.prototype.getClassNames = function() {
    if (!this._metadata || !this._metadata.class_names) return [];
    return this._metadata.class_names.slice();
};

/* ── Memory Info ────────────────────────────────────── */

/**
 * Get TF.js memory usage stats.
 * @returns {{ numTensors: number, numBytes: number, numMB: string }}
 */
WadjetClassifier.prototype.getMemoryInfo = function() {
    if (!WadjetClassifier.isAvailable()) {
        return { numTensors: 0, numBytes: 0, numMB: '0.0' };
    }
    var info = tf.memory();
    return {
        numTensors: info.numTensors,
        numBytes:   info.numBytes,
        numMB:      (info.numBytes / 1024 / 1024).toFixed(1)
    };
};

/* ── Memory Profiling (Phase 6.12) ──────────────────── */

/**
 * Get memory profile comparing current state to post-warmup baseline.
 * Useful for detecting tensor leaks over extended detection sessions.
 *
 * @returns {{
 *   baseline: { tensors: number, bytes: number },
 *   current:  { tensors: number, bytes: number, mb: string },
 *   delta:    { tensors: number, bytes: number },
 *   peak:     number,
 *   leaked:   boolean,
 *   leakWarnings: number,
 *   totalInferences: number
 * }}
 */
WadjetClassifier.prototype.getMemoryProfile = function() {
    var current = this.getMemoryInfo();
    var deltaTensors = current.numTensors - this._baselineTensors;
    var deltaBytes   = current.numBytes - this._baselineBytes;
    // Allow a small tolerance (2 tensors) for transient WebGL buffers
    var leaked = deltaTensors > 2;

    return {
        baseline: {
            tensors: this._baselineTensors,
            bytes:   this._baselineBytes
        },
        current: {
            tensors: current.numTensors,
            bytes:   current.numBytes,
            mb:      current.numMB
        },
        delta: {
            tensors: deltaTensors,
            bytes:   deltaBytes
        },
        peak:           this._peakTensors,
        leaked:         leaked,
        leakWarnings:   this._leakWarnings,
        totalInferences: this._totalInferences
    };
};

/**
 * Start periodic memory monitoring. Checks every 10 seconds for
 * tensor leaks (current tensors significantly above baseline).
 * Logs warnings if leaks are detected.
 *
 * @param {number} [intervalMs=10000] — check interval in milliseconds
 */
WadjetClassifier.prototype.startMemoryMonitor = function(intervalMs) {
    var self = this;
    var interval = intervalMs || 10000;

    this.stopMemoryMonitor();

    this._memoryMonitorId = setInterval(function() {
        if (self._state !== ClassifierState.READY) return;

        var profile = self.getMemoryProfile();

        // Track peak
        if (profile.current.tensors > self._peakTensors) {
            self._peakTensors = profile.current.tensors;
        }

        // Check for leaks: delta > 5 tensors is suspicious
        if (profile.delta.tensors > 5) {
            self._leakWarnings++;
            console.warn('[Wadjet Perf] Possible tensor leak — ' +
                'baseline: ' + profile.baseline.tensors +
                ', current: ' + profile.current.tensors +
                ', delta: +' + profile.delta.tensors +
                ' (warning #' + self._leakWarnings + ')');

            // Dispatch event for UI to show warning
            window.dispatchEvent(new CustomEvent('wadjet:memory-warning', {
                detail: profile
            }));
        }
    }, interval);

    console.log('[Wadjet Perf] Memory monitor started — interval: ' + interval + 'ms');
};

/**
 * Stop the periodic memory monitor.
 */
WadjetClassifier.prototype.stopMemoryMonitor = function() {
    if (this._memoryMonitorId) {
        clearInterval(this._memoryMonitorId);
        this._memoryMonitorId = null;
    }
};

/* ── Backend Info ───────────────────────────────────── */

/**
 * Get detailed model/runtime information.
 * @returns {Object}
 */
WadjetClassifier.prototype.getInfo = function() {
    return {
        state:           this._state,
        inputShape:      this._inputShape,
        numClasses:      this._numClasses,
        loadTimeMs:      this._loadTimeMs,
        warmupTimeMs:    this._warmupTimeMs,
        cachedLoad:      this._cachedLoad,
        modelUrl:        this._modelUrl,
        cacheKey:        this._cacheKey,
        lastInferenceMs: this._lastInferenceMs,
        totalInferences: this._totalInferences,
        backend:         WadjetClassifier.isAvailable() ? tf.getBackend() : null,
        tfVersion:       WadjetClassifier.isAvailable() ? tf.version.tfjs : null,
        memory:          this.getMemoryInfo(),
        memoryProfile:   this._baselineTensors > 0 ? this.getMemoryProfile() : null,
        quantization:    'float16'
    };
};

/* ── Static Methods ─────────────────────────────────── */

/**
 * Check if TensorFlow.js is loaded in the page.
 * @returns {boolean}
 */
WadjetClassifier.isAvailable = function() {
    return typeof tf !== 'undefined' && (typeof tf.loadGraphModel === 'function' || typeof tf.loadLayersModel === 'function');
};

/**
 * Get the active TF.js backend (webgl, wasm, cpu).
 * @returns {Promise<string|null>}
 */
WadjetClassifier.getBackend = function() {
    if (!WadjetClassifier.isAvailable()) {
        return Promise.resolve(null);
    }
    return tf.ready().then(function() {
        return tf.getBackend();
    });
};

/**
 * Initialize the best available TF.js backend (Phase 6.12).
 *
 * Priority: webgl → wasm → cpu
 *   - WebGL is fastest (GPU-accelerated) and is TF.js's default.
 *   - WASM is a solid fallback for devices without WebGL or with
 *     buggy GPU drivers (common on older Android devices).
 *   - CPU is the last resort (slowest but always available).
 *
 * Call this BEFORE loadModel() for optimal performance.
 *
 * @returns {Promise<string>} — name of the selected backend
 */
WadjetClassifier.initBackend = function() {
    if (!WadjetClassifier.isAvailable()) {
        return Promise.reject(new Error('TensorFlow.js is not loaded'));
    }

    var backends = ['webgl', 'wasm', 'cpu'];

    function tryBackend(index) {
        if (index >= backends.length) {
            return Promise.reject(new Error('No TF.js backend available'));
        }
        var name = backends[index];
        console.log('[Wadjet Perf] Trying backend: ' + name + '…');

        return tf.setBackend(name).then(function() {
            return tf.ready();
        }).then(function() {
            var active = tf.getBackend();
            console.log('[Wadjet Perf] Backend initialized: ' + active);

            // Log WebGL-specific info
            if (active === 'webgl') {
                try {
                    var gl = document.createElement('canvas').getContext('webgl2') ||
                             document.createElement('canvas').getContext('webgl');
                    if (gl) {
                        var renderer = gl.getParameter(gl.RENDERER) || 'unknown';
                        var vendor   = gl.getParameter(gl.VENDOR) || 'unknown';
                        console.log('[Wadjet Perf] WebGL renderer: ' + renderer + ' (' + vendor + ')');
                    }
                } catch (_) { /* ignore */ }
            }

            return active;
        }).catch(function(err) {
            console.warn('[Wadjet Perf] Backend "' + name + '" failed: ' + err.message);
            return tryBackend(index + 1);
        });
    }

    return tryBackend(0);
};

/* ── Cleanup ────────────────────────────────────────── */

/**
 * Dispose model and release all GPU/CPU memory.
 */
WadjetClassifier.prototype.dispose = function() {
    this.stopMemoryMonitor();
    if (this._model) {
        this._model.dispose();
        this._model = null;
    }
    this._metadata   = null;
    this._inputShape = null;
    this._numClasses = null;
    this._cachedLoad = false;
    this._loadTimeMs   = 0;
    this._warmupTimeMs = 0;
    this._lastInferenceMs = 0;
    this._totalInferences = 0;
    this._inferenceRunning = false;
    this._baselineTensors = 0;
    this._baselineBytes   = 0;
    this._peakTensors     = 0;
    this._leakWarnings    = 0;
    this._setState(ClassifierState.IDLE);
    console.log('[Wadjet] Classifier disposed');
};

/* ── Expose Globally ────────────────────────────────── */

window.WadjetClassifier = WadjetClassifier;
window.ClassifierState  = ClassifierState;
