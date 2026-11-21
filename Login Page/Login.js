// Login page. Demo only: checks the demo accounts in this browser. A real system must verify passwords on a server.
const DASHBOARD = '../Dashboard/Dashboard.html';
const DEMO = [
  {u:'owner', p:'owner123', name:'Owner', role:'Owner'},
  {u:'barista', p:'barista123', name:'Barista', role:'Barista'}
];
const card = document.getElementById('lf'), btn = card.querySelector('.go');
const form = card, err = document.getElementById('err'), note = document.getElementById('notice'), pw = form.p;

if (sessionStorage.me) location.replace(DASHBOARD); // already logged in

const msg = sessionStorage.notice;
if (msg) { note.textContent = msg; note.hidden = false; sessionStorage.removeItem('notice'); }

// Shake the card when a login fails.
const fail = text => { err.textContent = text; card.classList.remove('shake'); void card.offsetWidth; card.classList.add('shake'); };

form.addEventListener('submit', e => {
  e.preventDefault();
  const u = form.u.value.trim(), p = pw.value;
  err.textContent = '';
  if (!u || !p) {
    fail(!u ? 'Enter your username.' : 'Enter your password.');
    (!u ? form.u : pw).focus();
    return;
  }
  const acct = DEMO.find(x => x.u == u && x.p == p);
  if (!acct) {
    fail('Wrong username or password. Check both and try again.');
    pw.value = ''; pw.focus();
    return;
  }
  sessionStorage.me = JSON.stringify(acct); // remember who logged in
  btn.disabled = true; btn.textContent = 'Logging in...';
  setTimeout(() => location.href = DASHBOARD, 450);
});