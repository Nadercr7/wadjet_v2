/**
 * ═══════════════════════════════════════════════════════════════
 *  Wadjet AI — Real-Time Detection Loop & Stabilizer
 *  Phase 6.5: Continuous camera classification at ~2 FPS
 *  Phase 6.7: Prediction stabilizer (debounce / majority vote)
 * ═══════════════════════════════════════════════════════════════
 *
 *  Public API:
 *    new WadjetDetectionLoop(options)
 *    .start()        → void   — begin the detection loop
 *    .stop()         → void   — end the loop
 *    .pause()        → void   — temporarily pause (keep camera live)
 *    .resume()       → void   — resume from pause
 *    .getStats()     → Object — detection statistics
 *    .dispose()      → void   — clean up completely
 *
 *    new WadjetDetectionStabilizer(options)
 *    .push(result)   → StableResult|null — feed a raw result, get stabilized output
 *    .reset()        → void              — clear prediction history
 *    .getInfo()      → Object            — current stabilizer state
 *
 *  Options (WadjetDetectionLoop):
 *    classifier      — WadjetClassifier instance (default: window.wadjetClassifier)
 *    camera          — WadjetCamera instance (default: window.wadjetCamera)
 *    videoElement    — HTMLVideoElement (default: #camera-video)
 *    intervalMs      — ms between frames (default: 500 → ~2 FPS)
 *    debug           — show FPS counter (default: false)
 *    onResult        — (result) => void  callback on each detection
 *    onStateChange   — (state, prev) => void
 *    onError         — (error) => void
 *
 *  Options (WadjetDetectionStabilizer):
 *    windowSize      — number of frames in prediction window (default: 5)
 *    hysteresis      — consecutive frames to change locked label (default: 3)
 *
 *  Globals exposed:
 *    window.WadjetDetectionLoop
 *    window.WadjetDetectionStabilizer
 *    window.DetectionState
 */

'use strict';

/* ── Detection States ───────────────────────────────── */

var DetectionState = Object.freeze({
    IDLE:     'idle',
    RUNNING:  'running',
    PAUSED:   'paused',
    STOPPED:  'stopped'
});

/* ── WadjetDetectionLoop Class ──────────────────────── */

/**
 * @param {Object} [options]
 * @param {WadjetClassifier} [options.classifier]
 * @param {WadjetCamera}     [options.camera]
 * @param {HTMLVideoElement}  [options.videoElement]
 * @param {number}  [options.intervalMs=500]  — target ms between inferences (~2 FPS)
 * @param {boolean} [options.debug=false]     — show FPS counter
 * @param {Function} [options.onResult]       — called with ClassifyResult after each frame
 * @param {Function} [options.onStateChange]  — called with (newState, prevState)
 * @param {Function} [options.onError]        — called with Error
 */
function WadjetDetectionLoop(options) {
    options = options || {};

    this._classifier  = options.classifier   || null;
    this._camera      = options.camera       || null;
    this._videoEl     = options.videoElement  || null;
    this._intervalMs  = options.intervalMs    || 500;
    this._debug       = options.debug        || false;
    this._onResult    = options.onResult     || null;
    this._onStateChange = options.onStateChange || null;
    this._onError     = options.onError      || null;

    // Internal state
    this._state       = DetectionState.IDLE;
    this._rafId       = null;
    this._lastTickTime = 0;

    // Stats
    this._frameCount     = 0;
    this._skippedFrames  = 0;
    this._errorCount     = 0;
    this._fpsWindowStart = 0;
    this._fpsFrameCount  = 0;
    this._currentFps     = 0;
    this._lastResult     = null;
    this._startTime      = 0;
}

/* ── Getters ────────────────────────────────────────── */

Object.defineProperties(WadjetDetectionLoop.prototype, {
    state:          { get: function() { return this._state; } },
    isRunning:      { get: function() { return this._state === DetectionState.RUNNING; } },
    isPaused:       { get: function() { return this._state === DetectionState.PAUSED; } },
    lastResult:     { get: function() { return this._lastResult; } },
    frameCount:     { get: function() { return this._frameCount; } },
    skippedFrames:  { get: function() { return this._skippedFrames; } },
    currentFps:     { get: function() { return this._currentFps; } },
    debug:          {
        get: function() { return this._debug; },
        set: function(v) { this._debug = !!v; }
    }
});

/* ── State Management ───────────────────────────────── */

WadjetDetectionLoop.prototype._setState = function(state) {
    var prev = this._state;
    if (prev === state) return;
    this._state = state;
    if (this._onStateChange) {
        try { this._onStateChange(state, prev); } catch (_) { /* swallow */ }
    }
};

/* ── Start / Stop / Pause / Resume ──────────────────── */

/**
 * Start the real-time detection loop.
 * Requires: classifier in READY state + camera ACTIVE with a video element.
 */
WadjetDetectionLoop.prototype.start = function() {
    // Resolve lazy references (allow late binding)
    if (!this._classifier) this._classifier = window.wadjetClassifier;
    if (!this._camera)     this._camera     = window.wadjetCamera;
    if (!this._videoEl)    this._videoEl    = document.getElementById('camera-video');

    // Guard: classifier must be ready
    if (!this._classifier || !this._classifier.isReady) {
        var err = new Error('[Wadjet Detection] Cannot start — classifier not ready');
        if (this._onError) this._onError(err);
        console.warn(err.message);
        return;
    }

    // Guard: video element required
    if (!this._videoEl) {
        var err2 = new Error('[Wadjet Detection] Cannot start — no video element');
        if (this._onError) this._onError(err2);
        console.warn(err2.message);
        return;
    }

    // Guard: already running
    if (this._state === DetectionState.RUNNING) return;

    this._setState(DetectionState.RUNNING);
    this._startTime = performance.now();
    this._fpsWindowStart = performance.now();
    this._fpsFrameCount = 0;
    this._lastTickTime = 0;

    console.log('[Wadjet Detection] Loop started — target interval: ' +
        this._intervalMs + 'ms (~' + Math.round(1000 / this._intervalMs) + ' FPS)');

    // Start the rAF loop
    var self = this;
    this._rafId = requestAnimationFrame(function tick(timestamp) {
        self._tick(timestamp);
    });
};

/**
 * Stop the detection loop completely. Resets stats.
 */
WadjetDetectionLoop.prototype.stop = function() {
    if (this._rafId) {
        cancelAnimationFrame(this._rafId);
        this._rafId = null;
    }
    this._setState(DetectionState.STOPPED);
    console.log('[Wadjet Detection] Loop stopped — ' +
        this._frameCount + ' frames processed, ' +
        this._skippedFrames + ' skipped');
};

/**
 * Pause the loop (detection pauses, camera stays live).
 * Useful when user is inspecting a result.
 */
WadjetDetectionLoop.prototype.pause = function() {
    if (this._state !== DetectionState.RUNNING) return;
    this._setState(DetectionState.PAUSED);
    console.log('[Wadjet Detection] Loop paused');
};

/**
 * Resume from paused state.
 */
WadjetDetectionLoop.prototype.resume = function() {
    if (this._state !== DetectionState.PAUSED) return;
    this._setState(DetectionState.RUNNING);
    this._lastTickTime = 0; // reset so next rAF triggers immediately
    console.log('[Wadjet Detection] Loop resumed');
};

/* ── Core Tick (requestAnimationFrame) ──────────────── */

/**
 * Internal: called every animation frame. Throttles to _intervalMs.
 * Uses requestAnimationFrame for smooth scheduling + setTimeout fallback.
 *
 * @private
 * @param {number} timestamp — rAF DOMHighResTimeStamp
 */
WadjetDetectionLoop.prototype._tick = function(timestamp) {
    var self = this;

    // Bail if stopped
    if (this._state === DetectionState.STOPPED) return;

    // Schedule next frame first (keep loop alive even during pauses)
    this._rafId = requestAnimationFrame(function(ts) {
        self._tick(ts);
    });

    // Skip if paused
    if (this._state === DetectionState.PAUSED) return;

    // Throttle: enforce minimum interval between inferences
    if (this._lastTickTime > 0 && (timestamp - this._lastTickTime) < this._intervalMs) {
        return;
    }

    // Skip if classifier is busy (already running previous inference)
    if (this._classifier.inferenceRunning) {
        this._skippedFrames++;
        return;
    }

    // Skip if video not ready (camera not active or video has no dimensions)
    if (!this._videoEl || this._videoEl.videoWidth === 0 || this._videoEl.videoHeight === 0) {
        this._skippedFrames++;
        return;
    }

    this._lastTickTime = timestamp;

    // Run inference on current video frame
    this._classifier.classifyVideo(this._videoEl).then(function(result) {
        if (!result) {
            // null result = video not ready or throttled, already counted
            return;
        }

        self._frameCount++;
        self._lastResult = result;
        self._updateFps();

        // Notify callback
        if (self._onResult) {
            try { self._onResult(result); } catch (_) { /* swallow callback errors */ }
        }
    }).catch(function(err) {
        self._errorCount++;
        if (self._onError) {
            try { self._onError(err); } catch (_) { /* swallow */ }
        }
        // Don't stop the loop on a single frame error
        if (self._errorCount > 20) {
            console.error('[Wadjet Detection] Too many errors (' + self._errorCount + '), stopping loop');
            self.stop();
        }
    });
};

/* ── FPS Calculation ────────────────────────────────── */

/**
 * Update FPS counter using a sliding 2-second window.
 * @private
 */
WadjetDetectionLoop.prototype._updateFps = function() {
    this._fpsFrameCount++;
    var now = performance.now();
    var elapsed = now - this._fpsWindowStart;

    // Calculate FPS every 2 seconds
    if (elapsed >= 2000) {
        this._currentFps = Math.round((this._fpsFrameCount / elapsed) * 1000 * 10) / 10;
        this._fpsFrameCount = 0;
        this._fpsWindowStart = now;
    }
};

/* ── Stats ──────────────────────────────────────────── */

/**
 * Get detection loop statistics.
 * @returns {Object}
 */
WadjetDetectionLoop.prototype.getStats = function() {
    var uptime = this._startTime > 0 ? Math.round(performance.now() - this._startTime) : 0;
    return {
        state:          this._state,
        frameCount:     this._frameCount,
        skippedFrames:  this._skippedFrames,
        errorCount:     this._errorCount,
        currentFps:     this._currentFps,
        targetFps:      Math.round(1000 / this._intervalMs),
        intervalMs:     this._intervalMs,
        uptimeMs:       uptime,
        lastResult:     this._lastResult,
        debug:          this._debug
    };
};

/* ── Cleanup ────────────────────────────────────────── */

/**
 * Stop and clean up all resources.
 */
WadjetDetectionLoop.prototype.dispose = function() {
    this.stop();
    this._classifier  = null;
    this._camera      = null;
    this._videoEl     = null;
    this._lastResult  = null;
    this._onResult    = null;
    this._onStateChange = null;
    this._onError     = null;
    this._frameCount    = 0;
    this._skippedFrames = 0;
    this._errorCount    = 0;
    this._currentFps    = 0;
    this._state = DetectionState.IDLE;
    console.log('[Wadjet Detection] Disposed');
};

/* ── Expose Globally ────────────────────────────────── */

window.WadjetDetectionLoop = WadjetDetectionLoop;
window.DetectionState       = DetectionState;


/* ═══════════════════════════════════════════════════════════
   WadjetDetectionStabilizer — Prediction Debounce (Phase 6.7)
   5-frame sliding window + majority vote + hysteresis
   ═══════════════════════════════════════════════════════════ */

/**
 * Stabilizes raw per-frame detection results to prevent flickering.
 *
 * Algorithm:
 *   1. Maintain a sliding window of the last N predictions (default 5).
 *   2. On each .push(result):
 *      a. Add the result to the window (dropping the oldest if full).
 *      b. Count how many frames in the window agree on each className.
 *      c. Find the label with the most votes (the "majority label").
 *      d. If that label has strict majority (> windowSize/2), it's the candidate.
 *      e. Average the confidence of all agreeing frames for that candidate.
 *   3. Hysteresis (prevents rapid label switching):
 *      - Once a label is "locked", it stays until a *different* label wins
 *        the majority for `hysteresis` consecutive push() calls (default 3).
 *      - This means the camera must see 3 frames in a row of a new dominant
 *        label before the display switches.
 *   4. Returns a StableResult or null (if no majority yet).
 *
 * @param {Object} [options]
 * @param {number} [options.windowSize=5]  — prediction window size
 * @param {number} [options.hysteresis=3]  — frames before label switch
 */
function WadjetDetectionStabilizer(options) {
    options = options || {};
    this._windowSize  = options.windowSize || 5;
    this._hysteresis  = options.hysteresis || 3;

    // Sliding window of recent raw results
    this._window = [];

    // Locked label (the currently displayed / committed label)
    this._lockedLabel = null;
    this._lockedResult = null;

    // Counter for consecutive frames where a different label wins majority
    this._switchCounter = 0;
    this._switchCandidate = null;
}

/**
 * Push a raw detection result and get the stabilized output.
 *
 * @param {Object} result — raw ClassifyResult from classifier
 *   { className, displayName, confidence, index, top5, inferenceTimeMs, ... }
 * @returns {Object|null} — stabilized result or null if no stable prediction yet
 *   { className, displayName, confidence, index, top5, inferenceTimeMs,
 *     stableConfidence, agreeing, windowSize, isLocked }
 */
WadjetDetectionStabilizer.prototype.push = function(result) {
    if (!result || !result.className) return null;

    // Add to sliding window
    this._window.push(result);
    if (this._window.length > this._windowSize) {
        this._window.shift();
    }

    // Count votes per className in the window
    var votes = {};       // className → count
    var confSums = {};    // className → sum of confidence values
    var latestByClass = {}; // className → most recent result
    for (var i = 0; i < this._window.length; i++) {
        var r = this._window[i];
        var key = r.className;
        votes[key] = (votes[key] || 0) + 1;
        confSums[key] = (confSums[key] || 0) + r.confidence;
        latestByClass[key] = r;
    }

    // Find the label with the most votes
    var majorityLabel = null;
    var majorityCount = 0;
    for (var label in votes) {
        if (votes[label] > majorityCount) {
            majorityCount = votes[label];
            majorityLabel = label;
        }
    }

    // Require strict majority (> half of window)
    var threshold = this._window.length / 2;
    if (majorityCount <= threshold) {
        // No clear majority — keep current locked label if any
        this._switchCounter = 0;
        this._switchCandidate = null;
        if (this._lockedResult) {
            return this._buildStableResult(this._lockedResult, votes, confSums);
        }
        return null;
    }

    // We have a majority label. Apply hysteresis.
    if (this._lockedLabel === null) {
        // First lock — no hysteresis needed
        this._lockedLabel = majorityLabel;
        this._lockedResult = latestByClass[majorityLabel];
        this._switchCounter = 0;
        this._switchCandidate = null;
        return this._buildStableResult(this._lockedResult, votes, confSums);
    }

    if (majorityLabel === this._lockedLabel) {
        // Same label as locked — update locked result, reset switch counter
        this._lockedResult = latestByClass[majorityLabel];
        this._switchCounter = 0;
        this._switchCandidate = null;
        return this._buildStableResult(this._lockedResult, votes, confSums);
    }

    // Different label from locked — apply hysteresis
    if (this._switchCandidate === majorityLabel) {
        this._switchCounter++;
    } else {
        // New switch candidate — restart counter
        this._switchCandidate = majorityLabel;
        this._switchCounter = 1;
    }

    if (this._switchCounter >= this._hysteresis) {
        // Hysteresis threshold met — switch label
        this._lockedLabel = majorityLabel;
        this._lockedResult = latestByClass[majorityLabel];
        this._switchCounter = 0;
        this._switchCandidate = null;
        return this._buildStableResult(this._lockedResult, votes, confSums);
    }

    // Hysteresis not yet met — keep showing locked label
    return this._buildStableResult(this._lockedResult, votes, confSums);
};

/**
 * Build a stable result object with averaged confidence.
 * @private
 */
WadjetDetectionStabilizer.prototype._buildStableResult = function(baseResult, votes, confSums) {
    var label = baseResult.className;
    var agreeing = votes[label] || 0;
    var avgConf = agreeing > 0 ? (confSums[label] / agreeing) : baseResult.confidence;

    return {
        className:       baseResult.className,
        displayName:     baseResult.displayName,
        confidence:      Math.round(avgConf * 10000) / 10000,
        index:           baseResult.index,
        top5:            baseResult.top5,
        inferenceTimeMs: baseResult.inferenceTimeMs,
        // Stabilization metadata
        stableConfidence: Math.round(avgConf * 10000) / 10000,
        agreeing:         agreeing,
        windowSize:       this._window.length,
        isLocked:         this._lockedLabel === label
    };
};

/**
 * Reset the stabilizer (clear prediction history and locked label).
 */
WadjetDetectionStabilizer.prototype.reset = function() {
    this._window = [];
    this._lockedLabel = null;
    this._lockedResult = null;
    this._switchCounter = 0;
    this._switchCandidate = null;
};

/**
 * Get current stabilizer state for debugging.
 * @returns {Object}
 */
WadjetDetectionStabilizer.prototype.getInfo = function() {
    return {
        windowSize:      this._windowSize,
        hysteresis:      this._hysteresis,
        currentWindow:   this._window.length,
        lockedLabel:     this._lockedLabel,
        switchCandidate: this._switchCandidate,
        switchCounter:   this._switchCounter
    };
};

/* ── Expose Stabilizer Globally ─────────────────────── */

window.WadjetDetectionStabilizer = WadjetDetectionStabilizer;
