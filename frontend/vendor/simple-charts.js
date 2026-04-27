/**
 * simple-charts.js
 * Tiny local canvas bar chart helper for admin dashboards.
 */

function maxValue(values) {
  if (!Array.isArray(values) || values.length === 0) return 1;
  const max = Math.max(...values.map(v => Number(v) || 0));
  return max > 0 ? max : 1;
}

function niceStep(max) {
  if (max <= 10) return 2;
  if (max <= 50) return 10;
  if (max <= 200) return 25;
  if (max <= 1000) return 100;
  return Math.ceil(max / 6 / 100) * 100;
}

export function drawBarChart(canvas, labels, values, options = {}) {
  if (!canvas || !(canvas instanceof HTMLCanvasElement)) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const cssWidth = canvas.clientWidth || canvas.width;
  const cssHeight = canvas.clientHeight || canvas.height;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(cssWidth * dpr);
  canvas.height = Math.floor(cssHeight * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const width = cssWidth;
  const height = cssHeight;
  const padding = { top: 18, right: 12, bottom: 34, left: 56 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const max = maxValue(values);
  const step = niceStep(max);
  const roundedMax = Math.ceil(max / step) * step;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = options.background || 'transparent';
  if (options.background) ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = options.gridColor || 'rgba(255,255,255,0.12)';
  ctx.fillStyle = options.labelColor || 'rgba(255,255,255,0.7)';
  ctx.font = '12px ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';

  for (let yVal = 0; yVal <= roundedMax; yVal += step) {
    const y = padding.top + plotH - (yVal / roundedMax) * plotH;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    ctx.fillText(String(yVal), padding.left - 8, y);
  }

  const count = Math.max(1, values.length);
  const slotW = plotW / count;
  const barW = Math.max(6, slotW * 0.65);
  const barColor = options.barColor || '#3b82f6';

  for (let i = 0; i < count; i += 1) {
    const value = Number(values[i]) || 0;
    const label = String(labels[i] || '');
    const h = (value / roundedMax) * plotH;
    const x = padding.left + i * slotW + (slotW - barW) / 2;
    const y = padding.top + plotH - h;

    ctx.fillStyle = barColor;
    ctx.fillRect(x, y, barW, h);

    if (count <= 14 || i % 2 === 0) {
      ctx.save();
      ctx.translate(x + barW / 2, height - 5);
      ctx.rotate(-Math.PI / 6);
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = options.labelColor || 'rgba(255,255,255,0.75)';
      ctx.fillText(label, 0, 0);
      ctx.restore();
    }
  }

  if (options.title) {
    ctx.fillStyle = options.titleColor || 'rgba(255,255,255,0.9)';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.font = '600 13px ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif';
    ctx.fillText(options.title, padding.left, 2);
  }
}
