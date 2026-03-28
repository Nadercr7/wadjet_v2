/**
 * Wadjet AI — Camera Access Module
 * Phase 6.1: WebRTC camera initialization
 *
 * Provides:
 *   WadjetCamera class with:
 *     - initCamera()    → request permission & start stream
 *     - getStream()     → return active MediaStream
 *     - captureFrame()  → grab current frame as ImageData
 *     - switchCamera()  → toggle front/back (mobile)
 *     - stop()          → release camera resources
 *
 * Error handling for: permission denied, no camera, insecure context, etc.
 */

'use strict';

/* ═══════════════════════════════════════════════
   CAMERA ERROR TYPES
   ═══════════════════════════════════════════════ */

/** @enum {string} */
const CameraError = Object.freeze({
  PERMISSION_DENIED: 'permission_denied',
  NOT_FOUND: 'not_found',
  NOT_SUPPORTED: 'not_supported',
  INSECURE_CONTEXT: 'insecure_context',
  IN_USE: 'in_use',
  OVERCONSTRAINED: 'overconstrained',
  UNKNOWN: 'unknown',
});

/** @enum {string} */
const CameraState = Object.freeze({
  IDLE: 'idle',
  REQUESTING: 'requesting',
  ACTIVE: 'active',
  ERROR: 'error',
  STOPPED: 'stopped',
});

/** @enum {string} */
const FacingMode = Object.freeze({
  USER: 'user',        // front camera
  ENVIRONMENT: 'environment', // rear camera
});

/* ═══════════════════════════════════════════════
   WADJET CAMERA CLASS
   ═══════════════════════════════════════════════ */

class WadjetCamera {
  /**
   * @param {Object} [options]
   * @param {HTMLVideoElement} [options.videoElement] - Target <video> element
   * @param {string} [options.facingMode='environment'] - 'user' or 'environment'
   * @param {number} [options.width=640] - Preferred capture width
   * @param {number} [options.height=480] - Preferred capture height
   * @param {Function} [options.onStateChange] - Callback: (state, detail) => void
   * @param {Function} [options.onError] - Callback: (errorType, message) => void
   */
  constructor(options = {}) {
    this._videoEl = options.videoElement || null;
    this._facingMode = options.facingMode || FacingMode.ENVIRONMENT;
    this._preferredWidth = options.width || 640;
    this._preferredHeight = options.height || 480;
    this._onStateChange = options.onStateChange || null;
    this._onError = options.onError || null;

    /** @type {MediaStream|null} */
    this._stream = null;
    /** @type {string} */
    this._state = CameraState.IDLE;
    /** @type {HTMLCanvasElement} */
    this._captureCanvas = document.createElement('canvas');
    /** @type {CanvasRenderingContext2D} */
    this._captureCtx = this._captureCanvas.getContext('2d', { willReadFrequently: true });
    /** @type {string[]} */
    this._availableDevices = [];
    /** @type {string|null} */
    this._currentDeviceId = null;
  }

  /* ── Public API ─────────────────────────────── */

  /**
   * Request camera permission and start the video stream.
   * @returns {Promise<MediaStream>} The active media stream
   * @throws {Error} If camera cannot be initialized
   */
  async initCamera() {
    // Pre-flight checks
    if (!this._checkSupport()) return null;

    this._setState(CameraState.REQUESTING);

    try {
      const constraints = this._buildConstraints();
      this._stream = await navigator.mediaDevices.getUserMedia(constraints);

      // Attach to video element if provided
      if (this._videoEl) {
        this._videoEl.srcObject = this._stream;
        this._videoEl.setAttribute('playsinline', '');
        this._videoEl.setAttribute('autoplay', '');
        this._videoEl.muted = true;

        // Wait for video to be ready
        await this._waitForVideoReady();
      }

      // Cache available devices for switching
      await this._enumerateDevices();

      // Track the active device ID
      const videoTrack = this._stream.getVideoTracks()[0];
      if (videoTrack) {
        const settings = videoTrack.getSettings();
        this._currentDeviceId = settings.deviceId || null;
        console.log(
          `[Wadjet Camera] Active: ${videoTrack.label || 'Camera'} ` +
          `(${settings.width}×${settings.height}, ${settings.facingMode || 'unknown'})`
        );
      }

      this._setState(CameraState.ACTIVE);
      return this._stream;
    } catch (err) {
      this._handleError(err);
      return null;
    }
  }

  /**
   * Get the current active MediaStream.
   * @returns {MediaStream|null}
   */
  getStream() {
    return this._stream;
  }

  /**
   * Capture the current video frame as ImageData.
   * Returns null if the camera is not active or video has no dimensions.
   * @param {number} [targetWidth] - Optional resize width (height auto-calculated)
   * @param {number} [targetHeight] - Optional resize height
   * @returns {ImageData|null}
   */
  captureFrame(targetWidth, targetHeight) {
    if (this._state !== CameraState.ACTIVE || !this._videoEl) {
      return null;
    }

    const vw = this._videoEl.videoWidth;
    const vh = this._videoEl.videoHeight;
    if (vw === 0 || vh === 0) return null;

    const outW = targetWidth || vw;
    const outH = targetHeight || vh;

    // Reuse canvas — resize only if needed
    if (this._captureCanvas.width !== outW || this._captureCanvas.height !== outH) {
      this._captureCanvas.width = outW;
      this._captureCanvas.height = outH;
    }

    this._captureCtx.drawImage(this._videoEl, 0, 0, outW, outH);
    return this._captureCtx.getImageData(0, 0, outW, outH);
  }

  /**
   * Capture frame as an HTMLCanvasElement (useful for TF.js fromPixels).
   * @param {number} [targetWidth] - Optional resize width
   * @param {number} [targetHeight] - Optional resize height
   * @returns {HTMLCanvasElement|null}
   */
  captureFrameAsCanvas(targetWidth, targetHeight) {
    if (this._state !== CameraState.ACTIVE || !this._videoEl) {
      return null;
    }

    const vw = this._videoEl.videoWidth;
    const vh = this._videoEl.videoHeight;
    if (vw === 0 || vh === 0) return null;

    const outW = targetWidth || vw;
    const outH = targetHeight || vh;

    if (this._captureCanvas.width !== outW || this._captureCanvas.height !== outH) {
      this._captureCanvas.width = outW;
      this._captureCanvas.height = outH;
    }

    this._captureCtx.drawImage(this._videoEl, 0, 0, outW, outH);
    return this._captureCanvas;
  }

  /**
   * Switch between front and rear cameras.
   * On desktop, cycles through available video devices.
   * @returns {Promise<boolean>} true if switched successfully
   */
  async switchCamera() {
    if (this._state !== CameraState.ACTIVE) return false;

    // Stop current stream
    this._stopTracks();

    try {
      if (this._availableDevices.length > 1) {
        // Cycle to next device
        const currentIdx = this._availableDevices.indexOf(this._currentDeviceId);
        const nextIdx = (currentIdx + 1) % this._availableDevices.length;
        const nextDeviceId = this._availableDevices[nextIdx];

        const constraints = {
          video: {
            deviceId: { exact: nextDeviceId },
            width: { ideal: this._preferredWidth },
            height: { ideal: this._preferredHeight },
          },
          audio: false,
        };

        this._stream = await navigator.mediaDevices.getUserMedia(constraints);
        this._currentDeviceId = nextDeviceId;
      } else {
        // Toggle facing mode (mobile fallback)
        this._facingMode =
          this._facingMode === FacingMode.ENVIRONMENT
            ? FacingMode.USER
            : FacingMode.ENVIRONMENT;

        const constraints = this._buildConstraints();
        this._stream = await navigator.mediaDevices.getUserMedia(constraints);
      }

      // Reattach to video element
      if (this._videoEl) {
        this._videoEl.srcObject = this._stream;
        await this._waitForVideoReady();
      }

      // Update current device ID
      const track = this._stream.getVideoTracks()[0];
      if (track) {
        this._currentDeviceId = track.getSettings().deviceId || null;
        console.log(`[Wadjet Camera] Switched to: ${track.label || 'Camera'}`);
      }

      this._setState(CameraState.ACTIVE);
      return true;
    } catch (err) {
      console.error('[Wadjet Camera] Switch failed:', err);
      // Try to restart with original camera
      try {
        const constraints = this._buildConstraints();
        this._stream = await navigator.mediaDevices.getUserMedia(constraints);
        if (this._videoEl) {
          this._videoEl.srcObject = this._stream;
          await this._waitForVideoReady();
        }
        this._setState(CameraState.ACTIVE);
      } catch {
        this._handleError(err);
      }
      return false;
    }
  }

  /**
   * Stop camera and release all resources.
   */
  stop() {
    this._stopTracks();
    if (this._videoEl) {
      this._videoEl.srcObject = null;
    }
    this._stream = null;
    this._setState(CameraState.STOPPED);
    console.log('[Wadjet Camera] Stopped');
  }

  /**
   * Check if the camera is currently active and streaming.
   * @returns {boolean}
   */
  get isActive() {
    return this._state === CameraState.ACTIVE && this._stream !== null;
  }

  /**
   * Get the current camera state.
   * @returns {string}
   */
  get state() {
    return this._state;
  }

  /**
   * Get the current facing mode (user/environment).
   * @returns {string}
   */
  get facingMode() {
    return this._facingMode;
  }

  /**
   * Get the video element's actual resolution.
   * @returns {{ width: number, height: number } | null}
   */
  get resolution() {
    if (!this._videoEl || this._state !== CameraState.ACTIVE) return null;
    return {
      width: this._videoEl.videoWidth,
      height: this._videoEl.videoHeight,
    };
  }

  /**
   * Get the number of available video devices.
   * @returns {number}
   */
  get deviceCount() {
    return this._availableDevices.length;
  }

  /**
   * Check whether getUserMedia is available in this browser.
   * @returns {boolean}
   */
  static isSupported() {
    return !!(
      navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === 'function'
    );
  }

  /**
   * Check whether the page is in a secure context (HTTPS or localhost).
   * @returns {boolean}
   */
  static isSecureContext() {
    return window.isSecureContext === true;
  }

  /* ── Private helpers ────────────────────────── */

  /**
   * Check browser support and security context.
   * @returns {boolean}
   */
  _checkSupport() {
    if (!WadjetCamera.isSecureContext()) {
      const msg = 'Camera requires HTTPS or localhost. Current context is insecure.';
      console.warn(`[Wadjet Camera] ${msg}`);
      this._setState(CameraState.ERROR, CameraError.INSECURE_CONTEXT);
      if (this._onError) this._onError(CameraError.INSECURE_CONTEXT, msg);
      return false;
    }
    if (!WadjetCamera.isSupported()) {
      const msg = 'getUserMedia is not supported in this browser.';
      console.warn(`[Wadjet Camera] ${msg}`);
      this._setState(CameraState.ERROR, CameraError.NOT_SUPPORTED);
      if (this._onError) this._onError(CameraError.NOT_SUPPORTED, msg);
      return false;
    }
    return true;
  }

  /**
   * Build getUserMedia constraints.
   * @returns {MediaStreamConstraints}
   */
  _buildConstraints() {
    return {
      video: {
        facingMode: { ideal: this._facingMode },
        width: { ideal: this._preferredWidth },
        height: { ideal: this._preferredHeight },
      },
      audio: false,
    };
  }

  /**
   * Wait for the video element to be ready to play.
   * @returns {Promise<void>}
   */
  _waitForVideoReady() {
    return new Promise((resolve, reject) => {
      const video = this._videoEl;
      if (!video) {
        reject(new Error('No video element'));
        return;
      }

      // Already playing
      if (video.readyState >= HTMLMediaElement.HAVE_ENOUGH_DATA) {
        resolve();
        return;
      }

      const onCanPlay = () => {
        cleanup();
        resolve();
      };
      const onError = () => {
        cleanup();
        reject(new Error('Video element error'));
      };
      const timeout = setTimeout(() => {
        cleanup();
        reject(new Error('Video ready timeout (5s)'));
      }, 5000);

      const cleanup = () => {
        video.removeEventListener('canplay', onCanPlay);
        video.removeEventListener('error', onError);
        clearTimeout(timeout);
      };

      video.addEventListener('canplay', onCanPlay);
      video.addEventListener('error', onError);

      // Ensure playback starts
      video.play().catch(() => {});
    });
  }

  /**
   * Enumerate available video input devices.
   */
  async _enumerateDevices() {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      this._availableDevices = devices
        .filter((d) => d.kind === 'videoinput' && d.deviceId)
        .map((d) => d.deviceId);
      console.log(`[Wadjet Camera] Found ${this._availableDevices.length} camera(s)`);
    } catch {
      this._availableDevices = [];
    }
  }

  /**
   * Stop all tracks on the current stream.
   */
  _stopTracks() {
    if (this._stream) {
      this._stream.getTracks().forEach((track) => track.stop());
    }
  }

  /**
   * Map a native error to a CameraError type and fire callbacks.
   * @param {Error} err
   */
  _handleError(err) {
    let errorType = CameraError.UNKNOWN;
    let message = err.message || 'Unknown camera error';

    if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
      errorType = CameraError.PERMISSION_DENIED;
      message = 'Camera permission was denied. Please allow camera access and try again.';
    } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
      errorType = CameraError.NOT_FOUND;
      message = 'No camera found on this device.';
    } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
      errorType = CameraError.IN_USE;
      message = 'Camera is in use by another application.';
    } else if (err.name === 'OverconstrainedError') {
      errorType = CameraError.OVERCONSTRAINED;
      message = 'Camera does not meet the requested constraints.';
    } else if (err.name === 'TypeError') {
      errorType = CameraError.NOT_SUPPORTED;
      message = 'Camera API is not available.';
    }

    console.error(`[Wadjet Camera] ${errorType}: ${message}`, err);
    this._setState(CameraState.ERROR, errorType);
    if (this._onError) this._onError(errorType, message);
  }

  /**
   * Update state and fire the onStateChange callback.
   * @param {string} newState
   * @param {string} [detail]
   */
  _setState(newState, detail) {
    const prev = this._state;
    this._state = newState;
    if (this._onStateChange && prev !== newState) {
      this._onStateChange(newState, detail);
    }
  }
}

/* ═══════════════════════════════════════════════
   EXPORT
   ═══════════════════════════════════════════════ */

// Make available globally (no bundler)
window.WadjetCamera = WadjetCamera;
window.CameraError = CameraError;
window.CameraState = CameraState;
window.FacingMode = FacingMode;
