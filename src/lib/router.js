/**
 * SplatMaker — Simple hash-based SPA Router
 */
export class Router {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.routes = {};
    this.currentScreen = null;
    window.addEventListener('hashchange', () => this.navigate());
  }

  addRoute(path, screenFn) {
    this.routes[path] = screenFn;
  }

  start() {
    this.navigate();
  }

  navigate() {
    const hash = window.location.hash || '#/';
    const path = hash.replace('#', '') || '/';
    
    // Extract route params (e.g., /viewer/abc123)
    const parts = path.split('/').filter(Boolean);
    const basePath = '/' + (parts[0] || '');
    const params = parts.slice(1);

    const screenFn = this.routes[basePath] || this.routes[path] || this.routes['/'];
    
    if (screenFn) {
      // Cleanup current screen if it has a destroy method
      if (this.currentScreen && this.currentScreen.destroy) {
        this.currentScreen.destroy();
      }

      // Clear container
      this.container.innerHTML = '';
      
      // Render new screen
      this.currentScreen = screenFn(this.container, ...params);
    }
  }

  goto(path) {
    window.location.hash = '#' + path;
  }
}
