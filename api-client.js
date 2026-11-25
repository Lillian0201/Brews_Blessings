(function () {
  'use strict';

  const hostname = location.hostname;
  const local = location.protocol === 'file:' ||
    hostname === 'localhost' ||
    hostname === '127.0.0.1';
  const host = hostname === 'localhost' ? 'localhost' : '127.0.0.1';
  const base = local ? `http://${host}:5001/api` : '/api';

  async function fetchWithSession(input, options = {}) {
    const response = await window.fetch(input, {
      ...options,
      credentials: 'include'
    });
    const pathname = new URL(
      typeof input === 'string' ? input : input.url,
      location.href
    ).pathname.replace(/\/+$/, '');
    const endpoint = pathname.split('/').pop();

    const loginPage = /\/login(?:%20| )page\//i.test(location.pathname);
    if (response.status === 401 && !loginPage && endpoint !== 'login' && endpoint !== 'logout') {
      sessionStorage.removeItem('me');
      location.replace(new URL('../Login Page/Login.html', location.href).href);
    }

    return response;
  }

  window.BBAPI = { base, fetch: fetchWithSession };
})();
