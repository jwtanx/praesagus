(() => {
  if (!globalThis.customElements || customElements.get('praesagus-site-nav')) return;

  const paths = [
    { key: 'home', label: 'Home', path: '' },
    { key: 'reports', label: 'Reports', path: 'daily-market-brief/', view: 'brief' },
    { key: 'calendar', label: 'Financial calendar', path: 'daily-market-brief/?view=calendar', view: 'calendar' },
    { key: 'technical', label: 'Technical analysis', path: 'daily-market-brief/?view=technical', view: 'technical' },
    { key: 'tickers', label: 'Ticker forecasts', path: 'daily-market-brief/?view=tickers', view: 'tickers' },
    { key: 'seasonality', label: 'Seasonality', path: 'seasonality/' },
    { key: 'tickets', label: 'Tickets', path: 'tickets/' },
  ];

  class PraesagusSiteNav extends HTMLElement {
    connectedCallback() {
      if (this.dataset.ready === 'true') return;
      this.dataset.ready = 'true';
      const root = this.getAttribute('root') || './';
      const base = root.endsWith('/') ? root : `${root}/`;
      const current = this.getAttribute('current') || '';
      const requestedView = new URLSearchParams(globalThis.location?.search || '').get('view');
      const active = current === 'reports' && ['calendar', 'technical', 'tickers'].includes(requestedView)
        ? requestedView
        : current;
      const linksId = 'site-nav-links';
      this.innerHTML = `
        <div class="praesagus-nav-bar">
          <a class="praesagus-nav-brand" href="${base}" aria-label="Praesagus home">PRAESAGUS</a>
          <button class="praesagus-nav-menu" id="site-menu-toggle" type="button" aria-expanded="false" aria-controls="${linksId}">☰ Menu</button>
          <nav class="praesagus-nav-links" id="${linksId}" aria-label="Main navigation">
            ${paths.map((item) => {
              const href = `${base}${item.path}`;
              const activeAttribute = active === item.key ? ' aria-current="page"' : '';
              const viewAttribute = item.view ? ` data-view="${item.view}"` : '';
              return `<a href="${href}"${activeAttribute}${viewAttribute}>${item.label}</a>`;
            }).join('')}
          </nav>
        </div>`;

      const menu = this.querySelector('.praesagus-nav-menu');
      const links = this.querySelector('.praesagus-nav-links');
      const closeMenu = () => {
        links.classList.remove('is-open');
        menu.setAttribute('aria-expanded', 'false');
      };
      menu.addEventListener('click', () => {
        const isOpen = links.classList.toggle('is-open');
        menu.setAttribute('aria-expanded', String(isOpen));
      });
      this.addEventListener('click', (event) => {
        if (event.target.closest('a')) closeMenu();
      });
      this.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
          closeMenu();
          menu.focus();
        }
      });
    }
  }

  customElements.define('praesagus-site-nav', PraesagusSiteNav);
})();
