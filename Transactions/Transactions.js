/* Transactions page: Sales, Discounts, Voided, Refunded + Refund and Void forms.
   Data is kept in localStorage for now (mock). Replace load()/save() with fetch calls
   to the backend when it is ready. */
(() => {
  'use strict';

  /* ---------- Settings ---------- */
  const VOID_ROLES = ['Owner'];        // who may void a sale (requirements do not say; change if needed)
  const KEYS = { sales: 'bb_tx_sales', refunds: 'bb_tx_refunds' };   // separate from the shared 'bb' data so we never overwrite it

  /* ---------- Helpers ---------- */
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const peso = n => '₱' + Number(n).toLocaleString('en-PH', { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 });
  const shortDate = iso => { const d = new Date(iso + 'T00:00:00'); return `${d.getMonth() + 1}/${d.getDate()}`; };
  const today = () => new Date().toISOString().slice(0, 10);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function load(key, fallback) {
    try { const v = JSON.parse(localStorage.getItem(key)); return v ?? fallback; } catch { return fallback; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage full or blocked */ }
  }

  /* ---------- Seed data (matches the mockup) ---------- */
  const SEED_SALES = [
    { id: 'S01', date: '2026-10-28', orderNo: '001', items: [{ name: 'Spanish Latte', qty: 1, price: 180 }], discount: 0, serviceCharge: 0, payment: 'Cash', status: 'Completed' },
    { id: 'S02', date: '2026-10-28', orderNo: '002', items: [{ name: 'Café Latte', qty: 1, price: 150 }], discount: 0, serviceCharge: 0, payment: 'Cash', status: 'Refunded' },
    { id: 'S03', date: '2026-10-28', orderNo: '003', items: [{ name: 'Mocha Latte', qty: 1, price: 165 }], discount: 0, serviceCharge: 0, payment: 'Cash', status: 'Voided',
      voidReason: 'Customer left before paying', voidedBy: 'Owner', voidedAt: '2026-10-28' }
  ];
  const SEED_REFUNDS = [
    { id: 'R01', saleId: 'S02', item: 'Café Latte', amount: 150, reason: 'Wrong drink served', itemReturned: false,
      requestedBy: 'Barista', requestedAt: '2026-10-28', status: 'Approved', approvedBy: 'Owner', approvedAt: '2026-10-28' }
  ];

  let sales = load(KEYS.sales, null) || SEED_SALES;
  let refunds = load(KEYS.refunds, null) || SEED_REFUNDS;
  const persist = () => {
    save(KEYS.sales, sales); save(KEYS.refunds, refunds);
    window.dispatchEvent(new CustomEvent('transactions:changed'));   // Dashboard can listen to this
  };
  if (!localStorage.getItem(KEYS.sales)) persist();

  /* ---------- Current user (session set by the Login page, read through nav.js) ---------- */
  function currentUser() {
    return (window.BBNav && BBNav.getSessionUser()) || { name: 'Unknown', role: '' };
  }
  const isOwner = () => currentUser().role === 'Owner';

  /* ---------- Derived data ---------- */
  const subtotal = s => s.items.reduce((sum, i) => sum + i.qty * i.price, 0);
  const total = s => subtotal(s) - (s.discount || 0) + (s.serviceCharge || 0);
  const refundFor = (saleId, status) => refunds.find(r => r.saleId === saleId && (!status || r.status === status));
  const pendingFor = saleId => refundFor(saleId, 'Pending');

  /* ---------- Audit log + inventory hooks ---------- */
  function audit(action, tbl) {
    // Same format nav.js uses for the shared Audit log: localStorage 'bb' -> audit[] of {t, u, a, tbl}
    try {
      const raw = localStorage.getItem('bb');
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data || typeof data !== 'object' || Array.isArray(data)) return;
      if (!Array.isArray(data.audit)) data.audit = [];
      data.audit.unshift({ t: new Date().toLocaleString(), u: currentUser().name, a: action, tbl });
      localStorage.setItem('bb', JSON.stringify(data));
    } catch (error) {
      console.error('Could not write audit log:', error);
    }
  }

  // Inventory teammate: define window.Inventory = { restoreStock(info), recordWaste(info) } and these will be called.
  function inventory(type, sale, item) {
    const fn = type === 'restore' ? 'restoreStock' : 'recordWaste';
    const info = { saleId: sale.id, orderNo: sale.orderNo, item, items: sale.items };
    if (window.Inventory && typeof window.Inventory[fn] === 'function') window.Inventory[fn](info);
    else console.info(`[Inventory hook] ${fn}`, info);
  }

  /* ---------- UI state ---------- */
  const state = { tab: 'sales', selected: null, search: '', payment: '' };

  const COLUMNS = {
    sales: [
      ['Sale #', s => s.id], ['Date', s => shortDate(s.date)], ['Order #', s => s.orderNo],
      ['Discount', s => s.discount ? peso(s.discount) : '—'], ['Service Charge', s => s.serviceCharge ? peso(s.serviceCharge) : '—'],
      ['Total', s => peso(total(s)), 'num'], ['Payment', s => s.payment], ['Status', statusCell]
    ],
    discounts: [
      ['Sale #', s => s.id], ['Date', s => shortDate(s.date)], ['Order #', s => s.orderNo],
      ['Subtotal', s => peso(subtotal(s)), 'num'], ['Discount', s => peso(s.discount), 'num'],
      ['Total', s => peso(total(s)), 'num'], ['Status', statusCell]
    ],
    voided: [
      ['Sale #', s => s.id], ['Date', s => shortDate(s.date)], ['Order #', s => s.orderNo],
      ['Total', s => peso(total(s)), 'num'], ['Void Reason', s => esc(s.voidReason || '—')], ['Voided By', s => esc(s.voidedBy || '—')]
    ],
    refunded: [
      ['Sale #', s => s.id], ['Date', s => shortDate(s.date)], ['Order #', s => s.orderNo],
      ['Refund', s => peso(refundFor(s.id, 'Approved')?.amount ?? 0), 'num'],
      ['Reason', s => esc(refundFor(s.id, 'Approved')?.reason || '—')],
      ['Restocked', s => refundFor(s.id, 'Approved')?.itemReturned ? 'Yes' : 'No'],
      ['Approved By', s => esc(refundFor(s.id, 'Approved')?.approvedBy || '—')]
    ]
  };
  const EMPTY = {
    sales: 'No transactions match your search.',
    discounts: 'No discounted sales yet. Discounts applied at payment will show here.',
    voided: 'No voided sales.',
    refunded: 'No refunded sales.'
  };
  const TITLES = { sales: 'Sale Transaction', discounts: 'Discounted Sales', voided: 'Voided Transactions', refunded: 'Refunded Transactions' };

  function statusCell(s) {
    let html = `<span class="badge badge-${s.status.toLowerCase()}">${s.status}</span>`;
    if (s.status === 'Completed' && pendingFor(s.id)) html += `<span class="badge badge-pending">Refund requested</span>`;
    return html;
  }

  function tabSales(tab) {
    switch (tab) {
      case 'discounts': return sales.filter(s => s.discount > 0);
      case 'voided': return sales.filter(s => s.status === 'Voided');
      case 'refunded': return sales.filter(s => s.status === 'Refunded');
      default: return sales;
    }
  }

  /* ---------- Rendering ---------- */
  function renderTabs() {
    $$('.tab').forEach(btn => {
      const t = btn.dataset.tab, n = tabSales(t).length;
      const active = t === state.tab;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-selected', active);
      btn.innerHTML = `${btn.textContent.replace(/\s*\d+$/, '')}${t === 'sales' ? '' : `<span class="count">${n}</span>`}`;
    });
  }

  function renderTable() {
    const cols = COLUMNS[state.tab];
    $('#tableTitle').textContent = TITLES[state.tab];
    $('#txHead').innerHTML = `<tr>${cols.map(c => `<th class="${c[2] || ''}">${c[0]}</th>`).join('')}</tr>`;

    const q = state.search.trim().toLowerCase();
    const rows = tabSales(state.tab).filter(s =>
      (!q || s.id.toLowerCase().includes(q) || s.orderNo.toLowerCase().includes(q)) &&
      (!state.payment || s.payment === state.payment));

    $('#txBody').innerHTML = rows.map(s => `
      <tr tabindex="0" data-id="${s.id}" class="${s.id === state.selected ? 'is-selected' : ''}">
        ${cols.map(c => `<td class="${c[2] || ''}">${c[1](s)}</td>`).join('')}
      </tr>`).join('');

    const empty = $('#emptyMsg');
    empty.hidden = rows.length > 0;
    empty.textContent = EMPTY[state.tab];
  }

  function fillSaleSelect(sel, list, keep) {
    sel.innerHTML = `<option value="">Select a sale</option>` +
      list.map(s => `<option value="${s.id}">${s.id} · Order ${s.orderNo} · ${peso(total(s))}</option>`).join('');
    if (keep && list.some(s => s.id === keep)) sel.value = keep;
  }

  function renderForms() {
    const completed = sales.filter(s => s.status === 'Completed');
    fillSaleSelect($('#refundSale'), completed, $('#refundSale').value);
    fillSaleSelect($('#voidSale'), completed, $('#voidSale').value);
    renderItemSelect();

    const owner = isOwner();
    $('#refundApprover').value = owner ? currentUser().name : '';
    $('#refundApprover').placeholder = owner ? '' : 'Owner/Manager approval required';
    $('#btnApprove').disabled = !owner;
    $('#btnApprove').title = owner ? '' : 'Only an Owner/Manager can approve refunds';
    $('#btnVoid').disabled = !VOID_ROLES.includes(currentUser().role);
    $('#btnVoid').title = $('#btnVoid').disabled ? 'Only an Owner/Manager can void a sale' : '';
    renderPending();
  }

  function renderItemSelect(keepItem) {
    const sel = $('#refundItem');
    const sale = sales.find(s => s.id === $('#refundSale').value);
    if (!sale) {
      sel.innerHTML = '<option value="">Select a sale first</option>';
      sel.disabled = true;
      return;
    }
    sel.disabled = false;
    sel.innerHTML = '<option value="">Select an item</option>' +
      sale.items.map((i, idx) => `<option value="${idx}">${esc(i.name)} × ${i.qty}</option>`).join('') +
      '<option value="all">Whole order</option>';
    if (keepItem !== undefined) sel.value = keepItem;
  }

  function renderPending() {
    const list = refunds.filter(r => r.status === 'Pending');
    $('#pendingBox').hidden = list.length === 0;
    $('#pendingList').innerHTML = list.map(r => `
      <li>
        <span>${r.saleId} · ${peso(r.amount)}<small>${esc(r.reason)} · by ${esc(r.requestedBy)}</small></span>
        ${isOwner() ? `<button type="button" class="btn btn-soft" data-review="${r.id}">Review</button>` : ''}
      </li>`).join('');
  }

  function renderAll() { renderTabs(); renderTable(); renderForms(); }

  /* ---------- Feedback ---------- */
  let toastTimer;
  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg; t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.hidden = true; }, 3500);
  }
  function showError(id, msg) { const e = $(id); e.textContent = msg; e.hidden = !msg; }
  function mark(el, bad) { el.classList.toggle('invalid', !!bad); return !bad; }

  function confirmAction(title, msg, okLabel) {
    const dlg = $('#confirmDialog');
    $('#confirmTitle').textContent = title;
    $('#confirmMsg').textContent = msg;
    $('#confirmOk').textContent = okLabel || 'Confirm';
    return new Promise(resolve => {
      dlg.addEventListener('close', () => resolve(dlg.returnValue === 'ok'), { once: true });
      dlg.returnValue = 'cancel';
      dlg.showModal();
    });
  }

  /* ---------- Refund logic ---------- */
  function readRefundForm() {
    const saleEl = $('#refundSale'), itemEl = $('#refundItem'), amtEl = $('#refundAmount'), reasonEl = $('#refundReason');
    const sale = sales.find(s => s.id === saleEl.value);
    const amount = parseFloat(amtEl.value);
    const reason = reasonEl.value.trim();

    const okSale = mark(saleEl, !sale);
    const okItem = mark(itemEl, !itemEl.value);
    const okAmt = mark(amtEl, !(amount > 0) || (sale && amount > total(sale)));
    const okReason = mark(reasonEl, !reason);

    if (!(okSale && okItem && okAmt && okReason)) {
      let msg = 'Fill in all required fields.';
      if (sale && amount > total(sale)) msg = `Refund amount can't be more than the sale total (${peso(total(sale))}).`;
      else if (!(amount > 0) && amtEl.value) msg = 'Refund amount must be more than zero.';
      showError('#refundError', msg);
      return null;
    }
    showError('#refundError', '');
    const itemName = itemEl.value === 'all' ? 'Whole order' : sale.items[+itemEl.value].name;
    return { sale, amount, reason, item: itemName, itemReturned: $('#refundReturned').checked };
  }

  function nextRefundId() { return 'R' + String(refunds.length + 1).padStart(2, '0'); }

  function requestRefund() {
    const f = readRefundForm(); if (!f) return;
    if (pendingFor(f.sale.id)) { showError('#refundError', `Sale ${f.sale.id} already has a pending refund request.`); return; }
    refunds.push({ id: nextRefundId(), saleId: f.sale.id, item: f.item, amount: f.amount, reason: f.reason, itemReturned: f.itemReturned,
      requestedBy: currentUser().name, requestedAt: today(), status: 'Pending' });
    audit('Requested refund for ' + f.sale.id, 'REFUND');
    persist(); clearRefundForm(); renderAll();
    toast(`Refund requested for ${f.sale.id}. An Owner/Manager needs to approve it.`);
  }

  async function approveRefund() {
    if (!isOwner()) { showError('#refundError', 'Only an Owner/Manager can approve refunds.'); return; }
    const f = readRefundForm(); if (!f) return;
    const ok = await confirmAction('Approve this refund?',
      `${peso(f.amount)} will be refunded for sale ${f.sale.id}. The sale will be marked Refunded and ${f.itemReturned ? 'the item will be restocked' : 'the item will be recorded as waste'}.`,
      'Approve refund');
    if (!ok) return;

    let r = pendingFor(f.sale.id);
    if (!r) { r = { id: nextRefundId(), saleId: f.sale.id, requestedBy: currentUser().name, requestedAt: today() }; refunds.push(r); }
    Object.assign(r, { item: f.item, amount: f.amount, reason: f.reason, itemReturned: f.itemReturned,
      status: 'Approved', approvedBy: currentUser().name, approvedAt: today() });
    f.sale.status = 'Refunded';

    inventory(f.itemReturned ? 'restore' : 'waste', f.sale, f.item);
    audit('Approved refund for ' + f.sale.id, 'REFUND');
    persist(); clearRefundForm(); state.selected = f.sale.id; state.tab = 'refunded'; renderAll();
    toast(`Refund approved. ${f.sale.id} is now marked Refunded.`);
  }

  function clearRefundForm() {
    $('#refundForm').reset();
    $$('#refundForm .invalid').forEach(e => e.classList.remove('invalid'));
    showError('#refundError', '');
    renderItemSelect();
  }

  function reviewRequest(id) {
    const r = refunds.find(x => x.id === id); if (!r) return;
    $('#refundSale').value = r.saleId;
    renderItemSelect();
    const sale = sales.find(s => s.id === r.saleId);
    const idx = sale.items.findIndex(i => i.name === r.item);
    $('#refundItem').value = r.item === 'Whole order' ? 'all' : String(idx);
    $('#refundAmount').value = r.amount;
    $('#refundReason').value = r.reason;
    $('#refundReturned').checked = r.itemReturned;
    state.selected = r.saleId; renderTable();
  }

  /* ---------- Void logic ---------- */
  async function voidSale() {
    if (!VOID_ROLES.includes(currentUser().role)) { showError('#voidError', 'Only an Owner/Manager can void a sale.'); return; }
    const saleEl = $('#voidSale'), reasonEl = $('#voidReason');
    const sale = sales.find(s => s.id === saleEl.value);
    const reason = reasonEl.value.trim();
    const okSale = mark(saleEl, !sale), okReason = mark(reasonEl, !reason);
    if (!(okSale && okReason)) { showError('#voidError', 'Choose a sale and enter a void reason.'); return; }
    showError('#voidError', '');

    const ok = await confirmAction('Void this sale?',
      `Sale ${sale.id} (${peso(total(sale))}) will be marked Voided and its stock restored. This can't be undone.`, 'Void sale');
    if (!ok) return;

    Object.assign(sale, { status: 'Voided', voidReason: reason, voidedBy: currentUser().name, voidedAt: today() });
    if (pendingFor(sale.id)) refunds = refunds.filter(r => !(r.saleId === sale.id && r.status === 'Pending'));
    inventory('restore', sale, 'Whole order');
    audit('Voided sale ' + sale.id, 'SALE');
    persist();
    $('#voidForm').reset(); state.selected = sale.id; state.tab = 'voided'; renderAll();
    toast(`${sale.id} voided.`);
  }

  /* ---------- Events ---------- */
  function wire() {
    $$('.tab').forEach(b => b.addEventListener('click', () => { state.tab = b.dataset.tab; renderTabs(); renderTable(); }));

    $('#searchBox').addEventListener('input', e => { state.search = e.target.value; renderTable(); });
    $('#paymentFilter').addEventListener('change', e => { state.payment = e.target.value; renderTable(); });

    const pick = row => {
      if (!row) return;
      state.selected = row.dataset.id; renderTable();
      const s = sales.find(x => x.id === state.selected);
      if (s && s.status === 'Completed') {
        $('#refundSale').value = s.id; renderItemSelect();
        $('#voidSale').value = s.id;
      }
    };
    $('#txBody').addEventListener('click', e => pick(e.target.closest('tr')));
    $('#txBody').addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(e.target.closest('tr')); } });

    $('#refundSale').addEventListener('change', () => { renderItemSelect(); $('#refundAmount').value = ''; });
    $('#refundItem').addEventListener('change', () => {
      const sale = sales.find(s => s.id === $('#refundSale').value), v = $('#refundItem').value;
      if (!sale || !v) return;
      $('#refundAmount').value = v === 'all' ? total(sale) : sale.items[+v].qty * sale.items[+v].price;
    });
    $('#btnRequest').addEventListener('click', requestRefund);
    $('#btnApprove').addEventListener('click', approveRefund);
    $('#pendingList').addEventListener('click', e => { const b = e.target.closest('[data-review]'); if (b) reviewRequest(b.dataset.review); });
    $('#btnVoid').addEventListener('click', voidSale);

    // Clear red outline once the user edits a field
    $$('input, select').forEach(el => el.addEventListener('input', () => el.classList.remove('invalid')));

    // Keep in sync if another tab (e.g. POS) changes the data
    window.addEventListener('storage', e => {
      if (e.key === KEYS.sales || e.key === KEYS.refunds) { sales = load(KEYS.sales, sales); refunds = load(KEYS.refunds, refunds); renderAll(); }
    });
  }

  /* ---------- Start ---------- */
  window.addEventListener('DOMContentLoaded', () => {
    // nav.js: checks the login, redirects if this role can't see Transactions,
    // adds the shared sidebar and starts the 10-minute auto-logout.
    if (!window.BBNav) { console.error('nav.js did not load. Check the script path in Transactions.html.'); return; }
    if (!BBNav.mount('tx')) return;
    wire(); renderAll();
  });
})();
