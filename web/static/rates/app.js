// UI-only behavior: theme persistence, live clock, and basic search/sort.
// All financial computations + bank parsing should stay in Python (services).

function pad2(n) {
  return String(n).padStart(2, '0');
}

function startClock() {
  const clockEl = document.getElementById('clock');
  const dateEl = document.getElementById('date-str');
  if (!clockEl || !dateEl) return;

  const tick = () => {
    const now = new Date();
    clockEl.textContent = `${pad2(now.getHours())}:${pad2(now.getMinutes())}:${pad2(now.getSeconds())}`;
    // keep date string simple; you can localize via Django later
    dateEl.textContent = now.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
  };
  tick();
  setInterval(tick, 1000);
}

function initThemeToggle() {
  const btn = document.getElementById('theme-btn');
  if (!btn) return;

  const apply = (mode) => {
    const isDark = mode !== 'light';
    document.body.classList.toggle('light', !isDark);
    btn.textContent = isDark ? '🌙' : '☀️';
  };

  const saved = localStorage.getItem('pz_theme') || 'dark';
  apply(saved);

  btn.addEventListener('click', () => {
    const next = document.body.classList.contains('light') ? 'dark' : 'light';
    localStorage.setItem('pz_theme', next);
    apply(next);
  });
}

function initBankSearchAndSort() {
  const search = document.getElementById('bank-search');
  const sortSel = document.getElementById('sort-select');
  const grid = document.getElementById('bank-grid');
  if (!grid) return;

  const cards = () => Array.from(grid.querySelectorAll('[data-bank-card="1"]'));

  const applySearch = () => {
    const q = (search?.value || '').trim().toLowerCase();
    cards().forEach((el) => {
      const name = (el.getAttribute('data-bank-name') || '').toLowerCase();
      el.style.display = !q || name.includes(q) ? '' : 'none';
    });
  };

  const applySort = () => {
    if (!sortSel) return;
    const mode = sortSel.value;
    const list = cards();

    const keyName = (el) => el.getAttribute('data-bank-name') || '';
    const keyBuy = (el) => Number(el.getAttribute('data-buy') || '0');
    const keySell = (el) => Number(el.getAttribute('data-sell') || '0');

    list.sort((a, b) => {
      if (mode === 'buy-desc') return keyBuy(b) - keyBuy(a);
      if (mode === 'sell-asc') return keySell(a) - keySell(b);
      return keyName(a).localeCompare(keyName(b));
    });

    list.forEach((el) => grid.appendChild(el));
  };

  search?.addEventListener('input', () => applySearch());
  sortSel?.addEventListener('change', () => applySort());
}

document.addEventListener('DOMContentLoaded', () => {
  startClock();
  initThemeToggle();
  initBankSearchAndSort();
});

