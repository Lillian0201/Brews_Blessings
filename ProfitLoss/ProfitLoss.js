// Profit/Loss Report Logic
(function () {
  'use strict';

  // Mount navigation sidebar
  const me = BBNav.mount('pnl');
  if (!me) return;

  const money = n => '₱' + (+n).toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  });

  // Default financial snapshot from design
  let sales = 48600;
  let productCost = 16200;
  let grossProfit = sales - productCost; // 32400
  let expenses = 21800;
  let netProfit = grossProfit - expenses; // 10600

  // Set default dates
  const fromDate = document.getElementById('fromDate');
  const toDate = document.getElementById('toDate');
  const now = new Date();
  if (toDate) toDate.value = now.toISOString().split('T')[0];
  if (fromDate) {
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    fromDate.value = firstDay.toISOString().split('T')[0];
  }

  function updateDisplay() {
    document.getElementById('valTotalSales').textContent = money(sales);
    document.getElementById('valProductCost').textContent = money(productCost);
    document.getElementById('valGrossProfit').textContent = money(grossProfit);
    document.getElementById('valOperatingExpense').textContent = money(expenses);
    document.getElementById('valNetProfit').textContent = money(netProfit);

    const statusText = document.getElementById('statusText');
    if (netProfit >= 0) {
      statusText.textContent = 'Earning';
      statusText.style.color = '#2a7e3b';
    } else {
      statusText.textContent = 'Loss';
      statusText.style.color = '#a63a2b';
    }

    // Adjust chart bars proportionally (max height 180px)
    const maxHeight = 180;
    const maxVal = Math.max(sales, 1);
    
    document.getElementById('barSales').style.height = `${(sales / maxVal) * maxHeight}px`;
    document.getElementById('barProduct').style.height = `${(productCost / maxVal) * maxHeight}px`;
    document.getElementById('barExpense').style.height = `${(expenses / maxVal) * maxHeight}px`;
    document.getElementById('barNet').style.height = `${Math.max(15, (Math.abs(netProfit) / maxVal) * maxHeight)}px`;
  }

  document.getElementById('applyFilterBtn').addEventListener('click', () => {
    updateDisplay();
  });

  // Report modal actions
  const modal = document.getElementById('reportModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  const modalClose = document.getElementById('modalCloseBtn');

  document.querySelectorAll('.btn-report').forEach(btn => {
    btn.addEventListener('click', () => {
      const reportName = btn.dataset.report;
      modalTitle.textContent = reportName;
      modalBody.innerHTML = `
        <p><strong>Generated on:</strong> ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}</p>
        <p><strong>Period:</strong> ${fromDate.value || 'Beginning'} to ${toDate.value || 'Today'}</p>
        <hr style="border: 0; border-top: 1px solid #e3d2b8; margin: 12px 0;">
        <p>Summary for <em>${reportName}</em> is compiled and ready for review or export.</p>
        <p>Total Revenue: <strong>${money(sales)}</strong><br>Total Deductions: <strong>${money(productCost + expenses)}</strong><br>Net Outcome: <strong style="color: #2a7e3b;">${money(netProfit)}</strong></p>
      `;
      modal.classList.add('active');
    });
  });

  modalClose.addEventListener('click', () => {
    modal.classList.remove('active');
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('active');
  });

  // CSV Export handler
  const btnCsv = document.getElementById('btnCsvExport');
  if (btnCsv) {
    btnCsv.addEventListener('click', (e) => {
      e.stopPropagation();
      const csvRows = [
        ['Metric / Item', 'Amount (PHP)', 'Period From', 'Period To'],
        ['Total Sales', sales, fromDate.value || 'Beginning', toDate.value || 'Today'],
        ['Total Product Cost', productCost, '', ''],
        ['Gross Profit', grossProfit, '', ''],
        ['Operating Expense', expenses, '', ''],
        ['Net Profit / Loss', netProfit, '', ''],
        ['Financial Status', netProfit >= 0 ? 'Earning' : 'Loss', '', '']
      ];

      const csvContent = 'data:text/csv;charset=utf-8,' + csvRows.map(r => r.map(x => `"${x}"`).join(',')).join('\n');
      const encodedUri = encodeURI(csvContent);
      const link = document.createElement('a');
      link.setAttribute('href', encodedUri);
      link.setAttribute('download', `brews_blessings_financial_report_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    });
  }

  updateDisplay();
})();
