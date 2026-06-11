import { useMemo } from "react";


export default function GaugeChart({ value = 0, max = 100, label, unit, color = "#a855f7" }) {
  const clampedValue = Math.min(Math.max(value, 0), max);
  const percentage = clampedValue / max;

  // Arc geometry
  const cx = 150, cy = 140, r = 110;
  const startAngle = -225; // degrees (bottom-left)
  const endAngle = 45;     // degrees (bottom-right)
  const sweep = endAngle - startAngle; // 270°

  const toRad = (deg) => (deg * Math.PI) / 180;

  // Tick marks
  const ticks = useMemo(() => {
    const count = 9; // 0, 1/8, 2/8 ... 8/8
    const arr = [];
    for (let i = 0; i <= count; i++) {
      const frac = i / count;
      const angle = startAngle + frac * sweep;
      const rad = toRad(angle);
      const x1 = cx + (r - 8) * Math.cos(rad);
      const y1 = cy + (r - 8) * Math.sin(rad);
      const x2 = cx + (r + 6) * Math.cos(rad);
      const y2 = cy + (r + 6) * Math.sin(rad);
      const labelX = cx + (r + 22) * Math.cos(rad);
      const labelY = cy + (r + 22) * Math.sin(rad);
      const tickValue = Math.round((i / count) * max);
      arr.push({ x1, y1, x2, y2, labelX, labelY, tickValue, isMajor: true });
    }
    return arr;
  }, [max, sweep, startAngle, cx, cy, r]);

  // Minor ticks
  const minorTicks = useMemo(() => {
    const count = 36;
    const arr = [];
    for (let i = 0; i <= count; i++) {
      const frac = i / count;
      const angle = startAngle + frac * sweep;
      const rad = toRad(angle);
      const x1 = cx + (r - 3) * Math.cos(rad);
      const y1 = cy + (r - 3) * Math.sin(rad);
      const x2 = cx + (r + 2) * Math.cos(rad);
      const y2 = cy + (r + 2) * Math.sin(rad);
      arr.push({ x1, y1, x2, y2 });
    }
    return arr;
  }, [sweep, startAngle, cx, cy, r]);

  // Arc path for the background track
  const describeArc = (startDeg, endDeg) => {
    const sRad = toRad(startDeg);
    const eRad = toRad(endDeg);
    const x1 = cx + r * Math.cos(sRad);
    const y1 = cy + r * Math.sin(sRad);
    const x2 = cx + r * Math.cos(eRad);
    const y2 = cy + r * Math.sin(eRad);
    const angleDiff = endDeg - startDeg;
    const largeArc = angleDiff > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`;
  };

  // Needle angle
  const needleAngle = startAngle + percentage * sweep;
  const needleRad = toRad(needleAngle);
  const needleLen = r - 20;
  const nx = cx + needleLen * Math.cos(needleRad);
  const ny = cy + needleLen * Math.sin(needleRad);

  // Active arc end angle
  const activeEnd = startAngle + percentage * sweep;

  // Value color: smooth interpolation based on %
  const getValueColor = (pct) => {
    if (pct < 0.5) return color;
    if (pct < 0.75) return "#f59e0b";
    return "#ef4444";
  };

  const activeColor = getValueColor(percentage);

  return (
    <div className="gauge-wrapper">
      <svg
        className="gauge-svg"
        width="100%"
        viewBox="0 0 300 200"
        style={{ maxWidth: 280 }}
      >
        <defs>
          <filter id={`glow-${label}`}>
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id={`arcGrad-${label}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={color} />
            <stop offset="60%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
        </defs>

        {/* Background track */}
        <path
          d={describeArc(startAngle, endAngle)}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="12"
          strokeLinecap="round"
        />

        {/* Active arc */}
        {percentage > 0.005 && (
          <path
            d={describeArc(startAngle, activeEnd)}
            fill="none"
            stroke={`url(#arcGrad-${label})`}
            strokeWidth="12"
            strokeLinecap="round"
            filter={`url(#glow-${label})`}
            style={{
              transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
            }}
          />
        )}

        {/* Minor ticks */}
        {minorTicks.map((t, i) => (
          <line
            key={`mt-${i}`}
            x1={t.x1} y1={t.y1}
            x2={t.x2} y2={t.y2}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="1"
          />
        ))}

        {/* Major ticks & labels */}
        {ticks.map((t, i) => (
          <g key={`tk-${i}`}>
            <line
              x1={t.x1} y1={t.y1}
              x2={t.x2} y2={t.y2}
              stroke="rgba(255,255,255,0.35)"
              strokeWidth="2"
            />
            <text
              x={t.labelX}
              y={t.labelY}
              fill="rgba(255,255,255,0.4)"
              fontSize="9"
              textAnchor="middle"
              dominantBaseline="middle"
            >
              {t.tickValue}
            </text>
          </g>
        ))}

        {/* Needle */}
        <line
          x1={cx}
          y1={cy}
          x2={nx}
          y2={ny}
          stroke={activeColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          filter={`url(#glow-${label})`}
          style={{
            transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        />

        {/* Center dot */}
        <circle cx={cx} cy={cy} r="6" fill={activeColor} opacity="0.9" />
        <circle cx={cx} cy={cy} r="3" fill="#0f0a1e" />
      </svg>

      <div className="gauge-value-display">
        {typeof value === "number" ? value.toFixed(0) : "0"}
      </div>
      <div className="gauge-unit">{unit}</div>
    </div>
  );
}
