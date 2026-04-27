import { drawBarChart } from '/vendor/simple-charts.js';

const feedbackEl = document.getElementById('stats-feedback');
const summaryEl = document.getElementById('stats-summary');
const rangeEl = document.getElementById('stats-range-days');
const refreshBtn = document.getElementById('refresh-stats-btn');
const timelineCanvas = document.getElementById('stats-timeline-chart');
const connectorCanvas = document.getElementById('stats-connector-chart');
const connectorsTableWrap = document.getElementById('stats-connectors-table-wrap');
const conversationsTableWrap = document.getElementById('stats-conversations-table-wrap');

let showToastFn = () => {};

async function apiFetch(path) {
  const res = await fetch(path);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body && body.detail) detail = body.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

export function initStatistics({ showToast }) {
  showToastFn = showToast;
  refreshBtn.addEventListener('click', refresh);
  rangeEl.addEventListener('change', refresh);
  window.addEventListener('resize', redrawCharts);
  return { refresh };
}

let latestPayload = null;

async function refresh() {
  feedbackEl.innerHTML = '';
  summaryEl.innerHTML = '<div class="loading-row">Loading…</div>';
  connectorsTableWrap.innerHTML = '';
  conversationsTableWrap.innerHTML = '';

  const days = parseInt(rangeEl.value, 10) || 14;
  try {
    const payload = await apiFetch(`/api/statistics/?days=${days}&top=15`);
    latestPayload = payload;
    renderSummary(payload.summary || {});
    renderTables(payload);
    redrawCharts();
  } catch (err) {
    latestPayload = null;
    summaryEl.innerHTML = '';
    feedbackEl.innerHTML = `<div class="error-banner">Cannot load statistics: ${escHtml(err.message)}</div>`;
    showToastFn('Failed to load statistics.', true);
  }
}

function redrawCharts() {
  if (!latestPayload) return;
  renderTimelineChart(latestPayload.timeline || []);
  renderConnectorChart(latestPayload.by_connector || []);
}

function renderSummary(summary) {
  const cards = [
    { label: 'Messages', value: formatInt(summary.total_messages) },
    { label: 'Conversations', value: formatInt(summary.total_conversations) },
    { label: 'LLM Calls', value: formatInt(summary.llm_calls) },
    { label: 'Success Rate', value: `${Number(summary.success_rate || 0).toFixed(1)}%` },
    { label: 'Tokens In', value: formatInt(summary.tokens_in) },
    { label: 'Tokens Out', value: formatInt(summary.tokens_out) },
    { label: 'Total Tokens', value: formatInt(summary.total_tokens) },
    { label: 'Avg Latency', value: `${Number(summary.avg_latency_ms || 0).toFixed(1)} ms` },
  ];
  summaryEl.innerHTML = cards
    .map(card => `
      <article class="stats-card">
        <div class="stats-card-label">${escHtml(card.label)}</div>
        <div class="stats-card-value">${escHtml(card.value)}</div>
      </article>
    `)
    .join('');
}

function renderTimelineChart(timeline) {
  const labels = timeline.map(row => String(row.date || '').slice(5));
  const values = timeline.map(row => (Number(row.tokens_in || 0) + Number(row.tokens_out || 0)));
  drawBarChart(timelineCanvas, labels, values, {
    title: 'Tokens per day',
    barColor: '#50e3c2',
    labelColor: 'rgba(240,245,255,0.75)',
    gridColor: 'rgba(240,245,255,0.11)',
  });
}

function renderConnectorChart(byConnector) {
  const top = byConnector.slice(0, 8);
  const labels = top.map(row => (row.name || row.backend || '(unknown)').slice(0, 14));
  const values = top.map(row => Number(row.total_tokens || 0));
  drawBarChart(connectorCanvas, labels, values, {
    title: 'Top connector token usage',
    barColor: '#ffb347',
    labelColor: 'rgba(240,245,255,0.75)',
    gridColor: 'rgba(240,245,255,0.11)',
  });
}

function renderTables(payload) {
  connectorsTableWrap.innerHTML = renderTable(
    ['Connector', 'Backend', 'Calls', 'Success', 'Failed', 'Tokens In', 'Tokens Out', 'Avg Latency'],
    (payload.by_connector || []).map(row => [
      row.name || '(unknown)',
      row.backend || '(unknown)',
      formatInt(row.llm_calls),
      formatInt(row.success),
      formatInt(row.failed),
      formatInt(row.tokens_in),
      formatInt(row.tokens_out),
      `${Number(row.avg_latency_ms || 0).toFixed(1)} ms`,
    ]),
    'No connector usage recorded yet.'
  );

  conversationsTableWrap.innerHTML = renderTable(
    ['Conversation', 'Messages', 'LLM Calls', 'Tokens In', 'Tokens Out', 'Total', 'Avg Latency'],
    (payload.by_conversation || []).map(row => [
      row.title || row.conversation_id,
      formatInt(row.message_count),
      formatInt(row.llm_calls),
      formatInt(row.tokens_in),
      formatInt(row.tokens_out),
      formatInt(row.total_tokens),
      `${Number(row.avg_latency_ms || 0).toFixed(1)} ms`,
    ]),
    'No conversation usage recorded yet.'
  );
}

function renderTable(headers, rows, emptyMessage) {
  if (!rows.length) {
    return `<div class="loading-row">${escHtml(emptyMessage)}</div>`;
  }

  const thead = `<thead><tr>${headers.map(h => `<th>${escHtml(h)}</th>`).join('')}</tr></thead>`;
  const tbody = `<tbody>${rows
    .map(cols => `<tr>${cols.map(c => `<td>${escHtml(c)}</td>`).join('')}</tr>`)
    .join('')}</tbody>`;

  return `<div class="stats-table-wrap"><table class="stats-table">${thead}${tbody}</table></div>`;
}

function formatInt(value) {
  const n = Number(value || 0);
  return n.toLocaleString('en-US');
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
