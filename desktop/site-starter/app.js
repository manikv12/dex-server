// Dex design kit: React + htm (JSX-like markup, no build step) + Lucide icons (https://lucide.dev/icons).
// Page() below is only an example (a report). Build whatever layout fits the content: a report, a dashboard
// with a sidebar, a landing page, a document, a tool. Reuse the look (style.css tokens) and these parts:
//   <${Header} title subtitle tags=${[{icon, text, live}]} />      top of the page, with Download PDF and light/dark
//   <${Takeaways} items=${[{icon, title, text}]} />                 the 3 things to know, in one card
//   <${Kpi} label value delta note spark=${[numbers]} />            one number card (put 4 in <div class="grid g4">)
//   <${Card} title note end=${…}>…</>                              a card with a heading; `end` = a control on the right
//   <${Range} value options onChange />                             a compact segmented switch (7D / 30D / 90D)
//   <${Bars} labels series=${[{name, values}]} stacked />           bars over time
//   <${Area} labels series />                                       smooth trend with a soft fill
//   <${Ranked} items=${[{label, value, note}]} unit />              ranked list with shares
//   <${Heat} rows=${[{name, values}]} cols />                       item × day grid
//   <${Table} columns=${[{key, label, align, render}]} rows />
const { useState, useEffect, useMemo } = React;
const html = htm.bind(React.createElement);
const COLORS = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c5)"];
const fmt = (n) => (typeof n === "number" ? n.toLocaleString() : n);
const sum = (a) => a.reduce((x, y) => x + y, 0);

// ---- Example data: replace with the real data ----
const seed = ((s) => () => (s = (s * 9301 + 49297) % 233280) / 233280)(11);
const DAYS = Array.from({ length: 90 }, (_, i) => new Date(2026, 7, 14 + i));
const DATA = {
  title: "Page title",
  subtitle: "One sentence on what this shows and why it matters, in plain words.",
  tags: [{ icon: "calendar", text: "Aug 14 – Nov 11, 2026" }, { icon: "database", text: "Source: your system" }, { text: "Updated 7:17 AM", live: true }],
  takeaways: [
    { icon: "trending-up", title: "Calls are up 12%", text: "Mostly from the Bifold mailer in the last two weeks." },
    { icon: "phone-call", title: "93% were answered", text: "Missed calls cluster on Monday mornings." },
    { icon: "sparkles", title: "Bifold works best", text: "It brings 42% of calls for 30% of the pieces sent." },
  ],
  days: DAYS,
  series: ["Bifold", "6×9", "6×11"].map((name, k) => ({ name, values: DAYS.map((_, i) => Math.round(18 + 22 * seed() + k * 6 + i / 8)) })),
  items: ["Bifold — Dean", "Bifold — Wendy", "6×11 — Dean", "6×9 — Wendy", "6×9 — Dean"].map((name) => ({ name, values: DAYS.map(() => Math.round(seed() * 24)) })),
};

// ---- Parts ----
const Icon = ({ name }) => html`<i data-lucide=${name} aria-hidden="true"></i>`;

function Header({ title, subtitle, tags }) {
  const [theme, setTheme] = useState(() => {
    let saved = null;
    try { saved = localStorage.getItem("theme"); } catch (e) {}
    return saved || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  });
  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem("theme", theme); } catch (e) {} }, [theme]);
  return html`<header class="header"><div class="wrap">
    <div class="bar">
      <div class="brand"><img src="favicon.svg" alt="" />${title}</div>
      <div class="icons">
        <button class="ibtn" data-tip="Download PDF" onClick=${() => print()}><${Icon} name="download" /></button>
        <button class="ibtn" data-tip=${theme === "dark" ? "Light" : "Dark"} onClick=${() => setTheme(theme === "dark" ? "light" : "dark")}><${Icon} name=${theme === "dark" ? "sun" : "moon"} /></button>
      </div>
    </div>
    <h1>${title}</h1>
    <p class="subtitle">${subtitle}</p>
    <div class="meta">${tags.map((t) => html`<span key=${t.text} class=${"tag" + (t.live ? " live" : "")}>${t.icon && html`<${Icon} name=${t.icon} />`}${t.text}</span>`)}</div>
  </div></header>`;
}

const Takeaways = ({ items }) => html`<div class="card"><div class="takeaways">${items.map((t) => html`<div class="take" key=${t.title}>
  <div class="dot"><${Icon} name=${t.icon} /></div><div><b>${t.title}</b><span>${t.text}</span></div></div>`)}</div></div>`;

function Spark({ values }) {
  const max = Math.max(...values), min = Math.min(...values), w = 92, h = 30;
  const pts = values.map((v, i) => [(i / (values.length - 1)) * w, h - 3 - ((v - min) / Math.max(1, max - min)) * (h - 6)]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  return html`<svg class="spark" viewBox=${`0 0 ${w} ${h}`}><path d=${d + ` L${w} ${h} L0 ${h} Z`} fill="var(--soft)" />
    <path d=${d} fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>`;
}

const Kpi = ({ label, value, delta, note, spark }) => html`<div class="card kpi">
  <div class="top"><span class="label">${label}</span></div>
  <div class="value num">${fmt(value)}</div>
  <div class="foot"><div>${delta != null && html`<span class=${"delta " + (delta >= 0 ? "up" : "down")}><${Icon} name=${delta >= 0 ? "arrow-up-right" : "arrow-down-right"} />${Math.abs(delta)}%</span>`}
    ${note && html` <span class="note">${note}</span>`}</div>${spark && html`<${Spark} values=${spark} />`}</div></div>`;

const Card = ({ title, note, end, children }) => html`<div class="card">
  ${title && html`<div class="card-head"><div><h3>${title}</h3>${note && html`<p>${note}</p>`}</div>${end && html`<div class="end">${end}</div>`}</div>`}
  ${children}</div>`;

const Range = ({ value, options, onChange }) => html`<div class="seg" role="tablist">${options.map((o) => html`<button key=${o.value} role="tab"
  aria-selected=${value === o.value} class=${value === o.value ? "on" : ""} onClick=${() => onChange(o.value)}>${o.label}</button>`)}</div>`;

const Legend = ({ series }) => html`<div class="legend">${series.map((s, i) => html`<span key=${s.name}><i style=${{ background: COLORS[i % 5] }}></i>${s.name}</span>`)}</div>`;

function useTip() {
  const [tip, setTip] = useState(null);
  return [tip && html`<div class="tip" style=${{ left: Math.min(tip.x + 14, innerWidth - 200), top: tip.y + 14 }}>${tip.body}</div>`,
          (e, body) => setTip(body ? { x: e.clientX, y: e.clientY, body } : null)];
}
const tipBody = (label, series, i) => html`<b>${label}</b>${series.map((s, k) => html`<div key=${s.name}><i style=${{ background: COLORS[k % 5] }}></i>${s.name}<span>${fmt(s.values[i])}</span></div>`)}`;

function axis(max) { const step = Math.pow(10, Math.floor(Math.log10(Math.max(1, max)))); const top = Math.ceil(max / step) * step; return [0, top / 2, top]; }

function Bars({ labels, series, stacked = true, height = 250 }) {
  const [tip, show] = useTip();
  const W = 1000, H = height, L = 36, B = 24, n = labels.length;
  const totals = labels.map((_, i) => stacked ? sum(series.map((s) => s.values[i] || 0)) : Math.max(...series.map((s) => s.values[i] || 0)));
  const ticks = axis(Math.max(...totals)), max = ticks[2];
  const y = (v) => (H - B) - (v / max) * (H - B - 6), bw = (W - L) / n, every = Math.ceil(n / 7);
  return html`<div><${Legend} series=${series} /><svg class="chart" viewBox=${`0 0 ${W} ${H}`} onMouseLeave=${(e) => show(e, null)}>
    ${ticks.map((t) => html`<g key=${t}><line class="grid" x1=${L} x2=${W} y1=${y(t)} y2=${y(t)} /><text x=${L - 8} y=${y(t) + 4} text-anchor="end">${fmt(t)}</text></g>`)}
    ${labels.map((lab, i) => { let acc = 0; const x0 = L + i * bw;
      return html`<g key=${i} onMouseMove=${(e) => show(e, tipBody(lab, series, i))}><rect class="hover" x=${x0} y="0" width=${bw} height=${H - B} opacity="0" />
        ${series.map((s, k) => { const v = s.values[i] || 0; const yTop = y(acc + v), h = y(acc) - yTop; acc += v;
          const last = k === series.length - 1; const gap = Math.max(1, bw * 0.22);
          return html`<rect key=${k} x=${x0 + gap / 2} width=${bw - gap} y=${yTop + (last ? 0 : 0.6)} height=${Math.max(0, h - 1.2)} rx=${last ? Math.min(4, (bw - gap) / 3) : 1} fill=${COLORS[k % 5]} />`; })}
        ${i % every === 0 && html`<text x=${x0 + bw / 2} y=${H - 6} text-anchor="middle">${lab}</text>`}</g>`; })}
  </svg>${tip}</div>`;
}

function Area({ labels, series, height = 230 }) {
  const [tip, show] = useTip();
  const [hover, setHover] = useState(null);
  const W = 1000, H = height, L = 36, B = 24, n = labels.length;
  const ticks = axis(Math.max(...series.flatMap((s) => s.values))), max = ticks[2];
  const x = (i) => L + (i / Math.max(1, n - 1)) * (W - L - 4), y = (v) => (H - B) - (v / max) * (H - B - 6);
  const path = (vals) => vals.map((v, i) => { if (!i) return `M${x(0)} ${y(v)}`; const px = x(i - 1), cx = (px + x(i)) / 2;
    return `C${cx} ${y(vals[i - 1])} ${cx} ${y(v)} ${x(i)} ${y(v)}`; }).join(" ");
  const move = (e) => { const r = e.currentTarget.getBoundingClientRect(); const i = Math.round(((e.clientX - r.left) / r.width * W - L) / ((W - L) / Math.max(1, n - 1)));
    const k = Math.max(0, Math.min(n - 1, i)); setHover(k); show(e, tipBody(labels[k], series, k)); };
  return html`<div><${Legend} series=${series} /><svg class="chart" viewBox=${`0 0 ${W} ${H}`} onMouseMove=${move} onMouseLeave=${(e) => { setHover(null); show(e, null); }}>
    <defs>${series.map((s, k) => html`<linearGradient key=${k} id=${"fill" + k} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color=${COLORS[k % 5]} stop-opacity=".12" /><stop offset="1" stop-color=${COLORS[k % 5]} stop-opacity="0" /></linearGradient>`)}</defs>
    ${ticks.map((t) => html`<g key=${t}><line class="grid" x1=${L} x2=${W} y1=${y(t)} y2=${y(t)} /><text x=${L - 8} y=${y(t) + 4} text-anchor="end">${fmt(t)}</text></g>`)}
    ${series.map((s, k) => html`<g key=${s.name}><path d=${path(s.values) + ` L${x(n - 1)} ${H - B} L${x(0)} ${H - B} Z`} fill=${`url(#fill${k})`} />
      <path d=${path(s.values)} fill="none" stroke=${COLORS[k % 5]} stroke-width="2.4" stroke-linecap="round" /></g>`)}
    ${hover != null && html`<line x1=${x(hover)} x2=${x(hover)} y1="0" y2=${H - B} stroke="var(--line-2)" />`}
    ${hover != null && series.map((s, k) => html`<circle key=${k} cx=${x(hover)} cy=${y(s.values[hover])} r="4.5" fill="var(--card)" stroke=${COLORS[k % 5]} stroke-width="2.4" />`)}
    ${labels.map((lab, i) => i % Math.ceil(n / 7) === 0 && html`<text key=${i} x=${x(i)} y=${H - 6} text-anchor="middle">${lab}</text>`)}
  </svg>${tip}</div>`;
}

function Ranked({ items, unit = "" }) {
  const total = Math.max(1, sum(items.map((i) => i.value))), max = Math.max(1, ...items.map((i) => i.value));
  return html`<div class="rank">${items.map((it) => html`<div class="rrow" key=${it.label}>
    <div class="av">${it.label.split(/\s+/).filter((w) => /[A-Za-z0-9]/.test(w)).map((w) => w.replace(/[^A-Za-z0-9]/g, "")[0]).join("").slice(0, 2).toUpperCase()}</div>
    <div><div class="name">${it.label}<small>${Math.round((it.value / total) * 100)}%</small></div><div class="track"><i style=${{ width: `${(it.value / max) * 100}%` }}></i></div></div>
    <div class="val num">${fmt(it.value)}${unit}</div></div>`)}</div>`;
}

function Heat({ rows, cols }) {
  const [tip, show] = useTip();
  const max = Math.max(1, ...rows.flatMap((r) => r.values));
  const shade = (v) => (v <= 0 ? "var(--soft)" : `color-mix(in srgb, var(--c1) ${Math.round(15 + 85 * (v / max))}%, var(--soft))`);
  return html`<div class="heat" style=${{ gridTemplateColumns: `auto repeat(${cols.length}, minmax(12px, 1fr))` }} onMouseLeave=${(e) => show(e, null)}>
    <span></span>${cols.map((c, i) => html`<span key=${i} style=${{ textAlign: "center" }}>${i % 2 ? "" : c}</span>`)}
    ${rows.map((r) => html`<${React.Fragment} key=${r.name}><span class="rowname">${r.name}</span>${r.values.map((v, i) => html`<div key=${i} class="cell"
      style=${{ background: shade(v) }} onMouseMove=${(e) => show(e, html`<b>${r.name}</b><div>${cols[i]}<span>${fmt(v)}</span></div>`)}></div>`)}</${React.Fragment}>`)}
  ${tip}</div>`;
}

const Table = ({ columns, rows }) => html`<div class="tablewrap"><table>
  <thead><tr>${columns.map((c) => html`<th key=${c.key} class=${c.align === "right" ? "r" : ""}>${c.label}</th>`)}</tr></thead>
  <tbody>${rows.map((row, i) => html`<tr key=${i}>${columns.map((c) => html`<td key=${c.key} class=${c.align === "right" ? "r num" : ""}>${c.render ? c.render(row) : fmt(row[c.key])}</td>`)}</tr>`)}</tbody>
</table></div>`;

// ---- The page ----
const RANGES = [{ value: 7, label: "7D" }, { value: 30, label: "30D" }, { value: 90, label: "90D" }];
const dayLabel = (d) => d.toLocaleDateString("en-US", { month: "short", day: "numeric" });

function Page() {
  const [range, setRange] = useState(30);
  const days = DATA.days.slice(-range);
  const series = DATA.series.map((s) => ({ ...s, values: s.values.slice(-range) }));
  const prev = DATA.series.map((s) => s.values.slice(-range * 2, -range));
  const total = sum(series.flatMap((s) => s.values)), before = sum(prev.flat());
  const items = DATA.items.map((p) => ({ label: p.name, value: sum(p.values.slice(-range)) })).sort((a, b) => b.value - a.value);
  const daily = days.map((_, i) => sum(series.map((s) => s.values[i])));
  const control = html`<${Range} value=${range} options=${RANGES} onChange=${setRange} />`;
  useEffect(() => { lucide.createIcons(); });

  return html`<${Header} title=${DATA.title} subtitle=${DATA.subtitle} tags=${DATA.tags} />
  <main><div class="wrap">
    <${Takeaways} items=${DATA.takeaways} />
    <div class="gap"></div>
    <div class="grid g4">
      <${Kpi} label="Total calls" value=${total} delta=${before ? Math.round(((total - before) / before) * 100) : null} note=${`last ${range} days`} spark=${daily} />
      <${Kpi} label="Answered" value="93%" delta=${4} note="vs before" spark=${daily.map((v, i) => v * 0.9 + (i % 5))} />
      <${Kpi} label="First-time callers" value="72%" delta=${-2} note="1,981 people" spark=${daily.map((v, i) => v * 0.7 + (i % 3))} />
      <${Kpi} label="Top mailer" value=${items[0].label.split(" —")[0]} note=${fmt(items[0].value) + " calls"} />
    </div>
    <div class="gap"></div>
    <div class="grid g32">
      <${Card} title="Calls per day" note="By mail format. Hover a day for the numbers." end=${control}><${Bars} labels=${days.map(dayLabel)} series=${series} /></${Card}>
      <${Card} title="Top mail pieces" note=${`Last ${range} days`}><${Ranked} items=${items} /></${Card}>
    </div>
    <div class="gap"></div>
    <${Card} title="Trend" note="Each format's calls per day." end=${control}><${Area} labels=${days.map(dayLabel)} series=${series} /></${Card}>
    <div class="gap"></div>
    <${Card} title="Each piece by day" note="Darker means more calls."><${Heat} rows=${DATA.items.map((p) => ({ name: p.name, values: p.values.slice(-Math.min(range, 30)) }))}
      cols=${DATA.days.slice(-Math.min(range, 30)).map((d) => d.getDate())} /></${Card}>
    <div class="gap"></div>
    <${Card} title="Details">
      <${Table} columns=${[{ key: "label", label: "Mail piece" }, { key: "value", label: "Calls", align: "right" },
        { key: "share", label: "Share", align: "right", render: (r) => Math.round((r.value / Math.max(1, sum(items.map((i) => i.value)))) * 100) + "%" },
        { key: "s", label: "Status", render: (r) => html`<span class=${"badge " + (r.value === items[0].value ? "good" : "")}>${r.value === items[0].value ? "Leading" : "Steady"}</span>` }]}
        rows=${items} />
    </${Card}>
  </div></main>
  <footer><div class="wrap"><span>Source: your system, pulled Nov 11, 7:17 AM.</span><span>Numbers for Nov 11 are partial.</span></div></footer>`;
}

ReactDOM.createRoot(document.getElementById("root")).render(html`<${Page} />`);
