// Brews & Blessings Cafe - front-end prototype. Data is saved in this browser (localStorage).
// Demo logins: owner / owner123  and  barista / barista123 (a real system must hash passwords on a server).
const IDLE_MS = 10 * 60 * 1000; // auto-logout after inactivity
const $ = s => document.querySelector(s);
const money = n => '₱' + (+n).toFixed(2);
const day = () => new Date().toISOString().slice(0, 10);
const esc = s => String(s).replace(/[&<>"']/g, c => '&#' + c.charCodeAt(0) + ';');
const sum = (a, k) => a.reduce((s, x) => s + x[k], 0);

const seed = () => ({
  users: [{u:'owner',p:'owner123',name:'Owner',role:'Owner'}, {u:'barista',p:'barista123',name:'Barista',role:'Barista'}],
  ings: [
    {id:1,name:'Espresso beans',unit:'g',stock:5000,begin:5000,inn:0,out:0,reorder:1000,cost:1},
    {id:2,name:'Fresh milk',unit:'ml',stock:10000,begin:10000,inn:0,out:0,reorder:2000,cost:.08},
    {id:3,name:'Cups',unit:'pcs',stock:200,begin:200,inn:0,out:0,reorder:30,cost:4},
    {id:4,name:'Caramel syrup',unit:'ml',stock:1000,begin:1000,inn:0,out:0,reorder:200,cost:.3}],
  prods: [ // sample products: change names, prices and recipes to match the real menu
    {id:1,name:'Americano',price:90,pack:2,rec:{1:18,3:1}},
    {id:2,name:'Cafe Latte',price:120,pack:2,rec:{1:18,2:200,3:1}},
    {id:3,name:'Caramel Latte',price:140,pack:2,rec:{1:18,2:200,3:1,4:20}}],
  orders: [], sales: [], exps: [], refunds: [], audit: [], seq: 1, duty: ''
});
let db = JSON.parse(localStorage.bb || 'null') || seed();
let me = JSON.parse(sessionStorage.me || 'null'), view = '', idle, msg = '';
const save = () => localStorage.bb = JSON.stringify(db);
const st = i => i.stock <= 0 ? 'Out-of-Stock' : i.stock <= i.reorder ? 'Low-Stock' : 'Available';
const log = (a, t) => { db.audit.unshift({t:new Date().toLocaleString(), u:me.name, a, tbl:t}); save(); };
const P = id => db.prods.find(p => p.id == id);
const G = id => db.ings.find(g => g.id == id);
const pcost = p => p.pack + Object.entries(p.rec).reduce((s, [i, q]) => s + q * G(i).cost, 0);
// Deduct (sign 1) or restore (sign -1) the ingredients used by an order.
const use = (o, sign) => { for (const [i, q] of Object.entries(P(o.pid).rec)) { const g = G(i), d = sign * q * o.qty; g.stock -= d; g.out += d; } };

const NAV = {
  Owner: [['dash','Dashboard'],['orders','Orders (POS)'],['inv','Inventory'],['tx','Transactions'],['exp','Expenses'],['pnl','Profit / Loss'],['audit','Audit log']],
  Barista: [['orders','Orders (POS)'],['inv','Inventory']]
};
const tb = (h, r) => '<div class="tw"><table><tr>' + h.map(x => `<th>${x}</th>`).join('') + '</tr>' +
  (r.length ? r.map(x => '<tr>' + x.map(c => `<td>${c}</td>`).join('') + '</tr>').join('') : `<tr><td colspan="${h.length}" class="empty">Nothing here yet.</td></tr>`) + '</table></div>';
const k = (l, v) => `<div class="k"><b>${v}</b><span>${l}</span></div>`;
const alerts = () => { const a = db.ings.filter(i => st(i) != 'Available'); return a.length ? '<div class="warn"><b>Restock needed:</b> ' + a.map(i => `${esc(i.name)} (${st(i)})`).join(', ') + '</div>' : ''; };
const done = s => db.sales.filter(x => x.status == 'Completed');

const V = {
  dash() {
    const t = day(), o = db.orders.filter(x => x.date == t), best = {};
    done().forEach(x => best[x.pn] = (best[x.pn] || 0) + x.qty);
    const c = s => o.filter(x => x.status == s).length;
    return `<h1>Dashboard</h1>${alerts()}<div class="kp">
      ${k("Today's sales", money(sum(done().filter(x => x.date == t), 'total')))}${k('Orders today', o.length)}
      ${k("Today's expenses", money(sum(db.exps.filter(x => x.date == t), 'amt')))}
      ${k('Ingredients available', db.ings.filter(i => st(i) == 'Available').length + ' of ' + db.ings.length)}
      ${k('Pending / completed today', c('Pending') + ' / ' + c('Completed'))}${k('Barista on duty', esc(db.duty || 'No one yet'))}</div>
      <h2>Best-selling products</h2>${tb(['Product','Sold'], Object.entries(best).sort((a, b) => b[1] - a[1]).map(([n, q]) => [esc(n), q]))}`;
  },
  orders() {
    const opts = db.prods.map(p => `<option value="${p.id}">${esc(p.name)} (${money(p.price)})</option>`).join('');
    const rows = db.orders.slice().reverse().map(o => [o.no, esc(o.c),
      `${o.qty} x ${esc(P(o.pid).name)}${o.n ? '<br><small>' + esc(o.n) + '</small>' : ''}`,
      o.status == 'Cancelled' ? `Cancelled<br><small>${esc(o.reason)}</small>` :
        `<select data-act="status" data-id="${o.id}" aria-label="Order status">${['Pending','Preparing','Completed'].map(s => `<option${s == o.status ? ' selected' : ''}>${s}</option>`).join('')}</select>`,
      o.time,
      (['Pending','Preparing'].includes(o.status) ? `<button data-act="cancel" data-id="${o.id}">Cancel</button>` : '') +
      (o.status == 'Completed' && !db.sales.some(s => s.oid == o.id) ? `<button class="pr" data-act="pay" data-id="${o.id}">Record cash payment</button>` : '')]);
    return `<h1>Orders</h1>${alerts()}${msg}<form id="of" class="fm">
      <label>Customer name<input name="c" required></label><label>Product<select name="p">${opts}</select></label>
      <label>Quantity<input name="q" type="number" min="1" value="1" required></label><label>Details / customization<input name="n"></label>
      <button class="pr">Record order</button></form>${tb(['Order','Customer','Item','Status','Time','Actions'], rows)}`;
  },
  inv() {
    const own = me.role == 'Owner';
    return `<h1>Inventory</h1>${alerts()}` + tb(['Ingredient','Beginning','Stock-in','Stock-out','Remaining','Status', own ? 'Action' : ''],
      db.ings.map(i => [esc(i.name), i.begin + ' ' + i.unit, i.inn, i.out, i.stock + ' ' + i.unit,
        `<span class="tag${st(i) == 'Available' ? '' : ' bad'}">${st(i)}</span>`, own ? `<button data-act="stockin" data-id="${i.id}">Add stock</button>` : '']));
  },
  tx() {
    const sales = db.sales.slice().reverse().map(s => [s.id, s.date, esc(s.pn) + ' x ' + s.qty, money(s.total),
      `<span class="tag${s.status == 'Refunded' ? ' bad' : ''}">${s.status}</span>`,
      s.status == 'Completed' ? `<button data-act="refund" data-id="${s.id}">Refund</button>` : '']);
    const ref = db.refunds.slice().reverse().map(r => [r.sid, r.date, money(r.amt), esc(r.why), r.back ? 'Returned to stock' : 'Cannot be resold', esc(r.by)]);
    return `<h1>Transactions</h1>${msg}${tb(['Sale','Date','Item','Total','Status','Action'], sales)}<h2>Refunds</h2>${tb(['Sale','Date','Amount','Reason','Item','Approved by'], ref)}`;
  },
  exp() {
    const cats = ['Rent','Electricity','Water','Internet','Salaries/Wages','Supplies','Transportation','Maintenance','Other'];
    return `<h1>Expenses</h1><form id="ef" class="fm"><label>Type<select name="t">${cats.map(c => `<option>${c}</option>`).join('')}</select></label>
      <label>Description<input name="d"></label><label>Amount (₱)<input name="a" type="number" min="0.01" step="0.01" required></label>
      <button class="pr">Save expense</button></form>` +
      tb(['Date','Type','Description','Amount'], db.exps.slice().reverse().map(e => [e.date, e.t, esc(e.d), money(e.amt)])) + `<p><b>Total: ${money(sum(db.exps, 'amt'))}</b></p>`;
  },
  pnl() {
    const s = sum(done(), 'total'), c = sum(done(), 'cost'), e = sum(db.exps, 'amt'), n = s - c - e;
    return `<h1>Profit / Loss</h1><div class="kp">${k('Total sales', money(s))}${k('Total product costs', money(c))}${k('Gross profit', money(s - c))}${k('Operating expenses', money(e))}${k('Net profit / loss', money(n))}</div>
      <h2>Status</h2><p class="big">${n >= 0 ? 'Earning' : 'Losing money'}</p><p>Refunded sales are left out. Product cost = ingredients used + packaging.</p>
      <h2>Cost per product</h2>${tb(['Product','Price','Cost','Margin'], db.prods.map(p => [esc(p.name), money(p.price), money(pcost(p)), money(p.price - pcost(p))]))}`;
  },
  audit() { return '<h1>Audit log</h1>' + tb(['Time','User','Action','Area'], db.audit.map(a => [a.t, esc(a.u), esc(a.a), a.tbl])); }
};

function render() {
  clearTimeout(idle);
  if (!me) { location.replace('login.html'); return; } // not logged in: go to the login page
  idle = setTimeout(() => { me = null; sessionStorage.removeItem('me'); sessionStorage.notice = 'You were logged out after 10 minutes of inactivity.'; render(); }, IDLE_MS);
  const nav = NAV[me.role];
  if (!nav.some(n => n[0] == view)) view = nav[0][0];
  $('#app').innerHTML = `<header><span class="brand">Brews &amp; Blessings</span><span>${esc(me.name)} (${me.role}) <button data-act="out">Log out</button></span></header>
    <div class="shell"><nav>${nav.map(n => `<button data-act="nav" data-v="${n[0]}" class="${n[0] == view ? 'on' : ''}">${n[1]}</button>`).join('')}</nav><main>${V[view]()}</main></div>`;
  msg = '';
}

document.addEventListener('submit', e => {
  e.preventDefault(); const f = Object.fromEntries(new FormData(e.target));
  if (e.target.id == 'lf') {
    const u = db.users.find(x => x.u == f.u && x.p == f.p);
    if (!u) { msg = 'Wrong username or password. Check both and try again.'; return render(); }
    me = u; sessionStorage.me = JSON.stringify(u); if (u.role == 'Barista') db.duty = u.name; save(); log('Logged in', 'USER'); msg = ''; view = '';
  }
  if (e.target.id == 'of') {
    const p = P(f.p), q = +f.q, o = {id:db.seq++, pid:p.id, qty:q, c:f.c, n:f.n, status:'Pending', date:day(), time:new Date().toLocaleTimeString()};
    const short = Object.entries(p.rec).find(([i, n]) => G(i).stock < n * q);
    if (short) msg = `<div class="warn">Not enough ${esc(G(short[0]).name)} for this order. Add stock first.</div>`;
    else { o.no = 'BB-' + String(db.orders.length + 1).padStart(3, '0'); db.orders.push(o); use(o, 1); log('Recorded order ' + o.no, 'ORDERS'); }
  }
  if (e.target.id == 'ef') { db.exps.push({date:day(), t:f.t, d:f.d, amt:+f.a}); log('Added ' + f.t + ' expense', 'EXPENSE'); }
  save(); render();
});
document.addEventListener('change', e => {
  if (e.target.dataset.act != 'status') return;
  const o = db.orders.find(x => x.id == e.target.dataset.id); o.status = e.target.value; log(`Order ${o.no} set to ${o.status}`, 'ORDERS'); render();
});
document.addEventListener('click', e => {
  if (me) { clearTimeout(idle); idle = setTimeout(() => { me = null; sessionStorage.removeItem('me'); sessionStorage.notice = 'You were logged out after 10 minutes of inactivity.'; render(); }, IDLE_MS); }
  const b = e.target.closest('[data-act]'); if (!b || b.tagName == 'SELECT') return;
  const a = b.dataset.act, id = b.dataset.id, o = db.orders.find(x => x.id == id);
  if (a == 'nav') view = b.dataset.v;
  if (a == 'out') { log('Logged out', 'USER'); me = null; sessionStorage.removeItem('me'); }
  if (a == 'cancel') {
    const why = (prompt('Reason for cancelling this order (required):') || '').trim();
    if (!why) return alert('A reason is required to cancel an order.');
    o.status = 'Cancelled'; o.reason = why; use(o, -1); log(`Cancelled ${o.no}: ${why}`, 'ORDERS');
  }
  if (a == 'pay') {
    const p = P(o.pid), total = p.price * o.qty, t = parseFloat(prompt(`Total is ${money(total)}. Cash received (₱):`));
    if (isNaN(t) || t < total) return alert('Cash received must cover the total.');
    db.sales.push({id:'S' + String(db.sales.length + 1).padStart(3, '0'), oid:o.id, date:day(), pn:p.name, qty:o.qty, total, cost:pcost(p) * o.qty, status:'Completed'});
    log(`Recorded cash payment for ${o.no}`, 'SALE'); msg = `<div class="warn">Payment recorded. Change: ${money(t - total)}</div>`;
  }
  if (a == 'stockin') {
    const q = parseFloat(prompt('Quantity to add:')); if (!(q > 0)) return;
    const g = G(id); g.stock += q; g.inn += q; log(`Stock-in ${q} ${g.unit} ${g.name}`, 'STOCK_MOVEMENT');
  }
  if (a == 'refund' && me.role == 'Owner') {
    const s = db.sales.find(x => x.id == id), why = (prompt('Reason for refund (required):') || '').trim();
    if (!why) return alert('A reason is required for a refund.');
    const back = confirm('Can this item be resold? OK = yes, return ingredients to stock. Cancel = no.');
    s.status = 'Refunded'; db.refunds.push({sid:s.id, date:day(), amt:s.total, why, back, by:me.name});
    if (back) use(db.orders.find(x => x.id == s.oid), -1);
    log(`Approved refund ${s.id}: ${why}`, 'REFUND');
  }
  save(); render();
});
render();