(() => {
  "use strict";

  const API = BBAPI.base;
  const $ = (id) => document.getElementById(id);
  const fmtPeso = (n) => "\u20B1" + Number(n).toLocaleString("en-PH");
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  let items = [];
  let movements = [];
  let selectedId = null;

  async function api(method, path, body) {
    const response = await BBAPI.fetch(API + path, {
      method,
      headers: { ...(body ? { "Content-Type": "application/json" } : {}) },
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

  async function refreshMovements() {
    try {
      movements = await api("GET", "/inventory/movements");
      renderMovementLog();
    } catch (error) {
      flash(error.message, true);
    }
  }

  function populateItemSelect() {
    $("siItem").innerHTML =
      `<option value="">Select an item</option>` +
      items.map((item) => `<option value="${item.id}">${esc(item.name)}</option>`).join("");
  }

  function selectItem(id, { clearInputs = true, focusQuantity = true } = {}) {
    const parsedId = id === null || id === "" ? null : Number(id);
    selectedId = Number.isFinite(parsedId) && items.some((item) => item.id === parsedId)
      ? parsedId
      : null;
    $("siItem").value = selectedId === null ? "" : String(selectedId);
    $("itemRows").querySelectorAll("tr[data-item-id]").forEach((row) => {
      row.classList.toggle("selected", Number(row.dataset.itemId) === selectedId);
    });

    if (clearInputs) {
      $("siQty").value = "";
      $("siBatch").value = "";
    }
    if (focusQuantity) $("siQty").focus();
  }

  async function saveStockIn() {
    const ingredientId = selectedId;
    const quantity = Number($("siQty").value);
    const batchNo = $("siBatch").value.trim();
    if (ingredientId === null) {
      await BBDialog.notify("Missing item", "Select an inventory item.");
      return;
    }
    if (!(quantity > 0)) {
      await BBDialog.notify("Invalid quantity", "Enter a quantity greater than zero.");
      return;
    }
    if (!batchNo) {
      await BBDialog.notify("Missing batch number", "Enter a batch number.");
      return;
    }
    try {
      await api("POST", "/inventory/stock-in", { ingredientId, quantity, batchNo });
      $("siQty").value = "";
      $("siBatch").value = "";
      await refresh();
      flash("Stock-in saved.");
    } catch (error) {
      await BBDialog.notify("Stock-in failed", error.message);
    }
  }

  async function promptStockOut(ingredientId, name) {
    const item = items.find((entry) => entry.id === ingredientId);
    if (!item) return;
    const values = await BBDialog.form(`Stock-out: ${name}`, [
      {
        key: "quantity",
        label: `Quantity (${item.unit}; remaining ${item.remaining})`,
        inputMode: "decimal",
        placeholder: "e.g. 1"
      },
      {
        key: "type",
        label: "Type",
        initial: "Waste",
        options: ["Waste", "Stock-Out"]
      },
      {
        key: "reason",
        label: "Reason",
        placeholder: "e.g. expired, spilled"
      }
    ], {
      okText: "Save",
      message: "Stock-out means stock removed outside of a normal sale, such as waste or spills. Sales deduct stock automatically from recipes."
    });
    if (!values) return;

    const quantity = Number(values.quantity);
    const reason = values.reason.trim();
    if (!(quantity > 0)) {
      await BBDialog.notify("Invalid quantity", "Enter a quantity greater than zero.");
      return;
    }
    if (values.type === "Waste" && !reason) {
      await BBDialog.notify("Missing reason", "Enter a reason for waste.");
      return;
    }
    try {
      await api("POST", "/inventory/stock-out", {
        ingredientId,
        quantity,
        type: values.type,
        reason
      });
      await refresh();
      flash(`Stock-out saved for ${name}.`);
    } catch (error) {
      await BBDialog.notify("Stock-out failed", error.message);
    }
  }

  async function addItem() {
    const values = await BBDialog.form("Add Item", [
      { key: "name", label: "Item Name", required: true, placeholder: "e.g. Vanilla syrup" },
      {
        key: "unit",
        label: "Unit",
        initial: "pcs",
        options: ["pcs", "kg", "g", "L", "mL", "bottle"]
      },
      {
        key: "unitCost",
        label: "Unit Cost (\u20B1)",
        initial: "0",
        inputMode: "decimal",
        placeholder: "e.g. 70"
      },
      {
        key: "reorderLevel",
        label: "Reorder Level",
        initial: "0",
        inputMode: "decimal",
        placeholder: "e.g. 10"
      },
      { key: "barcode", label: "Barcode", placeholder: "Optional" }
    ], { okText: "Add" });
    if (!values) return;

    const name = values.name.trim();
    if (!name) {
      await BBDialog.notify("Missing information", "Enter the item name.");
      return;
    }
    try {
      await api("POST", "/inventory/items", {
        name,
        unit: values.unit,
        unitCost: Number(values.unitCost),
        reorderLevel: Number(values.reorderLevel),
        barcode: values.barcode.trim()
      });
      await refresh();
      flash(`${name} added. Use Stock-in to add its first batch.`);
    } catch (error) {
      await BBDialog.notify("Add item failed", error.message);
    }
  }

  function handleScanEnter(event) {
    if (event.key !== "Enter") return;
    const code = $("search").value.trim().toLowerCase();
    const hit = items.find((item) => String(item.barcode || "").toLowerCase() === code);
    if (hit) {
      selectItem(hit.id);
      flash(`Found ${hit.name}.`);
    }
  }

  function fmtDate(iso) {
    if (iso === null || iso === undefined || String(iso).trim() === "") return "—";

    const raw = String(iso);
    const milliseconds = raw.replace(/(\.\d{3})\d+(?=(?:Z|[+-]\d{2}:?\d{2})?$)/i, "$1");
    const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(milliseconds);
    const dateValue = hasTimezone
      ? milliseconds
      : /T/i.test(milliseconds)
        ? `${milliseconds}Z`
        : `${milliseconds}T00:00:00Z`;
    const date = new Date(dateValue);
    if (!Number.isFinite(date.getTime())) return raw;

    return date.toLocaleString("en-PH", {
      timeZone: "Asia/Manila",
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit"
    });
  }

  function renderMovementLog() {
    $("moveRows").innerHTML = movements.length
      ? movements.slice(0, 20).map((movement) =>
          `<tr><td>${esc(fmtDate(movement.date))}</td><td>${esc(movement.item)}</td><td>${esc(movement.type)}</td>
           <td>${movement.qty}</td><td>${esc(movement.batchNo || "")}</td><td>${esc(movement.by || "")}</td></tr>`
        ).join("")
      : `<tr><td colspan="6" class="empty">No movements yet.</td></tr>`;
  }

  function render() {
    const query = $("search").value.trim().toLowerCase();
    const shown = items.filter((item) =>
      item.name.toLowerCase().includes(query) ||
      String(item.barcode || "").toLowerCase().includes(query)
    );

    $("itemRows").innerHTML = shown.length
      ? shown.map((item) => `<tr data-item-id="${item.id}" tabindex="0">
          <td>${esc(item.name)}</td><td>${esc(item.barcode || "")}</td><td>${esc(item.unit)}</td>
          <td>${fmtPeso(item.unitCost)}</td><td>${item.beginning}</td><td>${item.stockIn}</td>
          <td>${item.stockOut}</td><td>${item.remaining}</td><td>${item.reorderLevel}</td>
          <td>${esc(item.batchNo)}</td>
          <td><span class="badge ${String(item.status).toLowerCase().replace(/[^a-z]/g, "")}">${esc(item.status)}</span></td>
          <td><button class="link" type="button" onclick="window.promptStockOut(${item.id}, '${esc(item.name).replace(/'/g, "\\'")}')">Stock-out</button></td>
        </tr>`).join("")
      : `<tr><td colspan="12" class="empty">No items match your search.</td></tr>`;
    selectItem(selectedId, { clearInputs: false, focusQuantity: false });

    const counts = { Available: 0, "Low-Stock": 0, "Out-of-Stock": 0 };
    items.forEach((item) => counts[item.status] = (counts[item.status] || 0) + 1);
    $("cntAvail").textContent = counts.Available;
    $("cntLow").textContent = counts["Low-Stock"];
    $("cntOut").textContent = counts["Out-of-Stock"];
    $("lowPill").textContent = `Stock alerts: ${(counts["Low-Stock"] || 0) + (counts["Out-of-Stock"] || 0)}`;
    renderMovementLog();
  }

  window.promptStockOut = promptStockOut;
  window.saveStockIn = saveStockIn;
  window.addItem = addItem;

  $("itemRows").addEventListener("click", (event) => {
    const row = event.target.closest("tr[data-item-id]");
    if (!row || event.target.closest("a") || event.target.closest("button.link")) return;
    selectItem(Number(row.dataset.itemId));
  });
  $("itemRows").addEventListener("keydown", (event) => {
    const row = event.target.closest("tr[data-item-id]");
    if (!row || event.target !== row || (event.key !== "Enter" && event.key !== " ")) return;
    event.preventDefault();
    selectItem(Number(row.dataset.itemId));
  });
  $("siItem").addEventListener("change", () => {
    selectItem($("siItem").value);
  });
  $("search").addEventListener("input", render);
  $("search").addEventListener("keydown", handleScanEnter);
  $("scanBtn").addEventListener("click", () => $("search").focus());
  $("todayPill").textContent =
    "Today: " + new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" });
  window.setInterval(refreshMovements, 30000);
  refresh();
})();
