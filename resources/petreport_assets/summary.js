// Region-table overlay inside the surface viewer: T opens it, sorts on header
// click, filters as you type. Acts on rows already in the DOM, so the report
// stays self-contained with no network.
(function () {
  const panel = document.getElementById('table-panel');
  const table = document.getElementById('summary-table');
  if (!panel || !table || table.dataset.wired) return;
  table.dataset.wired = '1';

  const tbody = table.tBodies[0];
  const rows = Array.from(tbody.rows);
  const filterEl = document.getElementById('summary-filter');
  const countEl = document.getElementById('summary-count');
  const scroller = panel.querySelector('.summary-scroll');

  // ── Open / close ────────────────────────────────────────────────────────
  function setOpen(open) {
    panel.classList.toggle('open', open);
    if (open && filterEl) filterEl.focus();
    if (!open && filterEl) filterEl.blur();
  }
  function toggle() { setOpen(!panel.classList.contains('open')); }

  window.addEventListener('keydown', (e) => {
    const t = e.target;
    const typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
    if (e.key === 'Escape' && panel.classList.contains('open')) { setOpen(false); return; }
    // T must still work while the filter is focused, which is where the
    // reader usually is when dismissing the panel.
    if ((e.key === 't' || e.key === 'T') && (!typing || t === filterEl)) {
      e.preventDefault();
      toggle();
    }
  });

  const closeBtn = document.getElementById('table-close');
  if (closeBtn) closeBtn.addEventListener('click', () => setOpen(false));

  // ── Sorting ─────────────────────────────────────────────────────────────
  // Numeric cells carry the unrounded value in data-v; sorting the rendered
  // 2-decimal text would tie rows that are not actually tied.
  function cellValue(row, idx, type) {
    const cell = row.cells[idx];
    return type === 'num' ? parseFloat(cell.dataset.v)
                          : cell.textContent.trim().toLowerCase();
  }

  let sortIdx = -1, sortDir = 1;
  function sortBy(idx, type) {
    sortDir = (idx === sortIdx) ? -sortDir : 1;
    sortIdx = idx;
    rows.slice().sort((a, b) => {
      const va = cellValue(a, idx, type), vb = cellValue(b, idx, type);
      if (va < vb) return -sortDir;
      if (va > vb) return sortDir;
      return 0;
    }).forEach(r => tbody.appendChild(r));

    Array.from(table.tHead.rows[0].cells).forEach((th, i) => {
      th.classList.toggle('sorted-asc', i === idx && sortDir === 1);
      th.classList.toggle('sorted-desc', i === idx && sortDir === -1);
    });
  }

  Array.from(table.tHead.rows[0].cells).forEach((th, i) => {
    th.addEventListener('click', () => sortBy(i, th.dataset.type));
  });

  // ── Filtering ───────────────────────────────────────────────────────────
  function applyFilter() {
    const q = (filterEl ? filterEl.value : '').trim().toLowerCase();
    let shown = 0;
    rows.forEach(r => {
      const hit = !q || r.cells[0].textContent.toLowerCase().includes(q);
      r.classList.toggle('filtered-out', !hit);
      if (hit) shown++;
    });
    if (countEl) countEl.textContent = q ? `${shown} of ${rows.length}` : '';
  }
  if (filterEl) filterEl.addEventListener('input', applyFilter);
  applyFilter();

  // ── Scrollbar: visible only while actually scrolling ─────────────────────
  if (scroller) {
    let idle;
    scroller.addEventListener('scroll', () => {
      scroller.classList.add('scrolling');
      clearTimeout(idle);
      idle = setTimeout(() => scroller.classList.remove('scrolling'), 700);
    }, { passive: true });
  }
})();
