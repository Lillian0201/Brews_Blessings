(() => {
  "use strict";

  const KEY = "bb_inventory_v1";

  // Ingredients used per ONE drink. Units must match the inventory unit (kg, L, bottle...).
  // Products not listed here use no stock. Fill these in from the team's recipes.
  const RECIPES = {
    // "Caramel Latte": [
    //   { item: "Espresso beans", qty: 0.018 },
    //   { item: "Fresh milk", qty: 0.2 },
    //   { item: "Caramel syrup", qty: 0.02 }
    // ],
  };

  const round = (n) => Math.round(n * 1000) / 1000;
  const today = () => new Date().toISOString().slice(0, 10);
  const shortDate = () => {
    const d = new Date();
    return (d.getMonth() + 1) + "/" + String(d.getDate()).padStart(2, "0");
  };

  function seed() {
    return {
      items: [
        { id: 1, name: "Espresso beans", barcode: "BC-001", unit: "kg", unitCost: 1200, reorder: 8,
          beginning: 20, stockIn: 10, stockOut: 14,
          batches: [{ batchNo: "B01", qty: 16, received: "2026-10-28" }] },
        { id: 2, name: "Fresh milk", barcode: "BC-002", unit: "L", unitCost: 70, reorder: 10,
          beginning: 30, stockIn: 20, stockOut: 46,
          batches: [{ batchNo: "B02", qty: 4, received: "2026-10-28" }] },
        { id: 3, name: "Caramel syrup", barcode: "BC-003", unit: "bottle", unitCost: 225, reorder: 2,
          beginning: 6, stockIn: 0, stockOut: 6, batches: [] }
      ],
      movements: [
        { date: "10/28", item: "Espresso beans", type: "Stock-in", qty: 10, batch: "B01", by: "Owner" },
        { date: "10/28", item: "Fresh milk", type: "Stock-out", qty: 12, batch: "B02", by: "Barista" }
      ]
    };
  }

  function save(state) {
    localStorage.setItem(KEY, JSON.stringify(state));
  }

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) { /* fall through to seed data */ }
    const s = seed();
    save(s);
    return s;
  }

  const remaining = (it) => round(it.beginning + it.stockIn - it.stockOut);

  function statusOf(it) {
    const r = remaining(it);
    if (r <= 0) return "Out-of-Stock";
    if (r <= it.reorder) return "Low-Stock";
    return "Available";
  }

  function oldestBatch(it) {
    const b = it.batches
      .filter((x) => x.qty > 0)
      .sort((a, b) => a.received.localeCompare(b.received))[0];
    return b ? b.batchNo : "—";
  }

  const findItem = (state, name) => state.items.find((i) => i.name === name);

  function logMove(state, name, type, qty, batch, by) {
    state.movements.push({ date: shortDate(), item: name, type, qty, batch, by });
  }

  // FIFO: take from the oldest batch first. Stock must already be checked.
  function takeFifo(state, it, qty, by) {
    let left = qty;
    const ordered = it.batches
      .filter((b) => b.qty > 0)
      .sort((a, b) => a.received.localeCompare(b.received));
    for (const b of ordered) {
      const take = Math.min(b.qty, left);
      b.qty = round(b.qty - take);
      left = round(left - take);
      logMove(state, it.name, "Stock-out", take, b.batchNo, by);
      if (left <= 0) break;
    }
    it.stockOut = round(it.stockOut + qty);
  }

  // Total ingredient amounts needed for a list of order items.
  function requirements(orderItems) {
    const need = {};
    orderItems.forEach((oi) => {
      (RECIPES[oi.name] || []).forEach((r) => {
        need[r.item] = round((need[r.item] || 0) + r.qty * oi.qty);
      });
    });
    return need;
  }

  function canFulfil(orderItems) {
    const state = load();
    const shortages = [];
    for (const [name, qty] of Object.entries(requirements(orderItems))) {
      const it = findItem(state, name);
      if (!it) shortages.push(name + " (not in inventory)");
      else if (remaining(it) < qty) {
        shortages.push(`${name} (need ${qty}, have ${remaining(it)} ${it.unit})`);
      }
    }
    return { ok: shortages.length === 0, shortages };
  }

  function deduct(orderItems, orderNo) {
    const state = load();
    const by = "POS #" + orderNo;
    for (const [name, qty] of Object.entries(requirements(orderItems))) {
      const it = findItem(state, name);
      if (it) takeFifo(state, it, qty, by);
    }
    save(state);
  }

  function restore(orderItems, orderNo) {
    const state = load();
    const by = "POS #" + orderNo;
    for (const [name, qty] of Object.entries(requirements(orderItems))) {
      const it = findItem(state, name);
      if (!it) continue;
      const batchNo = "RST-" + orderNo;
      it.batches.push({ batchNo, qty, received: today() });
      it.stockOut = round(it.stockOut - qty);
      logMove(state, name, "Restore", qty, batchNo, by);
    }
    save(state);
  }

  function stockIn(name, qty, batchNo, by = "Owner") {
    const state = load();
    const it = findItem(state, name);
    if (!it) throw new Error("Unknown item: " + name);
    it.batches.push({ batchNo, qty, received: today() });
    it.stockIn = round(it.stockIn + qty);
    logMove(state, name, "Stock-in", qty, batchNo, by);
    save(state);
  }

  function stockOut(name, qty, by = "Barista") {
    const state = load();
    const it = findItem(state, name);
    if (!it) throw new Error("Unknown item: " + name);
    if (qty > remaining(it)) throw new Error(`Only ${remaining(it)} ${it.unit} of ${name} left.`);
    takeFifo(state, it, qty, by);
    save(state);
  }

  function addItem(item) {
    const state = load();
    const id = Math.max(0, ...state.items.map((i) => i.id)) + 1;
    state.items.push({ id, beginning: 0, stockIn: 0, stockOut: 0, batches: [], ...item });
    save(state);
  }

  function alertCount() {
    return load().items.filter((i) => statusOf(i) !== "Available").length;
  }

  // Refresh a page when another tab changes the stored inventory.
  function onChange(fn) {
    window.addEventListener("storage", (e) => { if (e.key === KEY) fn(); });
  }

  window.BBInventory = {
    load, remaining, statusOf, oldestBatch, requirements, canFulfil,
    deduct, restore, stockIn, stockOut, addItem, alertCount, onChange
  };
})();