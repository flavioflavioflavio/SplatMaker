/**
 * SplatMaker — Three.js Gaussian Splat Viewer
 * Placeholder — will be implemented with @mkkellogg/gaussian-splats-3d
 */
export class SplatViewer {
  constructor(containerEl) {
    this.container = containerEl;
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    // TODO: Initialize Three.js scene, camera, renderer, controls
  }

  async loadSplat(url) {
    // TODO: Load .ply/.splat file using gaussian-splats-3d
  }

  resetCamera() {
    // TODO: Reset camera to initial position
  }

  destroy() {
    // TODO: Cleanup Three.js resources
  }
}
