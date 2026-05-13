/**
 * SplatMaker — 3D Splat Viewer Screen
 * Placeholder for Three.js gaussian splat renderer.
 */
export function viewerScreen(container, projectId) {
  container.innerHTML = `
    <div class="screen-header">
      <h1 class="screen-title">3D Viewer</h1>
      <p class="screen-subtitle">Interactive Gaussian Splat preview</p>
    </div>
    <div class="viewer-container" id="viewer-container">
      <div class="viewer-empty">
        <div style="font-size:80px; opacity:0.15; margin-bottom:20px;">🌐</div>
        <div style="font-size:var(--text-lg); font-weight:600; margin-bottom:8px;">
          No splat loaded
        </div>
        <div style="font-size:var(--text-sm); color:var(--text-tertiary); max-width:400px;">
          Complete a pipeline run to view your Gaussian Splat here.
          The viewer will load the .ply/.splat file automatically.
        </div>
        <div style="margin-top:24px;">
          <button class="btn btn-secondary" onclick="location.hash='#/import'">
            Import Video
          </button>
        </div>
      </div>
    </div>
  `;

  // TODO: Initialize Three.js + gaussian-splats-3d viewer
  // When a .ply file is available:
  // import { SplatViewer } from '../lib/splat-viewer.js';
  // const viewer = new SplatViewer(document.getElementById('viewer-container'));
  // viewer.loadSplat(`http://127.0.0.1:8420/api/splat/${projectId}/download`);

  return {
    destroy() {
      // Cleanup Three.js renderer if active
    }
  };
}
