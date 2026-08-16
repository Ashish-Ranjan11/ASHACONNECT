import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./role-workspace.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function getToken() {
  return (
    localStorage.getItem("token") ||
    localStorage.getItem("authToken") ||
    localStorage.getItem("access_token")
  );
}

function decodeToken(token) {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return {};
  }
}

async function request(path, token, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
      ...(options.headers || {}),
    },
  });

  const text = await response.text();

  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    throw new Error(data?.detail || data?.message || data || `Request failed: ${response.status}`);
  }

  return data;
}

function asArray(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.data)) return value.data;
  if (Array.isArray(value?.items)) return value.items;
  return [];
}

function workspaceTitle(role) {
  if (role === "phc_admin") return "PHC Command Workspace";
  if (role === "supervisor") return "Field Supervision Workspace";
  return "ASHA Care Workspace";
}

function workspaceDescription(role) {
  if (role === "phc_admin") {
    return "Manage PHC-level ASHA operations, staff visibility, risk monitoring, audit logs and care delivery performance.";
  }

  if (role === "supervisor") {
    return "Monitor field workers, village-level alerts, high-risk cases, missed follow-ups and workflow progress.";
  }

  return "Manage assigned beneficiaries, daily care tasks, follow-ups, pregnancy tracking, immunization work and field safety.";
}

function Metric({ label, value, tone = "" }) {
  return (
    <div className={`roleMetric ${tone}`}>
      <span>{label}</span>
      <b>{value ?? 0}</b>
    </div>
  );
}

function Empty({ title, text }) {
  return (
    <div className="roleEmpty">
      <div />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function RoleWorkspace() {
  const [token, setToken] = useState(getToken());
  const [open, setOpen] = useState(false);
  const [me, setMe] = useState(null);
  const [scope, setScope] = useState(null);
  const [tasks, setTasks] = useState(null);
  const [monitoring, setMonitoring] = useState(null);
  const [workers, setWorkers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [message, setMessage] = useState("");

  const decoded = decodeToken(token || "");
  const role = decoded.role || me?.role || "asha";

  async function loadRoleData() {
    if (!token) return;

    setMessage("");

    try {
      const [meResult, scopeResult, taskResult, monitorResult] = await Promise.allSettled([
        request("/api/auth/me", token),
        request("/api/security/access-scope", token),
        request("/api/tasks/today", token),
        request("/api/monitoring/overview", token),
      ]);

      if (meResult.status === "fulfilled") setMe(meResult.value);
      if (scopeResult.status === "fulfilled") setScope(scopeResult.value);
      if (taskResult.status === "fulfilled") setTasks(taskResult.value);
      if (monitorResult.status === "fulfilled") setMonitoring(monitorResult.value);

      const resolvedRole =
        decoded.role ||
        meResult.value?.role ||
        scopeResult.value?.current_user?.role ||
        "asha";

      if (resolvedRole === "phc_admin" || resolvedRole === "supervisor") {
        const [workerResult, auditResult] = await Promise.allSettled([
          request("/api/security/workers", token),
          request("/api/security/audit-logs", token),
        ]);

        if (workerResult.status === "fulfilled") setWorkers(asArray(workerResult.value));
        if (auditResult.status === "fulfilled") setAuditLogs(asArray(auditResult.value));
      } else {
        setWorkers([]);
        setAuditLogs([]);
      }
    } catch (err) {
      setMessage(err.message || "Could not load role workspace.");
    }
  }

  useEffect(() => {
    const check = () => setToken(getToken());

    check();

    const interval = setInterval(check, 700);
    window.addEventListener("focus", check);

    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", check);
    };
  }, []);

  useEffect(() => {
    if (token && open) {
      loadRoleData();
    }
  }, [token, open]);

  if (!token) return null;

  const taskSummary = tasks?.summary || {};
  const taskRows = asArray(tasks?.tasks);
  const monitorSummary = monitoring?.summary || {};
  const alerts = asArray(monitoring?.smart_alerts);
  const highRisk = asArray(monitoring?.high_risk_cases);
  const villages = asArray(monitoring?.village_summary);

  return (
    <>
      <button className="roleWorkspaceButton" type="button" onClick={() => setOpen(true)}>
        <span />
        <section>
          <b>{workspaceTitle(role)}</b>
          <small>{role}</small>
        </section>
      </button>

      {open && (
        <div className="roleOverlay">
          <section className="roleDialog">
            <aside className="roleSidebar">
              <div className="roleBrand">
                <div />
                <section>
                  <b>ASHA CONNECT</b>
                  <span>{workspaceTitle(role)}</span>
                </section>
              </div>

              <div className="roleIdentity">
                <span>Signed in as</span>
                <b>{me?.name || decoded.email || "ASHA User"}</b>
                <p>{workspaceDescription(role)}</p>
              </div>

              <button type="button" onClick={loadRoleData}>
                Refresh Workspace
              </button>
            </aside>

            <main className="roleMain">
              <button className="roleClose" type="button" onClick={() => setOpen(false)}>
                ×
              </button>

              <header className="roleHero">
                <p>Secure Staff Workspace</p>
                <h2>{workspaceTitle(role)}</h2>
                <span>{workspaceDescription(role)}</span>
              </header>

              {message && <div className="roleMessage">{message}</div>}

              {role === "asha" && (
                <>
                  <div className="roleMetrics">
                    <Metric label="Daily Tasks" value={taskSummary.total_tasks || 0} />
                    <Metric label="High Priority" value={taskSummary.high_priority || 0} tone="danger" />
                    <Metric label="Medium Priority" value={taskSummary.medium_priority || 0} tone="warning" />
                    <Metric label="Access Scope" value={scope?.visible_worker_ids?.length || 1} />
                  </div>

                  <section className="rolePanel">
                    <div className="rolePanelHead">
                      <h3>My Daily ASHA Care Queue</h3>
                      <span>Own assigned workflow</span>
                    </div>

                    {!taskRows.length ? (
                      <Empty
                        title="No tasks yet"
                        text="Appointments, pregnancy records and immunization records will generate tasks here."
                      />
                    ) : (
                      <div className="roleList">
                        {taskRows.slice(0, 10).map((task, index) => (
                          <article className={`roleListItem ${task.priority || ""}`} key={index}>
                            <b>{task.title}</b>
                            <p>{task.reason}</p>
                            <small>{task.action}</small>
                          </article>
                        ))}
                      </div>
                    )}
                  </section>

                  <section className="rolePanel">
                    <div className="rolePanelHead">
                      <h3>High Risk Cases Under My Scope</h3>
                      <span>{highRisk.length}</span>
                    </div>

                    {!highRisk.length ? (
                      <Empty title="No high-risk cases" text="No critical case is visible in your current scope." />
                    ) : (
                      <div className="roleList">
                        {highRisk.slice(0, 8).map((item) => (
                          <article className="roleListItem" key={item.beneficiary_id}>
                            <b>{item.name}</b>
                            <p>{item.village} · ASHA: {item.asha_worker_name}</p>
                            <small>Risk Score: {item.risk?.score || 0}%</small>
                          </article>
                        ))}
                      </div>
                    )}
                  </section>
                </>
              )}

              {role === "phc_admin" && (
                <>
                  <div className="roleMetrics">
                    <Metric label="ASHA Workers" value={workers.length} />
                    <Metric label="High Risk" value={monitorSummary.high_risk || 0} tone="danger" />
                    <Metric label="SOS Alerts" value={monitorSummary.sos_alerts || 0} tone="danger" />
                    <Metric label="Audit Logs" value={auditLogs.length} />
                  </div>

                  <div className="roleTwo">
                    <section className="rolePanel">
                      <div className="rolePanelHead">
                        <h3>PHC Worker Management</h3>
                        <span>Admin access</span>
                      </div>

                      <div className="roleTableWrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Name</th>
                              <th>Role</th>
                              <th>Village</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {workers.map((worker) => (
                              <tr key={worker.worker_id}>
                                <td>
                                  <b>{worker.name}</b>
                                  <small>{worker.email}</small>
                                </td>
                                <td>{worker.role}</td>
                                <td>{worker.village}</td>
                                <td>{worker.is_active ? "Active" : "Disabled"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </section>

                    <section className="rolePanel">
                      <div className="rolePanelHead">
                        <h3>Recent Audit Logs</h3>
                        <span>Security trail</span>
                      </div>

                      {!auditLogs.length ? (
                        <Empty title="No audit logs" text="Security activity will appear here." />
                      ) : (
                        <div className="roleList">
                          {auditLogs.slice(0, 10).map((log) => (
                            <article className="roleListItem" key={log.id}>
                              <b>{log.action}</b>
                              <p>{log.actor_role} · {log.details}</p>
                              <small>{log.created_at}</small>
                            </article>
                          ))}
                        </div>
                      )}
                    </section>
                  </div>
                </>
              )}

              {role === "supervisor" && (
                <>
                  <div className="roleMetrics">
                    <Metric label="Workers" value={workers.length} />
                    <Metric label="Villages" value={villages.length} />
                    <Metric label="High Risk" value={monitorSummary.high_risk || 0} tone="danger" />
                    <Metric label="Alerts" value={alerts.length} tone="warning" />
                  </div>

                  <div className="roleTwo">
                    <section className="rolePanel">
                      <div className="rolePanelHead">
                        <h3>Village Supervision</h3>
                        <span>Field monitoring</span>
                      </div>

                      {!villages.length ? (
                        <Empty title="No village data" text="Village summaries will appear after records are available." />
                      ) : (
                        <div className="roleVillageGrid">
                          {villages.map((village) => (
                            <article className="roleVillage" key={village.village}>
                              <h4>{village.village}</h4>
                              <p><span>Beneficiaries</span><b>{village.beneficiaries}</b></p>
                              <p><span>Children</span><b>{village.children}</b></p>
                              <p><span>High Risk</span><b>{village.high_risk}</b></p>
                            </article>
                          ))}
                        </div>
                      )}
                    </section>

                    <section className="rolePanel">
                      <div className="rolePanelHead">
                        <h3>Supervision Alerts</h3>
                        <span>{alerts.length}</span>
                      </div>

                      {!alerts.length ? (
                        <Empty title="No alerts" text="Supervisor alerts will appear here." />
                      ) : (
                        <div className="roleList">
                          {alerts.slice(0, 10).map((alert, index) => (
                            <article className={`roleListItem ${alert.priority || ""}`} key={index}>
                              <b>{alert.type}</b>
                              <p>{alert.message}</p>
                            </article>
                          ))}
                        </div>
                      )}
                    </section>
                  </div>
                </>
              )}
            </main>
          </section>
        </div>
      )}
    </>
  );
}

const rootId = "role-workspace-root";

if (!document.getElementById(rootId)) {
  const mount = document.createElement("div");
  mount.id = rootId;
  document.body.appendChild(mount);
  createRoot(mount).render(<RoleWorkspace />);
}
