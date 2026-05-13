/**
 * SplatMaker — Export Screen
 */
export function exportScreen(container) {
  container.innerHTML = `
    <div class="screen-header">
      <h1 class="screen-title">Export</h1>
      <p class="screen-subtitle">Download your Gaussian Splat files</p>
    </div>
    <div class="export-grid">
      <div class="card export-option">
        <div class="export-option-icon">📦</div>
        <div class="export-option-title">PLY File</div>
        <div class="export-option-desc">Standard point cloud format. Compatible with most 3D editors.</div>
        <button class="btn btn-primary" id="download-ply" disabled>Download .ply</button>
      </div>
      <div class="card export-option">
        <div class="export-option-icon">✨</div>
        <div class="export-option-title">SPLAT File</div>
        <div class="export-option-desc">Optimized Gaussian Splat format for web viewers.</div>
        <button class="btn btn-primary" id="download-splat" disabled>Download .splat</button>
      </div>
      <div class="card export-option">
        <div class="export-option-icon">🔗</div>
        <div class="export-option-title">Open in SuperSplat</div>
        <div class="export-option-desc">Edit and refine your splat in the SuperSplat web editor.</div>
        <a href="https://playcanvas.com/supersplat/editor" target="_blank" class="btn btn-secondary">
          Open Editor
        </a>
      </div>
      <div class="card export-option">
        <div class="export-option-icon">📂</div>
        <div class="export-option-title">Open Folder</div>
        <div class="export-option-desc">Browse all project files including intermediate outputs.</div>
        <button class="btn btn-secondary" id="open-folder" disabled>Open Folder</button>
      </div>
    </div>
  `;
}
