const API = BBAPI.base;
const DASHBOARD = '../Dashboard/Dashboard.html';
const card = document.getElementById('lf');
const btn = card.querySelector('.go');
const form = card;
const err = document.getElementById('err');
const note = document.getElementById('notice');
const pw = form.p;

BBAPI.fetch(`${API}/me`).then(async response => {
  if (!response.ok) {
    sessionStorage.removeItem('me');
    return;
  }
  const user = await response.json();
  sessionStorage.me = JSON.stringify({
    u: user.username,
    name: user.fullname,
    role: user.role
  });
  location.replace(DASHBOARD);
}).catch(error => {
  console.error('Unable to verify the existing session:', error);
});

const msg = sessionStorage.notice;
if (msg) {
  note.textContent = msg;
  note.hidden = false;
  sessionStorage.removeItem('notice');
}

const fail = text => {
  err.textContent = text;
  card.classList.remove('shake');
  void card.offsetWidth;
  card.classList.add('shake');
};

form.addEventListener('submit', async event => {
  event.preventDefault();
  const username = form.u.value.trim();
  const password = pw.value;
  err.textContent = '';

  if (!username || !password) {
    fail(!username ? 'Enter your username.' : 'Enter your password.');
    (!username ? form.u : pw).focus();
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Logging in...';
  try {
    const response = await BBAPI.fetch(`${API}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      fail(result.detail || 'Wrong username or password. Check both and try again.');
      pw.value = '';
      pw.focus();
      return;
    }

    // Keep the shape expected by the existing navigation and API request helpers.
    sessionStorage.me = JSON.stringify({
      u: result.username,
      name: result.fullname,
      role: result.role
    });
    location.href = DASHBOARD;
  } catch (error) {
    fail('Cannot reach the server. Check your connection and try again.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Log in';
  }
});
