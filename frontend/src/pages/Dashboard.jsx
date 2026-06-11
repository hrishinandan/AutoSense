import { useNavigate } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import Papa from "papaparse";
import GaugeChart from "./components/GaugeChart";
import SmoothLineChart from "./components/LineChart";
import DoughnutChart from "./components/DoughnutChart";
import "./Dashboard.css";


const CSV_PATH = "/cleaned_data.csv";

// How many milliseconds between each row (1000ms = 1 row per second)
const ROW_INTERVAL_MS = 50;

export default function Dashboard() {
  const [rows, setRows]       = useState([]);   // all CSV rows loaded once
  const [rowIndex, setRowIndex] = useState(0);  // current row pointer
  const [currentRow, setCurrentRow] = useState(null); // row shown on dashboard
  const [running, setRunning] = useState(false);
  const [csvReady, setCsvReady] = useState(false);
  const intervalRef = useRef(null);
  const navigate = useNavigate();

  // ── Step 1: Load and parse the CSV once on component mount ─────
  useEffect(() => {
    Papa.parse(CSV_PATH, {
      download: true,         // fetch from /public folder
      header: true,           // use first row as column names
      dynamicTyping: true,    // auto-convert numbers (no manual parseFloat needed)
      skipEmptyLines: true,
      complete: (result) => {
        if (result.data && result.data.length > 0) {
          setRows(result.data);
          setCsvReady(true);
          console.log(`[Dashboard] CSV loaded — ${result.data.length} rows`);
          console.log("[Dashboard] Columns:", Object.keys(result.data[0]));
        } else {
          console.error("[Dashboard] CSV loaded but no data found.");
        }
      },
      error: (err) => {
        console.error("[Dashboard] Failed to load CSV:", err);
      }
    });
  }, []);

  // ── Step 2: When running, advance one row every ROW_INTERVAL_MS ─
  useEffect(() => {
    if (running && csvReady && rows.length > 0) {
      // Show the first row immediately without waiting for first tick
      setCurrentRow(rows[rowIndex]);

      intervalRef.current = setInterval(() => {
        setRowIndex((prevIndex) => {
          const nextIndex = (prevIndex + 1) % rows.length; // loop back to 0 at end
          setCurrentRow(rows[nextIndex]);
          return nextIndex;
        });
      }, ROW_INTERVAL_MS);
    }

    // Cleanup: clear interval when stopped or component unmounts
    return () => clearInterval(intervalRef.current);
  }, [running, csvReady]);

  // ── Shorthand so JSX stays readable ───────────────────────────
  const d = currentRow;

  // ── Helper: safely get a numeric value from the current row ────
  // Returns 0 if the column is missing or not a number
  const val = (key) => {
    const v = d?.[key];
    return typeof v === "number" && !isNaN(v) ? v : 0;
  };

  return (
    <div className="dashboard-container">
      <div className="background-effects">
        <div className="neon-shape-1"></div>
        <div className="neon-shape-2"></div>
      </div>

      <div className="content-layer">
        <h1 className="dashboard-title">AutoSense Dashboard</h1>

        {/* CSV loading status */}
        {!csvReady && (
          <p style={{ color: "#a855f7", textAlign: "center" }}>
            Loading dataset...
          </p>
        )}

        {/* Row counter — helpful for debugging */}
        {csvReady && running && (
          <p style={{ color: "#888", textAlign: "center", fontSize: "0.8rem" }}>
            Row {rowIndex + 1} / {rows.length}
          </p>
        )}

        {!running ? (
          <div>
            <button
              className="start-btn"
              onClick={() => setRunning(true)}
              disabled={!csvReady}
            >
              {csvReady ? "Start Simulation" : "Loading..."}
            </button>

            {/* ── How This Works Section ── */}
            <div className="how-it-works-section">
              <h2 className="how-it-works-title">How this works ?</h2>

              <div className="workflow-container">
                {/* ROW 1: Dataset → Fault Injector */}
                <div className="workflow-row">
                  <div className="workflow-box workflow-box-1" id="box-dataset">
                    <div className="workflow-box-icon">🗄️</div>
                    <h3 className="workflow-box-heading" style={{ color: '#22d3ee' }}>1. Dataset</h3>
                    <p className="workflow-box-desc">
                      Collection of real vehicle sensor data under normal operating conditions.
                    </p>
                    <ul className="workflow-box-list">
                      <li><span className="list-dot" style={{ background: '#3b82f6' }}></span>Speed, RPM, Temperature, Fuel Level, etc.</li>
                      <li><span className="list-dot" style={{ background: '#3b82f6' }}></span>Historical data from vehicles</li>
                      <li><span className="list-dot" style={{ background: '#3b82f6' }}></span>Clean and labeled (if available)</li>
                    </ul>
                  </div>

                  {/* Arrow 1: horizontal right */}
                  <div className="workflow-arrow-h">
                    <svg viewBox="0 0 120 40" className="arrow-svg-h">
                      <defs>
                        <linearGradient id="arrowGrad1" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#22d3ee" stopOpacity="0" />
                          <stop offset="50%" stopColor="#22d3ee" stopOpacity="1" />
                          <stop offset="100%" stopColor="#22d3ee" stopOpacity="0" />
                        </linearGradient>
                        <filter id="glowFilter1">
                          <feGaussianBlur stdDeviation="3" result="blur" />
                          <feMerge>
                            <feMergeNode in="blur" />
                            <feMergeNode in="SourceGraphic" />
                          </feMerge>
                        </filter>
                      </defs>
                      {/* Static track line */}
                      <line x1="0" y1="20" x2="100" y2="20" stroke="rgba(34,211,238,0.15)" strokeWidth="2" />
                      <polygon points="100,12 120,20 100,28" fill="rgba(34,211,238,0.2)" />
                      {/* Animated glow line */}
                      <line x1="0" y1="20" x2="100" y2="20" stroke="url(#arrowGrad1)" strokeWidth="3" filter="url(#glowFilter1)" className="neon-travel-h" />
                      <polygon points="100,12 120,20 100,28" fill="#22d3ee" className="arrow-head-pulse" filter="url(#glowFilter1)" />
                    </svg>
                  </div>

                  <div className="workflow-box workflow-box-2" id="box-fault">
                    <div className="workflow-box-icon">⚠️</div>
                    <h3 className="workflow-box-heading" style={{ color: '#f59e0b' }}>2. Fault Injector</h3>
                    <p className="workflow-box-desc">
                      Artificially injects faults into the dataset to simulate abnormal conditions.
                    </p>
                    <ul className="workflow-box-list">
                      <li><span className="list-dot" style={{ background: '#f59e0b' }}></span>Overheating, RPM spike, Fuel drop, etc.</li>
                      <li><span className="list-dot" style={{ background: '#f59e0b' }}></span>Creates multiple fault scenarios</li>
                      <li><span className="list-dot" style={{ background: '#f59e0b' }}></span>Expands training and testing data</li>
                    </ul>
                  </div>
                </div>

                {/* L-shaped connector: Fault Injector (top-right) → ML Analysis (bottom-left) */}
                <div className="workflow-l-connector">
                  <svg viewBox="0 0 800 80" className="arrow-svg-l" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="arrowGradL" gradientUnits="userSpaceOnUse" x1="700" y1="0" x2="100" y2="80">
                        <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.6" />
                        <stop offset="50%" stopColor="#a855f7" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#10b981" stopOpacity="0.6" />
                      </linearGradient>
                      <filter id="glowFilterL">
                        <feGaussianBlur stdDeviation="4" result="blur" />
                        <feMerge>
                          <feMergeNode in="blur" />
                          <feMergeNode in="SourceGraphic" />
                        </feMerge>
                      </filter>
                    </defs>
                    {/* Static track: down from right, across left, down to left */}
                    <path d="M 600,0 L 600,35 L 200,35 L 200,80"
                          fill="none" stroke="rgba(168,85,247,0.12)" strokeWidth="2" />
                    {/* Arrowhead at bottom-left */}
                    <polygon points="192,65 200,80 208,65" fill="rgba(168,85,247,0.2)" />
                    {/* Animated neon travel path */}
                    <path d="M 600,0 L 600,35 L 200,35 L 200,80"
                          fill="none" stroke="url(#arrowGradL)" strokeWidth="3"
                          filter="url(#glowFilterL)" className="neon-travel-l" />
                    <polygon points="192,65 200,80 208,65" fill="#a855f7"
                             className="arrow-head-pulse" filter="url(#glowFilterL)" />
                  </svg>
                </div>

                {/* ROW 2: ML Analysis → Result */}
                <div className="workflow-row">
                  <div className="workflow-box workflow-box-3" id="box-ml">
                    <div className="workflow-box-icon">🧠</div>
                    <h3 className="workflow-box-heading" style={{ color: '#10b981' }}>3. ML Analysis</h3>
                    <p className="workflow-box-desc">
                      Machine learning models analyze the data to detect, classify, and assess faults.
                    </p>
                    <ul className="workflow-box-list">
                      <li><span className="list-dot" style={{ background: '#10b981' }}></span>Anomaly detection</li>
                      <li><span className="list-dot" style={{ background: '#10b981' }}></span>Fault classification</li>
                      <li><span className="list-dot" style={{ background: '#10b981' }}></span>Severity assessment</li>
                    </ul>
                  </div>

                  {/* Arrow 2: horizontal right */}
                  <div className="workflow-arrow-h">
                    <svg viewBox="0 0 120 40" className="arrow-svg-h">
                      <defs>
                        <linearGradient id="arrowGrad2" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#10b981" stopOpacity="0" />
                          <stop offset="50%" stopColor="#eab308" stopOpacity="1" />
                          <stop offset="100%" stopColor="#eab308" stopOpacity="0" />
                        </linearGradient>
                        <filter id="glowFilter2">
                          <feGaussianBlur stdDeviation="3" result="blur" />
                          <feMerge>
                            <feMergeNode in="blur" />
                            <feMergeNode in="SourceGraphic" />
                          </feMerge>
                        </filter>
                      </defs>
                      <line x1="0" y1="20" x2="100" y2="20" stroke="rgba(234,179,8,0.15)" strokeWidth="2" />
                      <polygon points="100,12 120,20 100,28" fill="rgba(234,179,8,0.2)" />
                      <line x1="0" y1="20" x2="100" y2="20" stroke="url(#arrowGrad2)" strokeWidth="3" filter="url(#glowFilter2)" className="neon-travel-h" />
                      <polygon points="100,12 120,20 100,28" fill="#eab308" className="arrow-head-pulse" filter="url(#glowFilter2)" />
                    </svg>
                  </div>

                  <div className="workflow-box workflow-box-4" id="box-result">
                    <div className="workflow-box-icon">📋</div>
                    <h3 className="workflow-box-heading" style={{ color: '#f59e0b' }}>4. Result</h3>
                    <p className="workflow-box-desc">
                      Detected faults, severity level, and recommended actions are presented to the user.
                    </p>
                    <ul className="workflow-box-list">
                      <li><span className="list-dot" style={{ background: '#f59e0b' }}></span>Fault type and severity</li>
                      <li><span className="list-dot" style={{ background: '#f59e0b' }}></span>Actionable recommendations</li>
                      <li><span className="list-dot" style={{ background: '#f59e0b' }}></span>Detailed analysis report</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            <button className="stop-btn" onClick={() => setRunning(false)}>
              Stop Simulation
            </button>

            {d && (
              <div className="dashboard-grid">
                {/* Row 1: Gauges — RPM & Speed */}
                <div className="row-label">Performance</div>
                <div className="dashboard-row">
                  <div className="dashboard-card" id="gauge-rpm">
                    <div className="card-title">RPM</div>
                    <GaugeChart
                      value={val("engine_rpm_")}
                      max={8000}
                      label="RPM"
                      unit="RPM"
                      color="#a855f7"
                    />
                  </div>
                  <div className="dashboard-card" id="gauge-speed">
                    <div className="card-title">Speed</div>
                    <GaugeChart
                      value={val("vehicle_speed_")}
                      max={240}
                      label="Speed"
                      unit="km/h"
                      color="#3b82f6"
                    />
                  </div>
                </div>

                {/* Row 2: Line Charts — Temperature & Voltage */}
                <div className="row-label">Thermal & Electrical</div>
                <div className="dashboard-row">
                  <div className="dashboard-card" id="chart-temp">
                    <div className="card-title">Temperature</div>
                    <SmoothLineChart
                      value={val("coolant_temperature_")}
                      label="Temperature"
                      unit="°C"
                      color="#f97316"
                      minY={0}
                      maxY={150}
                    />
                  </div>
                  <div className="dashboard-card" id="chart-voltage">
                    <div className="card-title">Voltage</div>
                    <SmoothLineChart
                      value={val("control_module_voltage_")}
                      label="Voltage"
                      unit="V"
                      color="#22d3ee"
                      minY={10}
                      maxY={16}
                    />
                  </div>
                </div>

                {/* Row 3: Doughnut Charts — Engine Load & Throttle */}
                <div className="row-label">Engine</div>
                <div className="dashboard-row">
                  <div className="dashboard-card" id="doughnut-load">
                    <div className="card-title">Engine Load</div>
                    <DoughnutChart
                      value={val("engine_load_")}
                      label="Engine Load"
                      unit="%"
                      color="#a855f7"
                    />
                  </div>
                  <div className="dashboard-card" id="doughnut-throttle">
                    <div className="card-title">Throttle</div>
                    <DoughnutChart
                      value={val("throttle_")}
                      label="Throttle"
                      unit="%"
                      color="#10b981"
                    />
                  </div>
                </div>

                {/* Row 4: Line Charts — Intake Temp & Fuel Level */}
                <div className="row-label">Intake & Fuel</div>
                <div className="dashboard-row">
                  <div className="dashboard-card" id="chart-intake">
                    <div className="card-title">Intake Temp</div>
                    <SmoothLineChart
                      value={val("intake_air_temp_")}
                      label="Intake Temp"
                      unit="°C"
                      color="#f43f5e"
                      minY={0}
                      maxY={100}
                    />
                  </div>
                  <div className="dashboard-card" id="chart-fuel">
                    <div className="card-title">Fuel Level</div>
                    <SmoothLineChart
                      value={val("fuel_tank_")}
                      label="Fuel Level"
                      unit="%"
                      color="#eab308"
                      minY={0}
                      maxY={100}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Navigate to AI Analysis — still passes the last fetched row */}
            <div>
              <button
                className="view-btn"
                onClick={() =>
                  navigate("/analysis", {
                    state: { data: currentRow, faults: [], analysis: null },
                  })
                }
              >
                View AI Analysis
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
