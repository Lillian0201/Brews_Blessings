(() => {
  "use strict";

  const API = "http://127.0.0.1:5001/api";
  const $ = (id) => document.getElementById(id);
  const fmtPeso = (n) => "₱" + Number(n).toLocaleString("en-PH");
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  let items = [];
  let movements = [];

  async function api(method, path, body) {
    const me = BBNav.getSessionUser() || {};
    const response = await fetch(API + path, {
      method,
      headers: { "X-Username": me.u || "", ...(body ? { "Content-Type": "application/json" } : {}) },
      body: body ? JSON.stringify(body) : undefined
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error((data && data.detail) || `Server error (${response.status}).`);
    return data;
  }

  function flash(text, isError = false) {
    $("msg").textContent = text;
    $("msg").className = "msg" + (isError ? " error" : "");
  }

  async function refresh() {
    try {
      [items, movements] = await Promise.all([
        api("GET", "/inventory"),
        api("GET", "/inventory/movements")
      ]);
      populateItemSelect();
      render();
    } catch (error) {
      flash(error.message, true);
    }
  }

  function populateItemSelect() {
    $("siItem").innerHTML =
      `<option value="">Select an item</option>` +
      items.map((item) => `<option value="${item.id}">${esc(item.name)}</option>`).join("");
  }

  async function saveStockIn() {
    const ingredientId = Number($("siItem").value);
    const quantity = Number($("siQty").value);
    const batchNo = $("siBatch").value.trim();
    if (!ingredientId || !(quantity > 0) || !batchNo) {
      return flash("Pick an item, enter a quantity and a batch no.", true);
    }
    try {
      await api("POST", "/inventory/stock-in", { ingredientId, quantity, batchNo });
      $("siQty").value = "";
      $("siBatch").value = "";
      await refresh();
      flash("Stock-in saved.");
    } catch (error) {
      flash(error.message, true);
    }
  }

  async function promptStockOut(ingredientId, name) {
    const item = items.find((entry) => entry.id === ingredientId);
    const quantity = Number(prompt(`Stock-out qty for ${name}. Remaining ${item ? item.remaining : 0}.`));
    if (!(quantity > 0)) return;
    try {
      await api("POST", "/inventory/stock-out", { ingredientId, quantity });
      await refresh();
      flash(`Stock-out saved for ${name}.`);
    } catch (error) {
      flash(error.message, true);
    }
  }

  async function addItem() {
    const name = prompt("Item name:");
    if (!name) return;
    const barcode = prompt("Barcode:") || "";
    const unit = prompt("Unit (kg, L, bottle, pcs...):") || "pcs";
    const unitCost = Number(prompt("Unit cost (₱):") || 0);
    const reorderLevel = Number(prompt("Reorder level:") || 0);
    try {
      await api("POST", "/inventory/items", { name, barcode, unit, unitCost, reorderLevel });
      await refresh();
      flash(`${name} added. Use Stock-in to add its first batch.`);
    } catch (error) {
      flash(error.message, true);
    }
  }

  function handleScanEnter(event) {
    if (event.key !== "Enter") return;
    const code = $("search").value.trim().toLowerCase();
    const hit = items.find((item) => String(item.barcode || "").toLowerCase() === code);
    if (hit) {
      $("siItem").value = String(hit.id);
      $("siItem").focus();
      flash(`Found ${hit.name}.`);
    }
  }

  function render() {
    const query = $("search").value.trim().toLowerCase();
    const shown = items.filter((item) =>
      item.name.toLowerCase().includes(query) ||
      String(item.barcode || "").toLowerCase().includes(query)
    );

    $("itemRows").innerHTML = shown.length
      ? shown.map((item) => `<tr>
          <td>${esc(item.name)}</td><td>${esc(item.barcode || "")}</td><td>${esc(item.unit)}</td>
          <td>${fmtPeso(item.unitCost)}</td><td>${item.beginning}</td><td>${item.stockIn}</td>
          <td>${item.stockOut}</td><td>${item.remaining}</td><td>${item.reorderLevel}</td>
          <td>${esc(item.batchNo)}</td>
          <td><span class="badge ${String(item.status).toLowerCase().replace(/[^a-z]/g, "")}">${esc(item.status)}</span></td>
          <td><button class="link" type="button" onclick="window.promptStockOut(${item.id}, '${esc(item.name).replace(/'/g, "\\'")}')">Stock-out</button></td>
        </tr>`).join("")
      : `<tr><td colspan="12" class="empty">No items match your search.</td></tr>`;

    const counts = { Available: 0, "Low-Stock": 0, "Out-of-Stock": 0 };
    items.forEach((item) => counts[item.status] = (counts[item.status] || 0) + 1);
    $("cntAvail").textContent = counts.Available;
    $("cntLow").textContent = counts["Low-Stock"];
    $("cntOut").textContent = counts["Out-of-Stock"];
    $("lowPill").textContent = `Stock alerts: ${(counts["Low-Stock"] || 0) + (counts["Out-of-Stock"] || 0)}`;

    $("moveRows").innerHTML = movements.length
      ? movements.slice(0, 20).map((movement) =>
          `<tr><td>${esc(movement.date)}</td><td>${esc(movement.item)}</td><td>${esc(movement.type)}</td>
           <td>${movement.qty}</td><td>${esc(movement.batchNo || "")}</td><td>${esc(movement.by || "")}</td></tr>`
        ).join("")
      : `<tr><td colspan="6" class="empty">No movements yet.</td></tr>`;
  }

  window.promptStockOut = promptStockOut;
  window.saveStockIn = saveStockIn;
  window.addItem = addItem;

  $("search").addEventListener("input", render);
  $("search").addEventListener("keydown", handleScanEnter);
  $("scanBtn").addEventListener("click", () => $("search").focus());
  $("todayPill").textContent =
    "Today: " + new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" });
  refresh();
})();
