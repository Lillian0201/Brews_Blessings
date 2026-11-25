// Settings Page Logic: products and users are saved in the database through the API.
(function () {
  'use strict';

  // Mount navigation sidebar
  const me = BBNav.mount('settings');
  if (!me) return;

  const API = BBAPI.base;
  const CATEGORIES = ['Coffee', 'Non-Coffee', 'Refreshers'];

  const $ = id => document.getElementById(id);
  const money = n => '\u20B1' + (+n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // ---------- API ----------
  async function api(method, path, body) {
    let res;
    try {
      res = await BBAPI.fetch(API + path, {
        method,
        headers: { ...(body ? { 'Content-Type': 'application/json' } : {}) },
        body: body ? JSON.stringify(body) : undefined
      });
    } catch {
      throw new Error("Can't reach the server. Check your connection and try again.");
    }
    let data = null;
    try { data = await res.json(); } catch { /* no body */ }
    if (!res.ok) throw new Error((data && data.detail) || `Server error (${res.status}).`);
    return data;
  }

  // ---------- State ----------
  let products = [];
  let users = [];
  let loadError = '';
  const state = { tab: 'products', category: 'All', search: '' };

  async function loadAll() {
    try {
      [products, users] = await Promise.all([api('GET', '/products'), api('GET', '/users')]);
      loadError = '';
    } catch (err) {
      loadError = err.message;
    }
    renderAll();
  }

  // ---------- Tabs ----------
  const CARDS = { products: 'cardProducts', users: 'cardUsers', backups: 'cardBackups' };

  function renderTabs() {
    document.querySelectorAll('.pills > .pill').forEach(p => p.classList.toggle('active', p.dataset.tab === state.tab));
    Object.entries(CARDS).forEach(([tab, id]) => { $(id).hidden = tab !== state.tab; });
  }

  document.querySelector('.pills').addEventListener('click', e => {
    const pill = e.target.closest('.pill');
    if (!pill) return;
    state.tab = pill.dataset.tab;
    renderTabs();
  });

  // ---------- Products ----------
  function renderChips() {
    const counts = { All: products.length };
    CATEGORIES.forEach(c => { counts[c] = products.filter(p => p.category === c).length; });
    $('catChips').innerHTML = ['All', ...CATEGORIES].map(c =>
      `<button type="button" class="pill${c === state.category ? ' active' : ''}" data-cat="${c}">${c}<span class="count">${counts[c]}</span></button>`
    ).join('');
  }

  function renderProducts() {
    renderChips();
    const q = state.search.trim().toLowerCase();
    const rows = products.filter(p =>
      (state.category === 'All' || p.category === state.category) && (!q || p.name.toLowerCase().includes(q)));

    $('productsTableBody').innerHTML = rows.map(p => `
      <tr>
        <td><strong>${esc(p.name)}</strong></td>
        <td>${esc(p.category)}</td>
        <td>${money(p.price)} / ${money(p.grandeurPrice ?? p.price)} / ${p.hotPrice == null ? '—' : money(p.hotPrice)}</td>
        <td>${money(p.packagingCost)}</td>
        <td><span class="${p.available ? 'badge-yes' : 'badge-no'}">${p.available ? 'Yes' : 'No'}</span></td>
        <td class="action-links">
          <button type="button" data-edit="${p.id}">Edit</button> |
          <button type="button" data-delete="${p.id}">Delete</button>
        </td>
      </tr>`).join('');

    const empty = $('productsEmpty');
    empty.hidden = !loadError && rows.length > 0;
    empty.textContent = loadError || (products.length ? 'No products match your search.' : 'No products yet. Click + Add Product.');
  }

  $('catChips').addEventListener('click', e => {
    const b = e.target.closest('[data-cat]');
    if (!b) return;
    state.category = b.dataset.cat;
    renderProducts();
  });
  $('productSearch').addEventListener('input', e => { state.search = e.target.value; renderProducts(); });

  $('productsTableBody').addEventListener('click', async e => {
    const edit = e.target.closest('[data-edit]');
    const del = e.target.closest('[data-delete]');
    if (edit) openProductModal(products.find(p => String(p.id) === edit.dataset.edit));
    if (del) await deleteProduct(products.find(p => String(p.id) === del.dataset.delete));
  });

  async function deleteProduct(p) {
    if (!p) return;
    if (!await BBDialog.confirm(
      'Delete product?',
      `Delete ${p.name}? If it already has sales or stock, it will be marked Unavailable instead.`,
      { okText: 'Delete', danger: true }
    )) return;
    try {
      const res = await api('DELETE', `/products/${p.id}`);
      await loadAll();
      if (!res.deleted) {
        await BBDialog.notify(
          'Product unavailable',
          `${p.name} has sales or stock records, so it was marked Unavailable instead of deleted.`
        );
      }
    } catch (err) {
      await BBDialog.notify('Delete failed', err.message);
    }
  }

  // ---------- Product modal (add + edit) ----------
  const prodModal = $('productModal');
  let editingProduct = null;

  function showError(id, msg) { const el = $(id); el.textContent = msg || ''; el.hidden = !msg; }

  function openProductModal(product) {
    editingProduct = product || null;
    $('productForm').reset();
    showError('prodError', '');
    $('prodModalTitle').textContent = product ? 'Edit Product' : 'Add Product';
    $('prodSubmit').textContent = product ? 'Save' : 'Add';
    if (product) {
      $('prodName').value = product.name;
      $('prodCategory').value = product.category;
      $('prodPrice').value = product.price;
      $('prodGrandeurPrice').value = product.grandeurPrice ?? product.price;
      $('prodHotPrice').value = product.hotPrice ?? '';
      $('prodPkg').value = product.packagingCost;
      $('prodAvailable').checked = product.available;
    }
    prodModal.classList.add('active');
    $('prodName').focus();
  }

  $('btnAddProduct').addEventListener('click', () => openProductModal(null));
  $('cancelProductBtn').addEventListener('click', () => prodModal.classList.remove('active'));

  $('productForm').addEventListener('submit', async e => {
    e.preventDefault();
    const body = {
      name: $('prodName').value.trim(),
      category: $('prodCategory').value,
      price: $('prodPrice').value,
      grandeurPrice: $('prodGrandeurPrice').value,
      hotPrice: $('prodHotPrice').value || null,
      packagingCost: $('prodPkg').value,
      available: $('prodAvailable').checked
    };
    $('prodSubmit').disabled = true;
    try {
      if (editingProduct) await api('PUT', `/products/${editingProduct.id}`, body);
      else await api('POST', '/products', body);
      prodModal.classList.remove('active');
      await loadAll();
    } catch (err) {
      showError('prodError', err.message);
    } finally {
      $('prodSubmit').disabled = false;
    }
  });

  // ---------- Users ----------
  function renderUsers() {
    $('usersTableBody').innerHTML = users.map(u => `
      <tr>
        <td><strong>${esc(u.name)}</strong></td>
        <td>${esc(u.username)}</td>
        <td>${esc(u.role)}</td>
        <td><span class="${u.active ? 'badge-yes' : 'badge-no'}">${u.active ? 'Yes' : 'No'}</span></td>
        <td class="action-links"><button type="button" data-toggle="${u.id}">${u.active ? 'Deactivate' : 'Activate'}</button></td>
      </tr>`).join('');
    const empty = $('usersEmpty');
    empty.hidden = !loadError && users.length > 0;
    empty.textContent = loadError || 'No users yet.';
  }

  $('usersTableBody').addEventListener('click', async e => {
    const b = e.target.closest('[data-toggle]');
    if (!b) return;
    const u = users.find(x => String(x.id) === b.dataset.toggle);
    if (!u) return;
    if (u.active && !await BBDialog.confirm(
      'Deactivate user?',
      `Deactivate ${u.name}? They won't be able to log in.`,
      { okText: 'Deactivate' }
    )) return;
    try {
      await api('PUT', `/users/${u.id}`, { active: !u.active });
      await loadAll();
    } catch (err) {
      await BBDialog.notify('User update failed', err.message);
    }
  });

  // ---------- User modal ----------
  const userModal = $('userModal');

  $('btnAddUser').addEventListener('click', () => {
    $('userForm').reset();
    showError('userError', '');
    userModal.classList.add('active');
    $('userName').focus();
  });
  $('cancelUserBtn').addEventListener('click', () => userModal.classList.remove('active'));

  $('userForm').addEventListener('submit', async e => {
    e.preventDefault();
    $('userSubmit').disabled = true;
    try {
      await api('POST', '/users', {
        name: $('userName').value.trim(),
        username: $('userUsername').value.trim(),
        role: $('userRole').value,
        password: $('userPassword').value
      });
      userModal.classList.remove('active');
      await loadAll();
    } catch (err) {
      showError('userError', err.message);
    } finally {
      $('userSubmit').disabled = false;
    }
  });

  // ---------- Backup action ----------
  const btnBackup = $('btnBackupNow');
  const backupStatus = $('backupStatusText');
  btnBackup.addEventListener('click', async () => {
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    backupStatus.textContent = `Last Backup: ${dateStr}`;

    // Generate JSON download (products and users as loaded from the database)
    const backupData = { timestamp: now.toISOString(), products, users };
    const blob = new Blob([JSON.stringify(backupData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `brews_blessings_backup_${now.toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    await BBDialog.notify('Backup complete', 'Backup generated and downloaded successfully!');
  });

  // ---------- Start ----------
  function renderAll() { renderTabs(); renderProducts(); renderUsers(); }
  renderAll();
  loadAll();
})();
