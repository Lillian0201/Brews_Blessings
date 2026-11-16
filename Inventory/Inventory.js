if (!window.BBNav) {
  console.error('nav.js is not loaded. Check the script path in Inventory.html.');
} else if (!BBNav.mount('inv')) {
  // mount() redirects the user if their role can't see this page, so stop here
  throw new Error('Not allowed on this page');
}

const $ = (id) => document.getElementById(id);
const S = window.BBInventory;
const fmtPeso = (n) => "₱" + Number(n).toLocaleString("en-PH");

let items = [];
let movements = [];

function refresh() {
  const s = S.load();
  items = s.items;
  movements = s.movements;
}

function flash(text, isError = false) {
  const m = $("msg");
  m.textContent = text;
  m.className = "msg" + (isError ? " error" : "");
}

function populateItemSelect() {
  refresh();
  $("siItem").innerHTML =
    `<option value="">Select an item</option>` +
    items.map((i) => `<option value="${i.name}">${i.name}</option>`).join("");
}

function saveStockIn() {
  const name = $("siItem").value;
  const qty = Number($("siQty").value);
  const batch = $("siBatch").value.trim();
  if (!name || !(qty > 0) || !batch) {
    return flash("Pick an item, enter a quantity and a batch no.", true);
  }
  try {
    S.stockIn(name, qty, batch, "Owner");
  } catch (err) {
    return flash(err.message, true);
  }
  $("siQty").value = "";
  $("siBatch").value = "";
  render();
  flash("Stock-in saved.");
}

function promptStockOut(name) {
  refresh();
  const it = items.find((i) => i.name === name);
  const qty = Number(prompt(`Stock-out qty for ${name} (${it.unit}). Max ${S.remaining(it)}.`));
  if (!(qty > 0)) return;
  try {
    S.stockOut(name, qty, "Barista");
    render();
    flash(`Stock-out saved for ${name}.`);
  } catch (err) {
    flash(err.message, true);
  }
}

function addItem() {
  const name = prompt("Item name:");
  if (!name) return;
  const barcode = prompt("Barcode:") || "";
  const unit = prompt("Unit (kg, L, bottle, pcs...):") || "pcs";
  const unitCost = Number(prompt("Unit cost (₱):") || 0);
  const reorder = Number(prompt("Reorder level:") || 0);
  S.addItem({ name, barcode, unit, unitCost, reorder });
  populateItemSelect();
  render();
  flash(`${name} added. Use Stock-in to add its first batch.`);
}

function handleScanEnter(e) {
  if (e.key !== "Enter") return;
  refresh();
  const code = $("search").value.trim().toLowerCase();
  const hit = items.find((i) => i.barcode.toLowerCase() === code);
  if (hit) {
    $("siItem").value = hit.name;
    $("siItem").focus();
    flash(`Found ${hit.name}.`);
  }
}

function render() {
  refresh();
  const q = $("search").value.trim().toLowerCase();
  const shown = items.filter(
    (i) => i.name.toLowerCase().includes(q) || i.barcode.toLowerCase().includes(q)
  );

  $("itemRows").innerHTML = shown.length
    ? shown.map((it) => {
        const st = S.statusOf(it);
        return `<tr>
          <td>${it.name}</td><td>${it.barcode}</td><td>${it.unit}</td><td>${fmtPeso(it.unitCost)}</td>
          <td>${it.beginning}</td><td>${it.stockIn}</td><td>${it.stockOut}</td><td>${S.remaining(it)}</td>
          <td>${it.reorder}</td><td>${S.oldestBatch(it)}</td>
          <td><span class="badge ${st.toLowerCase()}">${st}</span></td>
          <td><button class="link" onclick="promptStockOut('${it.name}')">Stock-out</button></td>
        </tr>`;
      }).join("")
    : `<tr><td colspan="12" class="empty">No items match your search.</td></tr>`;

  const counts = { Available: 0, "Low-Stock": 0, "Out-of-Stock": 0 };
  items.forEach((i) => counts[S.statusOf(i)]++);
  $("cntAvail").textContent = counts.Available;
  $("cntLow").textContent = counts["Low-Stock"];
  $("cntOut").textContent = counts["Out-of-Stock"];
  $("lowPill").textContent = `Stock alerts: ${counts["Low-Stock"] + counts["Out-of-Stock"]}`;

  $("moveRows").innerHTML = movements.length
    ? movements.slice().reverse().slice(0, 20).map((m) =>
        `<tr><td>${m.date}</td><td>${m.item}</td><td>${m.type}</td><td>${m.qty}</td><td>${m.batch}</td><td>${m.by}</td></tr>`
      ).join("")
    : `<tr><td colspan="6" class="empty">No movements yet.</td></tr>`;
}

// ---- Init ----
$("search").addEventListener("input", render);
$("search").addEventListener("keydown", handleScanEnter);
$("scanBtn").addEventListener("click", () => $("search").focus());
$("todayPill").textContent =
  "Today: " + new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" });
S.onChange(() => { populateItemSelect(); render(); });
populateItemSelect();
render();