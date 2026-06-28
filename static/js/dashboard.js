/* ══════════════════════════════════════════════════════════════════════════
   Netflix Analytics Pro — dashboard.js
   ══════════════════════════════════════════════════════════════════════════ */

/* ── Chart.js defaults ─────────────────────────────────────────────────── */
Chart.defaults.color          = '#9999b0';
Chart.defaults.borderColor    = '#2a2a38';
Chart.defaults.font.family    = "'Segoe UI', system-ui, sans-serif";
Chart.defaults.font.size      = 12;
Chart.defaults.animation.duration = 500;

/* ── Palette ─────────────────────────────────────────────────────────────── */
const P = {
  red:    '#e50914', red2:  '#ff2c3b',
  gold:   '#f5c518', green: '#46d369',
  blue:   '#3b9ef8', purple:'#a855f7',
  teal:   '#2dd4bf', orange:'#fb923c',
  pink:   '#f472b6', lime:  '#a3e635',
};
const PALETTE = [P.red, P.blue, P.gold, P.green, P.purple, P.teal, P.orange, P.pink, P.lime, '#60a5fa'];

const alpha = (hex, a) => hex + Math.round(a * 255).toString(16).padStart(2,'0');

/* ── State ──────────────────────────────────────────────────────────────── */
let country = 'All';
let charts  = {};
let growthMode = 'count';
let roiMode    = 'genre';
let sortKey    = 'popularity';
let engMetric  = 'views';
let titlesData = [];
let allTitles  = [];  // for search

/* ── DOM ────────────────────────────────────────────────────────────────── */
const $  = id => document.getElementById(id);
const countrySelect  = $('countrySelect');
const loadSpinner    = $('loadSpinner');
const titleSearch    = $('titleSearch');
const searchDropdown = $('searchDropdown');
const marketLabel    = $('marketLabel');

/* ── Sidebar toggle ─────────────────────────────────────────────────────── */
const sidebar   = document.getElementById('sidebar');
const hamburger = $('hamburger');
hamburger?.addEventListener('click', () => sidebar.classList.toggle('open'));

/* ── Active nav on scroll ───────────────────────────────────────────────── */
const sections = document.querySelectorAll('.page-section');
const navItems = document.querySelectorAll('.nav-item');
const observer = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      const id = e.target.id.replace('section-', '');
      navItems.forEach(n => n.classList.toggle('active', n.dataset.section === id));
    }
  });
}, { threshold: 0.3 });
sections.forEach(s => observer.observe(s));

/* ── Helpers ────────────────────────────────────────────────────────────── */
function showLoad(v) { loadSpinner.classList.toggle('hidden', !v); }

function api(url) {
  const sep = url.includes('?') ? '&' : '?';
  return fetch(`${url}${sep}country=${encodeURIComponent(country)}`).then(r => {
    if (!r.ok) throw new Error(`${url} → ${r.status}`);
    return r.json();
  });
}
function apiPlain(url) {
  return fetch(url).then(r => {
    if (!r.ok) throw new Error(`${url} → ${r.status}`);
    return r.json();
  });
}

function fmtM(n) {
  if (!n) return '$0';
  const v = Math.abs(n);
  const s = n < 0 ? '-' : '';
  if (v >= 1e9) return `${s}$${(v/1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${s}$${(v/1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${s}$${(v/1e3).toFixed(0)}K`;
  return `${s}$${v.toFixed(0)}`;
}
function fmtN(n)  { return n?.toLocaleString() ?? '—'; }
function fmtRoi(r){ return r == null ? '—' : `${r > 0 ? '+' : ''}${r.toFixed(1)}%`; }
function fmtCompact(n) {
  if (n == null) return '—';
  if (n >= 1000) return `${(n/1000).toFixed(1)}B`;
  return `${n.toFixed(1)}M`;
}

function kill(id) { if (charts[id]) { charts[id].destroy(); delete charts[id]; } }

function gradV(ctx, c1, c2) {
  const g = ctx.createLinearGradient(0, 0, 0, ctx.canvas.clientHeight || 300);
  g.addColorStop(0, c1); g.addColorStop(1, c2);
  return g;
}

/* ── Country change ─────────────────────────────────────────────────────── */
countrySelect.addEventListener('change', () => {
  country = countrySelect.value;
  marketLabel.textContent = country === 'All' ? 'All Countries' : country;
  updateExportLinks();
  updateAll();
});

function updateExportLinks() {
  $('exportPdfBtn').href   = `/api/export/pdf?country=${encodeURIComponent(country)}`;
  $('exportExcelBtn').href = `/api/export/excel?country=${encodeURIComponent(country)}`;
  $('exportScopeLabel').textContent = `Scope: ${country === 'All' ? 'All Countries' : country}`;
}

/* ── Growth tabs ────────────────────────────────────────────────────────── */
document.getElementById('growthTabs')?.addEventListener('click', e => {
  const btn = e.target.closest('.stab');
  if (!btn) return;
  growthMode = btn.dataset.mode;
  document.querySelectorAll('#growthTabs .stab').forEach(b => b.classList.toggle('active', b === btn));
  if (charts._growthData) drawGrowth(charts._growthData);
});

/* ── ROI tabs ───────────────────────────────────────────────────────────── */
document.getElementById('roiTabs')?.addEventListener('click', e => {
  const btn = e.target.closest('.stab');
  if (!btn) return;
  roiMode = btn.dataset.mode;
  document.querySelectorAll('#roiTabs .stab').forEach(b => b.classList.toggle('active', b === btn));
  updateRoiChart();
});

/* ── Engagement top tabs ────────────────────────────────────────────────── */
document.getElementById('engTopTabs')?.addEventListener('click', e => {
  const btn = e.target.closest('.stab');
  if (!btn) return;
  engMetric = btn.dataset.metric;
  document.querySelectorAll('#engTopTabs .stab').forEach(b => b.classList.toggle('active', b === btn));
  loadEngagementTop();
});

/* ── Table sort ─────────────────────────────────────────────────────────── */
$('tableSortSelect')?.addEventListener('change', e => {
  sortKey = e.target.value;
  if (titlesData.length) renderTable(titlesData);
});

/* ══════════════════════════════════════════════════════════════════════════
   CHART DRAW FUNCTIONS — Movie Market (existing)
═══════════════════════════════════════════════════════════════════════════ */

/* ── KPIs ────────────────────────────────────────────────────────────────── */
function renderKpis(d) {
  $('kv-total').textContent   = fmtN(d.total);
  $('kv-rating').textContent  = d.avg_rating?.toFixed(1) ?? '—';
  $('kv-budget').textContent  = fmtM(d.avg_budget);
  $('kv-revenue').textContent = fmtM(d.avg_revenue);
  $('kv-roi').textContent     = fmtRoi(d.roi);
  $('kv-lang').textContent    = d.top_language ?? '—';

  $('ks-budget').textContent  = `Total: ${fmtM(d.total_budget)}`;
  $('ks-revenue').textContent = `Total: ${fmtM(d.total_revenue)}`;
  $('ks-roi').textContent     = d.roi > 0 ? '✅ Profitable' : d.roi < 0 ? '⚠️ Loss-making' : '';
  $('ks-lang').textContent    = `Primary market language`;

  if (d.yoy_growth != null) {
    const arrow = d.yoy_growth > 0 ? '↑' : '↓';
    $('ks-total').textContent = `${arrow} ${Math.abs(d.yoy_growth)}% YoY`;
    $('ks-total').style.color = d.yoy_growth > 0 ? '#46d369' : '#e50914';
  }

  const roi = $('kv-roi');
  roi.style.color = d.roi > 0 ? '#46d369' : d.roi < 0 ? '#e50914' : '';

  const rPct = Math.min(100, Math.max(0, ((d.avg_rating - 4) / 6) * 100));
  $('kb-rating').style.width = rPct + '%';
}

/* ── Growth ─────────────────────────────────────────────────────────────── */
function drawGrowth(d) {
  charts._growthData = d;
  kill('growth');
  const ctx  = $('growthChart').getContext('2d');
  const isRating = growthMode === 'rating';
  const yData = isRating ? d.avg_ratings : d.counts;
  const label = isRating ? 'Avg Rating' : 'Titles Released';

  const grad = gradV(ctx, alpha(P.red, 0.35), alpha(P.red, 0.02));

  charts.growth = new Chart(ctx, {
    type: 'line',
    data: {
      labels: d.years,
      datasets: [
        {
          label,
          data: yData,
          borderColor: P.red,
          backgroundColor: grad,
          borderWidth: 2.5,
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: P.red,
        },
        ...(!isRating ? [{
          label: '3-Year Rolling Avg',
          data: d.rolling,
          borderColor: P.gold,
          borderWidth: 1.5,
          borderDash: [5,4],
          tension: 0.4,
          fill: false,
          pointRadius: 0,
        }] : []),
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index' },
      plugins: {
        legend: { labels: { boxWidth: 12, padding: 14 } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(isRating?2:0)}`,
          }
        }
      },
      scales: {
        x: { grid: { color: '#1c1c26' }, ticks: { maxTicksLimit: 12 } },
        y: { grid: { color: '#1c1c26' }, beginAtZero: false },
      }
    }
  });

  const total = d.counts.reduce((a,b)=>a+b,0);
  const peak  = d.years[d.counts.indexOf(Math.max(...d.counts))];
  $('growthMeta').textContent = `${fmtN(total)} total titles · peak year: ${peak}`;
}

/* ── Genres volume ──────────────────────────────────────────────────────── */
function drawGenres(d) {
  kill('genres');
  const ctx = $('genresChart').getContext('2d');
  charts.genres = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.genres,
      datasets: [{
        label: 'Titles',
        data: d.counts,
        backgroundColor: PALETTE.map(c => alpha(c, 0.75)),
        borderColor: PALETTE,
        borderWidth: 1.5,
        borderRadius: 5,
        borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#1c1c26' }, beginAtZero: true },
        y: { grid: { display: false } },
      }
    }
  });
}

/* ── Genre rating bar ────────────────────────────────────────────────────── */
function drawGenreRating(d) {
  kill('genreRating');
  const ctx = $('genreRatingChart').getContext('2d');
  charts.genreRating = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.genres,
      datasets: [{
        label: 'Avg Rating',
        data: d.avg_ratings,
        backgroundColor: d.avg_ratings.map(r => {
          if (r >= 7) return alpha(P.green,  0.75);
          if (r >= 6) return alpha(P.gold,   0.75);
          return alpha(P.red, 0.6);
        }),
        borderRadius: 5,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: c => ` Rating: ${c.parsed.y?.toFixed(2)}/10` } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 35 } },
        y: { grid: { color: '#1c1c26' }, min: 4, max: 8,
             title: { display: true, text: 'Rating /10', color: '#9999b0' } },
      }
    }
  });
}

/* ── ROI chart (genre or language) ─────────────────────────────────────── */
function drawRoiChart(d, labelKey) {
  kill('roi');
  const ctx = $('roiChart').getContext('2d');
  const labels = d[labelKey] ?? d.genres ?? d.languages;
  const rois   = d.roi;
  charts.roi = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Avg ROI %',
        data: rois,
        backgroundColor: rois.map(v => alpha(v >= 0 ? P.green : P.red, 0.7)),
        borderColor:      rois.map(v => v >= 0 ? P.green : P.red),
        borderWidth: 1.5,
        borderRadius: 5,
        borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: c => ` ROI: ${fmtRoi(c.parsed.x)}  (${d.counts?.[c.dataIndex]} titles)`,
          }
        }
      },
      scales: {
        x: { grid: { color: '#1c1c26' },
             title: { display: true, text: 'ROI %', color: '#9999b0' } },
        y: { grid: { display: false } },
      }
    }
  });
}

/* ── Yearly trend (combo) ────────────────────────────────────────────────── */
function drawYearly(d) {
  kill('yearly');
  const ctx = $('yearlyChart').getContext('2d');
  charts.yearly = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.years,
      datasets: [
        {
          type: 'bar',
          label: 'Avg Budget ($M)',
          data: d.avg_budgets,
          backgroundColor: alpha(P.red, 0.65),
          borderRadius: 4, yAxisID: 'y',
        },
        {
          type: 'line',
          label: 'Avg Revenue ($M)',
          data: d.avg_revenues,
          borderColor: P.gold,
          backgroundColor: alpha(P.gold, 0.12),
          borderWidth: 2.5,
          tension: 0.35,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: P.gold,
          yAxisID: 'y',
        },
        ...(d.regression ? [{
          type: 'line',
          label: `Revenue Trend (R²=${d.regression.r_squared})`,
          data: d.regression.x.map((x,i) => ({ x, y: d.regression.y_pred[i] })),
          borderColor: alpha(P.teal, 0.7),
          borderWidth: 1.5,
          borderDash: [6,4],
          pointRadius: 0,
          tension: 0,
          yAxisID: 'y',
        }] : []),
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index' },
      plugins: { legend: { labels: { boxWidth: 12, padding: 12, font: { size: 11 } } } },
      scales: {
        x: { grid: { color: '#1c1c26' }, ticks: { maxTicksLimit: 12 } },
        y: { grid: { color: '#1c1c26' }, beginAtZero: true,
             title: { display: true, text: 'Million USD', color: '#9999b0' } },
      }
    }
  });

  if (d.regression)
    $('yearlyMeta').textContent = `Revenue trend R² = ${d.regression.r_squared} · slope $${d.regression.slope.toFixed(2)}M/yr`;
}

/* ── Correlation heatmap (manual canvas) ────────────────────────────────── */
function drawCorrelation(d) {
  kill('corr');
  const canvas = $('corrChart');
  const ctx    = canvas.getContext('2d');
  const n      = d.labels.length;

  charts.corr = new Chart(ctx, {
    type: 'scatter',
    data: { datasets: [] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { display: false }, y: { display: false } },
      animation: { onComplete: () => _drawHeatmap(ctx, canvas, d, n) },
    }
  });
  setTimeout(() => _drawHeatmap(ctx, canvas, d, n), 100);
}

function _drawHeatmap(ctx, canvas, d, n) {
  const W = canvas.width, H = canvas.height;
  const pad = 70, cellW = (W - pad*2) / n, cellH = (H - pad*2) / n;
  ctx.clearRect(0, 0, W, H);

  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const v   = d.matrix[i][j] ?? 0;
      const x   = pad + j * cellW, y = pad + i * cellH;
      const t   = (v + 1) / 2;
      const r   = Math.round(229 * (1 - t) + 59  * t);
      const g   = Math.round(9   * (1 - t) + 158 * t);
      const b   = Math.round(20  * (1 - t) + 248 * t);
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(x, y, cellW - 2, cellH - 2);

      ctx.fillStyle = '#eee';
      ctx.font = `bold ${Math.min(12, cellW * 0.35)}px Segoe UI`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(v?.toFixed(2) ?? '', x + cellW/2, y + cellH/2);
    }
  }
  ctx.fillStyle = '#9999b0'; ctx.font = '11px Segoe UI';
  d.labels.forEach((lbl, i) => {
    ctx.save();
    ctx.translate(pad + i * cellW + cellW/2, pad - 8);
    ctx.rotate(-Math.PI/4);
    ctx.textAlign = 'left';
    ctx.fillText(lbl, 0, 0);
    ctx.restore();
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(lbl, pad - 6, pad + i * cellH + cellH/2);
  });
}

/* ── Ratings distribution ───────────────────────────────────────────────── */
function drawRatings(d) {
  kill('ratings');
  const ctx = $('ratingsChart').getContext('2d');
  const grad = d.bins.map((_, i) => {
    const t = i / (d.bins.length - 1);
    return alpha(t > 0.5 ? P.green : P.red, 0.75);
  });
  charts.ratings = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.bins,
      datasets: [{ label: 'Titles', data: d.counts, backgroundColor: grad, borderRadius: 5, borderSkipped: false }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { grid: { display: false } }, y: { grid: { color: '#1c1c26' }, beginAtZero: true } }
    }
  });
}

/* ── Language doughnut ──────────────────────────────────────────────────── */
function drawLanguage(d) {
  kill('lang');
  const ctx = $('langChart').getContext('2d');
  charts.lang = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: d.languages,
      datasets: [{
        data: d.counts,
        backgroundColor: PALETTE.map(c => alpha(c, 0.85)),
        borderColor: '#16161e', borderWidth: 3, hoverOffset: 8,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '58%',
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
        tooltip: { callbacks: { label: c => {
          const total = c.dataset.data.reduce((a,b)=>a+b,0);
          const pct   = (c.parsed / total * 100).toFixed(1);
          return ` ${c.label}: ${fmtN(c.parsed)} (${pct}%)`;
        }}}
      }
    }
  });
}

/* ── Country bar ────────────────────────────────────────────────────────── */
function drawCountry(d) {
  kill('country');
  const ctx = $('countryChart').getContext('2d');
  const hilite = d.countries.map(c => c === country ? P.gold : alpha(P.blue, 0.65));
  charts.country = new Chart(ctx, {
    type: 'bar',
    data: { labels: d.countries, datasets: [{ label: 'Titles', data: d.counts, backgroundColor: hilite, borderRadius: 4, borderSkipped: false }] },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        label: c => ` ${fmtN(c.parsed.x)} titles  ·  ROI: ${fmtRoi(d.avg_roi?.[c.dataIndex])}`,
      }}},
      scales: { x: { grid: { color: '#1c1c26' }, beginAtZero: true }, y: { grid: { display: false }, ticks: { font: { size: 10 } } } }
    }
  });
}

/* ── Budget vs Revenue scatter ──────────────────────────────────────────── */
function drawScatter(d) {
  kill('scatter');
  const ctx = $('scatterChart').getContext('2d');
  const points = d.budgets.map((b, i) => ({
    x: b, y: d.revenues[i], title: d.titles[i], rating: d.ratings[i],
    profitable: d.profitable[i], lang: d.languages?.[i] ?? '',
  }));

  const datasets = [
    { label: 'Profitable', data: points.filter(p => p.profitable), backgroundColor: alpha(P.green, 0.6), borderColor: P.green, borderWidth: 1, pointRadius: 5, pointHoverRadius: 8 },
    { label: 'Loss-making', data: points.filter(p => !p.profitable), backgroundColor: alpha(P.red, 0.5), borderColor: P.red, borderWidth: 1, pointRadius: 5, pointHoverRadius: 8 },
  ];

  if (d.regression) {
    const regPts = d.regression.x.map((x,i) => ({ x, y: d.regression.y_pred[i] }));
    datasets.push({ label: `Regression (R²=${d.r_squared})`, data: regPts, type: 'line', borderColor: alpha(P.gold, 0.8), borderWidth: 2, borderDash: [6,4], pointRadius: 0, fill: false });
  }

  const maxVal = Math.max(...d.budgets, ...d.revenues);
  datasets.push({ label: 'Break-even', data: [{ x: 0, y: 0 }, { x: maxVal, y: maxVal }], type: 'line', borderColor: alpha(P.teal, 0.5), borderWidth: 1.5, borderDash: [3,3], pointRadius: 0, fill: false });

  charts.scatter = new Chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, padding: 14 } },
        tooltip: { callbacks: { label: c => {
          const p = c.raw;
          if (!p.title) return ` ${c.dataset.label}`;
          return [`📽  ${p.title}`, `Budget: $${p.x}M  ·  Revenue: $${p.y}M`, `Rating: ⭐ ${p.rating}  ·  Lang: ${p.lang}`];
        }}}
      },
      scales: {
        x: { grid: { color: '#1c1c26' }, title: { display: true, text: 'Budget ($M)', color: '#9999b0' } },
        y: { grid: { color: '#1c1c26' }, title: { display: true, text: 'Revenue ($M)', color: '#9999b0' } },
      }
    }
  });

  const profitable = points.filter(p => p.profitable).length;
  $('scatterMeta').textContent = `${fmtN(points.length)} sampled titles · ${profitable} profitable (${(profitable/points.length*100).toFixed(0)}%) · R² = ${d.r_squared ?? '—'}`;
}

/* ── Genre evolution stacked area ───────────────────────────────────────── */
function drawEvolution(d) {
  kill('evolution');
  if (!d.periods?.length) return;
  const ctx = $('evolutionChart').getContext('2d');
  charts.evolution = new Chart(ctx, {
    type: 'line',
    data: {
      labels: d.periods,
      datasets: d.genres.map((g, i) => ({
        label: g, data: d.matrix[i], borderColor: PALETTE[i % PALETTE.length],
        backgroundColor: alpha(PALETTE[i % PALETTE.length], 0.15), borderWidth: 2,
        tension: 0.4, fill: true, pointRadius: 4, pointHoverRadius: 7,
      }))
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index' },
      plugins: { legend: { labels: { boxWidth: 12, padding: 12 } }, tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${c.parsed.y?.toFixed(1)}%` } } },
      scales: { x: { grid: { color: '#1c1c26' } }, y: { grid: { color: '#1c1c26' }, beginAtZero: true, title: { display: true, text: 'Share %', color: '#9999b0' } } }
    }
  });
}

/* ── Statistical significance bar ───────────────────────────────────────── */
function renderStatTest(d) {
  const bar = $('statTestBar');
  if (!d || d.p_value == null) { bar.classList.remove('show'); return; }
  const sig = d.significant;
  const pTxt = d.p_value < 0.001 ? '< 0.001' : d.p_value;
  bar.innerHTML = `
    <span class="stat-pill ${sig ? 'sig' : 'nosig'}">${sig ? 'Statistically Significant' : 'Not Significant'}</span>
    <span>One-way ANOVA across top ${d.n_genres_tested} genres by ROI: <b>F = ${d.f_stat}</b>, <b>p ${pTxt}</b> —
    ${sig ? 'genre really does drive ROI differences.' : 'observed ROI gaps could be sampling noise.'}</span>`;
  bar.classList.add('show');
}

/* ── Insights ────────────────────────────────────────────────────────────── */
function renderInsights(list, targetId = 'insightsGrid') {
  const grid = $(targetId);
  if (!list?.length) {
    grid.innerHTML = '<p style="color:var(--text2);padding:1rem">No insights available for this selection.</p>';
    return;
  }
  grid.innerHTML = list.map(ins => `
    <div class="insight-card ${ins.sentiment}">
      <div class="ic-icon">${ins.icon}</div>
      <div>
        <div class="ic-title">${ins.title}</div>
        <div class="ic-body">${ins.body}</div>
      </div>
      <div class="ic-type-tag">${ins.type}</div>
    </div>
  `).join('');
}

/* ── Table ───────────────────────────────────────────────────────────────── */
function renderTable(data) {
  titlesData = data;
  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey] ?? -Infinity;
    const bv = b[sortKey] ?? -Infinity;
    return bv - av;
  });
  $('tableBody').innerHTML = sorted.map((r, i) => {
    const rc    = i === 0 ? 'r1' : i === 1 ? 'r2' : i === 2 ? 'r3' : 'rn';
    const bw    = Math.round(Math.min(100, (r.vote_average / 10) * 80));
    const tags  = (r.genres || '').split(',').slice(0,3).map(g => `<span class="tag">${g.trim()}</span>`).join('');
    const roiCls = r.roi > 0 ? 'roi-pos' : r.roi < 0 ? 'roi-neg' : '';
    return `<tr>
      <td><span class="rank ${rc}">${i+1}</span></td>
      <td style="font-weight:600;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.title ?? '—'}</td>
      <td>${r.release_year ?? '—'}</td>
      <td><div class="rating-pill"><div class="rating-fill" style="width:${bw}px"></div>${r.vote_average}</div></td>
      <td>${r.popularity}</td>
      <td>$${r.budget}</td>
      <td>$${r.revenue}</td>
      <td class="${roiCls}">${fmtRoi(r.roi)}</td>
      <td><span class="tag lang-tag">${r.language ?? '—'}</span></td>
      <td>${tags}</td>
    </tr>`;
  }).join('');
}

/* ══════════════════════════════════════════════════════════════════════════
   NEW — FORECAST
═══════════════════════════════════════════════════════════════════════════ */
function _forecastDatasets(d, color, label) {
  const lastActualIdx = d.years.length - 1;
  const bridge = [{ x: d.years[lastActualIdx], y: d.actual[lastActualIdx] }, ...d.forecast_years.map((y,i) => ({ x: y, y: d.forecast[i] }))];
  const upperBridge = [{ x: d.years[lastActualIdx], y: d.actual[lastActualIdx] }, ...d.forecast_years.map((y,i) => ({ x: y, y: d.upper[i] }))];
  const lowerBridge = [{ x: d.years[lastActualIdx], y: d.actual[lastActualIdx] }, ...d.forecast_years.map((y,i) => ({ x: y, y: d.lower[i] }))];
  return [
    { label, data: d.years.map((y,i) => ({x:y, y:d.actual[i]})), borderColor: color, backgroundColor: alpha(color,0.08), borderWidth: 2.5, tension: 0.3, pointRadius: 3, fill: false },
    { label: 'Forecast', data: bridge, borderColor: P.gold, borderWidth: 2.5, borderDash: [6,4], tension: 0, pointRadius: 4, pointBackgroundColor: P.gold, fill: false },
    { label: 'Upper (80%)', data: upperBridge, borderColor: alpha(P.gold,0.25), borderWidth: 1, pointRadius: 0, fill: '+1', backgroundColor: alpha(P.gold,0.1), tension: 0 },
    { label: 'Lower (80%)', data: lowerBridge, borderColor: alpha(P.gold,0.25), borderWidth: 1, pointRadius: 0, fill: false, tension: 0 },
  ];
}

function drawForecastVolume(d) {
  kill('forecastVol');
  if (!d.years?.length) { $('forecastVolMeta').textContent = 'Not enough history to forecast.'; return; }
  const ctx = $('forecastVolChart').getContext('2d');
  charts.forecastVol = new Chart(ctx, {
    type: 'line',
    data: { datasets: _forecastDatasets(d, P.red, 'Titles Released') },
    options: {
      responsive: true, maintainAspectRatio: false,
      parsing: false,
      plugins: { legend: { labels: { boxWidth: 10, font: { size: 10 } }, filter: it => !['Upper (80%)','Lower (80%)'].includes(it.text) } },
      scales: { x: { type: 'linear', grid: { color: '#1c1c26' }, ticks: { stepSize: 1 } }, y: { grid: { color: '#1c1c26' }, beginAtZero: true } }
    }
  });
  if (d.slope_per_year != null) {
    const dir = d.slope_per_year >= 0 ? 'growing' : 'declining';
    $('forecastVolMeta').textContent = `Trend: ${dir} ~${Math.abs(d.slope_per_year)} titles/yr · ${d.forecast_years[d.forecast_years.length-1]} forecast: ${fmtN(Math.round(d.forecast[d.forecast.length-1]))} titles`;
  }
}

function drawForecastRevenue(d) {
  kill('forecastRev');
  if (!d.years?.length) { $('forecastRevMeta').textContent = 'Not enough history to forecast.'; return; }
  const ctx = $('forecastRevChart').getContext('2d');
  charts.forecastRev = new Chart(ctx, {
    type: 'line',
    data: { datasets: _forecastDatasets(d, P.blue, 'Avg Revenue ($M)') },
    options: {
      responsive: true, maintainAspectRatio: false,
      parsing: false,
      plugins: { legend: { labels: { boxWidth: 10, font: { size: 10 } }, filter: it => !['Upper (80%)','Lower (80%)'].includes(it.text) } },
      scales: { x: { type: 'linear', grid: { color: '#1c1c26' }, ticks: { stepSize: 1 } }, y: { grid: { color: '#1c1c26' }, beginAtZero: true, title: { display:true, text:'$M', color:'#9999b0' } } }
    }
  });
  if (d.slope_per_year != null) {
    const dir = d.slope_per_year >= 0 ? 'rising' : 'falling';
    $('forecastRevMeta').textContent = `Trend: ${dir} ~$${Math.abs(d.slope_per_year).toFixed(2)}M/yr · ${d.forecast_years[d.forecast_years.length-1]} forecast: $${d.forecast[d.forecast.length-1].toFixed(1)}M`;
  }
}

async function loadForecasts() {
  const [vol, rev] = await Promise.all([
    api('/api/forecast/volume').catch(() => null),
    api('/api/forecast/revenue').catch(() => null),
  ]);
  if (vol) drawForecastVolume(vol);
  if (rev) drawForecastRevenue(rev);
}

/* ══════════════════════════════════════════════════════════════════════════
   NEW — REAL NETFLIX ENGAGEMENT
═══════════════════════════════════════════════════════════════════════════ */
function renderEngagementKpis(d) {
  const grid = $('engKpiGrid');
  const breakdown = d.content_type_breakdown || {};
  grid.innerHTML = `
    <div class="kpi-card accent-gold">
      <div class="kpi-icon-wrap"><span>👑</span></div>
      <div class="kpi-body">
        <div class="kpi-val">${fmtN(d.total_titles)}</div>
        <div class="kpi-lbl">Titles Tracked</div>
        <div class="kpi-sub">Across 6 official reports</div>
      </div>
    </div>
    <div class="kpi-card accent-red">
      <div class="kpi-icon-wrap"><span>⏱️</span></div>
      <div class="kpi-body">
        <div class="kpi-val">${fmtCompact(d.sum_hours_viewed_millions)}</div>
        <div class="kpi-lbl">Hours Viewed</div>
        <div class="kpi-sub">${d.titles_with_hours} titles reported hours</div>
      </div>
    </div>
    <div class="kpi-card accent-blue">
      <div class="kpi-icon-wrap"><span>👁️</span></div>
      <div class="kpi-body">
        <div class="kpi-val">${fmtCompact(d.sum_views_millions)}</div>
        <div class="kpi-lbl">Views</div>
        <div class="kpi-sub">${d.titles_with_views} titles reported views</div>
      </div>
    </div>
    <div class="kpi-card accent-green">
      <div class="kpi-icon-wrap"><span>📺</span></div>
      <div class="kpi-body">
        <div class="kpi-val">${breakdown['TV Show'] ?? 0}:${breakdown['Movie'] ?? 0}</div>
        <div class="kpi-lbl">TV : Movie Mix</div>
        <div class="kpi-sub">Top genre: ${d.top_genre_by_views ?? '—'}</div>
      </div>
    </div>`;
}

function renderEngagementTop(d) {
  const list = $('engTopList');
  if (!d.titles?.length) { list.innerHTML = '<div class="rec-empty">No data for this metric.</div>'; return; }
  list.innerHTML = d.titles.map((t, i) => {
    const val = d.metric === 'hours' ? t.hours_viewed_millions : t.views_millions;
    const unit = d.metric === 'hours' ? 'M hrs' : 'M views';
    return `
    <div class="eng-row">
      <div class="eng-rank">${i+1}</div>
      <div class="eng-info">
        <div class="eng-title">${t.title}</div>
        <div class="eng-meta">
          <span class="tag">${t.content_type}</span>
          <span class="tag">${t.primary_genre}</span>
          <span class="tag lang-tag">${t.country_origin}</span>
          · ${t.report_period}
        </div>
      </div>
      <div class="eng-value">${val != null ? fmtCompact(val) : '—'}<small>${unit}</small></div>
    </div>`;
  }).join('');
}

async function loadEngagementTop() {
  const d = await apiPlain(`/api/engagement/top?metric=${engMetric}&limit=15`).catch(() => null);
  if (d) renderEngagementTop(d);
}

function drawEngagementGenre(d) {
  kill('engGenre');
  const ctx = $('engGenreChart').getContext('2d');
  charts.engGenre = new Chart(ctx, {
    type: 'bar',
    data: { labels: d.genres, datasets: [{ label: 'Total Views (M)', data: d.total_views, backgroundColor: PALETTE.map(c => alpha(c,0.75)), borderColor: PALETTE, borderWidth: 1.5, borderRadius: 5, borderSkipped: false }] },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${fmtCompact(c.parsed.x)} views · ${d.title_counts[c.dataIndex]} titles` } } },
      scales: { x: { grid: { color: '#1c1c26' }, beginAtZero: true }, y: { grid: { display: false } } }
    }
  });
}

function drawEngagementCountry(d) {
  kill('engCountry');
  const ctx = $('engCountryChart').getContext('2d');
  charts.engCountry = new Chart(ctx, {
    type: 'bar',
    data: { labels: d.countries, datasets: [{ label: 'Total Views (M)', data: d.total_views, backgroundColor: alpha(P.teal,0.7), borderColor: P.teal, borderWidth: 1.5, borderRadius: 4, borderSkipped: false }] },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ` ${fmtCompact(c.parsed.x)} views · ${d.title_counts[c.dataIndex]} titles` } } },
      scales: { x: { grid: { color: '#1c1c26' }, beginAtZero: true }, y: { grid: { display: false }, ticks: { font: { size: 10 } } } }
    }
  });
}

function drawEngagementTrend(d) {
  kill('engTrend');
  const ctx = $('engTrendChart').getContext('2d');
  charts.engTrend = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: d.periods,
      datasets: [
        { type: 'bar', label: 'Total Views (M)', data: d.total_views, backgroundColor: alpha(P.blue, 0.65), borderRadius: 4, yAxisID: 'y' },
        { type: 'bar', label: 'Total Hours (M)', data: d.total_hours, backgroundColor: alpha(P.red, 0.65), borderRadius: 4, yAxisID: 'y' },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index' },
      plugins: { legend: { labels: { boxWidth: 12, padding: 12, font: { size: 11 } } },
        tooltip: { callbacks: { afterBody: items => {
          const idx = items[0].dataIndex;
          return [`Titles tracked: ${d.title_counts[idx]} (${d.movie_counts[idx]} movies, ${d.tv_counts[idx]} TV)`];
        }}}
      },
      scales: { x: { grid: { color: '#1c1c26' } }, y: { grid: { color: '#1c1c26' }, beginAtZero: true, title: { display: true, text: 'Millions', color: '#9999b0' } } }
    }
  });
}

async function loadEngagementSection() {
  const [kpis, genre, ctry, trend, insights] = await Promise.all([
    apiPlain('/api/engagement/kpis').catch(() => null),
    apiPlain('/api/engagement/by-genre').catch(() => null),
    apiPlain('/api/engagement/by-country').catch(() => null),
    apiPlain('/api/engagement/trend').catch(() => null),
    apiPlain('/api/engagement/insights').catch(() => null),
  ]);
  if (kpis) renderEngagementKpis(kpis);
  if (genre) drawEngagementGenre(genre);
  if (ctry) drawEngagementCountry(ctry);
  if (trend) drawEngagementTrend(trend);
  if (insights) renderInsights(insights.insights, 'engInsightsGrid');
  await loadEngagementTop();
}

/* ══════════════════════════════════════════════════════════════════════════
   NEW — RECOMMENDER
═══════════════════════════════════════════════════════════════════════════ */
function renderRecommendations(d) {
  const box = $('recResults');
  if (!d.found) {
    box.innerHTML = `<div class="rec-empty">No close match for "<b>${d.query}</b>" — try another title.</div>`;
    return;
  }
  const matchedNote = d.matched_title.toLowerCase() !== d.query.toLowerCase()
    ? ` (matched to <b>${d.matched_title}</b>, ${d.matched_year})` : ` (${d.matched_year})`;
  const tiles = d.results.map(r => `
    <div class="rec-tile">
      <div class="rec-tile-title">${r.title}</div>
      <div class="rec-tile-meta">${r.release_year} · ⭐ ${r.vote_average} · ${(r.genres||'').split(',').slice(0,2).join(', ')}</div>
      <div class="rec-sim-bar-wrap"><div class="rec-sim-bar" style="width:${(r.similarity*100).toFixed(0)}%"></div></div>
      <div class="rec-sim-label">${(r.similarity*100).toFixed(0)}% match</div>
    </div>`).join('');
  box.innerHTML = `<div class="rec-matched">Because you searched <b>${d.query}</b>${matchedNote}:</div><div class="rec-grid">${tiles}</div>`;
}

async function runRecommend(title) {
  if (!title?.trim()) return;
  $('recResults').innerHTML = '<div class="rec-empty">Finding similar titles…</div>';
  const d = await apiPlain(`/api/recommend?title=${encodeURIComponent(title)}&n=8`).catch(() => null);
  if (d) renderRecommendations(d);
}

$('recButton')?.addEventListener('click', () => runRecommend($('recInput').value));
$('recInput')?.addEventListener('keydown', e => { if (e.key === 'Enter') runRecommend($('recInput').value); });

async function loadSeedChips() {
  const d = await apiPlain('/api/recommend/seed-titles?n=6').catch(() => null);
  if (!d?.titles?.length) return;
  $('seedChips').innerHTML = d.titles.map(t => `<span class="seed-chip">${t}</span>`).join('');
  document.querySelectorAll('.seed-chip').forEach(chip => {
    chip.addEventListener('click', () => { $('recInput').value = chip.textContent.replace('🎲 ',''); runRecommend(chip.textContent.replace('🎲 ','')); });
  });
}

/* ══════════════════════════════════════════════════════════════════════════
   SEARCH (global title search, movie market)
═══════════════════════════════════════════════════════════════════════════ */
let searchTimeout;
titleSearch.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  const q = titleSearch.value.trim();
  if (q.length < 2) { searchDropdown.classList.add('hidden'); return; }
  searchTimeout = setTimeout(() => doSearch(q), 280);
});
document.addEventListener('click', e => {
  if (!titleSearch.contains(e.target)) searchDropdown.classList.add('hidden');
});

async function doSearch(q) {
  const d = await apiPlain(`/api/search?q=${encodeURIComponent(q)}&limit=8`).catch(() => null);
  const matches = d?.results ?? [];
  if (!matches.length) { searchDropdown.classList.add('hidden'); return; }
  const hi = s => s.replace(new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), m => `<b>${m}</b>`);
  searchDropdown.innerHTML = matches.map(t => `
    <div class="sd-item">
      ${hi(t.title)}
      <span style="color:var(--text3);font-size:.72rem"> · ${t.release_year} · ⭐${t.vote_average?.toFixed?.(1) ?? t.vote_average}</span>
    </div>
  `).join('');
  searchDropdown.classList.remove('hidden');
}

/* ══════════════════════════════════════════════════════════════════════════
   ROI TAB SWITCH
═══════════════════════════════════════════════════════════════════════════ */
async function updateRoiChart() {
  const titleEl = $('roiChartTitle');
  if (roiMode === 'genre') {
    titleEl.textContent = 'ROI % by Genre';
    const d = await api('/api/roi-by-genre').catch(() => null);
    if (d) drawRoiChart(d, 'genres');
  } else {
    titleEl.textContent = 'ROI % by Language';
    const d = await api('/api/language-roi').catch(() => null);
    if (d) drawRoiChart(d, 'languages');
  }
}

/* ══════════════════════════════════════════════════════════════════════════
   MASTER UPDATE
═══════════════════════════════════════════════════════════════════════════ */
async function updateAll() {
  showLoad(true);
  const calls = [
    api('/api/kpis'),
    api('/api/growth'),
    api('/api/genres'),
    api('/api/ratings-distribution'),
    api('/api/yearly-trend'),
    api('/api/languages'),
    api('/api/budget-revenue-scatter'),
    api('/api/correlations'),
    api('/api/genre-evolution'),
    api('/api/insights'),
    api('/api/top-titles?limit=10'),
    apiPlain('/api/country-comparison'),
    api('/api/stats/genre-roi-significance'),
  ].map(p => p.catch(e => { console.warn(e); return null; }));

  const [kpis, growth, genres, ratings, yearly, langs, scatter,
         corr, evolution, insights, titles, cmpCountry, statTest] =
    await Promise.all(calls);

  if (kpis)       renderKpis(kpis);
  if (growth)     drawGrowth(growth);
  if (genres)     { drawGenres(genres); drawGenreRating(genres); }
  if (ratings)    drawRatings(ratings);
  if (yearly)     drawYearly(yearly);
  if (langs)      drawLanguage(langs);
  if (scatter)    drawScatter(scatter);
  if (corr)       drawCorrelation(corr);
  if (evolution)  drawEvolution(evolution);
  if (insights)   renderInsights(insights.insights);
  if (titles)     { renderTable(titles.titles); allTitles = titles.titles; }
  if (cmpCountry) drawCountry(cmpCountry);
  if (statTest)   renderStatTest(statTest);

  await updateRoiChart();
  await loadForecasts();

  showLoad(false);
}

/* ── Init ───────────────────────────────────────────────────────────────── */
updateExportLinks();
updateAll();
loadEngagementSection();
loadSeedChips();
