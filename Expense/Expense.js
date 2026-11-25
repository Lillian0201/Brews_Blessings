// Expense and Product Costing Logic
(function () {
  'use strict';

  // Mount navigation sidebar
  const me = BBNav.mount('exp');
  if (!me) return;

  const money = n => '₱' + (+n).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });

  // ---------- EXPENSE TRACKING ----------
  const defaultExpenses = [
    { date: '10/25', type: 'Supplies', desc: 'Cups and lids', amount: 1450 },
    { date: '10/26', type: 'Transport', desc: 'Delivery', amount: 320 },
    { date: '10/27', type: 'Utilities', desc: 'Electricity bill', amount: 3200 }
  ];

  function loadExpenses() {
    try {
      const raw = localStorage.getItem('bb');
      if (raw) {
        const data = JSON.parse(raw);
        if (data && Array.isArray(data.exps) && data.exps.length > 0) {
          return data.exps;
        }
      }
    } catch (e) {
      console.error(e);
    }
    return defaultExpenses;
  }

  function saveExpenses(exps) {
    try {
      const raw = localStorage.getItem('bb');
      let data = raw ? JSON.parse(raw) : {};
      data.exps = exps;
      localStorage.setItem('bb', JSON.stringify(data));
    } catch (e) {
      console.error(e);
    }
  }

  let expenses = loadExpenses();

  function renderExpenses() {
    const tbody = document.getElementById('expenseTableBody');
    tbody.innerHTML = expenses.map(item => `
      <tr>
        <td>${item.date}</td>
        <td>${item.type}</td>
        <td>${item.desc}</td>
        <td class="text-right">${money(item.amount)}</td>
      </tr>
    `).join('');
  }

  const expDateInput = document.getElementById('expDate');
  if (expDateInput) {
    const today = new Date();
    expDateInput.value = today.toISOString().split('T')[0];
  }

  const expenseForm = document.getElementById('expenseForm');
  expenseForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const type = document.getElementById('expType').value;
    const amount = parseFloat(document.getElementById('expAmount').value) || 0;
    const desc = document.getElementById('expDesc').value.trim();
    const rawDate = document.getElementById('expDate').value;
    
    // Format mm/dd
    let formattedDate = rawDate;
    if (rawDate) {
      const parts = rawDate.split('-');
      if (parts.length === 3) formattedDate = `${parts[1]}/${parts[2]}`;
    }

    expenses.unshift({ date: formattedDate, type, desc, amount });
    saveExpenses(expenses);
    renderExpenses();

    // Reset form
    document.getElementById('expAmount').value = '';
    document.getElementById('expDesc').value = '';
  });

  // ---------- COMPLETE MENU PRODUCT RECIPES ----------
  const recipes = {
    // === COFFEE ===
    'Caramel Latte': {
      category: 'Coffee',
      sellingPrice: 120,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Fresh milk', qty: '150 ml', costPerUnit: 0.07, subtotal: 10.50 },
        { name: 'Caramel syrup', qty: '15 ml', costPerUnit: 0.30, subtotal: 4.50 }
      ]
    },
    'Cafe Latte': {
      category: 'Coffee',
      sellingPrice: 120,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Fresh milk', qty: '180 ml', costPerUnit: 0.07, subtotal: 12.60 }
      ]
    },
    'Americano': {
      category: 'Coffee',
      sellingPrice: 80,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Filtered water', qty: '200 ml', costPerUnit: 0.01, subtotal: 2.00 }
      ]
    },
    'Caramel Macchiato': {
      category: 'Coffee',
      sellingPrice: 130,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Fresh milk', qty: '150 ml', costPerUnit: 0.07, subtotal: 10.50 },
        { name: 'Vanilla syrup', qty: '10 ml', costPerUnit: 0.30, subtotal: 3.00 },
        { name: 'Caramel drizzle', qty: '10 ml', costPerUnit: 0.40, subtotal: 4.00 }
      ]
    },
    'Caramelized Mocha': {
      category: 'Coffee',
      sellingPrice: 130,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Fresh milk', qty: '150 ml', costPerUnit: 0.07, subtotal: 10.50 },
        { name: 'Dark chocolate sauce', qty: '20 ml', costPerUnit: 0.35, subtotal: 7.00 },
        { name: 'Caramel syrup', qty: '10 ml', costPerUnit: 0.30, subtotal: 3.00 }
      ]
    },
    'Dirty Matcha': {
      category: 'Coffee',
      sellingPrice: 130,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Matcha powder', qty: '8 g', costPerUnit: 1.50, subtotal: 12.00 },
        { name: 'Fresh milk', qty: '150 ml', costPerUnit: 0.07, subtotal: 10.50 }
      ]
    },
    'Hazelnut Latte': {
      category: 'Coffee',
      sellingPrice: 120,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Fresh milk', qty: '150 ml', costPerUnit: 0.07, subtotal: 10.50 },
        { name: 'Hazelnut syrup', qty: '15 ml', costPerUnit: 0.30, subtotal: 4.50 }
      ]
    },
    'Salted Caramel Latte': {
      category: 'Coffee',
      sellingPrice: 120,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Fresh milk', qty: '150 ml', costPerUnit: 0.07, subtotal: 10.50 },
        { name: 'Salted caramel syrup', qty: '15 ml', costPerUnit: 0.35, subtotal: 5.25 }
      ]
    },
    'Spanish Latte': {
      category: 'Coffee',
      sellingPrice: 130,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Fresh milk', qty: '140 ml', costPerUnit: 0.07, subtotal: 9.80 },
        { name: 'Condensed milk', qty: '30 ml', costPerUnit: 0.25, subtotal: 7.50 }
      ]
    },
    'Tres Leche Latte': {
      category: 'Coffee',
      sellingPrice: 130,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Tres Leches milk blend', qty: '160 ml', costPerUnit: 0.12, subtotal: 19.20 }
      ]
    },
    'White Mocha Latte': {
      category: 'Coffee',
      sellingPrice: 130,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Fresh milk', qty: '150 ml', costPerUnit: 0.07, subtotal: 10.50 },
        { name: 'White chocolate sauce', qty: '20 ml', costPerUnit: 0.40, subtotal: 8.00 }
      ]
    },
    'Biscoff Latte': {
      category: 'Coffee',
      sellingPrice: 165,
      packingCost: 8,
      ingredients: [
        { name: 'Espresso beans', qty: '18 g', costPerUnit: 1.20, subtotal: 21.60 },
        { name: 'Fresh milk', qty: '150 ml', costPerUnit: 0.07, subtotal: 10.50 },
        { name: 'Lotus Biscoff spread', qty: '25 g', costPerUnit: 0.60, subtotal: 15.00 },
        { name: 'Biscoff biscuit crush', qty: '1 pc', costPerUnit: 5.00, subtotal: 5.00 }
      ]
    },

    // === NON-COFFEE ===
    'Matcha Milk': {
      category: 'Non-Coffee',
      sellingPrice: 120,
      packingCost: 8,
      ingredients: [
        { name: 'Premium Matcha powder', qty: '10 g', costPerUnit: 1.50, subtotal: 15.00 },
        { name: 'Fresh milk', qty: '180 ml', costPerUnit: 0.07, subtotal: 12.60 },
        { name: 'Sugar syrup', qty: '15 ml', costPerUnit: 0.15, subtotal: 2.25 }
      ]
    },
    'Blueberry Milk': {
      category: 'Non-Coffee',
      sellingPrice: 110,
      packingCost: 8,
      ingredients: [
        { name: 'Fresh milk', qty: '180 ml', costPerUnit: 0.07, subtotal: 12.60 },
        { name: 'Blueberry fruit puree', qty: '30 ml', costPerUnit: 0.35, subtotal: 10.50 }
      ]
    },
    'Caramel Milk': {
      category: 'Non-Coffee',
      sellingPrice: 110,
      packingCost: 8,
      ingredients: [
        { name: 'Fresh milk', qty: '180 ml', costPerUnit: 0.07, subtotal: 12.60 },
        { name: 'Caramel syrup & drizzle', qty: '25 ml', costPerUnit: 0.30, subtotal: 7.50 }
      ]
    },
    'Chocolate Milk': {
      category: 'Non-Coffee',
      sellingPrice: 110,
      packingCost: 8,
      ingredients: [
        { name: 'Fresh milk', qty: '180 ml', costPerUnit: 0.07, subtotal: 12.60 },
        { name: 'Rich chocolate sauce', qty: '30 ml', costPerUnit: 0.35, subtotal: 10.50 }
      ]
    },
    'Strawberry Milk': {
      category: 'Non-Coffee',
      sellingPrice: 110,
      packingCost: 8,
      ingredients: [
        { name: 'Fresh milk', qty: '180 ml', costPerUnit: 0.07, subtotal: 12.60 },
        { name: 'Strawberry fruit puree', qty: '30 ml', costPerUnit: 0.35, subtotal: 10.50 }
      ]
    },
    'Oreo Milk': {
      category: 'Non-Coffee',
      sellingPrice: 110,
      packingCost: 8,
      ingredients: [
        { name: 'Fresh milk', qty: '180 ml', costPerUnit: 0.07, subtotal: 12.60 },
        { name: 'Vanilla syrup', qty: '15 ml', costPerUnit: 0.25, subtotal: 3.75 },
        { name: 'Crushed Oreo cookies', qty: '2 pcs', costPerUnit: 4.00, subtotal: 8.00 }
      ]
    },
    'Strawberry Matcha': {
      category: 'Non-Coffee',
      sellingPrice: 120,
      packingCost: 8,
      ingredients: [
        { name: 'Matcha powder', qty: '8 g', costPerUnit: 1.50, subtotal: 12.00 },
        { name: 'Fresh milk', qty: '150 ml', costPerUnit: 0.07, subtotal: 10.50 },
        { name: 'Strawberry fruit puree', qty: '30 ml', costPerUnit: 0.35, subtotal: 10.50 }
      ]
    },
    'Strawberry Cocoa': {
      category: 'Non-Coffee',
      sellingPrice: 120,
      packingCost: 8,
      ingredients: [
        { name: 'Cocoa blend', qty: '20 g', costPerUnit: 0.50, subtotal: 10.00 },
        { name: 'Fresh milk', qty: '150 ml', costPerUnit: 0.07, subtotal: 10.50 },
        { name: 'Strawberry puree', qty: '25 ml', costPerUnit: 0.35, subtotal: 8.75 }
      ]
    },
    'Milky Berry Oreo': {
      category: 'Non-Coffee',
      sellingPrice: 120,
      packingCost: 8,
      ingredients: [
        { name: 'Fresh milk', qty: '160 ml', costPerUnit: 0.07, subtotal: 11.20 },
        { name: 'Mixed berry puree', qty: '25 ml', costPerUnit: 0.40, subtotal: 10.00 },
        { name: 'Oreo crumb topping', qty: '1.5 pcs', costPerUnit: 4.00, subtotal: 6.00 }
      ]
    },

    // === REFRESHERS ===
    'Blueberry Fizz': {
      category: 'Refreshers',
      sellingPrice: 69,
      packingCost: 8,
      ingredients: [
        { name: 'Sparkling soda water', qty: '200 ml', costPerUnit: 0.04, subtotal: 8.00 },
        { name: 'Blueberry syrup', qty: '30 ml', costPerUnit: 0.25, subtotal: 7.50 },
        { name: 'Lemon slice & mint', qty: '1 serving', costPerUnit: 3.00, subtotal: 3.00 }
      ]
    },
    'Green Apple Fizz': {
      category: 'Refreshers',
      sellingPrice: 69,
      packingCost: 8,
      ingredients: [
        { name: 'Sparkling soda water', qty: '200 ml', costPerUnit: 0.04, subtotal: 8.00 },
        { name: 'Green apple syrup', qty: '30 ml', costPerUnit: 0.25, subtotal: 7.50 },
        { name: 'Lemon slice & mint', qty: '1 serving', costPerUnit: 3.00, subtotal: 3.00 }
      ]
    },
    'Lychee Fizz': {
      category: 'Refreshers',
      sellingPrice: 69,
      packingCost: 8,
      ingredients: [
        { name: 'Sparkling soda water', qty: '200 ml', costPerUnit: 0.04, subtotal: 8.00 },
        { name: 'Lychee syrup & fruit', qty: '30 ml', costPerUnit: 0.30, subtotal: 9.00 }
      ]
    },
    'Mango Fizz': {
      category: 'Refreshers',
      sellingPrice: 69,
      packingCost: 8,
      ingredients: [
        { name: 'Sparkling soda water', qty: '200 ml', costPerUnit: 0.04, subtotal: 8.00 },
        { name: 'Mango syrup & puree', qty: '30 ml', costPerUnit: 0.25, subtotal: 7.50 }
      ]
    },
    'Strawberry Fizz': {
      category: 'Refreshers',
      sellingPrice: 69,
      packingCost: 8,
      ingredients: [
        { name: 'Sparkling soda water', qty: '200 ml', costPerUnit: 0.04, subtotal: 8.00 },
        { name: 'Strawberry syrup & puree', qty: '30 ml', costPerUnit: 0.25, subtotal: 7.50 }
      ]
    },
    'Passion Fruit Fizz': {
      category: 'Refreshers',
      sellingPrice: 69,
      packingCost: 8,
      ingredients: [
        { name: 'Sparkling soda water', qty: '200 ml', costPerUnit: 0.04, subtotal: 8.00 },
        { name: 'Passion fruit concentrate', qty: '30 ml', costPerUnit: 0.30, subtotal: 9.00 }
      ]
    },
    'Mango Passion': {
      category: 'Refreshers',
      sellingPrice: 110,
      packingCost: 8,
      ingredients: [
        { name: 'Jasmine green tea base', qty: '180 ml', costPerUnit: 0.03, subtotal: 5.40 },
        { name: 'Mango puree', qty: '25 ml', costPerUnit: 0.30, subtotal: 7.50 },
        { name: 'Passion fruit seeds', qty: '15 ml', costPerUnit: 0.40, subtotal: 6.00 },
        { name: 'Nata de coco', qty: '30 g', costPerUnit: 0.15, subtotal: 4.50 }
      ]
    },
    'Paradise Coconut': {
      category: 'Refreshers',
      sellingPrice: 140,
      packingCost: 8,
      ingredients: [
        { name: 'Pure coconut water', qty: '180 ml', costPerUnit: 0.08, subtotal: 14.40 },
        { name: 'Coconut cream splash', qty: '30 ml', costPerUnit: 0.20, subtotal: 6.00 },
        { name: 'Tropical fruit syrup', qty: '20 ml', costPerUnit: 0.30, subtotal: 6.00 },
        { name: 'Coconut jelly bits', qty: '30 g', costPerUnit: 0.20, subtotal: 6.00 }
      ]
    },
    'Pink Berry Drink': {
      category: 'Refreshers',
      sellingPrice: 140,
      packingCost: 8,
      ingredients: [
        { name: 'Coconut milk', qty: '150 ml', costPerUnit: 0.08, subtotal: 12.00 },
        { name: 'Strawberry acai base', qty: '50 ml', costPerUnit: 0.30, subtotal: 15.00 },
        { name: 'Freeze-dried strawberries', qty: '5 g', costPerUnit: 1.00, subtotal: 5.00 }
      ]
    }
  };

  // Populate Product Dropdown with all items organized by category
  const productSelect = document.getElementById('productSelect');
  const categories = ['Coffee', 'Non-Coffee', 'Refreshers'];

  function populateProductDropdown() {
    productSelect.innerHTML = '';
    categories.forEach(cat => {
      const optgroup = document.createElement('optgroup');
      optgroup.label = cat === 'Coffee' ? '☕ Coffee' : cat === 'Non-Coffee' ? '🥛 Non-Coffee' : '🍹 Refreshers';

      Object.keys(recipes).forEach(name => {
        if (recipes[name].category === cat) {
          const opt = document.createElement('option');
          opt.value = name;
          opt.textContent = `${name} (₱${recipes[name].sellingPrice})`;
          optgroup.appendChild(opt);
        }
      });

      productSelect.appendChild(optgroup);
    });

    // Default to Caramel Latte
    productSelect.value = 'Caramel Latte';
  }

  const costingTableBody = document.getElementById('costingTableBody');
  const packingCostInput = document.getElementById('packingCost');
  const totalCostInput = document.getElementById('totalCost');
  const sellingPriceInput = document.getElementById('sellingPrice');
  const marginInput = document.getElementById('margin');
  const saveCostingBtn = document.getElementById('saveCostingBtn');

  function calculateAndRenderCosting(productName) {
    const recipe = recipes[productName] || recipes['Caramel Latte'];
    
    // Ingredients table
    let ingredientsTotal = 0;
    costingTableBody.innerHTML = recipe.ingredients.map(ing => {
      ingredientsTotal += ing.subtotal;
      return `
        <tr>
          <td>${ing.name}</td>
          <td>${ing.qty}</td>
          <td>${money(ing.costPerUnit)}</td>
          <td class="text-right">${money(ing.subtotal)}</td>
        </tr>
      `;
    }).join('');

    const packing = parseFloat(String(packingCostInput.value).replace(/[^0-9.]/g, '')) || recipe.packingCost;
    const totalCost = ingredientsTotal + packing;
    const sellingPrice = parseFloat(String(sellingPriceInput.value).replace(/[^0-9.]/g, '')) || recipe.sellingPrice;
    const margin = sellingPrice - totalCost;

    totalCostInput.value = money(totalCost);
    marginInput.value = money(margin);
  }

  productSelect.addEventListener('change', () => {
    const selected = productSelect.value;
    const recipe = recipes[selected];
    if (recipe) {
      packingCostInput.value = money(recipe.packingCost);
      sellingPriceInput.value = money(recipe.sellingPrice);
    }
    calculateAndRenderCosting(selected);
  });

  [packingCostInput, sellingPriceInput].forEach(inp => {
    inp.addEventListener('input', () => {
      calculateAndRenderCosting(productSelect.value);
    });
  });

  saveCostingBtn.addEventListener('click', () => {
    alert(`Product costing for ${productSelect.value} saved successfully!`);
  });

  // Init renders
  renderExpenses();
  populateProductDropdown();
  calculateAndRenderCosting(productSelect.value);
})();
