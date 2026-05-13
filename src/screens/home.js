/**
 * SplatMaker — Home Screen (Project grid)
 */
import { api } from '../lib/api.js';

const STATUS_BADGES = {
  created: { label: 'Created', color: 'var(--text-tertiary)' },
  processing: { label: 'Processing', color: 'var(--accent)' },
  done: { label: 'Complete', color: 'var(--success)' },
  error: { label: 'Error', color: 'var(--error)' },
};

export function homeScreen(container) {
  container.innerHTML = `
    <div class="screen-header">
      <h1 class="screen-title">Projects</h1>
      <p class="screen-subtitle">Your Gaussian Splat projects</p>
    </div>
    <div class="project-grid" id="project-grid">
      <div class="empty-state" id="loading-state">
        <div class="empty-state-icon" style="animation:pulse 1.5s infinite">●</div>
        <div class="empty-state-text">Loading projects...</div>
      </div>
    </div>
  `;

  loadProjects();
}

async function loadProjects() {
  const grid = document.getElementById('project-grid');
  if (!grid) return;

  try {
    const data = await api.listProjects();
    const projects = data.projects || [];

    if (projects.length === 0) {
      grid.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📸</div>
          <div class="empty-state-text">No projects yet</div>
          <div class="empty-state-subtext">Import a 360° video to get started</div>
          <a href="#/import" class="btn btn-primary" style="margin-top:16px">Import Video</a>
        </div>
      `;
      return;
    }

    grid.innerHTML = projects.map(p => {
      const badge = STATUS_BADGES[p.status] || STATUS_BADGES.created;
      const thumb = p.thumbnail
        ? `<img src="http://127.0.0.1:8420${p.thumbnail}" alt="${p.name}" class="project-thumb" />`
        : `<div class="project-thumb-placeholder">📦</div>`;
      const frameText = p.frame_count ? `${p.frame_count} frames` : '';
      const date = p.created_at ? new Date(p.created_at).toLocaleDateString() : '';
      
      // Determine click target based on status
      const href = p.status === 'done' ? `#/viewer?id=${p.id}`
                 : p.status === 'processing' ? `#/pipeline?id=${p.id}`
                 : `#/import`;
      
      return `
        <a href="${href}" class="project-card card" data-project-id="${p.id}">
          <div class="project-thumb-wrap">${thumb}</div>
          <div class="project-info">
            <div class="project-name">${escapeHtml(p.name)}</div>
            <div class="project-meta">
              <span class="project-badge" style="color:${badge.color}">${badge.label}</span>
              ${frameText ? `<span class="project-frames">${frameText}</span>` : ''}
            </div>
            <div class="project-date">${date}</div>
          </div>
        </a>
      `;
    }).join('');

  } catch (e) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-text">Failed to load projects</div>
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
