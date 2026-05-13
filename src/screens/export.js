/**
 * SplatMaker — Export Screen
 * Download and share Gaussian Splat output.
 */
import { api } from '../lib/api.js';

export function exportScreen(container) {
  container.innerHTML = `
    <div class="screen-header">
      <h1 class="screen-title">Export</h1>
      <p class="screen-subtitle" id="export-subtitle">Download and share your Gaussian Splats</p>
    </div>
    <div id="export-content">
      <div class="empty-state" id="export-loading">
        <div class="empty-state-icon" style="animation:pulse 1.5s infinite">●</div>
        <div class="empty-state-text">Loading projects...</div>
      </div>
    </div>
  `;

  loadExportData();
}

async function loadExportData() {
  const content = document.getElementById('export-content');
  if (!content) return;

  try {
    const data = await api.listProjects();
    const projects = (data.projects || []).filter(p => p.status === 'done');

    if (projects.length === 0) {
      content.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📦</div>
          <div class="empty-state-text">No completed projects</div>
          <div class="empty-state-subtext">Run a pipeline to completion to export results</div>
          <a href="#/import" class="btn btn-primary" style="margin-top:16px">Import Video</a>
        </div>
      `;
      return;
    }

    content.innerHTML = projects.map(p => `
      <div class="card" style="margin-bottom:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div>
            <h3 style="font-size:var(--text-lg); font-weight:700;">${escapeHtml(p.name)}</h3>
            <div style="font-size:var(--text-xs); color:var(--text-tertiary);">
              ${p.frame_count || 0} frames • Created ${new Date(p.created_at).toLocaleDateString()}
            </div>
          </div>
          <span class="project-badge" style="color:var(--success)">COMPLETE</span>
        </div>
        <div class="export-grid">
          <div class="export-option card">
            <div class="export-option-icon">📄</div>
            <div class="export-option-title">PLY File</div>
            <div class="export-option-desc">Standard Gaussian Splat format. Compatible with most viewers.</div>
            <a href="http://127.0.0.1:8420/files/${p.id}/export/" target="_blank" 
               class="btn btn-primary">Download</a>
          </div>
          <div class="export-option card">
            <div class="export-option-icon">🎯</div>
            <div class="export-option-title">transforms.json</div>
            <div class="export-option-desc">Camera poses and intrinsics. Use with any Gaussian Splat trainer.</div>
            <a href="http://127.0.0.1:8420/files/${p.id}/transforms.json" target="_blank" 
               class="btn btn-secondary">Download</a>
          </div>
          <div class="export-option card">
            <div class="export-option-icon">🖼️</div>
            <div class="export-option-title">Perspective Views</div>
            <div class="export-option-desc">All split perspective images used for training.</div>
            <a href="http://127.0.0.1:8420/files/${p.id}/split/" target="_blank"
               class="btn btn-secondary">Browse</a>
          </div>
          <div class="export-option card">
            <div class="export-option-icon">🌐</div>
            <div class="export-option-title">SuperSplat Editor</div>
            <div class="export-option-desc">Edit and refine your splat in PlayCanvas SuperSplat.</div>
            <a href="https://playcanvas.com/supersplat/editor" target="_blank" 
               class="btn btn-secondary">Open Editor</a>
          </div>
        </div>
      </div>
    `).join('');

  } catch (e) {
    content.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-text">Failed to load export data</div>
        <div class="empty-state-subtext">${escapeHtml(e.message)}</div>
      </div>
    `;
  }
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}
