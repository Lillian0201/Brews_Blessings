// Login page. Demo only: checks the demo accounts in this browser. A real system must verify passwords on a server.
const DEMO = [
  {u:'owner', p:'owner123', name:'Owner', role:'Owner'},
  {u:'barista', p:'barista123', name:'Barista', role:'Barista'}
];
const form = document.getElementById('lf'), err = document.getElementById('err'), note = document.getElementById('notice'), pw = form.p;

if (sessionStorage.me) location.replace('index.html'); // already logged in

const msg = sessionStorage.notice;
if (msg) { note.textContent = msg; note.hidden = false; sessionStorage.removeItem('notice'); }

form.addEventListener('submit', e => {
  e.preventDefault();
  const u = form.u.value.trim(), p = pw.value;
  err.textContent = '';
  if (!u || !p) {
    err.textContent = !u ? 'Enter your username.' : 'Enter your password.';
    (!u ? form.u : pw).focus();
    return;
  }
  let db = null;
  try { db = JSON.parse(localStorage.bb || 'null'); } catch (x) {}
  const acct = (db ? db.users : DEMO).find(x => x.u == u && x.p == p);
  if (!acct) {
    err.textContent = 'Wrong username or password. Check both and try again.';
    pw.value = ''; pw.focus();
    return;
  }
  sessionStorage.me = JSON.stringify(acct);
  if (db) { // keep the main app's duty and audit records in sync
    if (acct.role == 'Barista') db.duty = acct.name;
    db.audit.unshift({t:new Date().toLocaleString(), u:acct.name, a:'Logged in', tbl:'USER'});
    localStorage.bb = JSON.stringify(db);
  }
  location.href = 'index.html';
});