import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./monitoring-widget.css";

function riskClass(level) {
  const value = String(level || "").toLowerCase();

  if (value.includes("high")) return "high";
  if (value.includes("medium")) return "medium";

  return "low";
}

function MonitoringWidget() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(localStorage.getItem("token")));

  async function loadMonitoring() {
    setLoading(true);
    setMessage("");

    try {
      const result = await api("/api/monitoring/overview");
      setData(result);
    } catch (err) {
      setMessage(err.message || "Could not load monitoring dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const checkLogin = () => {
      setIsLoggedIn(Boolean(localStorage.getItem("token")));
    };

    checkLogin();

    const interval = setInterval(checkLogin, 500);
    window.addEventListener("focus", checkLogin);

    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", checkLogin);
    };
  }, []);

  useEffect(() => {
    if (open && isLoggedIn) {
      loadMonitoring();
    }
  }, [open, isLoggedIn]);

  if (!isLoggedIn) {
    return null;
  }

  const summary = data?.summary || {};

  return (
    <>
      <button
        className="monitorFloatButton"
        type="button"
        onClick={() => setOpen(true)}
      >
        📊 Risk Monitor
      </button>

      {open && (
        <div className="monitorOverlay">
          <div className="monitorPanel">
            <div className="monitorTop">
              <div>
                <p>PHC / Supervisor Monitoring</p>
                <h2>Risk & Performance Dashboard</h2>
                <span>
                  Role: {data?.current_user?.role || "asha"} • User:{" "}
                  {data?.current_user?.name || "Demo User"}
                </span>
              </div>

              <button
                type="button"
                className="monitorClose"
                onClick={() => {
                  setOpen(false);
                  setData(null);
                  setMessage("");
                }}
              >
                ×
              </button>
            </div>

            <div className="monitorActions">
              <button type="button" onClick={loadMonitoring} disabled={loading}>
                {loading ? "Refreshing..." : "Refresh Monitor"}
              </button>
            </div>

            {message && <div className="monitorMessage">{message}</div>}

            {!data ? (
              <div className="monitorEmpty">
                <span>📊</span>
                <h3>{loading ? "Loading monitoring data..." : "Open monitoring dashboard"}</h3>
                <p>
                  This dashboard shows risk cases, ASHA performance, village summary,
                  missed appointments and pending care alerts.
                </p>
              </div>
            ) : (
              <>
                <div className="monitorStatsGrid">
                  <div>
                    <b>{summary.asha_workers || 0}</b>
                    <span>ASHA Workers</span>
                  </div>

                  <div>
                    <b>{summary.beneficiaries || 0}</b>
                    <span>Beneficiaries</span>
                  </div>

                  <div className="dangerStat">
                    <b>{summary.high_risk || 0}</b>
                    <span>High Risk</span>
                  </div>

                  <div className="warningStat">
                    <b>{summary.medium_risk || 0}</b>
                    <span>Medium Risk</span>
                  </div>

                  <div>
                    <b>{summary.missed_appointments || 0}</b>
                    <span>Missed Visits</span>
                  </div>

                  <div>
                    <b>{summary.pending_immunizations || 0}</b>
                    <span>Pending Immunization</span>
                  </div>

                  <div>
                    <b>{summary.active_pregnancies || 0}</b>
                    <span>Active Pregnancy</span>
                  </div>

                  <div>
                    <b>{summary.sos_alerts || 0}</b>
                    <span>SOS Alerts</span>
                  </div>
                </div>

                <div className="monitorGrid">
                  <section className="monitorCard">
                    <div className="monitorSectionHead">
                      <h3>Smart Alerts</h3>
                      <span>{data.smart_alerts?.length || 0}</span>
                    </div>

                    {!data.smart_alerts?.length ? (
                      <p className="monitorMuted">No urgent alerts right now.</p>
                    ) : (
                      <div className="alertList">
                        {data.smart_alerts.map((item, index) => (
                          <div className={`smartAlert ${item.priority}`} key={index}>
                            <b>{item.type}</b>
                            <p>{item.message}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>

                  <section className="monitorCard">
                    <div className="monitorSectionHead">
                      <h3>High Risk Cases</h3>
                      <span>{data.high_risk_cases?.length || 0}</span>
                    </div>

                    {!data.high_risk_cases?.length ? (
                      <p className="monitorMuted">No high-risk beneficiaries.</p>
                    ) : (
                      <div className="riskCaseList">
                        {data.high_risk_cases.slice(0, 6).map((item) => (
                          <div className="riskCase" key={item.beneficiary_id}>
                            <div>
                              <b>{item.name}</b>
                              <p>{item.village} • {item.category}</p>
                              <small>ASHA: {item.asha_worker_name}</small>
                            </div>

                            <div className={`riskBadge ${riskClass(item.risk?.level)}`}>
                              {item.risk?.score || 0}%
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                </div>

                <section className="monitorCard">
                  <div className="monitorSectionHead">
                    <h3>ASHA Worker Performance</h3>
                    <span>{data.worker_performance?.length || 0} workers</span>
                  </div>

                  <div className="monitorTableWrap">
                    <table className="monitorTable">
                      <thead>
                        <tr>
                          <th>ASHA Worker</th>
                          <th>Village</th>
                          <th>Beneficiaries</th>
                          <th>Appointments</th>
                          <th>Missed</th>
                          <th>SOS</th>
                          <th>High Risk</th>
                        </tr>
                      </thead>

                      <tbody>
                        {(data.worker_performance || []).map((worker) => (
                          <tr key={worker.worker_id}>
                            <td>
                              <b>{worker.name}</b>
                              <small>{worker.role}</small>
                            </td>
                            <td>{worker.village}</td>
                            <td>{worker.beneficiaries}</td>
                            <td>{worker.appointments}</td>
                            <td>{worker.missed_appointments}</td>
                            <td>{worker.sos_alerts}</td>
                            <td>
                              <span className="dangerPill">{worker.high_risk_cases}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section className="monitorCard">
                  <div className="monitorSectionHead">
                    <h3>Village-wise Health Summary</h3>
                    <span>{data.village_summary?.length || 0} villages</span>
                  </div>

                  <div className="villageGrid">
                    {(data.village_summary || []).map((village) => (
                      <div className="villageCard" key={village.village}>
                        <h4>{village.village}</h4>

                        <div>
                          <span>Beneficiaries</span>
                          <b>{village.beneficiaries}</b>
                        </div>

                        <div>
                          <span>Pregnant</span>
                          <b>{village.pregnant}</b>
                        </div>

                        <div>
                          <span>Children</span>
                          <b>{village.children}</b>
                        </div>

                        <div>
                          <span>High Risk</span>
                          <b>{village.high_risk}</b>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

const rootId = "monitoring-widget-root";

if (!document.getElementById(rootId)) {
  const mount = document.createElement("div");
  mount.id = rootId;
  document.body.appendChild(mount);
  createRoot(mount).render(<MonitoringWidget />);
}
