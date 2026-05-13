/**
 * SplatMaker — Three.js Gaussian Splat Viewer
 * Uses @mkkellogg/gaussian-splats-3d for real-time splat rendering.
 */
import * as GaussianSplats3D from '@mkkellogg/gaussian-splats-3d';
import * as THREE from 'three';

export class SplatViewer {
  constructor(containerEl) {
    this.container = containerEl;
    this.viewer = null;
    this.loaded = false;
    this._disposed = false;
  }

  /**
   * Initialize the viewer and load a splat file.
   * @param {string} url - URL to .ply or .splat file
   * @param {object} options - Optional viewer settings
   */
  async loadSplat(url, options = {}) {
    if (this._disposed) return;

    // Clear container
    this.container.innerHTML = '';

    try {
      // Create the viewer with sensible defaults
      this.viewer = new GaussianSplats3D.Viewer({
        cameraUp: [0, -1, 0],
        initialCameraPosition: [0, -2, 6],
        initialCameraLookAt: [0, 0, 0],
        rootElement: this.container,
        selfDrivenMode: true,
        useBuiltInControls: true,
        dynamicScene: false,
        sharedMemoryForWorkers: false,
        ...options,
      });

      // Add the splat scene
      await this.viewer.addSplatScene(url, {
        splatAlphaRemovalThreshold: 10,
        showLoadingUI: true,
        progressiveLoad: true,
      });

      this.viewer.start();
      this.loaded = true;

      // Add keyboard shortcut info
      this._addOverlay();

    } catch (err) {
      console.error('SplatViewer: Failed to load splat', err);
      this.container.innerHTML = `
        <div class="viewer-empty">
          <div style="font-size:48px; opacity:0.3; margin-bottom:16px;">⚠️</div>
          <div style="font-size:var(--text-md); font-weight:600; margin-bottom:8px;">
            Failed to load splat
          </div>
          <div style="font-size:var(--text-sm); color:var(--text-tertiary); max-width:400px;">
            ${err.message || 'Unknown error'}
          </div>
        </div>
      `;
    }
  }

  /**
   * Load a demo/preview PLY for testing the viewer.
   */
  async loadDemo() {
    // Use a publicly available gaussian splat demo
    const demoUrl = 'https://huggingface.co/cakewalk/splat-data/resolve/main/nike.splat';
    await this.loadSplat(demoUrl);
  }

  resetCamera() {
    if (this.viewer) {
      // Reset to initial camera position
      // The library handles this internally via its controls
    }
  }

  _addOverlay() {
    const overlay = document.createElement('div');
    overlay.className = 'viewer-controls-overlay';
    overlay.innerHTML = `
      <div class="viewer-controls-hint">
        <span>🖱️ Orbit</span>
        <span>⚙️ Scroll to zoom</span>
        <span>⌨️ WASD to pan</span>
      </div>
    `;
    this.container.appendChild(overlay);
  }

  destroy() {
    this._disposed = true;
    if (this.viewer) {
      try {
        this.viewer.dispose();
      } catch (e) {
        // Ignore disposal errors
      }
      this.viewer = null;
    }
    this.loaded = false;
  }
}
