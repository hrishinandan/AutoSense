import { useRef, useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const MAX_POINTS = 30;

/**
 * Smooth rolling line chart using Recharts AreaChart.
 * Props: value, label, unit, color (hex), minY, maxY
 */
export default function SmoothLineChart({
  value = 0,
  label,
  unit,
  color = "#a855f7",
  minY,
  maxY,
}) {
  const indexRef = useRef(0);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (typeof value !== "number") return;
    indexRef.current += 1;
    setHistory((prev) => {
      const next = [...prev, { idx: indexRef.current, value: parseFloat(value.toFixed(2)) }];
      if (next.length > MAX_POINTS) next.shift();
      return next;
    });
  }, [value]);

  // Calculate domain
  const domainMin = minY !== undefined ? minY : "auto";
  const domainMax = maxY !== undefined ? maxY : "auto";

  const gradientId = `lineGrad-${label?.replace(/\s/g, "")}`;

  return (
    <div className="line-chart-wrapper">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={history} margin={{ top: 8, right: 12, left: -20, bottom: 4 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.4} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.06)"
            vertical={false}
          />
          <XAxis dataKey="idx" hide />
          <YAxis
            domain={[domainMin, domainMax]}
            tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "rgba(15, 10, 30, 0.9)",
              border: "1px solid rgba(168,85,247,0.3)",
              borderRadius: 8,
              color: "white",
              fontSize: "0.8rem",
            }}
            labelFormatter={() => label}
            formatter={(v) => [`${v} ${unit}`, label]}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2.5}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, fill: color, stroke: "#fff", strokeWidth: 1 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
