    // â”€â”€ Carousel Navigation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    (function() {
        var carousel = document.getElementById('carousel');
        var prevBtn = document.getElementById('carousel-prev');
        var nextBtn = document.getElementById('carousel-next');
        if (!carousel) return;

        var scrollAmount = 320;

        if (prevBtn) {
            prevBtn.addEventListener('click', function() {
                carousel.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', function() {
                carousel.scrollBy({ left: scrollAmount, behavior: 'smooth' });
            });
        }
    })();

    // â”€â”€ Camera Initialization â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    (function() {
        'use strict';

        var videoEl      = document.getElementById('camera-video');
        var viewport     = document.getElementById('camera-viewport');
        var placeholder  = document.getElementById('camera-placeholder');
        var startBtn     = document.getElementById('camera-start-btn');
        var stopBtn      = document.getElementById('camera-stop-btn');
        var switchBtn    = document.getElementById('camera-switch-btn');
        var retryBtn     = document.getElementById('camera-retry-btn');
        var errorBox     = document.getElementById('camera-error');
        var errorMsg     = document.getElementById('camera-error-msg');
        var statusBadge  = document.getElementById('camera-status-badge');
        var unsupported  = document.getElementById('camera-unsupported-msg');
        var overlay      = document.getElementById('camera-overlay');
        var overlayContent = document.getElementById('camera-overlay-content');

        if (!videoEl || !viewport) return;

        // Pre-flight: show unsupported message if needed
        if (!WadjetCamera.isSecureContext()) {
            unsupported.textContent = 'Camera requires HTTPS or localhost';
            unsupported.classList.remove('hidden');
            startBtn.disabled = true;
            startBtn.classList.add('opacity-50', 'cursor-not-allowed');
        } else if (!WadjetCamera.isSupported()) {
            unsupported.textContent = 'Camera is not supported in this browser';
            unsupported.classList.remove('hidden');
            startBtn.disabled = true;
            startBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }

        var camera = new WadjetCamera({
            videoElement: videoEl,
            facingMode: 'environment',
            width: 640,
            height: 480,
            onStateChange: function(state) {
                updateUI(state);
            },
            onError: function(errorType, message) {
                showError(message);
            }
        });

        function updateUI(state) {
            if (state === CameraState.ACTIVE) {
                viewport.classList.remove('hidden');
                placeholder.classList.add('hidden');
                errorBox.classList.add('hidden');
                overlay.classList.add('hidden');
                statusBadge.textContent = 'â— Live';
                statusBadge.className = 'badge bg-green-500/20 text-green-600 dark:text-green-400 ml-2';
                // Show switch button if multiple cameras
                if (camera.deviceCount > 1) {
                    switchBtn.style.display = '';
                }
            } else if (state === CameraState.REQUESTING) {
                viewport.classList.remove('hidden');
                placeholder.classList.add('hidden');
                overlay.classList.remove('hidden');
                overlayContent.innerHTML = '<div class="spinner-scarab mx-auto mb-2"><span class="text-2xl">ð“†£</span></div><p class="text-sm text-papyrus/80">Requesting camera accessâ€¦</p>';
                statusBadge.textContent = 'Requestingâ€¦';
                statusBadge.className = 'badge bg-amber-500/20 text-amber-600 dark:text-amber-400 ml-2';
            } else if (state === CameraState.STOPPED || state === CameraState.IDLE) {
                viewport.classList.add('hidden');
                placeholder.classList.remove('hidden');
                errorBox.classList.add('hidden');
                statusBadge.classList.add('hidden');
                statusBadge.textContent = '';
            } else if (state === CameraState.ERROR) {
                viewport.classList.add('hidden');
                placeholder.classList.remove('hidden');
                statusBadge.textContent = 'â— Error';
                statusBadge.className = 'badge bg-red-500/20 text-red-600 dark:text-red-400 ml-2';
            }
        }

        function showError(message) {
            errorBox.classList.remove('hidden');
            errorMsg.textContent = message;
        }

        // Start camera
        startBtn.addEventListener('click', function() {
            if (startBtn.disabled) return;
            camera.initCamera();
        });

        // Stop camera
        stopBtn.addEventListener('click', function() {
            camera.stop();
        });

        // Switch camera
        switchBtn.addEventListener('click', function() {
            camera.switchCamera();
        });

        // Retry
        retryBtn.addEventListener('click', function() {
            errorBox.classList.add('hidden');
            camera.initCamera();
        });

        // Expose camera instance for Phase 6.2+ (model loader, detection loop)
        window.wadjetCamera = camera;
    })();

    // â”€â”€ Model Loader Initialization (Phase 6.2) â”€â”€â”€â”€
    (function() {
        'use strict';

        // UI elements
        var loaderUI     = document.getElementById('model-loader-ui');
        var loaderFill   = document.getElementById('model-loader-fill');
        var loaderStatus = document.getElementById('model-loader-status');
        var modelBadge   = document.getElementById('model-status-badge');

        if (!loaderUI || !loaderFill || !loaderStatus) return;

        // Check TF.js availability
        if (!WadjetClassifier.isAvailable()) {
            modelBadge.textContent = 'TF.js N/A';
            modelBadge.className = 'badge bg-gray-500/20 text-gray-500 ml-2';
            modelBadge.classList.remove('hidden');
            return;
        }

        var classifier = new WadjetClassifier({
            onProgress: function(fraction) {
                var pct = Math.round(fraction * 100);
                loaderFill.style.width = pct + '%';
                loaderStatus.textContent = 'Downloading modelâ€¦ ' + pct + '%';
            },
            onStateChange: function(state) {
                updateModelUI(state);
            },
            onError: function(error) {
                console.error('[Wadjet] Model load error:', error.message);
            }
        });

        function updateModelUI(state) {
            if (state === ClassifierState.LOADING) {
                loaderUI.classList.remove('hidden');
                loaderFill.style.width = '0%';
                loaderStatus.textContent = 'Loading modelâ€¦';
                modelBadge.textContent = 'Loadingâ€¦';
                modelBadge.className = 'badge bg-amber-500/20 text-amber-600 dark:text-amber-400 ml-2';
                modelBadge.classList.remove('hidden');
            } else if (state === ClassifierState.CACHING) {
                loaderFill.style.width = '90%';
                loaderStatus.textContent = 'Caching model for offline useâ€¦';
            } else if (state === ClassifierState.WARMING) {
                loaderFill.style.width = '95%';
                loaderStatus.textContent = 'Warming up AI engineâ€¦';
            } else if (state === ClassifierState.READY) {
                loaderFill.style.width = '100%';
                loaderStatus.textContent = 'Model ready â€” ' +
                    classifier.numClasses + ' landmarks, ' +
                    (classifier.cachedLoad ? 'loaded from cache' : classifier.loadTimeMs + 'ms') +
                    ', warmup ' + classifier.warmupTimeMs + 'ms';
                modelBadge.textContent = 'â— Model Ready';
                modelBadge.className = 'badge bg-green-500/20 text-green-600 dark:text-green-400 ml-2';
                // Fade out progress bar after 3 seconds
                setTimeout(function() {
                    loaderUI.style.opacity = '0';
                    loaderUI.style.transition = 'opacity 0.5s ease';
                    setTimeout(function() { loaderUI.classList.add('hidden'); loaderUI.style.opacity = ''; }, 500);
                }, 3000);
            } else if (state === ClassifierState.ERROR) {
                loaderFill.style.width = '100%';
                loaderFill.classList.add('model-loader-fill-error');
                loaderStatus.textContent = 'Model failed to load â€” check network';
                modelBadge.textContent = 'â— Model Error';
                modelBadge.className = 'badge bg-red-500/20 text-red-600 dark:text-red-400 ml-2';
                modelBadge.classList.remove('hidden');
            }
        }

        // Phase 6.12: Initialize backend (WebGL â†’ WASM â†’ CPU) then load model
        var backendPromise = WadjetClassifier.initBackend().catch(function(err) {
            console.warn('[Wadjet] Backend init failed, using default:', err.message);
            return 'default';
        });

        backendPromise.then(function(backend) {
            // Update badge to show backend during load
            if (backend && backend !== 'default') {
                modelBadge.textContent = 'Loadingâ€¦ (' + backend + ')';
            }
            // Start loading model
            return classifier.loadModel();
        }).then(function() {
            // Start memory monitor after model is ready (Phase 6.12)
            classifier.startMemoryMonitor(10000);
        }).catch(function(err) {
            console.error('[Wadjet] Model load failed:', err);
        });

        // Expose for Phase 6.3+ (preprocessing, inference, detection loop)
        window.wadjetClassifier = classifier;
    })();

    // â”€â”€ Detection Loop Initialization (Phase 6.5 + 6.7 Stabilizer) â”€â”€
    (function() {
        'use strict';

        // UI elements
        var detectionOverlay = document.getElementById('detection-overlay');
        var detectionResult  = document.getElementById('detection-result');
        var detectionIcon    = document.getElementById('detection-icon');
        var detectionLabel   = document.getElementById('detection-label');
        var detectionConf    = document.getElementById('detection-conf');
        var detectionTime    = document.getElementById('detection-time');
        var learnMoreBtn     = document.getElementById('detection-learn-more');
        var detectionFps     = document.getElementById('detection-fps');

        if (!detectionOverlay || !detectionResult) return;

        // Detection loop instance (created lazily)
        var loop = null;
        // Prediction stabilizer (Phase 6.7) â€” 5-frame window, 3-frame hysteresis
        var stabilizer = new WadjetDetectionStabilizer({
            windowSize: 5,
            hysteresis: 3
        });
        window.wadjetStabilizer = stabilizer;
        // Track current tier for smooth CSS transitions
        var currentTier = '';
        // Track last locked label for beep-on-new-detection (Phase 6.10)
        var _lastLockedLabel = '';

        /**
         * Called on each raw detection result from the loop.
         * Phase 6.7: feeds through stabilizer before rendering.
         */
        function onRawDetectionResult(result) {
            var stable = stabilizer.push(result);
            if (stable) {
                // Phase 6.10: dispatch event when a NEW label is locked
                if (stable.isLocked && stable.className && stable.className !== _lastLockedLabel) {
                    _lastLockedLabel = stable.className;
                    window.dispatchEvent(new CustomEvent('wadjet:stable-detection', {
                        detail: { className: stable.className, confidence: stable.stableConfidence }
                    }));
                }
                if (!stable.isLocked) {
                    _lastLockedLabel = '';
                }
                onDetectionResult(stable);
            }
        }

        /**
         * Called with a stabilized detection result â€” update confidence overlay.
         * Phase 6.6 enhanced: 4 visual tiers with icons, smooth CSS
         * transitions, and "Tap to learn more" button on confident detection.
         */
        function onDetectionResult(result) {
            detectionOverlay.classList.remove('hidden');

            var conf = Math.round(result.confidence * 100);
            var name = result.displayName || result.className;
            var time = result.inferenceTimeMs;

            // Determine visual state â€” 4 tiers per Phase 6.6 spec
            var tier, icon, labelText, showLearnMore;
            if (conf >= 80) {
                // Confident: green â€” show landmark name + confidence
                tier = 'high';
                icon = '\u2705';  // âœ…
                labelText = name;
                showLearnMore = true;
            } else if (conf >= 50) {
                // Uncertain: yellow â€” scanning indicator
                tier = 'medium';
                icon = '\uD83D\uDD04';  // ðŸ”„
                labelText = 'Scanning\u2026';
                showLearnMore = false;
            } else if (conf >= 30) {
                // Low confidence: dim result
                tier = 'low';
                icon = '\uD83D\uDD0D';  // ðŸ”
                labelText = name;
                showLearnMore = false;
            } else {
                // No match: prompt user
                tier = 'no-match';
                icon = '\uD83D\uDCF7';  // ðŸ“·
                labelText = 'Point at an Egyptian landmark';
                showLearnMore = false;
            }

            // Update confidence tier class (smooth CSS transition)
            if (tier !== currentTier) {
                detectionResult.className = 'detection-result detection-confidence-' + tier;
                currentTier = tier;
            }

            // Update individual child elements (avoids innerHTML reflow)
            detectionIcon.textContent = icon;
            detectionLabel.textContent = labelText;

            // Confidence percentage â€” hidden for no-match
            if (tier !== 'no-match') {
                detectionConf.textContent = conf + '%';
                detectionConf.classList.remove('hidden');
            } else {
                detectionConf.textContent = '';
                detectionConf.classList.add('hidden');
            }

            // Inference time â€” shown for confident & low tiers
            if (tier === 'high' || tier === 'low') {
                detectionTime.textContent = time + 'ms';
                detectionTime.classList.remove('hidden');
            } else {
                detectionTime.textContent = '';
                detectionTime.classList.add('hidden');
            }

            // "Tap to learn more" button â€” visible only on confident detection
            if (showLearnMore) {
                if (learnMoreBtn.classList.contains('hidden')) {
                    learnMoreBtn.classList.remove('hidden');
                    requestAnimationFrame(function() {
                        learnMoreBtn.classList.add('detection-learn-visible');
                    });
                }
                learnMoreBtn.dataset.landmark = name;
                learnMoreBtn.dataset.className = result.className;
                learnMoreBtn.dataset.confidence = conf;
            } else if (!learnMoreBtn.classList.contains('hidden')) {
                learnMoreBtn.classList.remove('detection-learn-visible');
                setTimeout(function() {
                    if (!learnMoreBtn.classList.contains('detection-learn-visible')) {
                        learnMoreBtn.classList.add('hidden');
                    }
                }, 300);
            }

            // Fade-in overlay smoothly (first frame)
            if (!detectionOverlay.classList.contains('detection-visible')) {
                requestAnimationFrame(function() {
                    detectionOverlay.classList.add('detection-visible');
                });
            }

            // FPS counter (debug mode only)
            if (loop && loop.debug) {
                detectionFps.classList.remove('hidden');
                detectionFps.textContent = loop.currentFps.toFixed(1) + ' FPS | ' +
                    loop.frameCount + ' frames';
            }
        }

        /**
         * "Learn More" button handler â€” pauses detection and dispatches
         * a custom event. Phase 6.8 will implement the full flow.
         */
        learnMoreBtn.addEventListener('click', function() {
            var detail = {
                landmark:   learnMoreBtn.dataset.landmark || '',
                className:  learnMoreBtn.dataset.className || '',
                confidence: parseInt(learnMoreBtn.dataset.confidence, 10) || 0
            };

            // Pause detection while user reads info
            if (loop && loop.isRunning) {
                loop.pause();
            }

            // Dispatch custom event for future "Learn More" flow
            window.dispatchEvent(new CustomEvent('wadjet:learn-more', { detail: detail }));
            console.log('[Wadjet] Learn More:', detail.landmark, '(' + detail.confidence + '%)');
        });

        /**
         * Try to start the detection loop when both camera
         * and classifier are ready.
         */
        function tryStartDetection() {
            var cam = window.wadjetCamera;
            var cls = window.wadjetClassifier;

            if (!cam || !cls) return;
            if (!cls.isReady) return;
            // Camera must be active (state getter on WadjetCamera)
            if (cam._state !== 'active') return;

            if (!loop) {
                loop = new WadjetDetectionLoop({
                    classifier:   cls,
                    camera:       cam,
                    videoElement: document.getElementById('camera-video'),
                    intervalMs:   500,
                    debug:        false,
                    onResult:     onRawDetectionResult,
                    onError:      function(err) {
                        console.warn('[Wadjet Detection]', err.message);
                    },
                    onStateChange: function(state) {
                        if (state === DetectionState.STOPPED) {
                            detectionOverlay.classList.add('hidden');
                        }
                    }
                });
                window.wadjetDetection = loop;
            }

            if (!loop.isRunning) {
                loop.start();
            }
        }

        /**
         * Stop detection when camera stops.
         */
        function stopDetection() {
            if (loop && loop.isRunning) {
                loop.stop();
            }
            // Reset stabilizer prediction history (Phase 6.7)
            stabilizer.reset();
            // Fade-out overlay, then reset
            detectionOverlay.classList.remove('detection-visible');
            setTimeout(function() {
                detectionOverlay.classList.add('hidden');
                detectionResult.className = 'detection-result';
                detectionIcon.textContent = '';
                detectionLabel.textContent = '';
                detectionConf.textContent = '';
                detectionConf.classList.remove('hidden');
                detectionTime.textContent = '';
                detectionTime.classList.remove('hidden');
                learnMoreBtn.classList.add('hidden');
                learnMoreBtn.classList.remove('detection-learn-visible');
                detectionFps.classList.add('hidden');
                currentTier = '';
            }, 350);
        }

        // Listen for camera state changes to auto-start/stop detection
        // The camera IIFE already sets window.wadjetCamera, so we
        // monkey-patch the onStateChange to also trigger detection.
        var origCameraStateChange = null;
        function watchCamera() {
            var cam = window.wadjetCamera;
            if (!cam) { setTimeout(watchCamera, 200); return; }

            origCameraStateChange = cam._onStateChange;
            cam._onStateChange = function(state, detail) {
                // Call original handler first
                if (origCameraStateChange) origCameraStateChange(state, detail);

                if (state === 'active') {
                    // Camera just became active â€” try starting detection
                    // (classifier might not be ready yet, that's ok)
                    setTimeout(tryStartDetection, 300);
                } else if (state === 'stopped' || state === 'error' || state === 'idle') {
                    stopDetection();
                }
            };
        }
        watchCamera();

        // Also listen for classifier readiness
        var origClassifierStateChange = null;
        function watchClassifier() {
            var cls = window.wadjetClassifier;
            if (!cls) { setTimeout(watchClassifier, 200); return; }

            origClassifierStateChange = cls._onStateChange;
            cls._onStateChange = function(state, prev) {
                if (origClassifierStateChange) {
                    try { origClassifierStateChange(state, prev); } catch (_) {}
                }
                if (state === 'ready') {
                    // Model just became ready â€” try starting detection
                    setTimeout(tryStartDetection, 100);
                }
            };
        }
        watchClassifier();
    })();

    // â”€â”€ "Learn More" Info Panel Flow (Phase 6.8) â”€â”€â”€
    (function() {
        'use strict';

        // Panel DOM elements
        var panel        = document.getElementById('learn-more-panel');
        var loading      = document.getElementById('learn-more-loading');
        var errorBox     = document.getElementById('learn-more-error');
        var errorMsg     = document.getElementById('learn-more-error-msg');
        var retryBtn     = document.getElementById('learn-more-retry');
        var content      = document.getElementById('learn-more-content');
        var nameEl       = document.getElementById('learn-more-name');
        var metaEl       = document.getElementById('learn-more-meta');
        var confBadge    = document.getElementById('learn-more-conf-badge');
        var descEl       = document.getElementById('learn-more-desc');
        var highlightsEl = document.getElementById('learn-more-highlights-text');
        var highlightsSec = document.getElementById('learn-more-highlights');
        var tipsEl       = document.getElementById('learn-more-tips-text');
        var tipsSec      = document.getElementById('learn-more-tips');
        var historyEl    = document.getElementById('learn-more-history-text');
        var historySec   = document.getElementById('learn-more-history');
        var resumeBtn    = document.getElementById('learn-more-resume');
        var chatLink     = document.getElementById('learn-more-chat');
        var directionsLink = document.getElementById('learn-more-directions');
        var offlineBanner  = document.getElementById('learn-more-offline-banner');

        if (!panel) return;

        // State
        var _lastClassName = '';
        var _lastConfidence = 0;
        var _abortController = null;

        /**
         * Show the panel with a specific inner state (loading / error / content).
         */
        function showPanelState(state) {
            loading.classList.add('hidden');
            errorBox.classList.add('hidden');
            content.classList.add('hidden');

            if (state === 'loading') loading.classList.remove('hidden');
            else if (state === 'error') errorBox.classList.remove('hidden');
            else if (state === 'content') content.classList.remove('hidden');

            // Show and animate panel
            panel.classList.remove('hidden');
            requestAnimationFrame(function() {
                panel.classList.add('learn-more-visible');
            });
        }

        /**
         * Hide the panel with slide-down animation.
         */
        function hidePanel() {
            panel.classList.remove('learn-more-visible');
            setTimeout(function() {
                panel.classList.add('hidden');
                loading.classList.add('hidden');
                errorBox.classList.add('hidden');
                content.classList.add('hidden');
            }, 400);
        }

        /**
         * Fetch enrichment data from the API (with offline cache â€” Phase 6.11).
         */
        var ENRICHMENT_CACHE_PREFIX = 'wadjet_enrich_';

        function _getEnrichmentCache(className) {
            try {
                var raw = localStorage.getItem(ENRICHMENT_CACHE_PREFIX + className);
                if (raw) return JSON.parse(raw);
            } catch (_) {}
            return null;
        }

        function _setEnrichmentCache(className, data) {
            try {
                localStorage.setItem(ENRICHMENT_CACHE_PREFIX + className, JSON.stringify(data));
            } catch (_) {}
        }

        function fetchEnrichment(className, language) {
            // Abort any in-flight request
            if (_abortController) {
                try { _abortController.abort(); } catch (_) {}
            }
            _abortController = new AbortController();

            var lang = language || document.documentElement.lang || 'en';

            // If offline, go straight to cache
            if (!navigator.onLine) {
                var cached = _getEnrichmentCache(className);
                if (cached) {
                    cached._fromCache = true;
                    return Promise.resolve(cached);
                }
                return Promise.reject(new Error('You are offline. Connect to the internet for landmark details.'));
            }

            return fetch('/api/v1/identify/enrich', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ class_name: className, language: lang }),
                signal: _abortController.signal
            })
            .then(function(resp) {
                if (!resp.ok) {
                    return resp.json().then(function(err) {
                        throw new Error(err.detail || err.message || 'Unknown error');
                    }).catch(function(e) {
                        if (e.message) throw e;
                        throw new Error('Server returned ' + resp.status);
                    });
                }
                return resp.json();
            })
            .then(function(json) {
                // Cache successful response for offline use
                _setEnrichmentCache(className, json);
                return json;
            })
            .catch(function(err) {
                // On network error, try cache fallback
                if (err.name !== 'AbortError') {
                    var fallback = _getEnrichmentCache(className);
                    if (fallback) {
                        fallback._fromCache = true;
                        return fallback;
                    }
                }
                throw err;
            });
        }

        /**
         * Populate the content panel with API data.
         */
        function populateContent(data, confidence) {
            var attraction = data.attraction;

            nameEl.textContent = attraction.name;

            // Meta line: city + era + type
            var metaParts = [];
            if (attraction.city) metaParts.push(attraction.city);
            if (attraction.era)  metaParts.push(attraction.era);
            if (attraction.type) metaParts.push(attraction.type);
            metaEl.textContent = metaParts.join(' Â· ');

            // Confidence badge
            confBadge.textContent = confidence + '% match';

            // Description
            descEl.textContent = attraction.description || '';

            // Highlights
            if (attraction.highlights) {
                highlightsEl.textContent = attraction.highlights;
                highlightsSec.classList.remove('hidden');
            } else {
                highlightsSec.classList.add('hidden');
            }

            // Visiting tips
            if (attraction.visiting_tips) {
                tipsEl.textContent = attraction.visiting_tips;
                tipsSec.classList.remove('hidden');
            } else {
                tipsSec.classList.add('hidden');
            }

            // Historical significance
            if (attraction.historical_significance) {
                historyEl.textContent = attraction.historical_significance;
                historySec.classList.remove('hidden');
            } else {
                historySec.classList.add('hidden');
            }

            // Chat link â€” pass landmark name as query param
            chatLink.href = '/chat?landmark=' + encodeURIComponent(attraction.name);

            // Directions link â€” Google Maps
            if (attraction.maps_url) {
                directionsLink.href = attraction.maps_url;
                directionsLink.classList.remove('hidden');
            } else {
                directionsLink.classList.add('hidden');
            }
        }

        /**
         * Main handler: called when user taps "Learn More".
         */
        function handleLearnMore(detail) {
            var className  = detail.className  || '';
            var confidence = detail.confidence || 0;

            if (!className) return;

            _lastClassName  = className;
            _lastConfidence = confidence;

            // Show loading
            showPanelState('loading');

            fetchEnrichment(className)
                .then(function(json) {
                    populateContent(json.data, confidence);
                    // Show offline banner if served from cache (Phase 6.11)
                    if (json._fromCache && offlineBanner) {
                        offlineBanner.classList.remove('hidden');
                    } else if (offlineBanner) {
                        offlineBanner.classList.add('hidden');
                    }
                    showPanelState('content');
                })
                .catch(function(err) {
                    if (err.name === 'AbortError') return;
                    console.error('[Wadjet Learn More]', err.message);
                    errorMsg.textContent = err.message || 'Could not load details';
                    showPanelState('error');
                });
        }

        /**
         * Resume scanning â€” hide panel and resume detection loop.
         */
        function resumeScanning() {
            hidePanel();

            // Resume detection loop
            var loop = window.wadjetDetection;
            if (loop && !loop.isRunning) {
                // Small delay to let animation finish
                setTimeout(function() { loop.resume(); }, 250);
            }
        }

        // â”€â”€ Event listeners â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        // Listen for the custom event dispatched by the detection overlay
        window.addEventListener('wadjet:learn-more', function(e) {
            handleLearnMore(e.detail || {});
        });

        // "Continue Scanning" button
        if (resumeBtn) {
            resumeBtn.addEventListener('click', resumeScanning);
        }

        // Retry button on error
        if (retryBtn) {
            retryBtn.addEventListener('click', function() {
                if (_lastClassName) {
                    handleLearnMore({ className: _lastClassName, confidence: _lastConfidence });
                }
            });
        }

        // Close panel on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && !panel.classList.contains('hidden')) {
                resumeScanning();
            }
        });

        // Expose for external access
        window.wadjetLearnMore = {
            show: handleLearnMore,
            hide: hidePanel,
            resume: resumeScanning
        };
    })();

    /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
       Phase 6.9 â€” Capture & Share IIFE
       â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
    (function() {
        'use strict';

        // â”€â”€ Constants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var GALLERY_KEY      = 'wadjet_captures';
        var MAX_GALLERY_ITEMS = 12;
        var TOAST_DURATION    = 2200;
        var WATERMARK_TEXT    = '\uD80C\uDC82 Wadjet AI';  // ð“‚€ Wadjet AI

        // â”€â”€ DOM refs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var captureBtn        = document.getElementById('camera-capture-btn');
        var toast             = document.getElementById('capture-toast');
        var toastMsg          = document.getElementById('capture-toast-msg');
        var gallery           = document.getElementById('capture-gallery');
        var galleryGrid       = document.getElementById('capture-gallery-grid');
        var galleryClearBtn   = document.getElementById('capture-gallery-clear');
        var detectionLabel    = document.getElementById('detection-label');
        var detectionConf     = document.getElementById('detection-conf');

        // State
        var _toastTimer = null;
        var _previewOverlay = null;

        // â”€â”€ Utility â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        /** Format date for watermark: "25 Jun 2025" */
        function formatDate(d) {
            var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            return d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
        }

        /** Pretty-format landmark name from class key */
        function prettifyName(raw) {
            if (!raw) return 'Unknown';
            return raw.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); });
        }

        /** Show toast notification */
        function showToast(msg) {
            if (!toast) return;
            toastMsg.textContent = msg || 'Captured!';
            toast.classList.remove('hidden');
            // Force reflow then add visible class
            void toast.offsetWidth;
            toast.classList.add('visible');

            clearTimeout(_toastTimer);
            _toastTimer = setTimeout(function() {
                toast.classList.remove('visible');
                setTimeout(function() { toast.classList.add('hidden'); }, 300);
            }, TOAST_DURATION);
        }

        // â”€â”€ Canvas compositing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        /**
         * Create a composited capture: video frame + landmark name + watermark + date
         * Returns a canvas element.
         */
        function createCompositeCapture() {
            var camera = window.wadjetCamera;
            if (!camera) return null;

            // Get raw frame as canvas
            var frameCanvas = camera.captureFrameAsCanvas();
            if (!frameCanvas) return null;

            var w = frameCanvas.width;
            var h = frameCanvas.height;

            // Create composite canvas
            var canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            var ctx = canvas.getContext('2d');

            // Draw video frame
            ctx.drawImage(frameCanvas, 0, 0);

            // Get current detection info
            var landmarkRaw  = (detectionLabel && detectionLabel.textContent) ? detectionLabel.textContent.trim() : '';
            var confidence   = (detectionConf && detectionConf.textContent) ? detectionConf.textContent.trim() : '';
            var landmarkName = prettifyName(landmarkRaw);
            var dateStr      = formatDate(new Date());

            // Semi-transparent bottom bar for text
            var barH = Math.max(48, h * 0.1);
            ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
            ctx.fillRect(0, h - barH, w, barH);

            // --- Landmark name (bottom-left) ---
            var fontSize = Math.max(14, Math.round(w * 0.04));
            ctx.font = '600 ' + fontSize + 'px "Cinzel", serif';
            ctx.fillStyle = '#D4AF37';
            ctx.textBaseline = 'middle';
            ctx.textAlign = 'left';
            var textY = h - barH / 2;
            if (landmarkRaw) {
                ctx.fillText(landmarkName, 12, textY - fontSize * 0.45);
                // Confidence below
                var confSize = Math.max(10, Math.round(fontSize * 0.6));
                ctx.font = '400 ' + confSize + 'px "Inter", sans-serif';
                ctx.fillStyle = 'rgba(255,255,255,0.7)';
                ctx.fillText(confidence, 12, textY + confSize * 0.7);
            }

            // --- Watermark (bottom-right) ---
            var wmSize = Math.max(10, Math.round(w * 0.028));
            ctx.font = '500 ' + wmSize + 'px "Inter", sans-serif';
            ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
            ctx.textAlign = 'right';
            ctx.fillText(WATERMARK_TEXT, w - 10, textY - wmSize * 0.3);

            // Date below watermark
            var dateSize = Math.max(9, Math.round(wmSize * 0.8));
            ctx.font = '400 ' + dateSize + 'px "Inter", sans-serif';
            ctx.fillStyle = 'rgba(255, 255, 255, 0.45)';
            ctx.fillText(dateStr, w - 10, textY + dateSize * 0.9);

            return canvas;
        }

        // â”€â”€ Download â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        /** Download canvas as PNG */
        function downloadCapture(canvas, landmarkName) {
            if (!canvas) return;
            var filename = 'wadjet_' + (landmarkName || 'capture').toLowerCase().replace(/\s+/g, '_') + '_' + Date.now() + '.png';
            try {
                canvas.toBlob(function(blob) {
                    if (!blob) return;
                    var url = URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    setTimeout(function() { URL.revokeObjectURL(url); }, 1000);
                }, 'image/png');
            } catch (e) {
                // Fallback: dataURL
                var dataUrl = canvas.toDataURL('image/png');
                var a = document.createElement('a');
                a.href = dataUrl;
                a.download = filename;
                a.click();
            }
        }

        // â”€â”€ Share (clipboard) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        /** Copy share caption to clipboard */
        function shareCapture(landmarkName) {
            var caption = '\uD83D\uDCF8 ' + (landmarkName || 'Unknown Landmark') +
                          ' \u2014 Identified by Wadjet AI | ' + formatDate(new Date());

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(caption).then(function() {
                    showToast('Caption copied!');
                }).catch(function() {
                    fallbackCopy(caption);
                });
            } else {
                fallbackCopy(caption);
            }
        }

        function fallbackCopy(text) {
            try {
                var ta = document.createElement('textarea');
                ta.value = text;
                ta.style.position = 'fixed';
                ta.style.left = '-9999px';
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                showToast('Caption copied!');
            } catch (e) {
                showToast('Could not copy');
            }
        }

        // â”€â”€ Gallery (localStorage) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        /** Load gallery items from localStorage */
        function loadGallery() {
            try {
                var raw = localStorage.getItem(GALLERY_KEY);
                return raw ? JSON.parse(raw) : [];
            } catch (e) {
                return [];
            }
        }

        /** Save gallery items to localStorage */
        function saveGallery(items) {
            try {
                localStorage.setItem(GALLERY_KEY, JSON.stringify(items));
            } catch (e) {
                // Quota exceeded â€” remove oldest
                if (items.length > 1) {
                    items.shift();
                    saveGallery(items);
                }
            }
        }

        /** Add a capture to gallery */
        function addToGallery(dataUrl, landmarkRaw, confidence) {
            var items = loadGallery();
            items.push({
                id: Date.now(),
                dataUrl: dataUrl,
                landmark: landmarkRaw || '',
                confidence: confidence || '',
                timestamp: new Date().toISOString()
            });
            // Trim to max
            while (items.length > MAX_GALLERY_ITEMS) {
                items.shift();
            }
            saveGallery(items);
            renderGallery();
        }

        /** Remove a capture from gallery by id */
        function removeFromGallery(id) {
            var items = loadGallery().filter(function(item) { return item.id !== id; });
            saveGallery(items);
            renderGallery();
        }

        /** Clear all gallery items */
        function clearGallery() {
            saveGallery([]);
            renderGallery();
        }

        /** Render gallery grid from localStorage */
        function renderGallery() {
            if (!galleryGrid || !gallery) return;
            var items = loadGallery();

            if (items.length === 0) {
                gallery.classList.add('hidden');
                galleryGrid.innerHTML = '';
                return;
            }

            gallery.classList.remove('hidden');
            galleryGrid.innerHTML = '';

            // Render newest first
            for (var i = items.length - 1; i >= 0; i--) {
                (function(item) {
                    var div = document.createElement('div');
                    div.className = 'capture-gallery-item';
                    div.setAttribute('data-capture-id', item.id);

                    // Thumbnail image
                    var img = document.createElement('img');
                    img.src = item.dataUrl;
                    img.alt = prettifyName(item.landmark) || 'Capture';
                    img.loading = 'lazy';
                    img.decoding = 'async';
                    div.appendChild(img);

                    // Label
                    var label = document.createElement('div');
                    label.className = 'capture-gallery-item-label';
                    label.textContent = prettifyName(item.landmark) || 'Capture';
                    div.appendChild(label);

                    // Hover action buttons
                    var actions = document.createElement('div');
                    actions.className = 'capture-gallery-item-actions';

                    // Download btn
                    var dlBtn = document.createElement('button');
                    dlBtn.className = 'capture-gallery-action-btn';
                    dlBtn.title = 'Download';
                    dlBtn.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3"/></svg>';
                    dlBtn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        downloadDataUrl(item.dataUrl, item.landmark);
                    });
                    actions.appendChild(dlBtn);

                    // Share btn
                    var shBtn = document.createElement('button');
                    shBtn.className = 'capture-gallery-action-btn';
                    shBtn.title = 'Copy caption';
                    shBtn.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/></svg>';
                    shBtn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        shareCapture(prettifyName(item.landmark));
                    });
                    actions.appendChild(shBtn);

                    // Delete btn
                    var rmBtn = document.createElement('button');
                    rmBtn.className = 'capture-gallery-action-btn';
                    rmBtn.title = 'Remove';
                    rmBtn.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>';
                    rmBtn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        removeFromGallery(item.id);
                    });
                    actions.appendChild(rmBtn);

                    div.appendChild(actions);

                    // Click thumbnail â†’ preview overlay
                    div.addEventListener('click', function() {
                        showPreview(item);
                    });

                    galleryGrid.appendChild(div);
                })(items[i]);
            }
        }

        /** Download from dataUrl */
        function downloadDataUrl(dataUrl, landmarkRaw) {
            var name = 'wadjet_' + (landmarkRaw || 'capture').toLowerCase().replace(/\s+/g, '_') + '.png';
            var a = document.createElement('a');
            a.href = dataUrl;
            a.download = name;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }

        // â”€â”€ Preview overlay â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        /** Create and show a fullscreen preview of a capture */
        function showPreview(item) {
            // Create overlay if not exists
            if (!_previewOverlay) {
                _previewOverlay = document.createElement('div');
                _previewOverlay.className = 'capture-preview-overlay';
                _previewOverlay.id = 'capture-preview-overlay';
                _previewOverlay.innerHTML =
                    '<img class="capture-preview-img" id="capture-preview-img" src="" alt="Capture preview" decoding="async">' +
                    '<div class="capture-preview-info">' +
                    '  <div class="landmark-name" id="capture-preview-name"></div>' +
                    '  <div id="capture-preview-date" style="margin-top:0.25rem;color:rgba(255,255,255,0.5);font-size:0.75rem;"></div>' +
                    '</div>' +
                    '<div class="capture-preview-actions">' +
                    '  <button class="capture-preview-btn capture-preview-btn-download" id="capture-preview-dl">â¬‡ Download</button>' +
                    '  <button class="capture-preview-btn capture-preview-btn-share" id="capture-preview-share">ðŸ“‹ Copy Caption</button>' +
                    '  <button class="capture-preview-btn capture-preview-btn-close" id="capture-preview-close">âœ• Close</button>' +
                    '</div>';
                document.body.appendChild(_previewOverlay);

                // Event listeners
                document.getElementById('capture-preview-close').addEventListener('click', hidePreview);
                _previewOverlay.addEventListener('click', function(e) {
                    if (e.target === _previewOverlay) hidePreview();
                });
            }

            // Populate
            document.getElementById('capture-preview-img').src = item.dataUrl;
            document.getElementById('capture-preview-name').textContent = prettifyName(item.landmark) || 'Capture';
            document.getElementById('capture-preview-date').textContent = item.timestamp ? new Date(item.timestamp).toLocaleString() : '';

            // Wire download / share for this item
            var dlBtn = document.getElementById('capture-preview-dl');
            var shBtn = document.getElementById('capture-preview-share');
            // Remove old listeners by cloning
            var newDl = dlBtn.cloneNode(true);
            dlBtn.parentNode.replaceChild(newDl, dlBtn);
            newDl.addEventListener('click', function() {
                downloadDataUrl(item.dataUrl, item.landmark);
            });
            var newSh = shBtn.cloneNode(true);
            shBtn.parentNode.replaceChild(newSh, shBtn);
            newSh.addEventListener('click', function() {
                shareCapture(prettifyName(item.landmark));
            });

            // Show
            void _previewOverlay.offsetWidth;
            _previewOverlay.classList.add('visible');

            // Escape to close
            document.addEventListener('keydown', _previewEscHandler);
        }

        function hidePreview() {
            if (_previewOverlay) {
                _previewOverlay.classList.remove('visible');
            }
            document.removeEventListener('keydown', _previewEscHandler);
        }

        function _previewEscHandler(e) {
            if (e.key === 'Escape') hidePreview();
        }

        // â”€â”€ Main capture handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function handleCapture() {
            if (!captureBtn) return;

            // Flash animation
            captureBtn.classList.add('capturing');
            setTimeout(function() { captureBtn.classList.remove('capturing'); }, 400);

            // Create composite
            var canvas = createCompositeCapture();
            if (!canvas) {
                showToast('Camera not ready');
                return;
            }

            // Get info for gallery
            var landmarkRaw = (detectionLabel && detectionLabel.textContent) ? detectionLabel.textContent.trim() : '';
            var confidence  = (detectionConf && detectionConf.textContent) ? detectionConf.textContent.trim() : '';
            var landmarkName = prettifyName(landmarkRaw);

            // Convert to dataURL for gallery storage
            var dataUrl = canvas.toDataURL('image/png');

            // Save to gallery
            addToGallery(dataUrl, landmarkRaw, confidence);

            // Download immediately
            downloadCapture(canvas, landmarkName);

            // Show toast
            showToast('Captured: ' + landmarkName);
        }

        // â”€â”€ Capture button visibility â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        /**
         * Show capture button when camera + model are both ready
         * and detection is running.
         */
        function updateCaptureButton() {
            if (!captureBtn) return;
            var camera  = window.wadjetCamera;
            var loop    = window.wadjetDetection;
            var hasStream  = camera && camera.getStream && camera.getStream();
            var isRunning  = loop && loop.isRunning;

            if (hasStream && isRunning) {
                captureBtn.style.display = '';
                captureBtn.disabled = false;
            } else if (hasStream) {
                captureBtn.style.display = '';
                captureBtn.disabled = false; // Allow capture even if detection paused
            } else {
                captureBtn.style.display = 'none';
            }
        }

        // Poll for state changes (lightweight â€” every 500ms)
        setInterval(updateCaptureButton, 500);

        // â”€â”€ Wire events â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        if (captureBtn) {
            captureBtn.addEventListener('click', handleCapture);
        }

        if (galleryClearBtn) {
            galleryClearBtn.addEventListener('click', function() {
                clearGallery();
                showToast('Gallery cleared');
            });
        }

        // Initial gallery render from existing localStorage
        renderGallery();

        // â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        window.wadjetCapture = {
            capture: handleCapture,
            download: downloadCapture,
            share: shareCapture,
            gallery: {
                load: loadGallery,
                add: addToGallery,
                remove: removeFromGallery,
                clear: clearGallery,
                render: renderGallery
            },
            showPreview: showPreview,
            hidePreview: hidePreview
        };

    })();

    /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
       Phase 6.10 â€” Camera Settings Panel IIFE
       â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
    (function() {
        'use strict';

        // â”€â”€ Constants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var SETTINGS_KEY = 'wadjet_camera_settings';
        var DEFAULTS = {
            camera:      'environment',
            resolution:  '640',
            sensitivity: 'balanced',
            showFps:     false,
            sound:       false,
            flash:       false
        };

        // Sensitivity presets: { windowSize, hysteresis, intervalMs }
        var SENSITIVITY_MAP = {
            conservative: { windowSize: 7, hysteresis: 4, intervalMs: 600 },
            balanced:     { windowSize: 5, hysteresis: 3, intervalMs: 500 },
            aggressive:   { windowSize: 3, hysteresis: 2, intervalMs: 350 }
        };

        // Resolution presets: { width, height }
        var RESOLUTION_MAP = {
            '480':  { width: 640,  height: 480 },
            '640':  { width: 640,  height: 480 },
            '720':  { width: 1280, height: 720 },
            '1080': { width: 1920, height: 1080 }
        };

        // â”€â”€ DOM refs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var settingsBtn    = document.getElementById('camera-settings-btn');
        var settingsPanel  = document.getElementById('camera-settings-panel');
        var closeBtn       = document.getElementById('camera-settings-close');
        var resetBtn       = document.getElementById('camera-settings-reset');
        var cameraSelect   = document.getElementById('settings-camera-select');
        var resolutionSel  = document.getElementById('settings-resolution');
        var sensitivitySel = document.getElementById('settings-sensitivity');
        var fpsToggle      = document.getElementById('settings-show-fps');
        var soundToggle    = document.getElementById('settings-sound');
        var flashToggle    = document.getElementById('settings-flash');
        var flashGroup     = document.getElementById('settings-flash-group');

        if (!settingsBtn || !settingsPanel) return;

        // Beep audio context (lazy-created for sound-on-detection)
        var _audioCtx = null;

        // â”€â”€ localStorage persistence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function loadSettings() {
            try {
                var raw = localStorage.getItem(SETTINGS_KEY);
                if (raw) {
                    var parsed = JSON.parse(raw);
                    // Merge with defaults to fill any missing keys
                    var merged = {};
                    for (var k in DEFAULTS) {
                        merged[k] = (parsed[k] !== undefined) ? parsed[k] : DEFAULTS[k];
                    }
                    return merged;
                }
            } catch (e) { /* ignore */ }
            return JSON.parse(JSON.stringify(DEFAULTS));
        }

        function saveSettings(settings) {
            try {
                localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
            } catch (e) { /* ignore */ }
        }

        var _currentSettings = loadSettings();

        // â”€â”€ Toggle helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function isToggleOn(btn) {
            return btn && btn.getAttribute('aria-checked') === 'true';
        }

        function setToggle(btn, on) {
            if (!btn) return;
            btn.setAttribute('aria-checked', on ? 'true' : 'false');
        }

        function wireToggle(btn, settingKey) {
            if (!btn) return;
            btn.addEventListener('click', function() {
                var newVal = !isToggleOn(btn);
                setToggle(btn, newVal);
                _currentSettings[settingKey] = newVal;
                saveSettings(_currentSettings);
                applySettings();
            });
        }

        // â”€â”€ Apply settings to camera/detection â”€â”€â”€â”€â”€â”€

        function applySettings() {
            var s = _currentSettings;

            // --- Sensitivity â†’ stabilizer + detection loop ---
            var preset = SENSITIVITY_MAP[s.sensitivity] || SENSITIVITY_MAP.balanced;

            // Update stabilizer if it exists
            var stabilizer = window.wadjetStabilizer;
            if (stabilizer) {
                stabilizer._windowSize = preset.windowSize;
                stabilizer._hysteresis = preset.hysteresis;
            }

            // Update detection loop interval
            var loop = window.wadjetDetection;
            if (loop) {
                loop._intervalMs = preset.intervalMs;
            }

            // --- FPS display ---
            var fpsEl = document.getElementById('detection-fps');
            if (fpsEl) {
                fpsEl.style.display = s.showFps ? '' : 'none';
            }

            // --- Flash / torch ---
            applyFlash(s.flash);

            // Note: camera & resolution changes require restart, handled separately
        }

        // â”€â”€ Flash (torch) support â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function checkFlashSupport() {
            var camera = window.wadjetCamera;
            if (!camera || !camera._stream) {
                if (flashGroup) flashGroup.classList.add('hidden');
                return;
            }
            var track = camera._stream.getVideoTracks()[0];
            if (!track) {
                if (flashGroup) flashGroup.classList.add('hidden');
                return;
            }
            try {
                var caps = track.getCapabilities ? track.getCapabilities() : {};
                if (caps.torch) {
                    if (flashGroup) flashGroup.classList.remove('hidden');
                } else {
                    if (flashGroup) flashGroup.classList.add('hidden');
                }
            } catch (e) {
                if (flashGroup) flashGroup.classList.add('hidden');
            }
        }

        function applyFlash(on) {
            var camera = window.wadjetCamera;
            if (!camera || !camera._stream) return;
            var track = camera._stream.getVideoTracks()[0];
            if (!track) return;
            try {
                var caps = track.getCapabilities ? track.getCapabilities() : {};
                if (caps.torch) {
                    track.applyConstraints({ advanced: [{ torch: !!on }] }).catch(function() {});
                }
            } catch (e) { /* ignore */ }
        }

        // â”€â”€ Sound on detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function playDetectionBeep() {
            if (!_currentSettings.sound) return;
            try {
                if (!_audioCtx) {
                    _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                }
                var osc = _audioCtx.createOscillator();
                var gain = _audioCtx.createGain();
                osc.connect(gain);
                gain.connect(_audioCtx.destination);
                osc.type = 'sine';
                osc.frequency.value = 880;
                gain.gain.value = 0.15;
                osc.start();
                gain.gain.exponentialRampToValueAtTime(0.001, _audioCtx.currentTime + 0.15);
                osc.stop(_audioCtx.currentTime + 0.15);
            } catch (e) { /* ignore */ }
        }

        // â”€â”€ Camera/resolution restart â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function applyCamera(facingMode, resKey) {
            var camera = window.wadjetCamera;
            if (!camera) return;
            if (camera._state !== 'active') return;

            var res = RESOLUTION_MAP[resKey] || RESOLUTION_MAP['640'];

            // Update internal preferred settings
            camera._facingMode = facingMode;
            camera._preferredWidth = res.width;
            camera._preferredHeight = res.height;

            // Stop current stream and reinit
            camera.stop();
            setTimeout(function() {
                camera.initCamera();
            }, 200);
        }

        // â”€â”€ Panel show/hide â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function showPanel() {
            settingsPanel.classList.remove('hidden');
            void settingsPanel.offsetWidth;
            settingsPanel.classList.add('settings-visible');
            settingsBtn.classList.add('settings-open');
            checkFlashSupport();
        }

        function hidePanel() {
            settingsPanel.classList.remove('settings-visible');
            settingsBtn.classList.remove('settings-open');
            setTimeout(function() {
                settingsPanel.classList.add('hidden');
            }, 200);
        }

        function togglePanel() {
            if (settingsPanel.classList.contains('settings-visible')) {
                hidePanel();
            } else {
                showPanel();
            }
        }

        // â”€â”€ Populate UI from settings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function populateUI() {
            var s = _currentSettings;
            if (cameraSelect)   cameraSelect.value   = s.camera;
            if (resolutionSel)  resolutionSel.value   = s.resolution;
            if (sensitivitySel) sensitivitySel.value   = s.sensitivity;
            setToggle(fpsToggle,   s.showFps);
            setToggle(soundToggle, s.sound);
            setToggle(flashToggle, s.flash);
        }

        // â”€â”€ Reset to defaults â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function resetDefaults() {
            _currentSettings = JSON.parse(JSON.stringify(DEFAULTS));
            saveSettings(_currentSettings);
            populateUI();
            applySettings();
        }

        // â”€â”€ Settings button visibility â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function updateSettingsButton() {
            if (!settingsBtn) return;
            var camera = window.wadjetCamera;
            if (camera && camera._stream && camera._state === 'active') {
                settingsBtn.style.display = '';
            } else {
                settingsBtn.style.display = 'none';
                // Auto-hide panel if camera stops
                if (settingsPanel.classList.contains('settings-visible')) {
                    hidePanel();
                }
            }
        }

        setInterval(updateSettingsButton, 500);

        // â”€â”€ Wire event listeners â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        settingsBtn.addEventListener('click', togglePanel);

        if (closeBtn) {
            closeBtn.addEventListener('click', hidePanel);
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', resetDefaults);
        }

        // Select changes
        if (cameraSelect) {
            cameraSelect.addEventListener('change', function() {
                _currentSettings.camera = cameraSelect.value;
                saveSettings(_currentSettings);
                applyCamera(cameraSelect.value, _currentSettings.resolution);
            });
        }

        if (resolutionSel) {
            resolutionSel.addEventListener('change', function() {
                _currentSettings.resolution = resolutionSel.value;
                saveSettings(_currentSettings);
                applyCamera(_currentSettings.camera, resolutionSel.value);
            });
        }

        if (sensitivitySel) {
            sensitivitySel.addEventListener('change', function() {
                _currentSettings.sensitivity = sensitivitySel.value;
                saveSettings(_currentSettings);
                applySettings();
            });
        }

        // Toggles
        wireToggle(fpsToggle, 'showFps');
        wireToggle(soundToggle, 'sound');
        wireToggle(flashToggle, 'flash');

        // Escape key closes panel
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && settingsPanel.classList.contains('settings-visible')) {
                hidePanel();
            }
        });

        // Listen for stable detection to play beep
        window.addEventListener('wadjet:stable-detection', function() {
            playDetectionBeep();
        });

        // â”€â”€ Startup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        populateUI();
        applySettings();

        // â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        window.wadjetSettings = {
            get:        function() { return JSON.parse(JSON.stringify(_currentSettings)); },
            save:       saveSettings,
            load:       loadSettings,
            apply:      applySettings,
            reset:      resetDefaults,
            show:       showPanel,
            hide:       hidePanel,
            toggle:     togglePanel,
            playBeep:   playDetectionBeep,
            DEFAULTS:   DEFAULTS,
            SENSITIVITY_MAP: SENSITIVITY_MAP,
            RESOLUTION_MAP:  RESOLUTION_MAP
        };

    })();

    // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    //  Phase 6.11 â€” Offline Mode IIFE
    //  Monitors online/offline status, shows indicator, manages
    //  offline-readiness of camera + detection pipeline.
    // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    (function() {
        'use strict';

        // â”€â”€ DOM references â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var indicator    = document.getElementById('offline-indicator');
        var indicatorTxt = indicator ? indicator.querySelector('.offline-indicator-text') : null;
        var indicatorSvg = indicator ? indicator.querySelector('.offline-indicator-icon') : null;

        if (!indicator) return;

        // â”€â”€ State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var _isOnline = navigator.onLine;
        var _flashTimer = null;

        // â”€â”€ Online/offline SVG icons â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var WIFI_OFF_SVG = '<line x1="1" y1="1" x2="23" y2="23"></line>' +
            '<path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"></path>' +
            '<path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"></path>' +
            '<path d="M10.71 5.05A16 16 0 0 1 22.56 9"></path>' +
            '<path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"></path>' +
            '<path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>' +
            '<line x1="12" y1="20" x2="12.01" y2="20"></line>';

        var WIFI_ON_SVG = '<path d="M5 12.55a11 11 0 0 1 14.08 0"></path>' +
            '<path d="M1.42 9a16 16 0 0 1 21.16 0"></path>' +
            '<path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>' +
            '<line x1="12" y1="20" x2="12.01" y2="20"></line>';

        // â”€â”€ Show / hide indicator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function showOffline() {
            _isOnline = false;
            indicator.classList.remove('online-flash');
            if (indicatorSvg) indicatorSvg.innerHTML = WIFI_OFF_SVG;
            if (indicatorTxt) indicatorTxt.textContent = 'Offline';
            indicator.classList.remove('hidden');
            // Small delay so CSS transition triggers
            requestAnimationFrame(function() {
                indicator.classList.add('offline-visible');
            });
            console.log('[Wadjet Offline] Network offline â€” detection still active');
        }

        function showOnlineFlash() {
            _isOnline = true;
            indicator.classList.add('online-flash');
            if (indicatorSvg) indicatorSvg.innerHTML = WIFI_ON_SVG;
            if (indicatorTxt) indicatorTxt.textContent = 'Back online';
            indicator.classList.remove('hidden');
            requestAnimationFrame(function() {
                indicator.classList.add('offline-visible');
            });
            console.log('[Wadjet Offline] Network restored');

            // Auto-hide after 3 seconds
            if (_flashTimer) clearTimeout(_flashTimer);
            _flashTimer = setTimeout(function() {
                indicator.classList.remove('offline-visible');
                setTimeout(function() {
                    indicator.classList.add('hidden');
                    indicator.classList.remove('online-flash');
                }, 400);
            }, 3000);
        }

        function hideIndicator() {
            indicator.classList.remove('offline-visible');
            setTimeout(function() {
                indicator.classList.add('hidden');
            }, 400);
        }

        // â”€â”€ Event listeners â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        window.addEventListener('online', function() {
            showOnlineFlash();
        });

        window.addEventListener('offline', function() {
            if (_flashTimer) clearTimeout(_flashTimer);
            showOffline();
        });

        // â”€â”€ Initial state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        if (!navigator.onLine) {
            // Start offline â€” show immediately
            showOffline();
        }

        // â”€â”€ Visibility-based check â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        // Re-check status when tab becomes visible (handles edge cases)
        document.addEventListener('visibilitychange', function() {
            if (document.visibilityState === 'visible') {
                var nowOnline = navigator.onLine;
                if (nowOnline && !_isOnline) {
                    showOnlineFlash();
                } else if (!nowOnline && _isOnline) {
                    showOffline();
                }
            }
        });

        // â”€â”€ Enrichment cache info helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        function getEnrichmentCacheStats() {
            var count = 0;
            var totalSize = 0;
            for (var i = 0; i < localStorage.length; i++) {
                var key = localStorage.key(i);
                if (key && key.indexOf('wadjet_enrich_') === 0) {
                    count++;
                    try { totalSize += localStorage.getItem(key).length * 2; } catch (_) {}
                }
            }
            return { count: count, sizeBytes: totalSize };
        }

        function clearEnrichmentCache() {
            var keys = [];
            for (var i = 0; i < localStorage.length; i++) {
                var key = localStorage.key(i);
                if (key && key.indexOf('wadjet_enrich_') === 0) {
                    keys.push(key);
                }
            }
            keys.forEach(function(k) { localStorage.removeItem(k); });
            return keys.length;
        }

        // â”€â”€ Offline readiness check â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        function checkOfflineReadiness() {
            var classifier = window.wadjetClassifier;
            var modelReady = !!(classifier && classifier.isReady);
            var metadataCached = !!localStorage.getItem('wadjet_model_metadata');
            var enrichStats = getEnrichmentCacheStats();

            return {
                modelLoaded: modelReady,
                metadataCached: metadataCached,
                enrichmentsCached: enrichStats.count,
                enrichmentCacheSize: enrichStats.sizeBytes,
                isOnline: navigator.onLine,
                fullyOfflineCapable: modelReady && metadataCached
            };
        }

        // â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        window.wadjetOffline = {
            isOnline:       function() { return _isOnline; },
            showOffline:    showOffline,
            showOnline:     showOnlineFlash,
            hide:           hideIndicator,
            checkReadiness: checkOfflineReadiness,
            cacheStats:     getEnrichmentCacheStats,
            clearCache:     clearEnrichmentCache
        };

    })();

    // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    //  Phase 6.12 â€” Performance Monitoring IIFE
    //  Tracks backend status, FPS, memory, tensor leaks, and
    //  renders a compact performance badge on the camera viewport.
    // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    (function() {
        'use strict';

        // â”€â”€ DOM references â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var badge = document.getElementById('perf-badge');

        if (!badge) return;

        // â”€â”€ State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var _updateIntervalId = null;
        var _backend = 'â€¦';
        var _lastFps  = 0;
        var _lastInfMs = 0;
        var _lastTensors = 0;
        var _memWarning = false;

        // â”€â”€ Rendering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function updateBadge() {
            var cls = window.wadjetClassifier;
            var loop = window.wadjetDetection;

            // Backend name
            if (cls && cls.isReady && typeof tf !== 'undefined') {
                _backend = tf.getBackend() || '?';
            }

            // FPS from detection loop
            if (loop && loop.isRunning) {
                _lastFps = loop.currentFps || 0;
            } else {
                _lastFps = 0;
            }

            // Inference time
            if (cls && cls.lastInferenceMs > 0) {
                _lastInfMs = cls.lastInferenceMs;
            }

            // Tensor count
            if (typeof tf !== 'undefined') {
                _lastTensors = tf.memory().numTensors;
            }

            // Check for memory warnings
            if (cls && cls.isReady && cls.baselineTensors > 0) {
                var delta = _lastTensors - cls.baselineTensors;
                _memWarning = delta > 5;
            }

            // Build badge text
            var parts = [];
            parts.push(_backend.toUpperCase());
            if (_lastFps > 0) {
                parts.push(_lastFps.toFixed(1) + ' FPS');
            }
            if (_lastInfMs > 0) {
                parts.push(_lastInfMs + 'ms');
            }
            parts.push(_lastTensors + 'T');

            badge.textContent = parts.join(' Â· ');

            // Visual state
            if (_memWarning) {
                badge.classList.add('perf-badge-warning');
            } else {
                badge.classList.remove('perf-badge-warning');
            }
        }

        // â”€â”€ Lifecycle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        function startMonitoring() {
            if (_updateIntervalId) return;
            badge.classList.remove('hidden');
            _updateIntervalId = setInterval(updateBadge, 2000);
            updateBadge(); // immediate first update
        }

        function stopMonitoring() {
            if (_updateIntervalId) {
                clearInterval(_updateIntervalId);
                _updateIntervalId = null;
            }
            badge.classList.add('hidden');
        }

        // Auto-start when the FPS toggle is on (Phase 6.10 settings)
        function checkFpsToggle() {
            var settings = window.wadjetSettings;
            if (settings) {
                var s = settings.get();
                if (s && s.showFps) {
                    startMonitoring();
                } else {
                    stopMonitoring();
                }
            }
        }

        // Poll settings state (lightweight)
        setInterval(checkFpsToggle, 1000);

        // Listen for memory warnings from classifier
        window.addEventListener('wadjet:memory-warning', function(e) {
            var profile = e.detail || {};
            badge.classList.add('perf-badge-warning');
            console.warn('[Wadjet Perf] Memory warning displayed â€” ' +
                'tensors: ' + (profile.current ? profile.current.tensors : '?') +
                ', delta: +' + (profile.delta ? profile.delta.tensors : '?'));
        });

        // â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        window.wadjetPerf = {
            start:    startMonitoring,
            stop:     stopMonitoring,
            update:   updateBadge,
            getStats: function() {
                var cls = window.wadjetClassifier;
                var loop = window.wadjetDetection;
                return {
                    backend:     _backend,
                    fps:         _lastFps,
                    inferenceMs: _lastInfMs,
                    tensors:     _lastTensors,
                    memWarning:  _memWarning,
                    memProfile:  cls && cls.isReady ? cls.getMemoryProfile() : null,
                    loopStats:   loop ? loop.getStats() : null,
                    classifierInfo: cls ? cls.getInfo() : null
                };
            }
        };

    })();

    /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
       Phase 6.13 â€” Mobile-Specific Camera Optimizations IIFE
       Provides:
         â€¢ Device detection (mobile, low-end, device profile)
         â€¢ Battery-conscious visibility pause (pause detection when tab hidden)
         â€¢ Device-adaptive detection frequency (1 FPS on low-end)
         â€¢ Fullscreen camera toggle (Fullscreen API + CSS fallback)
         â€¢ Auto-apply mobile optimizations on startup
       â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
    (function() {
        'use strict';

        // â”€â”€ DOM references â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var viewport        = document.getElementById('camera-viewport');
        var fullscreenBtn   = document.getElementById('camera-fullscreen-btn');
        var expandIcon      = document.getElementById('fullscreen-icon-expand');
        var collapseIcon    = document.getElementById('fullscreen-icon-collapse');

        // â”€â”€ Device Detection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        /**
         * Detect if the current device is mobile/tablet.
         * Uses userAgent + touch + screen heuristics.
         */
        function isMobile() {
            // Primary: userAgent check
            var ua = navigator.userAgent || '';
            var mobileRe = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|Tablet/i;
            if (mobileRe.test(ua)) return true;

            // Secondary: touch + small screen
            var hasTouch = ('ontouchstart' in window) ||
                           (navigator.maxTouchPoints && navigator.maxTouchPoints > 0);
            var smallScreen = Math.min(window.screen.width, window.screen.height) < 768;
            if (hasTouch && smallScreen) return true;

            // Tertiary: iPad with desktop UA (iPadOS 13+)
            if (hasTouch && /Macintosh/i.test(ua) && navigator.maxTouchPoints > 1) return true;

            return false;
        }

        /**
         * Detect if the device is low-end based on hardware hints.
         * Returns true if: <=4 cores, <=4GB RAM, or slow connection.
         */
        function isLowEnd() {
            // CPU cores (non-standard but widely supported)
            var cores = navigator.hardwareConcurrency || 0;
            if (cores > 0 && cores <= 4) return true;

            // Device memory (Chrome/Android only, in GB)
            var mem = navigator.deviceMemory || 0;
            if (mem > 0 && mem <= 4) return true;

            // Slow network connection (Network Information API)
            var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
            if (conn) {
                var ect = conn.effectiveType || '';
                if (ect === 'slow-2g' || ect === '2g' || ect === '3g') return true;
                if (conn.saveData) return true;
            }

            return false;
        }

        /**
         * Build a comprehensive device profile.
         */
        function getDeviceProfile() {
            var mobile = isMobile();
            var lowEnd = isLowEnd();
            var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
            return {
                isMobile:    mobile,
                isLowEnd:    lowEnd,
                cores:       navigator.hardwareConcurrency || 0,
                memoryGB:    navigator.deviceMemory || 0,
                screenWidth: window.screen.width,
                screenHeight: window.screen.height,
                pixelRatio:  window.devicePixelRatio || 1,
                touchPoints: navigator.maxTouchPoints || 0,
                connection:  conn ? (conn.effectiveType || 'unknown') : 'unknown',
                saveData:    conn ? !!conn.saveData : false,
                platform:    navigator.platform || 'unknown',
                tier:        lowEnd ? 'low' : (mobile ? 'mid' : 'high')
            };
        }

        // Cache the profile (won't change during session)
        var _profile = getDeviceProfile();

        console.log('[Wadjet Mobile] Device profile:', _profile.tier,
            '(mobile=' + _profile.isMobile +
            ', lowEnd=' + _profile.isLowEnd +
            ', cores=' + _profile.cores +
            ', mem=' + _profile.memoryGB + 'GB)');

        // â”€â”€ Battery-Conscious Visibility Pause â”€â”€â”€â”€â”€

        var _wasRunningBeforeHidden = false;
        var _visibilityPauseEnabled = true;

        function onVisibilityChange() {
            if (!_visibilityPauseEnabled) return;

            var loop = window.wadjetDetection;
            if (!loop) return;

            if (document.visibilityState === 'hidden') {
                // Page is hidden â€” pause detection to save battery
                if (loop.isRunning) {
                    _wasRunningBeforeHidden = true;
                    loop.pause();
                    console.log('[Wadjet Mobile] Detection paused â€” page hidden (battery save)');
                } else {
                    _wasRunningBeforeHidden = false;
                }
            } else if (document.visibilityState === 'visible') {
                // Page is visible again â€” resume if we paused it
                if (_wasRunningBeforeHidden && loop.isPaused) {
                    loop.resume();
                    console.log('[Wadjet Mobile] Detection resumed â€” page visible');
                    _wasRunningBeforeHidden = false;
                }
            }
        }

        document.addEventListener('visibilitychange', onVisibilityChange);

        // â”€â”€ Device-Adaptive Detection Frequency â”€â”€â”€â”€

        /**
         * Apply optimal settings based on device capabilities.
         * Called once on startup (after detection loop is available).
         */
        function applyAdaptiveSettings() {
            var loop = window.wadjetDetection;
            var stabilizer = window.wadjetStabilizer;

            if (_profile.isLowEnd) {
                // Low-end: 1 FPS, conservative stabilizer
                if (loop) {
                    loop._intervalMs = 1000;
                    console.log('[Wadjet Mobile] Low-end device â€” detection interval: 1000ms (1 FPS)');
                }
                if (stabilizer) {
                    stabilizer._windowSize = 7;
                    stabilizer._hysteresis = 4;
                }
            } else if (_profile.isMobile) {
                // Mobile mid-tier: ~1.5 FPS
                if (loop) {
                    loop._intervalMs = 650;
                    console.log('[Wadjet Mobile] Mobile device â€” detection interval: 650ms (~1.5 FPS)');
                }
            }
            // Desktop: keep defaults (500ms / ~2 FPS)
        }

        // â”€â”€ Fullscreen Camera Toggle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        var _isFullscreen = false;

        function isFullscreenSupported() {
            return !!(document.fullscreenEnabled ||
                      document.webkitFullscreenEnabled ||
                      document.mozFullScreenEnabled ||
                      document.msFullscreenEnabled);
        }

        function requestFullscreen(el) {
            if (el.requestFullscreen)            return el.requestFullscreen();
            if (el.webkitRequestFullscreen)      return el.webkitRequestFullscreen();
            if (el.mozRequestFullScreen)          return el.mozRequestFullScreen();
            if (el.msRequestFullscreen)           return el.msRequestFullscreen();
            return Promise.reject(new Error('Fullscreen API not supported'));
        }

        function exitFullscreen() {
            if (document.exitFullscreen)          return document.exitFullscreen();
            if (document.webkitExitFullscreen)    return document.webkitExitFullscreen();
            if (document.mozCancelFullScreen)      return document.mozCancelFullScreen();
            if (document.msExitFullscreen)         return document.msExitFullscreen();
            return Promise.reject(new Error('Fullscreen API not supported'));
        }

        function getFullscreenElement() {
            return document.fullscreenElement ||
                   document.webkitFullscreenElement ||
                   document.mozFullScreenElement ||
                   document.msFullscreenElement || null;
        }

        function updateFullscreenUI(isFs) {
            _isFullscreen = isFs;
            if (!expandIcon || !collapseIcon || !viewport) return;

            if (isFs) {
                expandIcon.classList.add('hidden');
                collapseIcon.classList.remove('hidden');
                viewport.classList.add('camera-fullscreen');
            } else {
                collapseIcon.classList.add('hidden');
                expandIcon.classList.remove('hidden');
                viewport.classList.remove('camera-fullscreen');
            }
        }

        function toggleFullscreen() {
            if (!viewport) return;

            if (getFullscreenElement()) {
                exitFullscreen().catch(function(err) {
                    console.warn('[Wadjet Mobile] Exit fullscreen failed:', err.message);
                    // CSS fallback â€” remove class
                    updateFullscreenUI(false);
                });
            } else if (isFullscreenSupported()) {
                requestFullscreen(viewport).catch(function(err) {
                    console.warn('[Wadjet Mobile] Fullscreen API failed, using CSS fallback:', err.message);
                    // CSS-only fallback for browsers that block fullscreen
                    updateFullscreenUI(true);
                });
            } else {
                // No Fullscreen API â€” CSS-only toggle
                updateFullscreenUI(!_isFullscreen);
            }
        }

        // Listen for fullscreen changes (handles Esc key, etc.)
        function onFullscreenChange() {
            var isFs = !!getFullscreenElement();
            updateFullscreenUI(isFs);
        }

        document.addEventListener('fullscreenchange', onFullscreenChange);
        document.addEventListener('webkitfullscreenchange', onFullscreenChange);
        document.addEventListener('mozfullscreenchange', onFullscreenChange);
        document.addEventListener('MSFullscreenChange', onFullscreenChange);

        // Bind fullscreen button
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', toggleFullscreen);
        }

        // â”€â”€ Show fullscreen button when camera is active â”€â”€â”€

        function showFullscreenButton() {
            if (fullscreenBtn) fullscreenBtn.style.display = '';
        }

        function hideFullscreenButton() {
            if (fullscreenBtn) fullscreenBtn.style.display = 'none';
        }

        // Watch camera state for showing/hiding fullscreen button
        var _cameraCheckInterval = setInterval(function() {
            var cam = window.wadjetCamera;
            if (cam && cam.state === 'active') {
                showFullscreenButton();
            } else if (cam && (cam.state === 'stopped' || cam.state === 'idle')) {
                hideFullscreenButton();
                // Exit fullscreen if camera stops
                if (_isFullscreen) {
                    if (getFullscreenElement()) {
                        exitFullscreen().catch(function() {});
                    }
                    updateFullscreenUI(false);
                }
            }
        }, 500);

        // â”€â”€ Auto-Apply on Startup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        /**
         * Wait for detection loop to be available, then apply adaptive settings.
         * Respects user-saved settings from Phase 6.10 (don't override if user changed).
         */
        function autoApplyOnStartup() {
            var retries = 0;
            var maxRetries = 20; // 10 seconds

            var checkInterval = setInterval(function() {
                retries++;
                var loop = window.wadjetDetection;
                if (loop || retries >= maxRetries) {
                    clearInterval(checkInterval);

                    if (loop) {
                        // Only apply adaptive settings if user hasn't customized sensitivity
                        var settings = window.wadjetSettings;
                        var userCustomized = false;
                        if (settings) {
                            var s = settings.get();
                            if (s && s.sensitivity !== 'balanced') {
                                userCustomized = true;
                            }
                        }

                        if (!userCustomized) {
                            applyAdaptiveSettings();
                        } else {
                            console.log('[Wadjet Mobile] User has customized settings â€” skipping adaptive defaults');
                        }
                    }
                }
            }, 500);
        }

        autoApplyOnStartup();

        // â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        window.wadjetMobile = {
            isMobile:            isMobile,
            isLowEnd:            isLowEnd,
            getDeviceProfile:    getDeviceProfile,
            profile:             _profile,
            toggleFullscreen:    toggleFullscreen,
            isFullscreen:        function() { return _isFullscreen; },
            setVisibilityPause:  function(enabled) {
                _visibilityPauseEnabled = !!enabled;
                console.log('[Wadjet Mobile] Visibility pause ' + (enabled ? 'enabled' : 'disabled'));
            },
            applyAdaptive:       applyAdaptiveSettings
        };

    })();

    /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
       Phase 7.1 â€” History / Gallery IIFE
       Saves identification records to localStorage when user
       views enrichment data via "Learn More". Max 50 entries.
       â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
    (function() {
        'use strict';

        var HISTORY_KEY = 'wadjet_history';
        var MAX_ITEMS   = 50;

        // â”€â”€ Storage helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        function loadHistory() {
            try {
                var raw = localStorage.getItem(HISTORY_KEY);
                return raw ? JSON.parse(raw) : [];
            } catch (_) { return []; }
        }

        function saveHistory(items) {
            try {
                localStorage.setItem(HISTORY_KEY, JSON.stringify(items));
            } catch (e) {
                // Quota exceeded â€” remove oldest and retry
                if (items.length > 1) {
                    items.shift();
                    saveHistory(items);
                }
            }
        }

        /**
         * Capture a small JPEG thumbnail from the camera for the history entry.
         * Returns a data URL string or empty string.
         */
        function captureThumbnail() {
            try {
                var cam = window.wadjetCamera;
                if (!cam || !cam._videoEl || cam._videoEl.paused) return '';

                var video = cam._videoEl;
                var w = 200;
                var h = Math.round(w * (video.videoHeight / (video.videoWidth || 1)));
                if (h < 1) h = 150;

                var c = document.createElement('canvas');
                c.width = w;
                c.height = h;
                var ctx = c.getContext('2d');
                ctx.drawImage(video, 0, 0, w, h);
                return c.toDataURL('image/jpeg', 0.6);
            } catch (_) {
                return '';
            }
        }

        /**
         * Add a new identification to history.
         */
        function addToHistory(entry) {
            var items = loadHistory();

            // Deduplicate: if same className within last 30 seconds, skip
            var now = Date.now();
            for (var i = items.length - 1; i >= 0; i--) {
                if (items[i].className === entry.className) {
                    var prev = new Date(items[i].timestamp).getTime();
                    if (now - prev < 30000) {
                        console.log('[Wadjet History] Skipping duplicate within 30s');
                        return;
                    }
                    break;
                }
            }

            items.push(entry);

            // Trim to max
            while (items.length > MAX_ITEMS) {
                items.shift();
            }

            saveHistory(items);
            console.log('[Wadjet History] Saved: ' + entry.displayName + ' (' + items.length + '/' + MAX_ITEMS + ')');
        }

        // â”€â”€ Hook into Learn More enrichment â”€â”€â”€â”€â”€â”€â”€â”€
        // The Learn More IIFE dispatches content populated via populateContent.
        // We intercept the wadjet:learn-more event and wait for enrichment to complete.
        var _pendingClassName  = '';
        var _pendingConfidence = 0;
        var _pendingThumbnail  = '';

        window.addEventListener('wadjet:learn-more', function(e) {
            var detail = e.detail || {};
            _pendingClassName  = detail.className  || '';
            _pendingConfidence = detail.confidence  || 0;
            // Capture thumbnail at the moment user taps "Learn More"
            _pendingThumbnail  = captureThumbnail();
        });

        // Observe when learn-more-content becomes visible (enrichment succeeded)
        var learnMoreContent = document.getElementById('learn-more-content');

        if (learnMoreContent) {
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(m) {
                    if (m.type === 'attributes' && m.attributeName === 'class') {
                        // Content just became visible â†’ enrichment succeeded
                        if (!learnMoreContent.classList.contains('hidden') && _pendingClassName) {
                            var nameEl = document.getElementById('learn-more-name');
                            var descEl = document.getElementById('learn-more-desc');

                            var entry = {
                                id:          Date.now(),
                                className:   _pendingClassName,
                                displayName: nameEl ? nameEl.textContent : _pendingClassName,
                                confidence:  _pendingConfidence,
                                timestamp:   new Date().toISOString(),
                                thumbnail:   _pendingThumbnail,
                                description: descEl ? descEl.textContent.substring(0, 120) : ''
                            };

                            addToHistory(entry);

                            // Reset pending
                            _pendingClassName  = '';
                            _pendingConfidence = 0;
                            _pendingThumbnail  = '';
                        }
                    }
                });
            });

            observer.observe(learnMoreContent, { attributes: true, attributeFilter: ['class'] });
        }

        // â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        window.wadjetHistory = {
            load:    loadHistory,
            save:    saveHistory,
            add:     addToHistory,
            clear:   function() { saveHistory([]); },
            count:   function() { return loadHistory().length; },
            KEY:     HISTORY_KEY,
            MAX:     MAX_ITEMS
        };

        console.log('[Wadjet History] Initialized â€” ' + loadHistory().length + ' entries');
    })();

    /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
       Phase 7.2 â€” Favorites System IIFE
       Manages a favorites list in localStorage. Heart icon on
       the learn-more panel + badge count in navbar.
       â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
    (function() {
        'use strict';

        var FAVORITES_KEY = 'wadjet_favorites';

        // â”€â”€ Storage helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        function loadFavorites() {
            try {
                var raw = localStorage.getItem(FAVORITES_KEY);
                return raw ? JSON.parse(raw) : [];
            } catch (_) { return []; }
        }

        function saveFavorites(items) {
            try {
                localStorage.setItem(FAVORITES_KEY, JSON.stringify(items));
            } catch (_) {}
        }

        function isFavorited(className) {
            var favs = loadFavorites();
            for (var i = 0; i < favs.length; i++) {
                if (favs[i].className === className) return true;
            }
            return false;
        }

        function addFavorite(entry) {
            var favs = loadFavorites();
            // Don't duplicate
            for (var i = 0; i < favs.length; i++) {
                if (favs[i].className === entry.className) return;
            }
            favs.push(entry);
            saveFavorites(favs);
            updateBadge();
            console.log('[Wadjet Favorites] Added: ' + entry.displayName);
        }

        function removeFavorite(className) {
            var favs = loadFavorites();
            favs = favs.filter(function(f) { return f.className !== className; });
            saveFavorites(favs);
            updateBadge();
            console.log('[Wadjet Favorites] Removed: ' + className);
        }

        function toggleFavorite(entry) {
            if (isFavorited(entry.className)) {
                removeFavorite(entry.className);
                return false;
            } else {
                addFavorite(entry);
                return true;
            }
        }

        // â”€â”€ Navbar badge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        function updateBadge() {
            var count = loadFavorites().length;
            var badges = document.querySelectorAll('.fav-badge-count');
            for (var i = 0; i < badges.length; i++) {
                badges[i].textContent = count;
                if (count > 0) {
                    badges[i].classList.remove('hidden');
                } else {
                    badges[i].classList.add('hidden');
                }
            }
        }

        // â”€â”€ Learn-more panel heart button â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        var favBtn  = document.getElementById('learn-more-favorite');
        var favIcon = document.getElementById('learn-more-fav-icon');
        var favText = document.getElementById('learn-more-fav-text');
        var _currentClassName = '';

        function updateFavButton(className) {
            _currentClassName = className;
            if (!favBtn) return;
            var fav = isFavorited(className);
            if (favIcon) favIcon.textContent = fav ? 'â¤ï¸' : 'ðŸ¤';
            if (favText) favText.textContent = fav ? 'Favorited' : 'Favorite';
            favBtn.classList.toggle('learn-more-btn-fav-active', fav);
            favBtn.setAttribute('aria-label', fav ? 'Remove from favorites' : 'Add to favorites');
        }

        // Listen for learn-more showing a landmark
        window.addEventListener('wadjet:learn-more', function(e) {
            var detail = e.detail || {};
            if (detail.className) {
                // Slight delay to let panel populate
                setTimeout(function() {
                    updateFavButton(detail.className);
                }, 100);
            }
        });

        // Heart button click
        if (favBtn) {
            favBtn.addEventListener('click', function() {
                if (!_currentClassName) return;

                var nameEl = document.getElementById('learn-more-name');
                var descEl = document.getElementById('learn-more-desc');

                var entry = {
                    className:   _currentClassName,
                    displayName: nameEl ? nameEl.textContent : _currentClassName,
                    description: descEl ? descEl.textContent.substring(0, 120) : '',
                    timestamp:   new Date().toISOString()
                };

                toggleFavorite(entry);
                updateFavButton(_currentClassName);
            });
        }

        // â”€â”€ Initialize â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        updateBadge();

        // Cross-tab sync
        window.addEventListener('storage', function(e) {
            if (e.key === FAVORITES_KEY) {
                updateBadge();
                if (_currentClassName) updateFavButton(_currentClassName);
            }
        });

        // â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        window.wadjetFavorites = {
            load:       loadFavorites,
            save:       saveFavorites,
            add:        addFavorite,
            remove:     removeFavorite,
            toggle:     toggleFavorite,
            isFavorited: isFavorited,
            count:      function() { return loadFavorites().length; },
            updateBadge: updateBadge,
            KEY:        FAVORITES_KEY
        };

        console.log('[Wadjet Favorites] Initialized â€” ' + loadFavorites().length + ' favorites');
    })();

    /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
       Phase 7.8 â€” AR-Style Information Overlay
       Semi-transparent info card over the camera feed when a
       landmark is confidently detected.  Shows quick facts
       (name / era / builder) + "Full Story" CTA.  Animated
       connection line links the card to the detection pill.
       â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
    (function() {
        'use strict';

        /* â”€â”€ AR Landmark Metadata â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
           { className: [displayName, eraLabel, eraEmoji, builder, shortDesc] }
        */
        var M = {
            abu_simbel:                  ['Abu Simbel Temples','Pharaonic','ðŸ›ï¸','Ramesses II','Massive rock-cut temples relocated from Lake Nasser'],
            abydos_temple:               ['Abydos Temple','Pharaonic','ðŸ›ï¸','Seti I','Sacred temple with the Abydos King List'],
            akhenaten:                   ['Akhenaten','Artifact','ðŸº','18th Dynasty','Pharaoh who introduced Aten monotheism'],
            al_azhar_mosque:             ['Al-Azhar Mosque','Islamic','ðŸ•Œ','Fatimid Caliphate','Oldest university and Fatimid mosque in Cairo'],
            al_azhar_park:               ['Al-Azhar Park','Modern','ðŸ™ï¸','Aga Khan Trust','Green oasis built over Ayyubid-era ruins'],
            al_muizz_street:             ['Al-Muizz Street','Islamic','ðŸ•Œ','Fatimid Cairo','Medieval open-air museum of Islamic architecture'],
            amenhotep_iii:               ['Amenhotep III','Artifact','ðŸº','18th Dynasty','Builder of Luxor Temple and the Colossi'],
            aswan_high_dam:              ['Aswan High Dam','Modern','ðŸ™ï¸','Gamal Abdel Nasser','Engineering marvel controlling the Nile floods'],
            bab_zuweila:                 ['Bab Zuweila','Islamic','ðŸ•Œ','Fatimid Dynasty','Medieval gate with twin Mamluk minarets'],
            baron_empain_palace:         ['Baron Empain Palace','Modern','ðŸ™ï¸','Baron Ã‰douard Empain','Hindu-inspired palace in Heliopolis'],
            bent_pyramid:                ['Bent Pyramid','Pharaonic','ðŸ›ï¸','Pharaoh Sneferu','Unique pyramid with change of angle at Dahshur'],
            bibliotheca_alexandrina:     ['Bibliotheca Alexandrina','Modern','ðŸ™ï¸','Egyptian Gov. & UNESCO','Revival of the ancient Library of Alexandria'],
            cairo_citadel:               ['Cairo Citadel','Islamic','ðŸ•Œ','Saladin','Medieval fortress atop Mokattam Hill'],
            cairo_tower:                 ['Cairo Tower','Modern','ðŸ™ï¸','Naoum Shebib','Lotus-shaped tower with panoramic city views'],
            catacombs_of_kom_el_shoqafa: ['Catacombs of Kom el-Shoqafa','Greco-Roman','ðŸ›ï¸','Roman-era (2nd c.)','Multi-level burial chambers blending Egyptian & Greek art'],
            citadel_of_qaitbay:          ['Citadel of Qaitbay','Islamic','ðŸ•Œ','Sultan Qaitbay','Mamluk fortress on the site of the Pharos'],
            colossi_of_memnon:           ['Colossi of Memnon','Pharaonic','ðŸ›ï¸','Amenhotep III','Twin stone statues on Luxor\'s west bank'],
            deir_el_medina:              ['Deir el-Medina','Pharaonic','ðŸ›ï¸','New Kingdom','Workers\' village near the Valley of the Kings'],
            dendera_temple:              ['Dendera Temple','Pharaonic','ðŸ›ï¸','Ptolemaic Dynasty','Well-preserved Hathor temple with zodiac ceiling'],
            edfu_temple:                 ['Edfu Temple','Pharaonic','ðŸ›ï¸','Ptolemy III','Best-preserved Ptolemaic temple of Horus'],
            egyptian_museum_cairo:       ['Egyptian Museum','Modern','ðŸ™ï¸','Auguste Mariette','Home of Tutankhamun treasures and royal mummies'],
            grand_egyptian_museum:       ['Grand Egyptian Museum','Modern','ðŸ™ï¸','Egyptian Ministry','World\'s largest archaeological museum near Giza'],
            great_pyramids_of_giza:      ['Great Pyramids of Giza','Pharaonic','ðŸ›ï¸','Pharaoh Khufu','Last standing wonder of the ancient world'],
            great_sphinx_of_giza:        ['Great Sphinx of Giza','Pharaonic','ðŸ›ï¸','Pharaoh Khafre','Limestone lion-body with human head'],
            hanging_church:              ['Hanging Church','Greco-Roman','â›ª','Coptic Christians','Suspended over a Roman gate in Old Cairo'],
            ibn_tulun_mosque:            ['Ibn Tulun Mosque','Islamic','ðŸ•Œ','Ahmad ibn Tulun','Oldest intact mosque in Cairo (9th century)'],
            karnak_temple:               ['Karnak Temple','Pharaonic','ðŸ›ï¸','Multiple Pharaohs','Vast Amun-Ra complex with hypostyle hall'],
            khan_el_khalili:             ['Khan El-Khalili','Islamic','ðŸ•Œ','Emir Djaharks el-Khalili','Historic bazaar in the heart of medieval Cairo'],
            king_thutmose_iii:           ['King Thutmose III','Artifact','ðŸº','18th Dynasty','Warrior pharaoh â€” "Napoleon of Egypt"'],
            kom_ombo_temple:             ['Kom Ombo Temple','Pharaonic','ðŸ›ï¸','Ptolemaic Dynasty','Unique dual temple for Sobek and Horus'],
            luxor_temple:                ['Luxor Temple','Pharaonic','ðŸ›ï¸','Amenhotep III','Ancient Thebes temple on the Nile\'s east bank'],
            mask_of_tutankhamun:         ['Mask of Tutankhamun','Artifact','ðŸº','18th Dynasty Artisans','Gold funerary mask â€” Egypt\'s most iconic artifact'],
            medinet_habu:                ['Medinet Habu','Pharaonic','ðŸ›ï¸','Ramesses III','Mortuary temple on Luxor\'s west bank'],
            montaza_palace:              ['Montaza Palace','Modern','ðŸ™ï¸','Khedive Abbas II','Royal palace & gardens on the Mediterranean'],
            muhammad_ali_mosque:         ['Muhammad Ali Mosque','Islamic','ðŸ•Œ','Muhammad Ali Pasha','Alabaster Ottoman mosque crowning the Citadel'],
            nefertiti_bust:              ['Nefertiti Bust','Artifact','ðŸº','Sculptor Thutmose','Iconic painted bust of the Amarna queen'],
            philae_temple:               ['Philae Temple','Pharaonic','ðŸ›ï¸','Ptolemaic Dynasty','Isis temple relocated to Agilkia Island'],
            pompeys_pillar:              ['Pompey\'s Pillar','Greco-Roman','ðŸ›ï¸','Prefect Postumus','Tall Roman triumphal column in Alexandria'],
            pyramid_of_djoser:           ['Pyramid of Djoser','Pharaonic','ðŸ›ï¸','Imhotep','First monumental stone building in history'],
            ramesses_ii:                 ['Ramesses II','Artifact','ðŸº','19th Dynasty','Great builder of Abu Simbel and the Ramesseum'],
            ramesseum:                   ['Ramesseum','Pharaonic','ðŸ›ï¸','Ramesses II','Mortuary temple on Luxor\'s west bank'],
            red_pyramid:                 ['Red Pyramid','Pharaonic','ðŸ›ï¸','Pharaoh Sneferu','First true smooth-sided pyramid at Dahshur'],
            saint_catherine_monastery:   ['Saint Catherine\'s Monastery','Greco-Roman','â›ª','Emperor Justinian I','6th-century monastery at Mount Sinai'],
            siwa_oasis:                  ['Siwa Oasis','Natural','ðŸŒ¿','Natural Formation','Remote desert oasis with the Oracle of Ammon'],
            statue_of_tutankhamun:       ['Statue of Tutankhamun','Artifact','ðŸº','18th Dynasty Artisans','Gilded wooden statues from the boy king\'s tomb'],
            sultan_hassan_mosque:        ['Sultan Hassan Mosque','Islamic','ðŸ•Œ','Sultan Hassan','Imposing Mamluk mosque-madrassa near the Citadel'],
            temple_of_hatshepsut:        ['Temple of Hatshepsut','Pharaonic','ðŸ›ï¸','Senenmut','Terraced mortuary temple at Deir el-Bahari'],
            tomb_of_nefertari:           ['Tomb of Nefertari','Pharaonic','ðŸ›ï¸','Ramesses II','Most beautiful tomb with vivid wall murals'],
            unfinished_obelisk:          ['Unfinished Obelisk','Pharaonic','ðŸ›ï¸','Pharaoh Hatshepsut','Giant granite obelisk in Aswan quarries'],
            valley_of_the_kings:         ['Valley of the Kings','Pharaonic','ðŸ›ï¸','New Kingdom Pharaohs','Royal necropolis with Tutankhamun\'s tomb'],
            valley_of_the_queens:        ['Valley of the Queens','Pharaonic','ðŸ›ï¸','New Kingdom','Burial site for queens and princes near Luxor'],
            white_desert:                ['White Desert','Natural','ðŸŒ¿','Natural Formation','Surreal chalk formations in the western desert']
        };

        /* â”€â”€ DOM references â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
        var overlay      = document.getElementById('ar-overlay');
        var arName       = document.getElementById('ar-name');
        var arEraBadge   = document.getElementById('ar-era-badge');
        var arEraText    = document.getElementById('ar-era-text');
        var arBuilder    = document.getElementById('ar-builder');
        var arDesc       = document.getElementById('ar-desc');
        var arCloseBtn   = document.getElementById('ar-close');
        var arStoryBtn   = document.getElementById('ar-full-story');
        var learnMoreBtn = document.getElementById('detection-learn-more');

        if (!overlay) return;

        var _autoHideTimer = null;
        var _currentClass  = '';
        var AUTO_HIDE_MS   = 10000;

        /* â”€â”€ Show AR card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
        function showAR(className, confidence) {
            var meta = M[className];
            if (!meta) return;

            _currentClass = className;

            arName.textContent      = meta[0];
            arEraBadge.textContent  = meta[2] + ' ' + meta[1];
            arEraText.textContent   = meta[1];
            arBuilder.textContent   = meta[3];
            arDesc.textContent      = meta[4];

            /* Set era color class */
            overlay.className = 'ar-overlay ar-era-' + eraKey(meta[1]);

            /* Trigger CSS entrance */
            overlay.classList.remove('hidden');
            requestAnimationFrame(function() {
                overlay.classList.add('ar-visible');
            });

            /* Auto-hide after timeout */
            clearTimeout(_autoHideTimer);
            _autoHideTimer = setTimeout(hideAR, AUTO_HIDE_MS);
        }

        /* â”€â”€ Hide AR card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
        function hideAR() {
            clearTimeout(_autoHideTimer);
            overlay.classList.remove('ar-visible');
            setTimeout(function() {
                if (!overlay.classList.contains('ar-visible')) {
                    overlay.classList.add('hidden');
                    _currentClass = '';
                }
            }, 400);
        }

        /* â”€â”€ Era key for CSS color classes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
        function eraKey(label) {
            return label.toLowerCase().replace(/[^a-z]/g, '-');
        }

        /* â”€â”€ Listen for confident stable detections â”€ */
        window.addEventListener('wadjet:stable-detection', function(e) {
            var d = e.detail;
            if (d && d.className && d.confidence >= 0.75) {
                showAR(d.className, d.confidence);
            }
        });

        /* â”€â”€ Hide when learn-more panel opens â”€â”€â”€â”€â”€â”€â”€ */
        window.addEventListener('wadjet:learn-more', function() {
            hideAR();
        });

        /* â”€â”€ Hide when camera stops â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
        window.addEventListener('wadjet:camera-stopped', function() {
            hideAR();
        });

        /* â”€â”€ Close button â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
        arCloseBtn.addEventListener('click', function() {
            hideAR();
        });

        /* â”€â”€ "Full Story" triggers learn-more panel â”€ */
        arStoryBtn.addEventListener('click', function() {
            if (_currentClass && learnMoreBtn) {
                /* Simulate click on the detection "Tap to learn more" */
                learnMoreBtn.dataset.className = _currentClass;
                var meta = M[_currentClass];
                if (meta) {
                    learnMoreBtn.dataset.landmark   = meta[0];
                    learnMoreBtn.dataset.confidence  = '90';
                }
                learnMoreBtn.click();
            }
            hideAR();
        });

        /* â”€â”€ Keyboard: Escape to dismiss â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && overlay.classList.contains('ar-visible')) {
                hideAR();
                e.stopPropagation();
            }
        });

        console.log('[Wadjet AR] Phase 7.8 â€” AR Information Overlay initialized');
    })();
</script>
{% endblock %}
