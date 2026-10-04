// src/components/dashboard/TrendChart.tsx — 批次均分趋势（纯 SVG，零依赖）
export interface TrendPoint {
  label: string;
  score: number;
}

export function TrendChart({ points }: { points: TrendPoint[] }) {
  const W = 640;
  const H = 160;
  const PAD = { l: 32, r: 12, t: 12, b: 22 };
  const iw = W - PAD.l - PAD.r;
  const ih = H - PAD.t - PAD.b;
  const max = 10;
  const stepX = points.length > 1 ? iw / (points.length - 1) : 0;
  const xy = points.map((p, i) => ({
    x: PAD.l + i * stepX,
    y: PAD.t + ih - (Math.min(p.score, max) / max) * ih,
    ...p,
  }));
  const line = xy.map((p) => `${p.x},${p.y}`).join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="批次均分趋势图">
      {[0, 5, 10].map((v) => {
        const y = PAD.t + ih - (v / max) * ih;
        return (
          <g key={v}>
            <line x1={PAD.l} y1={y} x2={W - PAD.r} y2={y} stroke="var(--border)" strokeWidth="1" />
            <text x={PAD.l - 6} y={y + 3} fontSize="9" textAnchor="end" fill="var(--muted)">
              {v}
            </text>
          </g>
        );
      })}
      <polyline points={line} fill="none" stroke="var(--primary)" strokeWidth="2" />
      {xy.map((p) => (
        <g key={p.label}>
          <circle cx={p.x} cy={p.y} r="3" fill="var(--primary)" />
          <text x={p.x} y={H - 6} fontSize="9" textAnchor="middle" fill="var(--muted)">
            {p.label}
          </text>
          <title>{`${p.label}: ${p.score}`}</title>
        </g>
      ))}
    </svg>
  );
}
