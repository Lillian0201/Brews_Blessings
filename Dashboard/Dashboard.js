(() => {
  "use strict";

  const API = "http://127.0.0.1:5001/api";
  const me = BBNav.requireLogin();
  if (!me) return;
  if (!BBNav.canSee(me.role, "dash")) {
    location.replace(BBNav.homeFor(me.role));
    return;
  }

  const $ = (selector) => document.querySelector(selector);
  const money = (value) => "₱" + Number(value).toLocaleString("en-US", {
    minimumFractionDigits: Number.isInteger(Number(value)) ? 0 : 2,
    maximumFractionDigits: 2
  });
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  async function api(path) {
    const response = await fetch(API + path, {
      headers: { "X-Username": me.u || "" }
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error((data && data.detail) || `Server error (${response.status}).`);
    return data;
  }

  function dashboardHTML(summary, orders) {
    const top = (summary.bestSellers || []).slice(0, 3);
    const max = top.length ? Number(top[0].qty) : 1;
    const cls = { Pending: "pend", Completed: "ok", Cancelled: "bad" };

    return `<div class="kp">
      <div class="k"><span>Today's sales</span><b>${money(summary.todaySales)}</b></div>
      <div class="k"><span>Number of orders</span><b>${summary.ordersToday}</b></div>
      <div class="k"><span>Today's expenses</span><b>${money(summary.expensesToday)}</b></div>
      <div class="k"><span>Available stock</span><b>${summary.availableStock} items</b></div>
    </div>

    <div class="two">
      <section class="box">
        <h2>Pending and completed orders</h2>
        <div class="pills">
          <span>Pending: ${summary.pending}</span>
          <span>Completed: ${summary.completed}</span>
          <span>Cancelled: ${summary.cancelled}</span>
        </div>
        ${orders.length
          ? `<ul class="list">${orders.slice(0, 5).map((order) =>
              `<li><span>[${esc(order.orderNumber)}] ${esc(order.customer)}</span>
               <span class="tag ${cls[order.status] || ""}">${esc(order.status)}</span></li>`
            ).join("")}</ul>`
          : '<p class="empty">No orders yet today.</p>'}
      </section>

      <section class="box">
        <h2>Best-selling products</h2>
        ${top.length
          ? top.map((item, index) =>
              `<div class="bs">
                <span>${index + 1}. ${esc(item.name)} - ${item.qty}</span>
                <div class="bar"><i style="width:${Number(item.qty) / max * 100}%"></i></div>
              </div>`
            ).join("")
          : '<p class="empty">Sales will show here once orders are placed.</p>'}
      </section>
    </div>

    <section class="box">
      <h2>Stock alerts</h2>
      ${summary.stockAlerts
        ? `<ul class="list sa">
            <li><span>Available: ${summary.availableStock}</span></li>
            <li><span>Low-stock: ${summary.lowStock}</span></li>
            <li><span>Out-of-stock: ${summary.outOfStock}</span></li>
          </ul>`
        : '<p class="empty">All ingredients are stocked.</p>'}
    </section>`;
  }

  async function render() {
    const app = $("#app");
    if (!app) return;
    BBNav.startIdle();

    try {
      const [summary, orders] = await Promise.all([
        api("/dashboard/summary"),
        api("/orders")
      ]);

      app.innerHTML = `<div class="shell">
        ${BBNav.sidebar("dash")}
        <main>
          <div class="top">
            <h1>Dashboard</h1>
            <div class="meta">
              <span>Today: ${new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
              <span class="pill">Logged in: ${esc(me.name)}</span>
              <span class="pill" title="Stock alerts">Stock alerts: ${summary.stockAlerts}</span>
            </div>
          </div>
          ${dashboardHTML(summary, orders)}
        </main>
      </div>`;
    } catch (error) {
      app.innerHTML = `<main><h1>Dashboard</h1>
        <div class="warn">${esc(error.message)} Backend: http://127.0.0.1:5001/api</div></main>`;
    }
  }

  render();
})();
