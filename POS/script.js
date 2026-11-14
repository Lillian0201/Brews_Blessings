(() => {
  "use strict";

  // Check login and load the shared POS sidebar.
  if (!window.BBNav) {
    console.error("BBNav is not loaded. Check the nav.js script path.");
    return;
  }

  const me = BBNav.mount("orders");

  if (!me) return;
  /* ---------- Helpers ---------- */
  const $ = (id) => document.getElementById(id);
  const round2 = (n) => Math.round((n + Number.EPSILON) * 100) / 100;
  const peso = (n) => {
    n = round2(n);
    return "₱" + n.toLocaleString("en-PH", {
      minimumFractionDigits: Number.isInteger(n) ? 0 : 2,
      maximumFractionDigits: 2
    });
  };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtShort = (d) => {
    const h = d.getHours();
    return (d.getMonth() + 1) + "/" + d.getDate() + " " + (h % 12 || 12) + ":" +
      String(d.getMinutes()).padStart(2, "0") + " " + (h >= 12 ? "PM" : "AM");
  };
  const fmtLong = (d) => d.toLocaleString("en-PH", {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit"
  });
  const IMGS = window.IMG || {};
  const custText = (i) => [
    i.size, i.shots, "Sweetness " + i.sweetness, i.ice, i.notes ? "Notes: " + i.notes : ""
  ].filter(Boolean).join(" · ");

  let toastTimer;
  function toast(msg) {
    const t = $("toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
  }

  /* ---------- Orders storage (saved in this browser) ---------- */
  const STORE_KEY = "bb_pos_orders_v1";

  function makeOrder(o) {
    const subtotal = round2(o.items.reduce((s, i) => s + i.price * i.qty, 0));
    const total = round2(subtotal - o.discount);
    return Object.assign({}, o, {
      subtotal, total, change: round2(Math.max(0, o.tendered - total))
    });
  }

  function seedOrders() {
    const now = Date.now(), min = 60000;
    return [
      makeOrder({
        no: "001", customer: "Anna", createdAt: now - 95 * min, status: "Pending",
        items: [{ name: "Caramel Latte", size: "Classic", shots: "1 Shot", sweetness: "50%", ice: "Less ice", price: 120, qty: 2 }],
        discount: 0, payment: "Cash", tendered: 300
      }),
      makeOrder({
        no: "002", customer: "Ben", createdAt: now - 60 * min, status: "Completed",
        items: [
          { name: "Americano", size: "Grandeur", shots: "2 Shots", sweetness: "0%", ice: "Regular ice", price: 110, qty: 1 },
          { name: "Blueberry Fizz", size: "Classic", shots: null, sweetness: "100%", ice: "Regular ice", price: 69, qty: 1 }
        ],
        discount: 0, payment: "GCash", tendered: 179
      }),
      makeOrder({
        no: "003", customer: "Carla", createdAt: now - 30 * min, status: "Cancelled",
        items: [{ name: "Matcha Milk", size: "Hot", shots: null, sweetness: "50%", ice: null, price: 115, qty: 1 }],
        discount: 0, payment: "Cash", tendered: 200
      })
    ];
  }

  function loadOrders() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) return arr;
      }
    } catch (e) { /* ignore */ }
    return seedOrders();
  }

  function saveOrders() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(orders)); } catch (e) { /* ignore */ }
  }

  let orders = loadOrders();
  let cart = [];
  let activeCat = "all";

  const nextOrderNo = () => {
    const max = orders.reduce((m, o) => Math.max(m, parseInt(o.no, 10) || 0), 0);
    return String(max + 1).padStart(3, "0");
  };

  // NEW: keep the header pill in sync with the shared inventory
  function refreshAlerts() {
    $("lowPill").textContent = "Stock alerts: " + BBInventory.alertCount();
  }

  /* ---------- Products + filter ---------- */
  function renderChips() {
    const cats = [{ id: "all", label: "All" }].concat(CATEGORIES);
    $("chips").innerHTML = cats.map((c) =>
      `<button type="button" class="chip${c.id === activeCat ? " active" : ""}" data-cat="${c.id}" aria-pressed="${c.id === activeCat}">${esc(c.label)}</button>`
    ).join("");
  }

  // Each tile: photo, name, and the product's price (Classic).
  function renderProducts() {
    $("products").innerHTML = MENU
      .map((m, i) => ({ m, i }))
      .filter(({ m }) => activeCat === "all" || m.cat === activeCat)
      .map(({ m, i }) =>
        `<button type="button" class="product" data-i="${i}">
          <img src="${IMGS[m.name] || ""}" alt="${esc(m.name)}" loading="lazy">
          <b>${esc(m.name)}</b>
          <span class="price">${peso(m.prices.Classic)}</span>
        </button>`
      ).join("");
  }

  $("chips").addEventListener("click", (e) => {
    const b = e.target.closest(".chip");
    if (!b) return;
    activeCat = b.dataset.cat;
    renderChips();
    renderProducts();
  });

  $("products").addEventListener("click", (e) => {
    const b = e.target.closest(".product");
    if (b) openCustomize(MENU[+b.dataset.i]);
  });

  /* ---------- Customize dialog ---------- */
  const customDlg = $("customDialog");
  let current = null, currentCat = null;
  const sel = { size: "", shots: "1 Shot", sweet: "100%", ice: "Regular ice", qty: 1 };

  const radio = (name, value, label, checked) =>
    `<label class="opt"><input type="radio" name="${name}" value="${esc(value)}"${checked ? " checked" : ""}><span>${esc(label)}</span></label>`;

  function openCustomize(item) {
    current = item;
    currentCat = CATEGORIES.find((c) => c.id === item.cat);
    const sizes = SIZES.filter((s) => item.prices[s] != null);
    sel.size = sizes[0];
    sel.shots = SHOTS[1];
    sel.sweet = "100%";
    sel.ice = ICE[0];
    sel.qty = 1;

    $("cName").textContent = item.name;
    $("cCat").textContent = currentCat.label;
    $("cImg").src = IMGS[item.name] || "";
    $("cImg").hidden = !IMGS[item.name];
    $("cSize").innerHTML = sizes.map((s) =>
      radio("size", s, s + " · " + peso(item.prices[s]), s === sel.size)).join("");
    $("cShotsWrap").hidden = !currentCat.espresso;
    $("cShots").innerHTML = SHOTS.map((s) => radio("shots", s, s, s === sel.shots)).join("");
    $("cSweet").innerHTML = SWEETNESS.map((s) => radio("sweet", s.value, s.label, s.value === sel.sweet)).join("");
    $("cIce").innerHTML = ICE.map((s) => radio("ice", s, s, s === sel.ice)).join("");
    $("cNotes").value = "";
    updateCustomTotal();
    customDlg.showModal();
  }

  function updateCustomTotal() {
    $("cTotal").textContent = peso(current.prices[sel.size] * sel.qty);
    $("cQty").textContent = sel.qty;
    $("cIceWrap").hidden = sel.size === "Hot"; // no ice option for hot drinks
  }

  customDlg.addEventListener("change", (e) => {
    const n = e.target.name;
    if (n === "size") sel.size = e.target.value;
    else if (n === "shots") sel.shots = e.target.value;
    else if (n === "sweet") sel.sweet = e.target.value;
    else if (n === "ice") sel.ice = e.target.value;
    updateCustomTotal();
  });
  $("cMinus").addEventListener("click", () => { sel.qty = Math.max(1, sel.qty - 1); updateCustomTotal(); });
  $("cPlus").addEventListener("click", () => { sel.qty = Math.min(99, sel.qty + 1); updateCustomTotal(); });

  $("cAdd").addEventListener("click", () => {
    addToCart({
      name: current.name,
      size: sel.size,
      shots: currentCat.espresso ? sel.shots : null,
      sweetness: sel.sweet,
      ice: sel.size === "Hot" ? null : sel.ice,
      notes: $("cNotes").value.trim(),
      price: current.prices[sel.size],
      qty: sel.qty
    });
    customDlg.close();
    toast(sel.qty + " × " + current.name + " added");
  });

  // Close buttons + click on the backdrop (works for both dialogs)
  [customDlg, $("orderDialog")].forEach((dlg) => {
    dlg.addEventListener("click", (e) => {
      if (e.target === dlg || e.target.closest("[data-close]")) dlg.close();
    });
  });

  /* ---------- Order form ---------- */
  function addToCart(it) {
    const key = [it.name, it.size, it.shots, it.sweetness, it.ice, it.notes].join("|");
    const found = cart.find((c) => c.key === key);
    if (found) found.qty = Math.min(99, found.qty + it.qty);
    else cart.push(Object.assign({ key }, it));
    renderCart();
  }

  function renderCart() {
    const el = $("items");
    if (!cart.length) {
      el.innerHTML = '<p class="empty">No items yet. Click a product to add it.</p>';
    } else {
      el.innerHTML = cart.map((i, idx) => `
        <div class="item">
          <div>${esc(i.name)} × ${i.qty}<small>Customization: ${esc(custText(i))}</small></div>
          <div class="stepper">
            <button type="button" data-act="minus" data-idx="${idx}" aria-label="Decrease quantity">−</button>
            <span>${i.qty}</span>
            <button type="button" data-act="plus" data-idx="${idx}" aria-label="Increase quantity">+</button>
          </div>
          <div class="i-price">${peso(i.price * i.qty)}</div>
          <button type="button" class="rm" data-act="remove" data-idx="${idx}" aria-label="Remove ${esc(i.name)}">✕</button>
        </div>`).join("");
    }
    updateSummary();
  }

  $("items").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-act]");
    if (!b) return;
    const idx = +b.dataset.idx, item = cart[idx];
    if (!item) return;
    if (b.dataset.act === "plus") item.qty = Math.min(99, item.qty + 1);
    else if (b.dataset.act === "minus") { item.qty -= 1; if (item.qty < 1) cart.splice(idx, 1); }
    else cart.splice(idx, 1);
    setMsg("");
    renderCart();
  });

  // Discount is a % of the subtotal.
  function totals() {
    const subtotal = round2(cart.reduce((s, i) => s + i.price * i.qty, 0));
    const dv = Math.max(0, parseFloat($("discount").value) || 0);
    const discount = round2(Math.min(subtotal * Math.min(dv, 100) / 100, subtotal));
    return { subtotal, discount, total: round2(subtotal - discount) };
  }

  function updateSummary() {
    const t = totals();
    $("subtotal").textContent = peso(t.subtotal);
    $("total").textContent = peso(t.total);
    $("discHint").textContent = t.discount > 0 ? "− " + peso(t.discount) : "";

    const raw = $("tendered").value.trim();
    const tendered = parseFloat(raw);
    const ch = $("change");
    ch.classList.remove("short");
    if (!cart.length || raw === "" || !isFinite(tendered)) {
      ch.textContent = "Change: ₱0";
    } else if (tendered >= t.total) {
      ch.textContent = "Change: " + peso(tendered - t.total);
    } else {
      ch.textContent = "Short by " + peso(t.total - tendered);
      ch.classList.add("short");
    }
    $("tendered").placeholder = $("payment").value === "Cash" ? "0" : "Exact amount";
  }

  ["discount", "payment", "tendered"].forEach((id) => {
    $(id).addEventListener("input", () => { setMsg(""); updateSummary(); });
    $(id).addEventListener("change", () => { setMsg(""); updateSummary(); });
  });

  function setMsg(text) { $("formMsg").textContent = text; }
  function fail(text, focusId) {
    setMsg(text);
    if (focusId) $(focusId).focus();
  }

  // Order no. and Date/Time are generated, never typed by the user.
  function tick() { $("dt").value = fmtShort(new Date()); }
  setInterval(tick, 15000);

  function resetForm() {
    cart = [];
    $("customer").value = "";
    $("discount").value = "";
    $("payment").value = "Cash";
    $("tendered").value = "";
    $("ono").value = nextOrderNo();
    tick();
    setMsg("");
    renderCart();
  }

  function placeOrder() {
    setMsg("");
    if (!cart.length) return fail("Add at least one item to the order.");

    const t = totals();
    const method = $("payment").value;
    const raw = $("tendered").value.trim();
    let tendered;
    if (raw === "") {
      if (method === "Cash" && t.total > 0) return fail("Enter the amount tendered.", "tendered");
      tendered = t.total;
    } else {
      tendered = parseFloat(raw);
    }
    if (!isFinite(tendered) || tendered < 0) return fail("Enter a valid amount tendered.", "tendered");
    if (tendered < t.total) return fail("Amount tendered is short by " + peso(t.total - tendered) + ".", "tendered");

    const order = {
      no: nextOrderNo(),
      customer: $("customer").value.trim() || "Walk-in",
      createdAt: Date.now(),
      status: "Pending",
      items: cart.map((i) => ({
        name: i.name, size: i.size, shots: i.shots, sweetness: i.sweetness,
        ice: i.ice, notes: i.notes, price: i.price, qty: i.qty
      })),
      subtotal: t.subtotal,
      discount: t.discount,
      total: t.total,
      payment: method,
      tendered: round2(tendered),
      change: round2(tendered - t.total),
      stockDeducted: false // NEW
    };

    // NEW: check stock first, then deduct it from the shared inventory
    const stock = BBInventory.canFulfil(order.items);
    if (!stock.ok) return fail("Not enough stock: " + stock.shortages.join("; ") + ".");
    BBInventory.deduct(order.items, order.no);
    order.stockDeducted = true;

    orders.push(order);
    saveOrders();
    resetForm();
    renderOrders();
    refreshAlerts(); // NEW
    toast("Order #" + order.no + " placed");
  }

  $("payBtn").addEventListener("click", placeOrder);
  $("cancelBtn").addEventListener("click", () => {
    const dirty = cart.length || $("customer").value.trim();
    if (dirty && !confirm("Clear this order?")) return;
    resetForm();
    if (dirty) toast("Order cleared");
  });

  /* ---------- Current orders ---------- */
  function renderOrders() {
    $("orders").innerHTML = orders.slice()
      .sort((a, b) => b.createdAt - a.createdAt)
      .map((o) =>
        `<button type="button" class="order-row" data-no="${esc(o.no)}"><span>#${esc(o.no)} ${esc(o.customer)}</span><span class="badge ${o.status.toLowerCase()}">${esc(o.status)}</span></button>`
      ).join("");
  }

  const orderDlg = $("orderDialog");
  let viewing = null;
  const STATUSES = ["Pending", "Completed", "Cancelled"];

  function renderOrderDialog(o, focusStatus) {
    const items = o.items.map((i) =>
      `<div class="d-item"><div><b>${esc(i.name)} × ${i.qty}</b><small>Customization: ${esc(custText(i))}</small></div><span>${peso(i.price * i.qty)}</span></div>`
    ).join("");
    const lines = [
      ["Subtotal", peso(o.subtotal), ""],
      o.discount > 0 ? ["Discount", "− " + peso(o.discount), ""] : null,
      ["Total", peso(o.total), "total"],
      ["Payment", o.payment, ""],
      ["Amount tendered", peso(o.tendered), ""],
      ["Change", peso(o.change), ""]
    ].filter(Boolean).map(([l, v, c]) => `<div class="line ${c}"><span>${l}</span><span>${esc(v)}</span></div>`).join("");

    $("oBody").innerHTML = `
      <div class="modal-head">
        <div>
          <h2>Order #${esc(o.no)}</h2>
          <p class="sub">${esc(o.customer)} · ${esc(fmtLong(new Date(o.createdAt)))}</p>
        </div>
        <span class="badge ${o.status.toLowerCase()}">${esc(o.status)}</span>
        <button type="button" class="x" data-close aria-label="Close">×</button>
      </div>
      <div>${items}</div>
      <div class="d-lines">${lines}</div>
      <label class="status-label">Update status</label>
      <div class="seg-group">
        ${STATUSES.map((s) => `<button type="button" class="seg${s === o.status ? " active" : ""}" data-status="${s}">${s}</button>`).join("")}
      </div>
      <div class="modal-foot"><span></span><button type="button" class="btn cancel" data-close>Close</button></div>`;
    if (focusStatus) {
      const b = $("oBody").querySelector('[data-status="' + focusStatus + '"]');
      if (b) b.focus();
    }
  }

  $("orders").addEventListener("click", (e) => {
    const b = e.target.closest(".order-row");
    if (!b) return;
    const o = orders.find((x) => x.no === b.dataset.no);
    if (!o) return;
    viewing = o.no;
    renderOrderDialog(o);
    orderDlg.showModal();
  });

  orderDlg.addEventListener("click", (e) => {
    const b = e.target.closest("[data-status]");
    if (!b) return;
    const o = orders.find((x) => x.no === viewing);
    if (!o || o.status === b.dataset.status) return;

    // NEW: restore stock when cancelling, deduct again when reopening
    if (b.dataset.status === "Cancelled" && o.stockDeducted) {
      BBInventory.restore(o.items, o.no);
      o.stockDeducted = false;
    } else if (o.status === "Cancelled" && b.dataset.status !== "Cancelled" && !o.stockDeducted) {
      const stock = BBInventory.canFulfil(o.items);
      if (!stock.ok) return toast("Not enough stock to reopen: " + stock.shortages.join("; "));
      BBInventory.deduct(o.items, o.no);
      o.stockDeducted = true;
    }

    o.status = b.dataset.status;
    saveOrders();
    renderOrders();
    refreshAlerts(); // NEW
    renderOrderDialog(o, o.status);
  });

  /* ---------- Init ---------- */
  renderChips();
  renderProducts();
  renderOrders();
  refreshAlerts(); // NEW
  resetForm();
})();