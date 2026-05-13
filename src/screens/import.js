/**
 * SplatMaker — Import Screen (Video upload + Pipeline config)
 */
import { api } from '../lib/api.js';

export function importScreen(container) {
  container.innerHTML = `
    <div class="screen-header">
      <h1 class="screen-title">Import Video</h1>
      <p class="screen-subtitle">Drop an Insta360 equirectangular video and configure the pipeline</p>
    </div>
    <div class="import-layout">
      <div class="import-main">
        <div class="drop-zone" id="drop-zone">
          <div class="drop-zone-icon">📹</div>
          <div class="drop-zone-title">Drop video here</div>
          <div class="drop-zone-subtitle">Supports .mp4, .insv — equirectangular 360° video</div>
          <input type="file" id="file-input" accept=".mp4,.insv,.mov" style="display:none" />
        </div>
        <div id="video-info" style="display:none; margin-top:16px;">
          <div class="video-info">
            <div class="video-info-icon">🎬</div>
            <div>
              <div class="video-info-name" id="video-name">—</div>
              <div class="video-info-size" id="video-size">—</div>
            </div>
          </div>
        </div>
      </div>
      <div class="import-config card">
        <div class="config-section">
          <div class="config-section-title">Extraction</div>
          <div class="slider-group">
            <div class="slider-header">
              <span class="input-label">Frames per second</span>
              <span class="slider-value" id="fps-value">2</span>
            </div>
            <input type="range" id="fps-slider" min="1" max="5" value="2" step="1" />
          </div>
          <div class="slider-group">
            <div class="slider-header">
              <span class="input-label">Crop top/bottom</span>
              <span class="slider-value" id="crop-value">15%</span>
            </div>
            <input type="range" id="crop-slider" min="0" max="30" value="15" step="1" />
          </div>
        </div>
        <div class="config-section">
          <div class="config-section-title">Processing</div>
          <div class="input-group">
            <label class="input-label">Views per frame</label>
            <select class="select" id="views-select">
              <option value="6">6 views</option>
              <option value="8" selected>8 views</option>
              <option value="10">10 views (+ up)</option>
            </select>
          </div>
          <div class="input-group">
            <label class="input-label">Masking mode</label>
            <select class="select" id="mask-select">
              <option value="none">None (fastest)</option>
              <option value="auto">Auto (YOLO + SAM2)</option>
              <option value="interactive">Interactive</option>
            </select>
          </div>
          <div class="input-group">
            <label class="input-label">SfM engine</label>
            <select class="select" id="sfm-select">
              <option value="synthetic" selected>Synthetic (360° — no COLMAP)</option>
              <option value="glomap">GLOMAP (faster)</option>
              <option value="colmap">COLMAP (standard)</option>
            </select>
          </div>
        </div>
        <div class="config-section">
          <div class="config-section-title">Training</div>
          <div class="slider-group">
            <div class="slider-header">
              <span class="input-label">Max iterations</span>
              <span class="slider-value" id="iters-value">30k</span>
            </div>
            <input type="range" id="iters-slider" min="10000" max="50000" value="30000" step="5000" />
          </div>
        </div>
        <div style="margin-top:20px;">
          <button class="btn btn-primary btn-lg" id="start-btn" style="width:100%" disabled>
            Start Pipeline
          </button>
        </div>
      </div>
    </div>
  `;

  // ── State ───────────────────────────────────────────────────────────────
  let selectedFile = null;
  let videoFilePath = '';  // For Tauri: absolute path; for browser: filename
  let projectName = '';

  // ── Slider bindings ─────────────────────────────────────────────────────
  bindSlider('fps-slider', 'fps-value', v => v);
  bindSlider('crop-slider', 'crop-value', v => v + '%');
  bindSlider('iters-slider', 'iters-value', v => (v / 1000) + 'k');

  // ── Drop zone ───────────────────────────────────────────────────────────
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');

  // Handle Tauri drag-drop events (sends file paths)
  if (window.__TAURI__) {
    window.__TAURI__.event.listen('tauri://drag-drop', (event) => {
      const paths = event.payload.paths || event.payload;
      if (Array.isArray(paths) && paths.length > 0) {
        const filePath = paths[0];
        const fileName = filePath.split(/[/\\]/).pop();
        videoFilePath = filePath;
        projectName = fileName.replace(/\.[^.]+$/, '');
        showFileInfo(fileName, '—');
      }
    });
  }

  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
  });

  function handleFile(file) {
    selectedFile = file;
    projectName = file.name.replace(/\.[^.]+$/, '');
    // In browser mode, we'll use the file name and need to have the file 
    // accessible to the backend. For development, we use a known path.
    videoFilePath = file.name;
    showFileInfo(file.name, formatSize(file.size));
  }

  function showFileInfo(name, size) {
    document.getElementById('video-name').textContent = name;
    document.getElementById('video-size').textContent = size;
    document.getElementById('video-info').style.display = 'block';
    document.getElementById('start-btn').disabled = false;
    dropZone.innerHTML = `
      <div class="drop-zone-icon">✅</div>
      <div class="drop-zone-title">${name}</div>
      <div class="drop-zone-subtitle">${size} — Click to change</div>
    `;
  }

  // ── Start pipeline ──────────────────────────────────────────────────────
  document.getElementById('start-btn').addEventListener('click', async () => {
    if (!videoFilePath && !selectedFile) return;

    const startBtn = document.getElementById('start-btn');
    startBtn.disabled = true;
    startBtn.textContent = 'Creating project...';

    const config = {
      fps: parseInt(document.getElementById('fps-slider').value),
      views_per_frame: parseInt(document.getElementById('views-select').value),
      crop_top_bottom: parseInt(document.getElementById('crop-slider').value) / 100,
      mask_mode: document.getElementById('mask-select').value,
      sfm_engine: document.getElementById('sfm-select').value,
      max_iterations: parseInt(document.getElementById('iters-slider').value),
    };

    try {
      // Create project first
      const project = await api.createProject(projectName, videoFilePath);
      
      // Start pipeline
      config.project_id = project.id;
      await api.startPipeline(config);
      
      // Navigate to pipeline screen
      window.location.hash = `#/pipeline`;
    } catch (e) {
      startBtn.disabled = false;
      startBtn.textContent = 'Start Pipeline';
      alert('Failed to start pipeline: ' + e.message);
    }
  });
}

function bindSlider(sliderId, valueId, formatter) {
  const slider = document.getElementById(sliderId);
  const display = document.getElementById(valueId);
  if (slider && display) {
    slider.addEventListener('input', () => {
      display.textContent = formatter(parseInt(slider.value));
    });
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
  return (bytes / 1073741824).toFixed(2) + ' GB';
}
