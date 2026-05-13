/**
 * SplatMaker — Home Screen (Project List)
 */
import { api } from '../lib/api.js';

export function homeScreen(container) {
  container.innerHTML = `
    <div class="screen-header">
      <h1 class="screen-title">Projects</h1>
      <p class="screen-subtitle">Your Gaussian Splat pipelines</p>
    </div>
    <div style="margin-bottom:20px;">
      <button class="btn btn-primary" id="new-project-btn">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M8 3V13M3 8H13"/>
        </svg>
        New Project
      </button>
    </div>
    <div id="projects-grid" class="projects-grid">
      <div class="empty-state">
        <div class="empty-state-icon">🎯</div>
        <div class="empty-state-title">No projects yet</div>
        <div class="empty-state-text">Import an Insta360 video to create your first Gaussian Splat.</div>
        <button class="btn btn-primary" id="empty-new-btn">Create Project</button>
      </div>
    </div>
  `;

  // Load projects
  loadProjects(container);

  // Bind new project buttons
  const newBtn = document.getElementById('new-project-btn');
  const emptyBtn = document.getElementById('empty-new-btn');
  const goImport = () => { window.location.hash = '#/import'; };
  newBtn?.addEventListener('click', goImport);
  emptyBtn?.addEventListener('click', goImport);
}

async function loadProjects(container) {
  try {
    const data = await api.listProjects();
    const grid = document.getElementById('projects-grid');
    
    if (data.projects && data.projects.length > 0) {
      grid.innerHTML = data.projects.map(p => `
        <div class="card project-card" data-id="${p.id}" data-status="${p.status}">
          <div class="card-thumbnail">
            ${p.thumbnail
              ? `<img src="${p.thumbnail}" alt="${p.name}" />`
              : `<div class="placeholder">🌐</div>`
            }
          </div>
          <div class="card-name">${p.name}</div>
          <div class="card-meta">
            <span class="badge badge-${statusBadge(p.status)}">${p.status}</span>
            <span>${p.frame_count || 0} frames</span>
            <span>${formatDate(p.created_at)}</span>
          </div>
        </div>
      `).join('');

      // Click handlers
      grid.querySelectorAll('.project-card').forEach(card => {
        card.addEventListener('click', () => {
          const id = card.dataset.id;
          const status = card.dataset.status;
          if (status === 'done') {
            window.location.hash = `#/viewer/${id}`;
          } else if (status === 'processing') {
            window.location.hash = `#/pipeline/${id}`;
          } else {
            window.location.hash = `#/import/${id}`;
          }
        });
      });
    }
  } catch (e) {
    // Backend might not be ready yet — show empty state
  }
}

function statusBadge(status) {
  const map = { created: 'info', processing: 'warning', done: 'success', error: 'error' };
  return map[status] || 'info';
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
