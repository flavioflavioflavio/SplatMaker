/**
 * SplatMaker — 3D Splat Viewer Screen
 * Full Three.js gaussian splat renderer with controls.
 */
import { SplatViewer } from '../lib/splat-viewer.js';
import { api } from '../lib/api.js';

export function viewerScreen(container, params) {
  let viewer = null;

  container.innerHTML = `
    <div class="screen-header" style="display:flex; justify-content:space-between; align-items:flex-start;">
      <div>
        <h1 class="screen-title">3D Viewer</h1>
        <p class="screen-subtitle" id="viewer-subtitle">Interactive Gaussian Splat preview</p>
      </div>
      <div class="viewer-actions" style="display:flex; gap:8px;">
        <select class="select" id="project-select" style="min-width:180px;">
          <option value="">Select project...</option>
        </select>
        <button class="btn btn-secondary" id="load-demo-btn">Load Demo</button>
        <button class="btn btn-secondary" id="load-file-btn">Load .ply</button>
        <input type="file" id="splat-file-input" accept=".ply,.splat,.ksplat" style="display:none" />
      </div>
    </div>
    <div class="viewer-container" id="viewer-container">
      <div class="viewer-empty" id="viewer-empty">
        <div style="font-size:80px; opacity:0.15; margin-bottom:20px;">🌐</div>
        <div style="font-size:var(--text-lg); font-weight:600; margin-bottom:8px;">
          No splat loaded
        </div>
        <div style="font-size:var(--text-sm); color:var(--text-tertiary); max-width:400px; margin-bottom:24px;">
          Complete a pipeline run to view your Gaussian Splat here,
          or load a demo to preview the viewer.
        </div>
        <div style="display:flex; gap:12px; flex-wrap:wrap; justify-content:center;">
          <button class="btn btn-primary" id="empty-demo-btn">
            🎮 Load Demo Splat
          </button>
          <button class="btn btn-secondary" id="empty-import-btn" onclick="location.hash='#/import'">
            📹 Import Video
          </button>
        </div>
      </div>
    </div>
  `;

  // Populate project selector
  populateProjects();

  // ── Event Handlers ──────────────────────────────────────────────────────

  // Load demo button (both toolbar and empty state)
  const bindDemo = (id) => {
    document.getElementById(id)?.addEventListener('click', async () => {
      await initViewer();
      document.getElementById('viewer-subtitle').textContent = 'Loading demo splat...';
      await viewer.loadDemo();
      document.getElementById('viewer-subtitle').textContent = 'Demo — nike.splat';
    });
  };
  bindDemo('load-demo-btn');
  bindDemo('empty-demo-btn');

  // Load local .ply file
  document.getElementById('load-file-btn')?.addEventListener('click', () => {
    document.getElementById('splat-file-input').click();
  });

  document.getElementById('splat-file-input')?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    await initViewer();
    document.getElementById('viewer-subtitle').textContent = `Loading ${file.name}...`;
    
    // Create object URL for local file
    const url = URL.createObjectURL(file);
    await viewer.loadSplat(url);
    document.getElementById('viewer-subtitle').textContent = file.name;
  });

  // Project selector
  document.getElementById('project-select')?.addEventListener('change', async (e) => {
    const projectId = e.target.value;
    if (!projectId) return;
    
    await initViewer();
    document.getElementById('viewer-subtitle').textContent = 'Loading project splat...';
    
    // Try to load the project's exported splat
    const splatUrl = `http://127.0.0.1:8420/files/${projectId}/export/splat.ply`;
    try {
      await viewer.loadSplat(splatUrl);
      document.getElementById('viewer-subtitle').textContent = `Project ${projectId}`;
    } catch (err) {
      document.getElementById('viewer-subtitle').textContent = 'No exported splat found for this project';
    }
  });

  // ── Helpers ─────────────────────────────────────────────────────────────

  async function initViewer() {
    // Hide empty state
    const emptyEl = document.getElementById('viewer-empty');
    if (emptyEl) emptyEl.style.display = 'none';

    // Destroy old viewer if exists
    if (viewer) {
      viewer.destroy();
    }

    viewer = new SplatViewer(document.getElementById('viewer-container'));
  }

  async function populateProjects() {
    try {
      const data = await api.listProjects();
      const select = document.getElementById('project-select');
      if (!select) return;

      const projects = (data.projects || []).filter(p => p.status === 'done');
      projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.frame_count} frames)`;
        select.appendChild(opt);
      });
    } catch (e) {
      // Ignore — projects list will be empty
    }
  }

  return {
    destroy() {
      if (viewer) {
        viewer.destroy();
        viewer = null;
      }
    }
  };
}
