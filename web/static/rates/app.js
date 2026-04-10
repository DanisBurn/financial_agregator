function pad2(n) {
  return String(n).padStart(2, '0');
}

function getLocale() {
  return document.documentElement.lang || undefined;
}

function formatCompactNumber(value) {
  return new Intl.NumberFormat(getLocale(), {
    maximumFractionDigits: 0,
  }).format(Math.round(Number(value)));
}

function parseJsonScript(id) {
  const el = document.getElementById(id);
  if (!el) return null;

  try {
    return JSON.parse(el.textContent);
  } catch (error) {
    return null;
  }
}

function startClock() {
  const clockEl = document.getElementById('clock');
  const dateEl = document.getElementById('date-str');
  if (!clockEl || !dateEl) return;

  const locale = getLocale();
  const tick = () => {
    const now = new Date();
    clockEl.textContent = `${pad2(now.getHours())}:${pad2(now.getMinutes())}:${pad2(now.getSeconds())}`;
    dateEl.textContent = now.toLocaleDateString(locale, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
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
      if (mode === 'buy-asc') return keyBuy(a) - keyBuy(b);
      if (mode === 'sell-desc') return keySell(b) - keySell(a);
      if (mode === 'sell-asc') return keySell(a) - keySell(b);
      return keyName(a).localeCompare(keyName(b), getLocale());
    });

    list.forEach((el) => grid.appendChild(el));
  };

  applySort();
  search?.addEventListener('input', applySearch);
  sortSel?.addEventListener('change', applySort);
}

function initGoldSelector() {
  const goldData = parseJsonScript('gold-data');
  if (!goldData || !Array.isArray(goldData.options) || goldData.options.length === 0) return;

  const buttons = Array.from(document.querySelectorAll('[data-gold-weight]'));
  const priceEl = document.querySelector('[data-gold-price]');
  const unitEl = document.querySelector('[data-gold-unit]');
  const perGramEl = document.querySelector('[data-gold-per-gram]');
  const changeEl = document.querySelector('[data-gold-change]');
  const statPriceEl = document.querySelector('[data-gold-stat-price]');
  const statWeightEl = document.querySelector('[data-gold-stat-weight]');
  const unitPrefix = 'UZS /';

  const optionsByWeight = new Map(goldData.options.map((option) => [option.weight, option]));

  const renderWeight = (weight) => {
    const option = optionsByWeight.get(weight);
    if (!option) return;

    buttons.forEach((button) => {
      button.classList.toggle('active', button.getAttribute('data-gold-weight') === weight);
    });

    if (priceEl) priceEl.textContent = option.price_display || '—';
    if (unitEl) unitEl.textContent = `${unitPrefix} ${option.weight}`;
    if (perGramEl) perGramEl.textContent = option.per_gram_display || '—';
    if (statPriceEl) statPriceEl.textContent = option.price_display || '—';
    if (statWeightEl) statWeightEl.textContent = option.weight || '—';
    if (changeEl) {
      const change = Number(option.change_pct || 0);
      if (change > 0) {
        changeEl.innerHTML = `<span class="up-text">▲ +${change}%</span>`;
      } else if (change < 0) {
        changeEl.innerHTML = `<span class="down-text">▼ ${change}%</span>`;
      } else {
        changeEl.innerHTML = '<span class="tick-flat">— 0%</span>';
      }
    }
  };

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      renderWeight(button.getAttribute('data-gold-weight'));
    });
  });

  renderWeight(goldData.selected_weight || goldData.options[0].weight);
}

function buildLineSegments(seriesValues, xForIndex, yForValue) {
  const segments = [];
  let current = [];

  seriesValues.forEach((value, index) => {
    if (value === null || value === undefined) {
      if (current.length) {
        segments.push(current);
        current = [];
      }
      return;
    }

    current.push({ x: xForIndex(index), y: yForValue(value), value });
  });

  if (current.length) segments.push(current);
  return segments;
}

function buildPath(points) {
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
}

function renderLineChart(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!data || !Array.isArray(data.labels) || !Array.isArray(data.series) || data.series.length === 0) {
    return;
  }

  const values = data.series
    .flatMap((series) => series.values || [])
    .filter((value) => value !== null && value !== undefined)
    .map(Number);

  if (values.length === 0) return;

  const width = Math.max(container.clientWidth || 320, 320);
  const height = Math.max(container.clientHeight || 280, 240);
  const padding = { top: 28, right: 20, bottom: 38, left: 54 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const pad = (max - min) * 0.12;
  min -= pad;
  max += pad;

  const xForIndex = (index) => {
    if (data.labels.length <= 1) return padding.left + innerWidth / 2;
    return padding.left + (innerWidth * index) / (data.labels.length - 1);
  };
  const yForValue = (value) => padding.top + innerHeight - ((value - min) / (max - min)) * innerHeight;

  const gridLines = [];
  const gridLabelCount = 4;
  for (let i = 0; i <= gridLabelCount; i += 1) {
    const ratio = i / gridLabelCount;
    const y = padding.top + innerHeight * ratio;
    const value = max - (max - min) * ratio;
    gridLines.push(`
      <line class="chart-grid-line" x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}"></line>
      <text class="chart-grid-label" x="${padding.left - 8}" y="${y + 4}" text-anchor="end">${formatCompactNumber(value)}</text>
    `);
  }

  const xLabels = data.labels
    .map((label, index) => {
      const x = xForIndex(index);
      return `<text class="chart-axis-label" x="${x}" y="${height - 12}" text-anchor="middle">${label}</text>`;
    })
    .join('');

  const seriesMarkup = data.series
    .map((series) => {
      const segments = buildLineSegments(series.values || [], xForIndex, yForValue);
      const paths = segments
        .map((points) => `<path class="chart-series-line" d="${buildPath(points)}" stroke="${series.color}"></path>`)
        .join('');
      const points = segments
        .flat()
        .map(
          (point) =>
            `<circle class="chart-series-point" cx="${point.x}" cy="${point.y}" r="4" fill="${series.color}"><title>${series.label}: ${formatCompactNumber(point.value)}</title></circle>`,
        )
        .join('');
      return `${paths}${points}`;
    })
    .join('');

  const legend = data.series
    .map(
      (series) =>
        `<span class="chart-legend-item"><span class="chart-legend-swatch" style="background:${series.color}"></span>${series.label}</span>`,
    )
    .join('');

  container.innerHTML = `
    <svg class="chart-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
      ${gridLines.join('')}
      ${seriesMarkup}
      ${xLabels}
    </svg>
    <div class="chart-legend">${legend}</div>
  `;
}

function initCharts() {
  const historyChart = parseJsonScript('history-chart-data');
  const forecastChart = parseJsonScript('forecast-chart-data');

  const render = () => {
    renderLineChart('chart-history', historyChart);
    renderLineChart('chart-forecast', forecastChart);
  };

  let resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(render, 120);
  });

  render();
}

document.addEventListener('DOMContentLoaded', () => {
  startClock();
  initThemeToggle();
  initBankSearchAndSort();
  initGoldSelector();
  initCharts();
});
