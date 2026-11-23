// Login through the local Flask API. Keep the URL in sync with backend/app.py.
const API = 'http://127.0.0.1:5001/api';
const DASHBOARD = '../Dashboard/Dashboard.html';
const card = document.getElementById('lf');
const btn = card.querySelector('.go');
const form = card;
const err = document.getElementById('err');
const note = document.getElementById('notice');
const pw = form.p;

if (sessionStorage.me) location.replace(DASHBOARD);

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
    const response = await fetch(`${API}/login`, {
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
    fail('Cannot reach the local backend. Start it from the backend folder and try again.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Log in';
  }
});
