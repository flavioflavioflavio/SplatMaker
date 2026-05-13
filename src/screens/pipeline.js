/**
 * SplatMaker — Pipeline Runner Screen
 */
import { wsManager } from '../lib/ws.js';
import { api } from '../lib/api.js';

const STEP_NAMES = ['extract', 'split', 'mask', 'sfm', 'train', 'export'];
const STEP_LABELS = { extract: 'Extract', split: 'Split', mask: 'Mask',
  sfm: 'SfM', train: 'Train', export: 'Export' };

export function pipelineScreen(container) {
  const state = { logs: [], steps: {} };
  STEP_NAMES.forEach(s => { state.steps[s] = { status: 'pending', progress: 0, message: '', elapsed: 0 }; });

  container.innerHTML = `
    <div class="screen-header">
      <h1 class="screen-title">Pipeline</h1>
      <p class="screen-subtitle" id="pipeline-subtitle">Waiting for pipeline...</p>
    </div>
    <div class="pipeline-layout">
      <div class="pipeline-steps" id="pipeline-steps"></div>
      <div class="pipeline-stats" id="pipeline-stats">
        <div class="stat-card"><div class="stat-label">Current Step</div>
          <div class="stat-value accent" id="stat-step">—</div></div>
        <div class="stat-card"><div class="stat-label">Progress</div>
          <div class="stat-value" id="stat-progress">0%</div></div>
        <div class="stat-card"><div class="stat-label">Elapsed</div>
          <div class="stat-value" id="stat-elapsed">0s</div></div>
      </div>
      <div class="card" style="padding:0">
        <div class="progress-bar"><div class="progress-bar-fill" id="overall-progress" style="width:0%"></div></div>
      </div>
      <div class="log-console" id="log-console">
        <div class="log-header" id="log-toggle">
          <span class="log-header-title">Live Logs</span>
          <span style="font-size:var(--text-xs);color:var(--text-tertiary)">▼</span>
        </div>
        <div class="log-body" id="log-body"></div>
      </div>
      <div>
        <button class="btn btn-danger" id="stop-btn">Stop Pipeline</button>
      </div>
    </div>
  `;

  renderSteps(state);

  // Log toggle
  document.getElementById('log-toggle')?.addEventListener('click', () => {
    document.getElementById('log-body')?.classList.toggle('collapsed');
  });

  // Stop button
  document.getElementById('stop-btn')?.addEventListener('click', async () => {
    try { await api.stopPipeline(); } catch (e) { /* ignore */ }
  });

  // WebSocket listeners
  const unsubs = [];
  unsubs.push(wsManager.on('pipeline_progress', (data) => {
    const step = data.step;
    if (state.steps[step]) {
      state.steps[step].status = data.status;
      state.steps[step].progress = data.progress;
      state.steps[step].message = data.message || '';
      state.steps[step].elapsed = data.elapsed_seconds || 0;
    }
    renderSteps(state);
    updateStats(state, data);
  }));

  unsubs.push(wsManager.on('log', (data) => {
    addLog(state, data.message, data.level);
  }));

  unsubs.push(wsManager.on('pipeline_complete', (data) => {
    document.getElementById('pipeline-subtitle').textContent =
      `Complete! Total time: ${formatTime(data.total_time_seconds)}`;
    addLog(state, `Pipeline complete in ${formatTime(data.total_time_seconds)}`, 'info');
  }));

  return {
    destroy() { unsubs.forEach(fn => fn()); }
  };
}

function renderSteps(state) {
  const el = document.getElementById('pipeline-steps');
  if (!el) return;
  el.innerHTML = STEP_NAMES.map((name, i) => {
    const s = state.steps[name];
    const icon = s.status === 'done' ? '✓' : s.status === 'running' ? '●' :
                 s.status === 'error' ? '✗' : '○';
    const conn = i < STEP_NAMES.length - 1
      ? `<div class="step-connector ${s.status === 'done' ? 'done' : ''}"></div>` : '';
    return `<div class="pipeline-step ${s.status}">
      <span class="step-icon">${icon}</span> ${STEP_LABELS[name]}
      ${s.status === 'running' ? ` <span style="opacity:0.7">${s.progress}%</span>` : ''}
    </div>${conn}`;
  }).join('');
}

function updateStats(state, data) {
  const stepEl = document.getElementById('stat-step');
  const progEl = document.getElementById('stat-progress');
  const elapsedEl = document.getElementById('stat-elapsed');
  const overallEl = document.getElementById('overall-progress');

  if (stepEl) stepEl.textContent = STEP_LABELS[data.step] || data.step;
  if (progEl) progEl.textContent = data.progress + '%';
  if (elapsedEl) elapsedEl.textContent = formatTime(data.elapsed_seconds);

  // Overall progress = (completed steps + current %) / total steps
  const doneCount = STEP_NAMES.filter(s => state.steps[s].status === 'done').length;
  const currentProg = data.progress / 100;
  const overall = ((doneCount + currentProg) / STEP_NAMES.length * 100).toFixed(1);
  if (overallEl) overallEl.style.width = overall + '%';
}

function addLog(state, message, level = 'info') {
  const time = new Date().toLocaleTimeString('en-US', { hour12: false });
  state.logs.push({ time, message, level });
  const body = document.getElementById('log-body');
  if (body) {
    const line = document.createElement('div');
    line.className = `log-line ${level}`;
    line.innerHTML = `<span class="log-time">${time}</span>${escapeHtml(message)}`;
    body.appendChild(line);
    body.scrollTop = body.scrollHeight;
  }
}

function formatTime(seconds) {
  if (!seconds) return '0s';
  if (seconds < 60) return Math.round(seconds) + 's';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}
