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

function getCsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
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

  if (document.body.classList.contains('is-miniapp') || document.body.dataset.telegramThemeLocked === '1') {
    btn.style.display = 'none';
    return;
  }

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

function parseOptionalNumber(rawValue) {
  if (rawValue === null || rawValue === undefined || rawValue === '') return null;
  const numeric = Number(rawValue);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeTelegramUser(rawUser) {
  if (!rawUser) return null;

  const firstName = rawUser.first_name || rawUser.firstName || '';
  const lastName = rawUser.last_name || rawUser.lastName || '';
  const username = rawUser.username || '';
  const displayName = rawUser.display_name || [firstName, lastName].filter(Boolean).join(' ').trim() || username || 'Telegram user';
  const initials = rawUser.initials || displayName.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'TG';

  return {
    displayName,
    initials,
    username,
    photoUrl: rawUser.photo_url || rawUser.photoUrl || '',
  };
}

function renderTelegramUser(rawUser) {
  const user = normalizeTelegramUser(rawUser);
  const chip = document.getElementById('tg-user-chip');
  const avatar = document.getElementById('tg-user-avatar');
  const name = document.getElementById('tg-user-name');
  const meta = document.getElementById('tg-user-meta');
  if (!chip || !avatar || !name || !meta) return;

  if (!user) {
    chip.classList.add('is-hidden');
    return;
  }

  chip.classList.remove('is-hidden');
  name.textContent = user.displayName;
  meta.textContent = user.username ? `@${user.username}` : 'Signed in with Telegram';

  if (user.photoUrl) {
    avatar.textContent = '';
    avatar.style.backgroundImage = `url("${user.photoUrl}")`;
    avatar.style.backgroundSize = 'cover';
    avatar.style.backgroundPosition = 'center';
  } else {
    avatar.style.backgroundImage = '';
    avatar.textContent = user.initials;
  }
}

function applyTelegramTheme(themeParams, colorScheme) {
  if (!themeParams && !colorScheme) return;

  const root = document.documentElement;
  const setVar = (name, value) => {
    if (value) root.style.setProperty(name, value);
  };

  setVar('--bg', themeParams?.bg_color);
  setVar('--surface', themeParams?.secondary_bg_color || themeParams?.section_bg_color);
  setVar('--surface2', themeParams?.section_bg_color || themeParams?.secondary_bg_color);
  setVar('--text', themeParams?.text_color);
  setVar('--muted', themeParams?.hint_color);
  setVar('--accent', themeParams?.button_color);
  setVar('--accent3', themeParams?.destructive_text_color);
  setVar('--header-logo', themeParams?.text_color);
  setVar('--ticker-bg', themeParams?.secondary_bg_color || themeParams?.bg_color);
  setVar('--sort-bg', themeParams?.secondary_bg_color || themeParams?.bg_color);
  setVar('--rate-box-bg', themeParams?.section_bg_color || themeParams?.secondary_bg_color);
  setVar('--table-head-bg', themeParams?.secondary_bg_color || themeParams?.bg_color);

  if (colorScheme === 'light') {
    document.body.classList.add('light');
  } else if (colorScheme === 'dark') {
    document.body.classList.remove('light');
  }

  document.body.dataset.telegramThemeLocked = '1';
}

function updateTelegramSafeArea(webApp) {
  const insets = webApp?.contentSafeAreaInset || webApp?.safeAreaInset || {};
  const root = document.documentElement;
  root.style.setProperty('--tg-safe-top', `${Number(insets.top || 0)}px`);
  root.style.setProperty('--tg-safe-bottom', `${Number(insets.bottom || 0)}px`);
}

async function authenticateTelegramMiniApp(config, webApp) {
  if (!config?.authUrl || !webApp?.initData) return null;

  try {
    const response = await fetch(config.authUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ init_data: webApp.initData }),
    });
    const payload = await response.json();
    if (!response.ok || !payload?.ok) return null;
    return payload.user || null;
  } catch (error) {
    return null;
  }
}

async function initTelegramMiniApp() {
  const config = parseJsonScript('miniapp-config') || {};
  const existingUser = parseJsonScript('telegram-user-data');
  const webApp = window.Telegram?.WebApp;

  if (!config.mode && !webApp) {
    renderTelegramUser(existingUser);
    return;
  }

  document.body.classList.add('is-miniapp');
  renderTelegramUser(existingUser || config.telegramUser);

  if (!webApp) return;

  try {
    webApp.ready();
    webApp.expand();
  } catch (error) {
    // noop
  }

  applyTelegramTheme(webApp.themeParams || {}, webApp.colorScheme);
  updateTelegramSafeArea(webApp);
  renderTelegramUser(existingUser || config.telegramUser || webApp.initDataUnsafe?.user);

  if (typeof webApp.onEvent === 'function') {
    webApp.onEvent('themeChanged', () => {
      applyTelegramTheme(webApp.themeParams || {}, webApp.colorScheme);
    });
    webApp.onEvent('viewportChanged', () => {
      updateTelegramSafeArea(webApp);
      window.dispatchEvent(new Event('resize'));
    });
  }

  const authenticatedUser = await authenticateTelegramMiniApp(config, webApp);
  if (authenticatedUser) {
    renderTelegramUser(authenticatedUser);
  }
}

function initBankSearchAndSort() {
  const search = document.getElementById('bank-search');
  const sortSel = document.getElementById('sort-select');
  const grid = document.getElementById('bank-grid');
  const compareRows = () => Array.from(document.querySelectorAll('[data-compare-row="1"]'));
  if (!grid) return;

  const cards = () => Array.from(grid.querySelectorAll('[data-bank-card="1"]'));

  const applySearch = () => {
    const q = (search?.value || '').trim().toLowerCase();
    cards().forEach((el) => {
      const name = (el.getAttribute('data-bank-name') || '').toLowerCase();
      el.style.display = !q || name.includes(q) ? '' : 'none';
    });
    compareRows().forEach((row) => {
      const name = (row.getAttribute('data-bank-name') || '').toLowerCase();
      row.style.display = !q || name.includes(q) ? '' : 'none';
    });
  };

  const applySort = () => {
    if (!sortSel) return;
    const mode = sortSel.value;
    const cardList = cards();
    const tableRows = compareRows();

    const keyName = (el) => el.getAttribute('data-bank-name') || '';
    const keyBuy = (el) => parseOptionalNumber(el.getAttribute('data-buy'));
    const keySell = (el) => parseOptionalNumber(el.getAttribute('data-sell'));
    const compareNullable = (left, right, fallback) => {
      if (left === null && right === null) return fallback;
      if (left === null) return 1;
      if (right === null) return -1;
      return 0;
    };
    const comparator = (a, b) => {
      if (mode === 'sell-to-bank') {
        const nullableResult = compareNullable(keyBuy(a), keyBuy(b), keyName(a).localeCompare(keyName(b), getLocale()));
        if (nullableResult !== 0) return nullableResult;
        return keyBuy(b) - keyBuy(a) || keyName(a).localeCompare(keyName(b), getLocale());
      }
      if (mode === 'buy-from-bank') {
        const nullableResult = compareNullable(keySell(a), keySell(b), keyName(a).localeCompare(keyName(b), getLocale()));
        if (nullableResult !== 0) return nullableResult;
        return keySell(a) - keySell(b) || keyName(a).localeCompare(keyName(b), getLocale());
      }
      return keyName(a).localeCompare(keyName(b), getLocale());
    };

    cardList.sort(comparator);
    tableRows.sort(comparator);

    cardList.forEach((el) => grid.appendChild(el));
    tableRows.forEach((row) => row.parentNode?.appendChild(row));
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
  const buyEl = document.querySelector('[data-gold-buy]');
  const buyDamagedEl = document.querySelector('[data-gold-buy-damaged]');
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

    if (priceEl) priceEl.textContent = option.sell_display || option.price_display || '—';
    if (unitEl) unitEl.textContent = `${unitPrefix} ${option.weight}`;
    if (perGramEl) perGramEl.textContent = option.per_gram_display || '—';
    if (buyEl) buyEl.textContent = option.buy_display || '—';
    if (buyDamagedEl) buyDamagedEl.textContent = option.buy_damaged_display || '—';
    if (statPriceEl) statPriceEl.textContent = option.sell_display || option.price_display || '—';
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
        .map(
          (points) =>
            `<path class="chart-series-line" d="${buildPath(points)}" stroke="${series.color}"${series.dasharray ? ` stroke-dasharray="${series.dasharray}"` : ''}></path>`,
        )
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

function setupTabbedChart({ chartData, containerId, chartKey }) {
  if (!chartData || !chartData.datasets) return () => {};

  const buttons = Array.from(document.querySelectorAll(`[data-chart-switch="${chartKey}"]`));
  const metaEl = document.querySelector(`[data-chart-meta="${chartKey}"]`);
  const datasetKeys = Object.keys(chartData.datasets);
  let activeKey = chartData.selected_key && chartData.datasets[chartData.selected_key]
    ? chartData.selected_key
    : datasetKeys[0];

  const renderActive = () => {
    const activeDataset = chartData.datasets[activeKey];
    if (!activeDataset) return;

    buttons.forEach((button) => {
      button.classList.toggle('active', button.getAttribute('data-chart-key') === activeKey);
    });

    if (metaEl) metaEl.textContent = activeDataset.meta || '—';
    renderLineChart(containerId, activeDataset);
  };

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      activeKey = button.getAttribute('data-chart-key') || activeKey;
      renderActive();
    });
  });

  renderActive();
  return renderActive;
}

function initCharts() {
  const historyChart = parseJsonScript('history-chart-data');
  const forecastChart = parseJsonScript('forecast-chart-data');
  const renderers = [
    setupTabbedChart({ chartData: historyChart, containerId: 'chart-history', chartKey: 'history' }),
    setupTabbedChart({ chartData: forecastChart, containerId: 'chart-forecast', chartKey: 'forecast' }),
  ];

  const render = () => {
    renderers.forEach((renderChart) => renderChart());
  };

  let resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(render, 120);
  });

  render();
}

document.addEventListener('DOMContentLoaded', async () => {
  startClock();
  await initTelegramMiniApp();
  initThemeToggle();
  initBankSearchAndSort();
  initGoldSelector();
  initCharts();
});
