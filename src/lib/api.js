/**
 * SplatMaker — REST API client wrapper
 */
const BASE_URL = 'http://127.0.0.1:8420';

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }
  const response = await fetch(url, config);
  if (!response.ok) {
    const error = await response.text().catch(() => 'Unknown error');
    throw new Error(`API Error ${response.status}: ${error}`);
  }
  return response.json();
}

export const api = {
  getHealth: () => request('/health'),
  listProjects: () => request('/api/projects'),
  createProject: (name, videoPath) =>
    request('/api/project/create', { method: 'POST', body: { name, video_path: videoPath } }),
  startPipeline: (config) =>
    request('/api/pipeline/start', { method: 'POST', body: config }),
  stopPipeline: () =>
    request('/api/pipeline/stop', { method: 'POST' }),
  getPipelineStatus: () => request('/api/pipeline/status'),
  systemCheck: () => request('/api/system/check'),
};
