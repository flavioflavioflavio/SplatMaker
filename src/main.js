/**
 * SplatMaker — Main entry point
 * Sets up router, WebSocket, backend health check, and screen navigation.
 */
import { Router } from './lib/router.js';
import { api } from './lib/api.js';
import { wsManager } from './lib/ws.js';
import { homeScreen } from './screens/home.js';
import { importScreen } from './screens/import.js';
import { pipelineScreen } from './screens/pipeline.js';
import { viewerScreen } from './screens/viewer.js';
import { exportScreen } from './screens/export.js';

// ── Router Setup ──────────────────────────────────────────────────────────

const router = new Router('main-content');

router.addRoute('/', homeScreen);
router.addRoute('/import', importScreen);
router.addRoute('/pipeline', pipelineScreen);
router.addRoute('/viewer', viewerScreen);
router.addRoute('/export', exportScreen);

// ── Navigation Highlighting ───────────────────────────────────────────────

function updateActiveNav() {
  const hash = window.location.hash || '#/';
  const route = hash.replace('#', '') || '/';
  document.querySelectorAll('.nav-item').forEach(item => {
    const itemRoute = item.getAttribute('href')?.replace('#', '') || '/';
    item.classList.toggle('active', itemRoute === route);
  });
}

window.addEventListener('hashchange', updateActiveNav);

// ── Backend Health Check ──────────────────────────────────────────────────

const loadingOverlay = document.getElementById('loading-overlay');
const appContainer = document.getElementById('app');
const statusDot = document.querySelector('.status-dot');
const statusText = document.querySelector('.sidebar-status span');

async function waitForBackend() {
  let attempts = 0;
  const maxAttempts = 60;

  while (attempts < maxAttempts) {
    try {
      const health = await api.getHealth();
      if (health && health.status === 'ok') {
        onBackendReady(health);
        return;
      }
    } catch (e) {
      // Backend not ready yet
    }
    attempts++;
    await new Promise(r => setTimeout(r, 500));
  }

  onBackendError();
}

function onBackendReady(health) {
  // Hide loading overlay
  loadingOverlay.classList.add('hidden');
  appContainer.style.display = 'flex';

  // Update status indicator
  statusDot.classList.add('connected');
  statusDot.classList.remove('error');
  const gpuName = health.gpu?.name || 'No GPU';
  statusText.textContent = gpuName;

  // Connect WebSocket
  wsManager.connect();

  // Start router
  router.start();
  updateActiveNav();
}

function onBackendError() {
  // Show error in loading overlay
  const subtitle = document.querySelector('.loading-subtitle');
  subtitle.textContent = 'Failed to connect to backend. Please restart the app.';
  subtitle.style.color = 'var(--error)';
  
  const bar = document.querySelector('.loading-bar');
  bar.style.display = 'none';
}

// ── Listen for Tauri events (if running inside Tauri) ─────────────────────

if (window.__TAURI__) {
  const { listen } = window.__TAURI__.event;
  listen('backend-ready', () => {
    api.getHealth().then(onBackendReady).catch(onBackendError);
  });
  listen('backend-error', () => onBackendError());
}

// ── Start ─────────────────────────────────────────────────────────────────

waitForBackend();
