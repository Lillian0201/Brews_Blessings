// Brews & Blessings Cafe - Dashboard page.
// Navigation bar, login check and auto-logout come from nav.js (shared with the POS page).
// Orders are read from the POS page's saved orders; stock and expenses from the 'bb' data.

const me = BBNav.requireLogin();

// Only roles that have "Dashboard" in their menu may stay on this page.
if (me && !BBNav.canSee(me.role, 'dash')) {
  location.replace(BBNav.homeFor(me.role));
}

console.log('1. Dashboard.js loaded');
console.log('2. Logged-in user:', me);

const $ = s => document.querySelector(s);
const money = n => '₱' + (+n).toLocaleString('en-US', {
  minimumFractionDigits: Number.isInteger(+n) ? 0 : 2,
  maximumFractionDigits: 2
});
const pad = n => String(n).padStart(2, '0');
// Today's date in the local time zone, as YYYY-MM-DD.
const dayOf = d => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
const day = () => dayOf(new Date());
const esc = s => String(s).replace(/[&<>"']/g, c => '&#' + c.charCodeAt(0) + ';');
const sum = (a, k) => a.reduce((s, x) => s + (+x[k] || 0), 0);

// ---------- Saved data ----------
// Stock (ings) and expenses (exps) live in localStorage under 'bb'.
// This page only reads it; it never writes it back.
const seed = () => ({
  ings: [
    {id:1,name:'Espresso beans',unit:'g',stock:5000,begin:5000,inn:0,out:0,reorder:1000,cost:1},
    {id:2,name:'Fresh milk',unit:'ml',stock:10000,begin:10000,inn:0,out:0,reorder:2000,cost:.08},
    {id:3,name:'Cups',unit:'pcs',stock:200,begin:200,inn:0,out:0,reorder:30,cost:4},
    {id:4,name:'Caramel syrup',unit:'ml',stock:1000,begin:1000,inn:0,out:0,reorder:200,cost:.3}
  ],
  exps: []
});

let dbWarning = '';

function loadDatabase() {
  const raw = localStorage.getItem('bb');

  if (!raw) {
    return seed();
  }

  try {
    const saved = JSON.parse(raw);

    if (!saved || typeof saved !== 'object' || Array.isArray(saved)) {
      throw new Error('Invalid dashboard database format.');
    }

    const defaults = seed();

    return {
      ings: Array.isArray(saved.ings) ? saved.ings : defaults.ings,
      exps: Array.isArray(saved.exps) ? saved.exps : defaults.exps
    };

  } catch (error) {
    console.error('Dashboard database loading error:', error);

    // Keep a backup of the original saved data before using demo defaults.
    try {
      if (!localStorage.getItem('bb_backup')) {
        localStorage.setItem('bb_backup', raw);
      }
    } catch (backupError) {
      console.error('Could not back up saved data:', backupError);
    }

    dbWarning = 'Warning: Saved dashboard data could not be read. A backup of the original data was attempted. Demo data is currently being displayed.';

    return seed();
  }
}

// Orders placed on the POS page (same key the POS page saves to).
const POS_KEY = 'bb_pos_orders_v1';

function loadPosOrders() {
  try {
    const arr = JSON.parse(localStorage.getItem(POS_KEY) || '[]');
    return Array.isArray(arr) ? arr : [];
  } catch (error) {
    console.error('Could not read POS orders:', error);
    return [];
  }
}

const st = i => i.stock <= 0
  ? 'Out-of-Stock'
  : i.stock <= i.reorder
    ? 'Low-Stock'
    : 'Available';

const k = (l, v) =>
  `<div class="k"><span>${l}</span><b>${v}</b></div>`;

// ---------- Dashboard view ----------
function dashboardHTML(db) {
  const t = day();
  const all = loadPosOrders();
  const today = all.filter(o => dayOf(new Date(o.createdAt)) == t);

  // Payment is taken when an order is placed, so every order that is not cancelled counts as a sale.
  const sold = o => o.status != 'Cancelled';

  const best = {};
  all.filter(sold).forEach(o => {
    (o.items || []).forEach(i => {
      best[i.name] = (best[i.name] || 0) + (+i.qty || 0);
    });
  });

  const top = Object.entries(best)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  const max = top.length ? top[0][1] : 1;
  const c = s => today.filter(o => o.status == s).length;
  const low = db.ings.filter(i => st(i) != 'Available');

  const cls = {
    Pending:'pend',
    Completed:'ok',
    Cancelled:'bad'
  };

  return `<div class="kp">
    ${k("Today's sales", money(sum(today.filter(sold), 'total')))}
    ${k('Number of orders', today.length)}
    ${k("Today's expenses", money(sum(db.exps.filter(x => x.date == t), 'amt')))}
    ${k('Available stock', db.ings.filter(i => st(i) == 'Available').length + ' items')}
  </div>

  <div class="two">
    <section class="box">
      <h2>Pending and completed orders</h2>
      <div class="pills">
        <span>Pending: ${c('Pending')}</span>
        <span>Completed: ${c('Completed')}</span>
        <span>Cancelled: ${c('Cancelled')}</span>
      </div>

      ${today.length
        ? '<ul class="list">' +
          today.slice().sort((a, b) => b.createdAt - a.createdAt).slice(0, 5).map(o =>
            `<li><span>[${esc(o.no)}] ${esc(o.customer)}</span>
            <span class="tag ${cls[o.status] || ''}">${esc(o.status)}</span></li>`
          ).join('') +
          '</ul>'
        : '<p class="empty">No orders yet today.</p>'}
    </section>

    <section class="box">
      <h2>Best-selling products</h2>
      ${top.length
        ? top.map(([n, q], i) =>
          `<div class="bs">
            <span>${i + 1}. ${esc(n)} - ${q}</span>
            <div class="bar"><i style="width:${q / max * 100}%"></i></div>
          </div>`
        ).join('')
        : '<p class="empty">Sales will show here once orders are placed.</p>'}
    </section>
  </div>

  <section class="box">
    <h2>Stock alerts</h2>
    ${low.length
      ? '<ul class="list sa">' +
        low.map(i =>
          `<li>
            <span>${esc(i.name)}</span>
            <span>Remaining: ${i.stock} ${i.unit}</span>
            <span class="tag ${st(i) == 'Low-Stock' ? 'pend' : 'bad'}">
              ${st(i) == 'Low-Stock' ? 'Low-stock' : 'Out of Stock'}
            </span>
          </li>`
        ).join('') +
        '</ul>'
      : '<p class="empty">All ingredients are stocked.</p>'}
  </section>`;
}

// ---------- Page rendering ----------
function render() {
  if (!me || !BBNav.canSee(me.role, 'dash')) return;

  const app = $('#app');

  if (!app) {
    console.error('Dashboard error: Element #app was not found.');
    return;
  }

  BBNav.startIdle();

  const db = loadDatabase();
  const alertN = db.ings.filter(i => st(i) != 'Available').length;

  try {
    app.innerHTML = `
      <div class="shell">
        ${BBNav.sidebar('dash')}

        <main>
          <div class="top">
            <h1>Dashboard</h1>
            <div class="meta">
              <span>Today: ${new Date().toLocaleDateString('en-US', {
                month:'short',
                day:'numeric'
              })}</span>
              <span class="pill">Logged in: ${esc(me.name)}</span>
              <span class="pill" title="Stock alerts">Stock alerts: ${alertN}</span>
            </div>
          </div>

          ${dbWarning ? `<div class="warn">${esc(dbWarning)}</div>` : ''}

          ${dashboardHTML(db)}
        </main>
      </div>
    `;

    console.log('Dashboard rendered successfully.');

  } catch (error) {
    console.error('Dashboard rendering error:', error);

    app.innerHTML = `
      <main>
        <h1>Dashboard Loading Error</h1>
        <div class="warn">
          Something went wrong while displaying the dashboard.
          Please check the browser Console for details.
        </div>
      </main>
    `;
  }
}

// Refresh the numbers when the user comes back to this page with the browser's Back button.
window.addEventListener('pageshow', e => {
  if (e.persisted) render();
});

// Start the dashboard.
console.log('3. Starting dashboard render');

render();

console.log('4. Dashboard initialization finished');