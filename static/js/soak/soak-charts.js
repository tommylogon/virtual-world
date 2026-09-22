/**
 * @module soak-charts — dependency-free SVG charts for the Soak Lab
 * @contributes line/area-band/bar/histogram/donut/sparkline renderers plus axis + scale helpers
 * @powers vitals-over-time, survival curve, death causes/times, growth curves, throughput sparkline
 * @relates used by soak-ui.js; consumes data shaped by soak-state.js
 * @docs none
 */
(function () {
    'use strict';

    const F = window.SoakFormat;
    let uidCounter = 0;
    const uid = (p) => `${p}-${++uidCounter}`;

    function esc(s) { return F.esc(s); }

    function extent(values) {
        let min = Infinity; let max = -Infinity;
        values.forEach((v) => {
            if (v === null || v === undefined || Number.isNaN(v)) return;
            if (v < min) min = v;
            if (v > max) max = v;
        });
        if (min === Infinity) return [0, 1];
        if (min === max) { min -= 1; max += 1; }
        return [min, max];
    }

    function niceTicks(min, max, count) {
        const target = Math.max(2, count || 5);
        if (min === max) return [min];
        const span = max - min;
        const step0 = span / target;
        const mag = Math.pow(10, Math.floor(Math.log10(step0)));
        const norm = step0 / mag;
        let step;
        if (norm < 1.5) step = 1 * mag;
        else if (norm < 3) step = 2 * mag;
        else if (norm < 7) step = 5 * mag;
        else step = 10 * mag;
        const start = Math.ceil(min / step) * step;
        const ticks = [];
        for (let v = start; v <= max + step * 1e-6; v += step) ticks.push(Number(v.toFixed(10)));
        return ticks.length ? ticks : [min, max];
    }

    function scaleFor(domain, range, logY) {
        const [d0, d1] = domain;
        const [r0, r1] = range;
        if (logY) {
            const la = Math.log10(Math.max(d0, 1e-6));
            const lb = Math.log10(Math.max(d1, 1e-6));
            const span = (lb - la) || 1;
            return (v) => r1 - ((Math.log10(Math.max(v, 1e-6)) - la) / span) * (r1 - r0);
        }
        const span = (d1 - d0) || 1;
        return (v) => r1 - ((v - d0) / span) * (r1 - r0);
    }

    function pointPath(points, sx, sy) {
        let d = '';
        let open = false;
        points.forEach((p) => {
            if (p[0] === null || p[1] === null || p[1] === undefined || Number.isNaN(p[1])) {
                open = false;
                return;
            }
            d += (open ? ' L ' : ' M ') + sx(p[0]).toFixed(2) + ' ' + sy(p[1]).toFixed(2);
            open = true;
        });
        return d;
    }

    function bandPath(area, sx, sy) {
        const lower = area.lower.filter((p) => p[1] !== null && p[1] !== undefined);
        const upper = area.upper.filter((p) => p[1] !== null && p[1] !== undefined);
        if (!lower.length || !upper.length) return '';
        let d = 'M ' + sx(upper[0][0]).toFixed(2) + ' ' + sy(upper[0][1]).toFixed(2);
        upper.slice(1).forEach((p) => { d += ' L ' + sx(p[0]).toFixed(2) + ' ' + sy(p[1]).toFixed(2); });
        for (let i = lower.length - 1; i >= 0; i -= 1) {
            d += ' L ' + sx(lower[i][0]).toFixed(2) + ' ' + sy(lower[i][1]).toFixed(2);
        }
        return d + ' Z';
    }

    function renderLineChart(opts) {
        const o = Object.assign({
            width: 720, height: 260,
            padding: { l: 52, r: 18, t: 16, b: 30 },
            series: [], xDomain: null, yDomain: null, logY: false,
            xTicks: 6, yTicks: 5, xFormat: (v) => String(v), yFormat: (v) => F.fmtNum(v, 1),
            yLabel: '', xLabel: '', emptyText: 'No data yet',
        }, opts || {});
        const W = o.width; const H = o.height;
        const pad = o.padding;
        const plotW = W - pad.l - pad.r;
        const plotH = H - pad.t - pad.b;

        const allX = []; const allY = [];
        o.series.forEach((s) => {
            (s.points || []).forEach((p) => { if (p[1] !== null && p[1] !== undefined) { allX.push(p[0]); allY.push(p[1]); } });
        });
        if (!allX.length) {
            return `<svg viewBox="0 0 ${W} ${H}" class="soak-chart" role="img">`
                + `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" class="soak-chart-empty">${esc(o.emptyText)}</text></svg>`;
        }
        const xDomain = o.xDomain || extent(allX);
        const yDomain = o.yDomain || extent(allY);
        const sx = scaleFor(xDomain, [pad.l + plotW, pad.l], false);
        const sy = scaleFor(yDomain, [pad.t, pad.t + plotH], o.logY);

        let svg = `<svg viewBox="0 0 ${W} ${H}" class="soak-chart" role="img" preserveAspectRatio="xMidYMid meet">`;
        const clipId = uid('clip');
        svg += `<defs><clipPath id="${clipId}"><rect x="${pad.l}" y="${pad.t}" width="${plotW}" height="${plotH}"/></clipPath></defs>`;

        const yTicks = niceTicks(Math.min(yDomain[0], yDomain[1]), Math.max(yDomain[0], yDomain[1]), o.yTicks);
        yTicks.forEach((t) => {
            const y = sy(t);
            if (y < pad.t - 1 || y > pad.t + plotH + 1) return;
            svg += `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${pad.l + plotW}" y2="${y.toFixed(1)}" class="soak-grid"/>`;
            svg += `<text x="${pad.l - 8}" y="${(y + 3.5).toFixed(1)}" text-anchor="end" class="soak-axis-label">${esc(o.yFormat(t))}</text>`;
        });
        const xTicks = niceTicks(Math.min(xDomain[0], xDomain[1]), Math.max(xDomain[0], xDomain[1]), o.xTicks);
        xTicks.forEach((t) => {
            const x = sx(t);
            if (x < pad.l - 1 || x > pad.l + plotW + 1) return;
            svg += `<line x1="${x.toFixed(1)}" y1="${pad.t}" x2="${x.toFixed(1)}" y2="${pad.t + plotH}" class="soak-grid soak-grid-x"/>`;
            svg += `<text x="${x.toFixed(1)}" y="${pad.t + plotH + 18}" text-anchor="middle" class="soak-axis-label">${esc(o.xFormat(t))}</text>`;
        });
        svg += `<rect x="${pad.l}" y="${pad.t}" width="${plotW}" height="${plotH}" class="soak-plot-frame"/>`;

        if (o.yLabel) {
            svg += `<text x="12" y="${pad.t + plotH / 2}" text-anchor="middle" class="soak-axis-title" transform="rotate(-90 12 ${pad.t + plotH / 2})">${esc(o.yLabel)}</text>`;
        }
        if (o.xLabel) {
            svg += `<text x="${pad.l + plotW / 2}" y="${H - 2}" text-anchor="middle" class="soak-axis-title">${esc(o.xLabel)}</text>`;
        }

        svg += `<g clip-path="url(#${clipId})">`;
        o.series.forEach((s) => {
            if (s.hidden) return;
            const color = s.color || F.PALETTE[0];
            if (s.area) {
                const d = bandPath(s.area, sx, sy);
                if (d) svg += `<path d="${d}" fill="${color}" opacity="0.12" stroke="none"/>`;
            }
            const d = pointPath(s.points || [], sx, sy);
            if (d) {
                svg += `<path d="${d}" fill="none" stroke="${color}" stroke-width="${s.width || 1.8}"`
                    + `${s.dash ? ` stroke-dasharray="${s.dash}"` : ''} stroke-linejoin="round" stroke-linecap="round"/>`;
            }
        });
        svg += '</g>';

        // Hover targets with native tooltips (bounded so big series stay snappy).
        const totalPoints = o.series.reduce((n, s) => n + (s.points || []).length, 0);
        if (totalPoints <= 1500) {
            svg += '<g>';
            o.series.forEach((s) => {
                if (s.hidden || !s.points) return;
                s.points.forEach((p) => {
                    if (p[1] === null || p[1] === undefined) return;
                    svg += `<circle cx="${sx(p[0]).toFixed(2)}" cy="${sy(p[1]).toFixed(2)}" r="6" fill="transparent">`
                        + `<title>${esc(s.name)} · ${esc(o.xFormat(p[0]))} · ${esc(o.yFormat(p[1]))}</title></circle>`;
                });
            });
            svg += '</g>';
        }
        svg += '</svg>';
        return svg;
    }

    function renderBarChart(opts) {
        const o = Object.assign({
            width: 720, height: 220,
            padding: { l: 110, r: 24, t: 12, b: 24 },
            items: [], color: '#58a6ff', valueFormat: (v) => F.fmtInt(v),
            labelWidth: 104, horizontal: true, emptyText: 'No data',
        }, opts || {});
        const W = o.width; const H = o.height;
        const pad = o.padding;
        if (!o.items.length) {
            return `<svg viewBox="0 0 ${W} ${H}" class="soak-chart" role="img">`
                + `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" class="soak-chart-empty">${esc(o.emptyText)}</text></svg>`;
        }
        const max = Math.max(1, ...o.items.map((i) => i.value));
        const plotW = W - pad.l - pad.r;
        const plotH = H - pad.t - pad.b;
        const rowH = plotH / o.items.length;
        const barH = Math.min(22, rowH * 0.62);
        let svg = `<svg viewBox="0 0 ${W} ${H}" class="soak-chart" role="img">`;
        o.items.forEach((item, idx) => {
            const y = pad.t + idx * rowH + (rowH - barH) / 2;
            const w = Math.max(2, (item.value / max) * plotW);
            const color = item.color || o.color;
            svg += `<text x="${pad.l - 8}" y="${(y + barH / 2 + 3.5).toFixed(1)}" text-anchor="end" class="soak-axis-label">${esc(item.label)}</text>`;
            svg += `<rect x="${pad.l}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${barH.toFixed(1)}" rx="3" fill="${color}" opacity="0.85">`
                + `<title>${esc(item.label)}: ${esc(o.valueFormat(item.value))}</title></rect>`;
            svg += `<text x="${(pad.l + w + 6).toFixed(1)}" y="${(y + barH / 2 + 3.5).toFixed(1)}" class="soak-axis-label">${esc(o.valueFormat(item.value))}</text>`;
        });
        svg += '</svg>';
        return svg;
    }

    function histogram(values, binCount) {
        const clean = (values || []).filter((v) => v !== null && v !== undefined && !Number.isNaN(v));
        if (!clean.length) return [];
        const [min, max] = extent(clean);
        const bins = Math.max(1, Math.min(binCount || 12, 40));
        const width = (max - min) / bins || 1;
        const counts = new Array(bins).fill(0);
        clean.forEach((v) => {
            let idx = Math.floor((v - min) / width);
            if (idx >= bins) idx = bins - 1;
            if (idx < 0) idx = 0;
            counts[idx] += 1;
        });
        return counts.map((count, i) => ({
            label: F.fmtNum(min + i * width, 0),
            value: count,
            range: [min + i * width, min + (i + 1) * width],
        }));
    }

    function renderVerticalBars(opts) {
        const o = Object.assign({
            width: 720, height: 220, padding: { l: 42, r: 18, t: 14, b: 40 },
            items: [], color: '#58a6ff', valueFormat: (v) => F.fmtInt(v), emptyText: 'No data',
        }, opts || {});
        const W = o.width; const H = o.height; const pad = o.padding;
        if (!o.items.length) {
            return `<svg viewBox="0 0 ${W} ${H}" class="soak-chart" role="img">`
                + `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" class="soak-chart-empty">${esc(o.emptyText)}</text></svg>`;
        }
        const max = Math.max(1, ...o.items.map((i) => i.value));
        const plotW = W - pad.l - pad.r;
        const plotH = H - pad.t - pad.b;
        const step = plotW / o.items.length;
        const barW = Math.max(2, step * 0.7);
        let svg = `<svg viewBox="0 0 ${W} ${H}" class="soak-chart" role="img">`;
        [0, 0.5, 1].forEach((f) => {
            const y = pad.t + plotH * (1 - f);
            svg += `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${pad.l + plotW}" y2="${y.toFixed(1)}" class="soak-grid"/>`;
            svg += `<text x="${pad.l - 6}" y="${(y + 3.5).toFixed(1)}" text-anchor="end" class="soak-axis-label">${esc(o.valueFormat(Math.round(max * f)))}</text>`;
        });
        o.items.forEach((item, idx) => {
            const h = (item.value / max) * plotH;
            const x = pad.l + idx * step + (step - barW) / 2;
            const y = pad.t + plotH - h;
            svg += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${Math.max(1, h).toFixed(1)}" rx="2" fill="${item.color || o.color}" opacity="0.85">`
                + `<title>${esc(item.label)}: ${esc(o.valueFormat(item.value))}</title></rect>`;
            if (o.items.length <= 24 || idx % Math.ceil(o.items.length / 12) === 0) {
                svg += `<text x="${(pad.l + idx * step + step / 2).toFixed(1)}" y="${pad.t + plotH + 14}" text-anchor="middle" class="soak-axis-label">${esc(item.label)}</text>`;
            }
        });
        svg += '</svg>';
        return svg;
    }

    function renderDonut(opts) {
        const o = Object.assign({ size: 170, thickness: 26, slices: [], emptyText: 'No data' }, opts || {});
        const total = o.slices.reduce((s, x) => s + x.value, 0);
        const R = o.size / 2;
        const r = R - o.thickness;
        if (!total) {
            return `<svg viewBox="0 0 ${o.size} ${o.size}" class="soak-chart" role="img">`
                + `<text x="${R}" y="${R}" text-anchor="middle" class="soak-chart-empty">${esc(o.emptyText)}</text></svg>`;
        }
        let angle = -Math.PI / 2;
        let svg = `<svg viewBox="0 0 ${o.size} ${o.size}" class="soak-chart" role="img">`;
        o.slices.forEach((slice) => {
            const frac = slice.value / total;
            const a2 = angle + frac * Math.PI * 2;
            const large = frac > 0.5 ? 1 : 0;
            const x1 = R + R * Math.cos(angle); const y1 = R + R * Math.sin(angle);
            const x2 = R + R * Math.cos(a2); const y2 = R + R * Math.sin(a2);
            const x3 = R + r * Math.cos(a2); const y3 = R + r * Math.sin(a2);
            const x4 = R + r * Math.cos(angle); const y4 = R + r * Math.sin(angle);
            const d = `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${R} ${R} 0 ${large} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} `
                + `L ${x3.toFixed(2)} ${y3.toFixed(2)} A ${r} ${r} 0 ${large} 0 ${x4.toFixed(2)} ${y4.toFixed(2)} Z`;
            svg += `<path d="${d}" fill="${slice.color}" opacity="0.9"><title>${esc(slice.label)}: ${esc(F.fmtInt(slice.value))} (${F.pct(frac, 0)})</title></path>`;
            angle = a2;
        });
        svg += `<text x="${R}" y="${R - 2}" text-anchor="middle" class="soak-donut-total">${esc(F.fmtInt(total))}</text>`;
        svg += `<text x="${R}" y="${R + 14}" text-anchor="middle" class="soak-axis-label">${esc(o.centerLabel || 'total')}</text>`;
        svg += '</svg>';
        return svg;
    }

    function renderSparkline(values, opts) {
        const o = Object.assign({ width: 120, height: 28, color: '#58a6ff', fill: true }, opts || {});
        const clean = (values || []).filter((v) => v !== null && v !== undefined && !Number.isNaN(v));
        if (clean.length < 2) return `<svg viewBox="0 0 ${o.width} ${o.height}" class="soak-spark"></svg>`;
        const [min, max] = extent(clean);
        const sx = scaleFor([0, clean.length - 1], [1, o.width - 1], false);
        const sy = scaleFor([min, max], [2, o.height - 2], false);
        const pts = clean.map((v, i) => [i, v]);
        const d = pointPath(pts, sx, sy);
        let svg = `<svg viewBox="0 0 ${o.width} ${o.height}" class="soak-spark" preserveAspectRatio="none">`;
        if (o.fill) {
            svg += `<path d="${d} L ${o.width - 1} ${o.height - 1} L 1 ${o.height - 1} Z" fill="${o.color}" opacity="0.15"/>`;
        }
        svg += `<path d="${d}" fill="none" stroke="${o.color}" stroke-width="1.6"/>`;
        svg += '</svg>';
        return svg;
    }

    window.SoakCharts = {
        extent, niceTicks, renderLineChart, renderBarChart, renderVerticalBars,
        renderDonut, renderSparkline, histogram, scaleFor, pointPath,
    };
})();
