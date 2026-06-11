import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

/**
 * Doughnut chart for percentage values (0-100).
 * Props: value, label, unit, color (hex)
 */
export default function DoughnutChart({
  value = 0,
  label,
  unit = "%",
  color = "#a855f7",
}) {
  const clamped = Math.min(Math.max(value, 0), 100);
  const data = [
    { name: "Active", value: clamped },
    { name: "Remaining", value: 100 - clamped },
  ];

  return (
    <div className="doughnut-chart-wrapper">
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            startAngle={90}
            endAngle={-270}
            dataKey="value"
            stroke="none"
            animationDuration={600}
            animationEasing="ease-out"
          >
            <Cell fill={color} />
            <Cell fill="rgba(255,255,255,0.06)" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="doughnut-center-label">
        <span className="doughnut-value">
          {typeof value === "number" ? value.toFixed(1) : "0"}
        </span>
        <span className="doughnut-unit">{unit}</span>
      </div>
    </div>
  );
}
