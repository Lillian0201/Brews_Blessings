// Settings Page Logic
(function () {
  'use strict';

  // Mount navigation sidebar
  const me = BBNav.mount('settings');
  if (!me) return;

  const money = n => '₱' + (+n).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  });

  // ---------- COMPLETE MENU PRODUCTS FOR SETTINGS ----------
  let products = [
    // Coffee
    { id: 1, name: 'Americano', category: 'Coffee', price: 80, pkg: 8, available: true },
    { id: 2, name: 'Cafe Latte', category: 'Coffee', price: 120, pkg: 8, available: true },
    { id: 3, name: 'Caramel Latte', category: 'Coffee', price: 120, pkg: 8, available: true },
    { id: 4, name: 'Caramel Macchiato', category: 'Coffee', price: 130, pkg: 8, available: true },
    { id: 5, name: 'Caramelized Mocha', category: 'Coffee', price: 130, pkg: 8, available: true },
    { id: 6, name: 'Dirty Matcha', category: 'Coffee', price: 130, pkg: 8, available: true },
    { id: 7, name: 'Hazelnut Latte', category: 'Coffee', price: 120, pkg: 8, available: true },
    { id: 8, name: 'Salted Caramel Latte', category: 'Coffee', price: 120, pkg: 8, available: true },
    { id: 9, name: 'Spanish Latte', category: 'Coffee', price: 130, pkg: 8, available: true },
    { id: 10, name: 'Tres Leche Latte', category: 'Coffee', price: 130, pkg: 8, available: true },
    { id: 11, name: 'White Mocha Latte', category: 'Coffee', price: 130, pkg: 8, available: true },
    { id: 12, name: 'Biscoff Latte', category: 'Coffee', price: 165, pkg: 8, available: true },

    // Non-Coffee
    { id: 13, name: 'Blueberry Milk', category: 'Non Coffee', price: 110, pkg: 8, available: true },
    { id: 14, name: 'Caramel Milk', category: 'Non Coffee', price: 110, pkg: 8, available: true },
    { id: 15, name: 'Chocolate Milk', category: 'Non Coffee', price: 110, pkg: 8, available: true },
    { id: 16, name: 'Strawberry Milk', category: 'Non Coffee', price: 110, pkg: 8, available: true },
    { id: 17, name: 'Oreo Milk', category: 'Non Coffee', price: 110, pkg: 8, available: true },
    { id: 18, name: 'Matcha Milk', category: 'Non Coffee', price: 120, pkg: 8, available: true },
    { id: 19, name: 'Strawberry Matcha', category: 'Non Coffee', price: 120, pkg: 8, available: true },
    { id: 20, name: 'Strawberry Cocoa', category: 'Non Coffee', price: 120, pkg: 8, available: true },
    { id: 21, name: 'Milky Berry Oreo', category: 'Non Coffee', price: 120, pkg: 8, available: true },

    // Refreshers
    { id: 22, name: 'Blueberry Fizz', category: 'Refreshers', price: 69, pkg: 8, available: true },
    { id: 23, name: 'Green Apple Fizz', category: 'Refreshers', price: 69, pkg: 8, available: true },
    { id: 24, name: 'Lychee Fizz', category: 'Refreshers', price: 69, pkg: 8, available: true },
    { id: 25, name: 'Mango Fizz', category: 'Refreshers', price: 69, pkg: 8, available: true },
    { id: 26, name: 'Strawberry Fizz', category: 'Refreshers', price: 69, pkg: 8, available: true },
    { id: 27, name: 'Passion Fruit Fizz', category: 'Refreshers', price: 69, pkg: 8, available: true },
    { id: 28, name: 'Mango Passion', category: 'Refreshers', price: 110, pkg: 8, available: true },
    { id: 29, name: 'Paradise Coconut', category: 'Refreshers', price: 140, pkg: 8, available: true },
    { id: 30, name: 'Pink Berry Drink', category: 'Refreshers', price: 140, pkg: 8, available: true }
  ];

  let users = [
    { id: 1, name: 'Francis', username: 'francis', role: 'Owner/Manager', active: true },
    { id: 2, name: 'Barista 1', username: 'barista1', role: 'POS User', active: true }
  ];

  let auditLogs = [
    { date: '10/28 2:15 PM', user: 'francis', action: 'Approved refund', table: 'REFUND' },
    { date: '10/28 1:40 PM', user: 'barista1', action: 'Created order', table: 'ORDERS' },
    { date: '10/28 12:05 PM', user: 'francis', action: 'Stock-in', table: 'STOCK_MOVEMENT' }
  ];

  // Load any audit logs from localStorage if present
  try {
    const raw = localStorage.getItem('bb');
    if (raw) {
      const data = JSON.parse(raw);
      if (Array.isArray(data.audit) && data.audit.length > 0) {
        const mapped = data.audit.map(item => ({
          date: item.t,
          user: item.u,
          action: item.a,
          table: item.tbl
        }));
        auditLogs = [...mapped, ...auditLogs];
      }
    }
  } catch (e) {
    console.error(e);
  }

  // ---------- RENDER FUNCTIONS ----------
  function renderProducts() {
    const tbody = document.getElementById('productsTableBody');
    tbody.innerHTML = products.map(p => `
      <tr>
        <td><strong>${p.name}</strong></td>
        <td>${p.category}</td>
        <td>${money(p.price)}</td>
        <td>${money(p.pkg)}</td>
        <td><span class="badge-yes">${p.available ? 'Yes' : 'No'}</span></td>
        <td class="action-links">
          <button type="button" onclick="window.editProduct(${p.id})">Edit</button> | 
          <button type="button" onclick="window.deleteProduct(${p.id})">Delete</button>
        </td>
      </tr>
    `).join('');
  }

  function renderUsers() {
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = users.map(u => `
      <tr>
        <td><strong>${u.name}</strong></td>
        <td>${u.username}</td>
        <td>${u.role}</td>
        <td><span class="badge-yes">${u.active ? 'Yes' : 'No'}</span></td>
      </tr>
    `).join('');
  }

  function renderAudit() {
    const tbody = document.getElementById('auditTableBody');
    tbody.innerHTML = auditLogs.slice(0, 10).map(a => `
      <tr>
        <td>${a.date}</td>
        <td>${a.user}</td>
        <td>${a.action}</td>
        <td><strong>${a.table}</strong></td>
      </tr>
    `).join('');
  }

  // Window global actions for table buttons
  window.deleteProduct = function (id) {
    if (confirm('Are you sure you want to delete this product?')) {
      products = products.filter(p => p.id !== id);
      renderProducts();
    }
  };

  window.editProduct = function (id) {
    const prod = products.find(p => p.id === id);
    if (!prod) return;
    const newPrice = prompt(`Enter new selling price for ${prod.name}:`, prod.price);
    if (newPrice !== null && !isNaN(newPrice)) {
      prod.price = parseFloat(newPrice);
      renderProducts();
    }
  };

  // Modals handling
  const prodModal = document.getElementById('productModal');
  const userModal = document.getElementById('userModal');

  document.getElementById('btnAddProduct').addEventListener('click', () => {
    prodModal.classList.add('active');
  });

  document.getElementById('cancelProductBtn').addEventListener('click', () => {
    prodModal.classList.remove('active');
  });

  document.getElementById('productForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const name = document.getElementById('prodName').value.trim();
    const category = document.getElementById('prodCategory').value;
    const price = parseFloat(document.getElementById('prodPrice').value) || 0;
    const pkg = parseFloat(document.getElementById('prodPkg').value) || 0;

    products.push({ id: Date.now(), name, category, price, pkg, available: true });
    renderProducts();
    prodModal.classList.remove('active');
    document.getElementById('productForm').reset();
  });

  document.getElementById('btnAddUser').addEventListener('click', () => {
    userModal.classList.add('active');
  });

  document.getElementById('cancelUserBtn').addEventListener('click', () => {
    userModal.classList.remove('active');
  });

  document.getElementById('userForm').addEventListener('submit', (e) => {
    e.preventDefault();
    const name = document.getElementById('userName').value.trim();
    const username = document.getElementById('userUsername').value.trim();
    const role = document.getElementById('userRole').value;

    users.push({ id: Date.now(), name, username, role, active: true });
    renderUsers();
    userModal.classList.remove('active');
    document.getElementById('userForm').reset();
  });

  // Backup action
  const btnBackup = document.getElementById('btnBackupNow');
  const backupStatus = document.getElementById('backupStatusText');
  btnBackup.addEventListener('click', () => {
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    backupStatus.textContent = `Last Backup: ${dateStr}`;

    // Generate JSON download
    const backupData = {
      timestamp: now.toISOString(),
      products,
      users,
      auditLogs,
      localStorageBackup: { ...localStorage }
    };
    const blob = new Blob([JSON.stringify(backupData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `brews_blessings_backup_${now.toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    alert('Backup generated and downloaded successfully!');
  });

  // Tabs / Pills interactivity
  document.querySelectorAll('.pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');

      const tab = pill.dataset.tab;
      if (tab === 'products') document.getElementById('cardProducts').scrollIntoView({ behavior: 'smooth' });
      else if (tab === 'users') document.getElementById('cardUsers').scrollIntoView({ behavior: 'smooth' });
      else if (tab === 'audit') document.getElementById('cardAudit').scrollIntoView({ behavior: 'smooth' });
      else if (tab === 'backups') document.getElementById('cardBackups').scrollIntoView({ behavior: 'smooth' });
    });
  });

  // Init renders
  renderProducts();
  renderUsers();
  renderAudit();
})();
