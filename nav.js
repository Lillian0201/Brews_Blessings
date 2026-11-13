// Brews & Blessings - shared navigation bar + session helpers.
// Used by Dashboard.html AND pos.html (and any other page you add later),
// so every page has the same sidebar, login check and auto-logout.
//
// To connect a new page: put its file name in PAGES below. That's the only edit needed.

(function () {
  'use strict';

  const LOGIN_URL = '../Login Page/Login.html';
  const IDLE_MS = 10 * 60 * 1000; // auto-logout after 10 minutes of inactivity

  // ---------- Page file names (edit these) ----------
  // Leave a page as '' until its file is ready; clicking it shows a "not connected yet" notice.
  const PAGES = {
    dash: '../Dashboard/Dashboard.html',
    orders: '../POS/POS.html',
    inv: '',
    tx: '../Transactions/Transactions.html',
    exp: '',
    pnl: '',
    audit: '',
    settings: ''
};

  const NAV = {
    Owner: [
      ['dash', 'Dashboard'],
      ['orders', 'Order/POS'],
      ['inv', 'Inventory'],
      ['tx', 'Transactions'],
      ['exp', 'Expense and Costing'],
      ['pnl', 'Profit/Loss Report'],
      ['audit', 'Audit log'],
      ['settings', 'Settings (Owner)']
    ],
    Barista: [
      ['orders', 'Order/POS'],
      ['inv', 'Inventory']
    ]
  };

  const ICON = {
    dash: '<path d="M3 11l9-8 9 8v10H3z"/>',
    orders: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/>',
    inv: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 10h8M8 14h8"/>',
    tx: '<path d="M4 9h16l-4-4M20 15H4l4 4"/>',
    exp: '<path d="M4 4h8l8 8-8 8-8-8z"/><circle cx="8.5" cy="8.5" r="1"/>',
    pnl: '<rect x="4" y="4" width="16" height="16"/><path d="M10 4v16M15 4v16"/>',
    audit: '<circle cx="12" cy="12" r="8"/><path d="M12 8v5l3 2"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/>',
    out: '<path d="M10 4H5v16h5M15 8l4 4-4 4M19 12H9"/>'
  };

  const ico = (n) => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${ICON[n]}</svg>`;
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => '&#' + c.charCodeAt(0) + ';');

  // ---------- Styles (injected once, scoped to .side so they never clash with a page's own CSS) ----------
  const CSS = `
.side{width:220px;flex-shrink:0;background:#3b2518;color:#f3e6d6;padding:16px 12px;display:flex;flex-direction:column;gap:4px;font:14px/1.45 system-ui,sans-serif;box-sizing:border-box}
.side *{box-sizing:border-box}
.side .brandbox{display:flex;align-items:center;gap:10px;font:700 14px/1.45 Georgia,serif;padding:4px 6px 18px}
.side .brandbox img{width:36px;height:36px;border-radius:50%;background:#fff;object-fit:cover;flex-shrink:0}
.side nav,.side .foot{display:flex;flex-direction:column;gap:4px}
.side nav{flex:1}
.side a,.side button{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:0;background:none;color:inherit;padding:10px;margin:0;border-radius:6px;cursor:pointer;transition:background .2s;font:inherit;text-decoration:none}
.side a:hover,.side button:hover{background:rgba(255,255,255,.12)}
.side a.on{background:#9a5c2c;color:#fff}
.side a:focus-visible,.side button:focus-visible{outline:3px solid #fff;outline-offset:1px}
.side .ic{width:16px;height:16px;flex-shrink:0;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
@media(max-width:760px){.side{width:auto}.side nav,.side .foot{flex-direction:row;flex-wrap:wrap}.side a,.side button{width:auto}}
@media(prefers-reduced-motion:reduce){.side a,.side button{transition:none}}
`;

  function injectCSS() {
    if (document.getElementById('bb-nav-css')) return;
    const s = document.createElement('style');
    s.id = 'bb-nav-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  // ---------- Session ----------
  function getSessionUser() {
    try {
      return JSON.parse(sessionStorage.getItem('me') || 'null');
    } catch (error) {
      console.error('Session loading error:', error);
      sessionStorage.removeItem('me');
      return null;
    }
  }

  // Returns the logged-in user, or sends the visitor to the login page and returns null.
  function requireLogin() {
    const me = getSessionUser();
    if (!me || !NAV[me.role]) {
      sessionStorage.removeItem('me');
      location.replace(LOGIN_URL);
      return null;
    }
    return me;
  }

  const canSee = (role, key) => !!NAV[role] && NAV[role].some((n) => n[0] === key);

  // The first page in a role's menu (where that role lands after login).
  function homeFor(role) {
    const first = NAV[role] && NAV[role][0][0];
    return (first && PAGES[first]) || PAGES.orders;
  }

  // Adds a line to the shared audit log (same 'bb' data the Audit log module reads).
  function auditLog(action, tbl, user) {
    try {
      const raw = localStorage.getItem('bb');
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data || typeof data !== 'object' || Array.isArray(data)) return;
      if (!Array.isArray(data.audit)) data.audit = [];
      data.audit.unshift({ t: new Date().toLocaleString(), u: user.name, a: action, tbl });
      localStorage.setItem('bb', JSON.stringify(data));
    } catch (error) {
      console.error('Could not write audit log:', error);
    }
  }

  function logout() {
    const me = getSessionUser();
    if (me) auditLog('Logged out', 'USER', me);
    sessionStorage.removeItem('me');
    location.replace(LOGIN_URL);
  }

  // ---------- Auto-logout after inactivity ----------
  let idleTimer;
  let idleStarted = false;

  function resetIdle() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      sessionStorage.removeItem('me');
      sessionStorage.notice = 'You were logged out after 10 minutes of inactivity.';
      location.replace(LOGIN_URL);
    }, IDLE_MS);
  }

  function startIdle() {
    resetIdle();
    if (idleStarted) return;
    idleStarted = true;
    ['click', 'keydown'].forEach((ev) => document.addEventListener(ev, resetIdle));
  }

  // ---------- Sidebar ----------
  // active = the key of the current page ('dash', 'orders', ...)
  function sidebar(active) {
    const me = getSessionUser();
    const nav = (me && NAV[me.role]) || [];
    const logo = window.LOGO || '../Img/B&B Logo.jpg';

    const item = (n) => {
      const href = PAGES[n[0]];
      const on = n[0] === active;
      return `<a href="${href ? esc(href) : '#'}"${href ? '' : ' data-soon="1"'} class="${on ? 'on' : ''}"${on ? ' aria-current="page"' : ''}>${ico(n[0])}${esc(n[1])}</a>`;
    };

    return `<aside class="side">
      <div class="brandbox">
        <img src="${esc(logo)}" alt="Cafe logo">
        <span>Brews &amp; Blessings</span>
      </div>
      <nav aria-label="Main">
        ${nav.filter((n) => n[0] !== 'settings').map(item).join('')}
      </nav>
      <div class="foot">
        ${nav.filter((n) => n[0] === 'settings').map(item).join('')}
        <button type="button" data-nav-out>${ico('out')}Log out</button>
      </div>
    </aside>`;
  }

  // For pages that have no JS-built layout (like pos.html): checks login, adds the sidebar
  // as the first thing in <body>, and starts the inactivity timer.
  function mount(active) {
    const me = requireLogin();
    if (!me) return null;
    if (!canSee(me.role, active)) {
      location.replace(homeFor(me.role));
      return null;
    }
    document.body.insertAdjacentHTML('afterbegin', sidebar(active));
    startIdle();
    return me;
  }

  // Sidebar clicks (works for sidebars added at any time).
  document.addEventListener('click', (e) => {
    const out = e.target.closest('[data-nav-out]');
    if (out) {
      e.preventDefault();
      logout();
      return;
    }
    const soon = e.target.closest('.side a[data-soon]');
    if (soon) {
      e.preventDefault();
      alert('This page is not connected yet.');
    }
  });

  injectCSS();

  window.BBNav = { requireLogin, getSessionUser, canSee, homeFor, sidebar, mount, startIdle, logout, LOGIN_URL };
})();