(() => {
  "use strict";

  if (!window.BBNav) return;
  const me = BBNav.mount("orders");
  if (!me) return;

  const API = "http://127.0.0.1:5001/api";
  const $ = (id) => document.getElementById(id);
  const round2 = (n) => Math.round((n + Number.EPSILON) * 100) / 100;
  const peso = (n) => "\u20B1" + round2(n).toLocaleString("en-PH", {
    minimumFractionDigits: Number.isInteger(round2(n)) ? 0 : 2,
    maximumFractionDigits: 2
  });
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtShort = (value) => new Date(value).toLocaleString("en-PH", {
    month: "numeric", day: "numeric", hour: "numeric", minute: "2-digit"
  });
  const fmtLong = (value) => new Date(value).toLocaleString("en-PH", {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit"
  });
  const IMGS = window.IMG || {};

  async function api(method, path, body) {
    const response = await fetch(API + path, {
      method,
      headers: { "X-Username": me.u || "", ...(body ? { "Content-Type": "application/json" } : {}) },
      body: body ? JSON.stringify(body) : undefined
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error((data && data.detail) || `Server error (${response.status}).`);
    return data;
  }

  let toastTimer;
  // The toast is a popover, so it sits in the browser's top layer and stays
  // visible even while a modal dialog is open.
  function toast(message, type) {
    const el = $("toast");
    clearTimeout(toastTimer);
    el.textContent = message;
    el.classList.toggle("ok", type === "ok");
    if (typeof el.showPopover === "function") {
      try { if (!el.matches(":popover-open")) el.showPopover(); } catch (e) { /* ignore */ }
    }
    requestAnimationFrame(() => el.classList.add("show"));
    toastTimer = setTimeout(() => {
      el.classList.remove("show");
      setTimeout(() => {
        if (el.classList.contains("show")) return;
        if (typeof el.hidePopover === "function") {
          try { el.hidePopover(); } catch (e) { /* ignore */ }
        }
      }, 300);
    }, 3500);
  }

  let backendProducts = [];
  let cart = [];
  let orders = [];
  let activeCat = "all";
  const customDlg = $("customDialog");
  const orderDlg = $("orderDialog");
  let viewing = null;
  let current = null;
  let currentCat = null;
  const sel = { size: "", shots: "1 Shot", sweet: "100%", ice: "Regular ice", qty: 1 };

  function backendProductId(name) {
    const product = backendProducts.find((item) => item.name === name);
    return product ? product.id : null;
  }

  function currentMenu() {
    return backendProducts.map((product) => {
      const saved = MENU.find((entry) => entry.name === product.name);
      const category = saved ? CATEGORIES.find((entry) => entry.id === saved.cat) :
        CATEGORIES.find((entry) => entry.label === product.category);
      return {
        cat: category ? category.id : "noncoffee",
        name: product.name,
        prices: product.prices || { Classic: product.price },
        espresso: saved ? !!category.espresso : product.category === "Coffee"
      };
    }).filter((entry) => entry.prices && entry.prices.Classic != null);
  }

  async function refreshAlerts() {
    try {
      const inventory = await api("GET", "/inventory");
      const alerts = inventory.filter((item) => item.status !== "Available").length;
      $("lowPill").textContent = "Stock alerts: " + alerts;
    } catch (error) {
      $("lowPill").textContent = "Stock alerts: unavailable";
    }
  }

  function renderChips() {
    const categories = [{ id: "all", label: "All" }].concat(CATEGORIES);
    $("chips").innerHTML = categories.map((category) =>
      `<button type="button" class="chip${category.id === activeCat ? " active" : ""}" data-cat="${category.id}" aria-pressed="${category.id === activeCat}">${esc(category.label)}</button>`
    ).join("");
  }

  function renderProducts() {
    const menu = currentMenu();
    $("products").innerHTML = menu
      .filter((item) => activeCat === "all" || item.cat === activeCat)
      .map((item) => {
        const index = menu.indexOf(item);
        return `<button type="button" class="product" data-i="${index}">
          <img src="${IMGS[item.name] || ""}" alt="${esc(item.name)}" loading="lazy">
          <b>${esc(item.name)}</b>
          <span class="price">${peso(item.prices.Classic)}</span>
        </button>`;
      }).join("");
  }

  const radio = (name, value, label, checked) =>
    `<label class="opt"><input type="radio" name="${name}" value="${esc(value)}"${checked ? " checked" : ""}><span>${esc(label)}</span></label>`;

  function openCustomize(item) {
    current = item;
    currentCat = CATEGORIES.find((category) => category.id === item.cat) || { label: "Product", espresso: item.espresso };
    const sizes = SIZES.filter((size) => item.prices[size] != null);
    sel.size = sizes[0];
    sel.shots = SHOTS[1];
    sel.sweet = "100%";
    sel.ice = ICE[0];
    sel.qty = 1;
    $("cName").textContent = item.name;
    $("cCat").textContent = currentCat.label;
    $("cImg").src = IMGS[item.name] || "";
    $("cImg").hidden = !IMGS[item.name];
    $("cSize").innerHTML = sizes.map((size) =>
      radio("size", size, size + " · " + peso(item.prices[size]), size === sel.size)).join("");
    $("cShotsWrap").hidden = !currentCat.espresso;
    $("cShots").innerHTML = SHOTS.map((shot) => radio("shots", shot, shot, shot === sel.shots)).join("");
    $("cSweet").innerHTML = SWEETNESS.map((sweet) =>
      radio("sweet", sweet.value, sweet.label, sweet.value === sel.sweet)).join("");
    $("cIce").innerHTML = ICE.map((ice) => radio("ice", ice, ice, ice === sel.ice)).join("");
    $("cNotes").value = "";
    updateCustomTotal();
    customDlg.showModal();
  }

  function updateCustomTotal() {
    $("cTotal").textContent = peso(current.prices[sel.size] * sel.qty);
    $("cQty").textContent = sel.qty;
    $("cIceWrap").hidden = sel.size === "Hot";
  }

  function custText(item) {
    return [item.size, item.shots, "Sweetness " + item.sweetness, item.ice,
      item.notes ? "Notes: " + item.notes : ""].filter(Boolean).join(" · ");
  }

  customDlg.addEventListener("change", (event) => {
    const name = event.target.name;
    if (name === "size") sel.size = event.target.value;
    else if (name === "shots") sel.shots = event.target.value;
    else if (name === "sweet") sel.sweet = event.target.value;
    else if (name === "ice") sel.ice = event.target.value;
    updateCustomTotal();
  });
  $("cMinus").addEventListener("click", () => { sel.qty = Math.max(1, sel.qty - 1); updateCustomTotal(); });
  $("cPlus").addEventListener("click", () => { sel.qty = Math.min(99, sel.qty + 1); updateCustomTotal(); });
  $("cAdd").addEventListener("click", () => {
    addToCart({
      name: current.name,
      productId: backendProductId(current.name),
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

  $("chips").addEventListener("click", (event) => {
    const button = event.target.closest(".chip");
    if (!button) return;
    activeCat = button.dataset.cat;
    renderChips();
    renderProducts();
  });
  $("products").addEventListener("click", (event) => {
    const button = event.target.closest(".product");
    if (button) openCustomize(currentMenu()[Number(button.dataset.i)]);
  });
  [customDlg, orderDlg].forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog || event.target.closest("[data-close]")) dialog.close();
    });
  });

  function addToCart(item) {
    const key = [item.name, item.size, item.shots, item.sweetness, item.ice, item.notes].join("|");
    const found = cart.find((entry) => entry.key === key);
    if (found) found.qty = Math.min(99, found.qty + item.qty);
    else cart.push({ key, ...item });
    renderCart();
  }

  function totals() {
    const subtotal = round2(cart.reduce((sum, item) => sum + item.price * item.qty, 0));
    const percent = Math.max(0, parseFloat($("discount").value) || 0);
    const discount = round2(Math.min(subtotal * Math.min(percent, 100) / 100, subtotal));
    return { subtotal, discount, total: round2(subtotal - discount) };
  }

  function renderCart() {
    $("items").innerHTML = cart.length
      ? cart.map((item, index) => `<div class="item">
          <div>${esc(item.name)} × ${item.qty}<small>Customization: ${esc(custText(item))}</small></div>
          <div class="stepper">
            <button type="button" data-act="minus" data-idx="${index}" aria-label="Decrease quantity">−</button>
            <span>${item.qty}</span>
            <button type="button" data-act="plus" data-idx="${index}" aria-label="Increase quantity">+</button>
          </div>
          <div class="i-price">${peso(item.price * item.qty)}</div>
          <button type="button" class="rm" data-act="remove" data-idx="${index}" aria-label="Remove ${esc(item.name)}">✕</button>
        </div>`).join("")
      : '<p class="empty">No items yet. Click a product to add it.</p>';
    updateSummary();
  }

  function updateSummary() {
    const totalsValue = totals();
    $("subtotal").textContent = peso(totalsValue.subtotal);
    $("total").textContent = peso(totalsValue.total);
    $("discHint").textContent = totalsValue.discount > 0 ? "− " + peso(totalsValue.discount) : "";
    const tendered = parseFloat($("tendered").value);
    if (!cart.length || $("tendered").value.trim() === "" || !isFinite(tendered)) {
      $("change").textContent = "Change: " + "\u20B1" + "0";
      $("change").classList.remove("short");
    } else if (tendered >= totalsValue.total) {
      $("change").textContent = "Change: " + peso(tendered - totalsValue.total);
      $("change").classList.remove("short");
    } else {
      $("change").textContent = "Short by " + peso(totalsValue.total - tendered);
      $("change").classList.add("short");
    }
  }

  $("items").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-act]");
    if (!button) return;
    const index = Number(button.dataset.idx);
    const item = cart[index];
    if (button.dataset.act === "plus") item.qty = Math.min(99, item.qty + 1);
    else if (button.dataset.act === "minus") {
      item.qty -= 1;
      if (item.qty < 1) cart.splice(index, 1);
    } else cart.splice(index, 1);
    setMsg("");
    renderCart();
  });
  ["discount", "payment", "tendered"].forEach((id) => {
    $(id).addEventListener("input", updateSummary);
    $(id).addEventListener("change", updateSummary);
  });

  function setMsg(message) { $("formMsg").textContent = message; }

  function resetForm() {
    cart = [];
    $("customer").value = "";
    $("discount").value = "";
    $("discNote").value = "";
    $("payment").value = "Cash";
    $("tendered").value = "";
    $("ono").value = "AUTO";
    $("dt").value = fmtShort(new Date());
    setMsg("");
    renderCart();
  }

  async function placeOrder() {
    setMsg("");
    if (!cart.length) return setMsg("Add at least one item to the order.");
    const totalsValue = totals();
    const discountPercent = parseFloat($("discount").value) || 0;
    const discountNote = $("discNote").value.trim();
    if (discountPercent > 0 && !discountNote) {
      $("discNote").focus();
      return setMsg("Enter a discount note (e.g. Senior Citizen, PWD).");
    }
    const rawTendered = $("tendered").value.trim();
    const tendered = rawTendered === "" ? totalsValue.total : parseFloat(rawTendered);
    if (!isFinite(tendered) || tendered < totalsValue.total) {
      return setMsg("Amount tendered is short by " + peso(totalsValue.total - (tendered || 0)) + ".");
    }

    try {
      await api("POST", "/orders", {
        items: cart.map((item) => ({
          productId: item.productId,
          qty: item.qty,
          price: item.price,
          size: item.size,
          shots: item.shots,
          sweetness: item.sweetness,
          ice: item.ice,
          notes: item.notes
        })),
        discountPercent,
        discountNote: discountPercent > 0 ? discountNote : "",
        payment: $("payment").value,
        tendered,
        customer: $("customer").value.trim()
      });
      resetForm();
      toast("\u2713 Order placed", "ok");
      refreshOrders();
      refreshAlerts();
    } catch (error) {
      setMsg(error.message);
    }
  }

  $("payBtn").addEventListener("click", placeOrder);
  $("cancelBtn").addEventListener("click", async () => {
    const dirty = cart.length || $("customer").value.trim();
    if (dirty && !(await BBDialog.confirm("Clear this order?", "The current order will be cleared."))) return;
    resetForm();
  });

  async function refreshOrders() {
    try {
      const rows = await api("GET", "/orders");
      orders = await Promise.all(rows.map(async (row) => api("GET", `/orders/${row.id}`)));
      renderOrders();
    } catch (error) {
      setMsg(error.message);
    }
  }

  function renderOrders() {
    $("orders").innerHTML = orders.length
      ? orders.slice().sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
          .map((order) => `<button type="button" class="order-row" data-no="${esc(order.orderNumber)}">
            <span>#${esc(order.orderNumber)} ${esc(order.customer)}</span>
            <span class="badge ${String(order.status).toLowerCase()}">${esc(order.status)}</span>
          </button>`).join("")
      : '<p class="empty">No orders today.</p>';
  }

  function renderOrderDialog(order) {
    const items = (order.items || []).map((item) =>
      `<div class="d-item"><div><b>${esc(item.name)} × ${item.qty}</b><small>Customization: ${esc(item.customization || "")}</small></div><span>${peso(item.price * item.qty)}</span></div>`
    ).join("");
    $("oBody").innerHTML = `
      <div class="modal-head">
        <div><h2>Order #${esc(order.orderNumber)}</h2><p class="sub">${esc(order.customer)} · ${esc(fmtLong(order.createdAt))}</p></div>
        <span class="badge ${String(order.status).toLowerCase()}">${esc(order.status)}</span>
        <button type="button" class="x" data-close aria-label="Close">×</button>
      </div>
      <div>${items}</div>
      <div class="d-lines">
        ${order.discount > 0 ? `<div class="line"><span>Discount${order.discountNote ? " (" + esc(order.discountNote) + ")" : ""}</span><span>− ${peso(order.discount)}</span></div>` : ""}
        <div class="line total"><span>Total</span><span>${peso(order.total)}</span></div>
        <div class="line"><span>Payment</span><span>${esc(order.payment)}</span></div>
        <div class="line"><span>Amount tendered</span><span>${peso(order.tendered)}</span></div>
      </div>
      <label class="status-label">Update status</label>
      <div class="seg-group">
        ${["Pending", "Completed", "Cancelled"].map((status) =>
          `<button type="button" class="seg${status === order.status ? " active" : ""}" data-status="${status}">${status}</button>`
        ).join("")}
      </div>
      <div class="modal-foot"><span></span><button type="button" class="btn cancel" data-close>Close</button></div>`;
  }

  $("orders").addEventListener("click", (event) => {
    const button = event.target.closest(".order-row");
    if (!button) return;
    const order = orders.find((entry) => entry.orderNumber === button.dataset.no);
    if (!order) return;
    viewing = order.id;
    renderOrderDialog(order);
    orderDlg.showModal();
  });

  orderDlg.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-status]");
    if (!button) return;
    const status = button.dataset.status;
    let reason;
    if (status === "Cancelled") {
      reason = await BBDialog.ask("Cancel order", {
        label: "Reason for cancelling",
        placeholder: "Enter a reason",
        okText: "Continue"
      });
      if (reason === null) return;
      if (!reason.trim()) {
        await BBDialog.notify("Missing reason", "Enter a reason for cancelling the order.");
        return;
      }
      reason = reason.trim();
    }
    try {
      await api("PATCH", `/orders/${viewing}/status`, { status, reason });
      await refreshOrders();
      await refreshAlerts();
      const updated = orders.find((order) => order.id === viewing);
      if (updated) renderOrderDialog(updated);
      toast("Order status updated", "ok");
    } catch (error) {
      toast(error.message);
    }
  });

  async function init() {
    renderChips();
    try {
      backendProducts = await api("GET", "/products?available=true");
    } catch (error) {
      setMsg(error.message);
    }
    renderProducts();
    resetForm();
    await Promise.all([refreshOrders(), refreshAlerts()]);
  }

  init();
})();
