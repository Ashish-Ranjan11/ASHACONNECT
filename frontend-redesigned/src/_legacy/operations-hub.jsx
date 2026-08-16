import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./operations-hub.css";

const tabs = [
  { key: "overview", label: "Command Overview" },
  { key: "tasks", label: "Daily Tasks" },
  { key: "risk", label: "Risk Monitor" },
  { key: "individual", label: "Individual Portfolio" },
  { key: "family", label: "Family Portfolio" },
  { key: "register", label: "Register Details" },
];

const emptyRegisterForm = {
  beneficiary_id: "",
  education: "",
  occupation_type: "",
  occupation_detail: "",
  marital_status: "",
  religion: "",
  family_baby_count: 0,
  last_baby_birth_date: "",
};

function riskClass(level) {
  const value = String(level || "").toLowerCase();
  if (value.includes("high")) return "high";
  if (value.includes("medium")) return "medium";
  return "low";
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function Metric({ label, value, tone = "default" }) {
  return (
    <div className={`oh-metric ${tone}`}>
      <span>{label}</span>
      <b>{value ?? 0}</b>
    </div>
  );
}

function Panel({ title, subtitle, children, right }) {
  return (
    <section className="oh-panel">
      <div className="oh-panel-head">
        <div>
          <h3>{title}</h3>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

function EmptyState({ title, text }) {
  return (
    <div className="oh-empty">
      <div className="oh-empty-mark" />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function goToWorkspace(label) {
  const targets = Array.from(document.querySelectorAll("button, a, [role='button']"));
  const found = targets.find((el) =>
    String(el.textContent || "").toLowerCase().includes(label.toLowerCase())
  );

  if (found) {
    found.click();
  }
}

function OperationsHub() {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(localStorage.getItem("token")));
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [tasks, setTasks] = useState(null);
  const [monitoring, setMonitoring] = useState(null);
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [families, setFamilies] = useState([]);
  const [selectedBeneficiaryId, setSelectedBeneficiaryId] = useState("");
  const [selectedFamilyName, setSelectedFamilyName] = useState("");
  const [profile, setProfile] = useState(null);
  const [familyPortfolio, setFamilyPortfolio] = useState(null);
  const [registerForm, setRegisterForm] = useState(emptyRegisterForm);

  const selectedBeneficiary = useMemo(() => {
    return beneficiaries.find(
      (item) => String(item.beneficiary_id || item.id) === String(selectedBeneficiaryId)
    );
  }, [beneficiaries, selectedBeneficiaryId]);

  async function loadAll() {
    setLoading(true);
    setMessage("");

    try {
      const [taskData, monitorData, beneficiaryData, familyData] = await Promise.allSettled([
        api("/api/tasks/today"),
        api("/api/monitoring/overview"),
        api("/api/beneficiaries"),
        api("/api/families"),
      ]);

      if (taskData.status === "fulfilled") setTasks(taskData.value);
      if (monitorData.status === "fulfilled") setMonitoring(monitorData.value);

      if (beneficiaryData.status === "fulfilled") {
        const list = safeArray(beneficiaryData.value);
        setBeneficiaries(list);

        if (list.length && !selectedBeneficiaryId) {
          const firstId = list[0].beneficiary_id || list[0].id;
          setSelectedBeneficiaryId(firstId);
          hydrateRegisterForm(firstId, list);
        }
      }

      if (familyData.status === "fulfilled") {
        const list = safeArray(familyData.value);
        setFamilies(list);

        if (list.length && !selectedFamilyName) {
          setSelectedFamilyName(list[0].family_name);
        }
      }
    } catch (err) {
      setMessage(err.message || "Unable to load operations hub.");
    } finally {
      setLoading(false);
    }
  }

  async function loadTasks() {
    setLoading(true);
    setMessage("");

    try {
      setTasks(await api("/api/tasks/today"));
    } catch (err) {
      setMessage(err.message || "Could not generate daily tasks.");
    } finally {
      setLoading(false);
    }
  }

  async function loadMonitoring() {
    setLoading(true);
    setMessage("");

    try {
      setMonitoring(await api("/api/monitoring/overview"));
    } catch (err) {
      setMessage(err.message || "Could not load risk monitoring.");
    } finally {
      setLoading(false);
    }
  }

  async function loadIndividualProfile(id = selectedBeneficiaryId) {
    if (!id) {
      setMessage("Select a beneficiary first.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      setProfile(await api(`/api/beneficiaries/${id}/profile`));
    } catch (err) {
      setMessage(err.message || "Could not load beneficiary portfolio.");
    } finally {
      setLoading(false);
    }
  }

  async function loadFamilyPortfolio(name = selectedFamilyName) {
    if (!name) {
      setMessage("Select a family first.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      setFamilyPortfolio(await api(`/api/families/${encodeURIComponent(name)}/portfolio`));
    } catch (err) {
      setMessage(err.message || "Could not load family portfolio.");
    } finally {
      setLoading(false);
    }
  }

  function hydrateRegisterForm(id, source = beneficiaries) {
    const item = source.find((row) => String(row.beneficiary_id || row.id) === String(id));

    if (!item) {
      setRegisterForm({ ...emptyRegisterForm, beneficiary_id: id || "" });
      return;
    }

    setRegisterForm({
      beneficiary_id: item.beneficiary_id || item.id,
      education: item.education || "",
      occupation_type: item.occupation_type || "",
      occupation_detail: item.occupation_detail || "",
      marital_status: item.marital_status || "",
      religion: item.religion || "",
      family_baby_count: item.family_baby_count || 0,
      last_baby_birth_date: item.last_baby_birth_date || "",
    });
  }

  async function saveRegisterDetails(e) {
    e.preventDefault();

    if (!registerForm.beneficiary_id) {
      setMessage("Select a beneficiary first.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      await api(`/api/beneficiaries/${registerForm.beneficiary_id}`, {
        method: "PUT",
        body: JSON.stringify(registerForm),
      });

      setMessage("Register details updated successfully.");

      const rows = await api("/api/beneficiaries");
      setBeneficiaries(safeArray(rows));
    } catch (err) {
      setMessage(err.message || "Could not update register details.");
    } finally {
      setLoading(false);
    }
  }

  async function triggerSOS() {
    setLoading(true);
    setMessage("");

    try {
      await api("/api/sos", {
        method: "POST",
        body: JSON.stringify({}),
      });

      setMessage("SOS alert triggered successfully.");
      await loadMonitoring();
    } catch (err) {
      setMessage(err.message || "Could not trigger SOS.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const checkLogin = () => setIsLoggedIn(Boolean(localStorage.getItem("token")));

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
      loadAll();
    }
  }, [open, isLoggedIn]);

  useEffect(() => {
    if (selectedBeneficiaryId) {
      hydrateRegisterForm(selectedBeneficiaryId);
    }
  }, [selectedBeneficiaryId]);

  if (!isLoggedIn) return null;

  const taskSummary = tasks?.summary || {};
  const monitorSummary = monitoring?.summary || {};
  const taskRows = safeArray(tasks?.tasks);
  const alerts = safeArray(monitoring?.smart_alerts);
  const highRisk = safeArray(monitoring?.high_risk_cases);
  const workers = safeArray(monitoring?.worker_performance);
  const villages = safeArray(monitoring?.village_summary);

  const profileBeneficiary = profile?.beneficiary || {};
  const profileRisk = profile?.risk || {};

  const family = familyPortfolio?.family || {};
  const familyRisk = familyPortfolio?.family_risk || {};
  const familyMembers = safeArray(familyPortfolio?.members);

  return (
    <>
      <button className="oh-launcher" type="button" onClick={() => setOpen(true)}>
        <span />
        Operations Hub
      </button>

      {open && (
        <div className="oh-overlay">
          <div className="oh-shell">
            <aside className="oh-nav">
              <div className="oh-brand">
                <div>AC</div>
                <section>
                  <b>ASHA CONNECT</b>
                  <span>Healthcare Operations Suite</span>
                </section>
              </div>

              <nav>
                {tabs.map((tab) => (
                  <button
                    key={tab.key}
                    type="button"
                    className={activeTab === tab.key ? "active" : ""}
                    onClick={() => setActiveTab(tab.key)}
                  >
                    {tab.label}
                  </button>
                ))}
              </nav>

              <div className="oh-system-card">
                <span>System Status</span>
                <b>Live Operations</b>
                <p>Connected to local ASHACONNECT backend.</p>
              </div>
            </aside>

            <main className="oh-main">
              <header className="oh-header">
                <div>
                  <p>Command Center</p>
                  <h1>Healthcare Workflow Management</h1>
                  <span>
                    Beneficiary records, family portfolios, risk monitoring and daily ASHA work automation in one place.
                  </span>
                </div>

                <div className="oh-header-actions">
                  <button type="button" onClick={loadAll} disabled={loading}>
                    {loading ? "Refreshing..." : "Refresh Data"}
                  </button>
                  <button type="button" className="danger" onClick={triggerSOS}>
                    Trigger SOS
                  </button>
                  <button type="button" className="ghost" onClick={() => setOpen(false)}>
                    Close
                  </button>
                </div>
              </header>

              {message && <div className="oh-message">{message}</div>}

              {activeTab === "overview" && (
                <>
                  <div className="oh-metrics-grid">
                    <Metric label="Beneficiaries" value={monitorSummary.beneficiaries || beneficiaries.length} />
                    <Metric label="Daily Tasks" value={taskSummary.total_tasks || 0} />
                    <Metric label="High Risk Cases" value={monitorSummary.high_risk || 0} tone="danger" />
                    <Metric label="Pending Immunization" value={monitorSummary.pending_immunizations || 0} tone="warning" />
                    <Metric label="ASHA Workers" value={monitorSummary.asha_workers || 0} />
                    <Metric label="SOS Alerts" value={monitorSummary.sos_alerts || 0} tone="danger" />
                  </div>

                  <div className="oh-action-grid">
                    {[
                      ["Dashboard", "Open operational dashboard"],
                      ["Beneficiaries", "Manage person-level records"],
                      ["Pregnancy", "Track ANC and maternal records"],
                      ["Immunization", "Track child vaccine records"],
                      ["Appointments", "Schedule follow-up visits"],
                      ["Events", "Manage outreach activities"],
                      ["Notices", "Send beneficiary communication"],
                      ["Reports", "Generate reports"],
                    ].map(([label, text]) => (
                      <button
                        key={label}
                        type="button"
                        onClick={() => {
                          goToWorkspace(label);
                          setOpen(false);
                        }}
                      >
                        <b>{label}</b>
                        <span>{text}</span>
                      </button>
                    ))}
                  </div>

                  <div className="oh-two-col">
                    <Panel title="Priority Alerts" subtitle="Cases that need attention">
                      {!alerts.length ? (
                        <EmptyState title="No urgent alerts" text="No immediate operational warnings found." />
                      ) : (
                        <div className="oh-list">
                          {alerts.slice(0, 6).map((item, index) => (
                            <div className={`oh-list-row ${item.priority || ""}`} key={index}>
                              <b>{item.type}</b>
                              <p>{item.message}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </Panel>

                    <Panel title="High Risk Beneficiaries" subtitle="Clinical or workflow risk indicators">
                      {!highRisk.length ? (
                        <EmptyState title="No high-risk cases" text="Risk monitor has not found critical cases." />
                      ) : (
                        <div className="oh-list">
                          {highRisk.slice(0, 6).map((item) => (
                            <div className="oh-risk-row" key={item.beneficiary_id}>
                              <div>
                                <b>{item.name}</b>
                                <p>{item.village} • ASHA: {item.asha_worker_name}</p>
                              </div>
                              <span className={`oh-risk-pill ${riskClass(item.risk?.level)}`}>
                                {item.risk?.score || 0}%
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </Panel>
                  </div>
                </>
              )}

              {activeTab === "tasks" && (
                <Panel
                  title="Daily ASHA Work Plan"
                  subtitle="Automatically generated from appointments, pregnancy, immunization, SOS and event records"
                  right={<button className="oh-small-btn" onClick={loadTasks}>Regenerate</button>}
                >
                  <div className="oh-metrics-grid compact">
                    <Metric label="Total Tasks" value={taskSummary.total_tasks || 0} />
                    <Metric label="High Priority" value={taskSummary.high_priority || 0} tone="danger" />
                    <Metric label="Medium Priority" value={taskSummary.medium_priority || 0} tone="warning" />
                    <Metric label="Low Priority" value={taskSummary.low_priority || 0} />
                  </div>

                  {!taskRows.length ? (
                    <EmptyState title="No tasks generated" text="Generate tasks after adding appointments, pregnancy records or immunization records." />
                  ) : (
                    <div className="oh-task-list">
                      {taskRows.map((item, index) => (
                        <article className={`oh-task ${item.priority}`} key={index}>
                          <div>
                            <span>{item.priority}</span>
                            <b>{item.title}</b>
                            <p>{item.reason}</p>
                          </div>
                          <section>
                            {item.beneficiary_name && <small>Beneficiary: {item.beneficiary_name}</small>}
                            {item.beneficiary_phone && <small>Phone: {item.beneficiary_phone}</small>}
                            {item.village && <small>Family/Village: {item.village}</small>}
                            {item.due_date && <small>Due: {item.due_date}</small>}
                            <small>Action: {item.action}</small>
                          </section>
                        </article>
                      ))}
                    </div>
                  )}
                </Panel>
              )}

              {activeTab === "risk" && (
                <>
                  <div className="oh-metrics-grid">
                    <Metric label="High Risk" value={monitorSummary.high_risk || 0} tone="danger" />
                    <Metric label="Medium Risk" value={monitorSummary.medium_risk || 0} tone="warning" />
                    <Metric label="Missed Visits" value={monitorSummary.missed_appointments || 0} tone="danger" />
                    <Metric label="Pending Immunization" value={monitorSummary.pending_immunizations || 0} tone="warning" />
                  </div>

                  <Panel title="ASHA Worker Performance" subtitle="Supervisor and PHC-level operations view">
                    <div className="oh-table-wrap">
                      <table className="oh-table">
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
                          {workers.map((worker) => (
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
                              <td>{worker.high_risk_cases}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Panel>

                  <Panel title="Village-wise Health Summary" subtitle="Coverage distribution by household group">
                    <div className="oh-village-grid">
                      {villages.map((village) => (
                        <div className="oh-village-card" key={village.village}>
                          <h4>{village.village}</h4>
                          <p><span>Beneficiaries</span><b>{village.beneficiaries}</b></p>
                          <p><span>Pregnant</span><b>{village.pregnant}</b></p>
                          <p><span>Children</span><b>{village.children}</b></p>
                          <p><span>High Risk</span><b>{village.high_risk}</b></p>
                        </div>
                      ))}
                    </div>
                  </Panel>
                </>
              )}

              {activeTab === "individual" && (
                <Panel
                  title="Individual Health Portfolio"
                  subtitle="Open complete beneficiary profile with risk, timeline and clinical records"
                  right={<button className="oh-small-btn" onClick={() => loadIndividualProfile()}>Open Profile</button>}
                >
                  <div className="oh-control-row">
                    <select
                      value={selectedBeneficiaryId}
                      onChange={(e) => {
                        setSelectedBeneficiaryId(e.target.value);
                        setProfile(null);
                      }}
                    >
                      {beneficiaries.map((item) => (
                        <option key={item.beneficiary_id || item.id} value={item.beneficiary_id || item.id}>
                          {item.full_name || item.name} — {item.address || "No family"}
                        </option>
                      ))}
                    </select>
                  </div>

                  {!profile ? (
                    <EmptyState title="Select and open a profile" text="Use Open Profile to view beneficiary risk, timeline and care records." />
                  ) : (
                    <>
                      <div className="oh-profile-hero">
                        <div>
                          <h2>{profileBeneficiary.full_name || profileBeneficiary.name}</h2>
                          <p>{profileBeneficiary.category} • {profileBeneficiary.gender} • Age {profileBeneficiary.age}</p>
                          <p>Family: {profileBeneficiary.address || "N/A"}</p>
                          <p>ASHA Worker: {profile.asha_worker?.name || "N/A"}</p>
                        </div>
                        <span className={`oh-score ${riskClass(profileRisk.level)}`}>
                          <b>{profileRisk.score || 0}%</b>
                          {profileRisk.level || "Low Risk"}
                        </span>
                      </div>

                      <div className="oh-two-col">
                        <Panel title="Risk Reasons">
                          <ul className="oh-clean-list">
                            {safeArray(profileRisk.reasons).map((item, index) => <li key={index}>{item}</li>)}
                          </ul>
                        </Panel>

                        <Panel title="Next ASHA Actions">
                          <ul className="oh-clean-list">
                            {safeArray(profile.next_actions).map((item, index) => <li key={index}>{item}</li>)}
                          </ul>
                        </Panel>
                      </div>

                      <Panel title="Care Timeline">
                        <div className="oh-timeline">
                          {safeArray(profile.timeline).map((item, index) => (
                            <div key={index}>
                              <span>{item.type}</span>
                              <b>{item.title}</b>
                              <p>{item.detail}</p>
                              <time>{item.date || "N/A"}</time>
                            </div>
                          ))}
                        </div>
                      </Panel>
                    </>
                  )}
                </Panel>
              )}

              {activeTab === "family" && (
                <Panel
                  title="Family Health Portfolio"
                  subtitle="Household-level care profile based on family group from ASHA register"
                  right={<button className="oh-small-btn" onClick={() => loadFamilyPortfolio()}>Open Family</button>}
                >
                  <div className="oh-control-row">
                    <select
                      value={selectedFamilyName}
                      onChange={(e) => {
                        setSelectedFamilyName(e.target.value);
                        setFamilyPortfolio(null);
                      }}
                    >
                      {families.map((item) => (
                        <option key={item.family_name} value={item.family_name}>
                          {item.family_name} — {item.members} members
                        </option>
                      ))}
                    </select>
                  </div>

                  {!familyPortfolio ? (
                    <EmptyState title="Select and open a family" text="Use Open Family to view household members, risk, timeline and recommended actions." />
                  ) : (
                    <>
                      <div className="oh-profile-hero">
                        <div>
                          <h2>{family.family_name}</h2>
                          <p>Total Members: {family.total_members}</p>
                          <p>ASHA Worker: {family.asha_worker?.name || "N/A"}</p>
                        </div>
                        <span className={`oh-score ${riskClass(familyRisk.level)}`}>
                          <b>{familyRisk.score || 0}%</b>
                          {familyRisk.level || "Low Risk"}
                        </span>
                      </div>

                      <div className="oh-metrics-grid compact">
                        <Metric label="Members" value={family.total_members || 0} />
                        <Metric label="Children" value={family.children || 0} />
                        <Metric label="Elderly" value={family.elderly || 0} />
                        <Metric label="Pregnant" value={family.pregnant || 0} />
                        <Metric label="Appointments" value={familyPortfolio.stats?.appointments || 0} />
                        <Metric label="Immunization" value={familyPortfolio.stats?.immunization_records || 0} />
                      </div>

                      <Panel title="Family Members">
                        <div className="oh-member-grid">
                          {familyMembers.map((item) => {
                            const member = item.member || {};
                            const memberRisk = item.risk || {};
                            return (
                              <div className="oh-member" key={member.beneficiary_id}>
                                <div>{String(member.full_name || member.name || "M").charAt(0)}</div>
                                <section>
                                  <b>{member.full_name || member.name}</b>
                                  <p>{member.age} yrs • {member.gender} • {member.category}</p>
                                  <span className={riskClass(memberRisk.level)}>
                                    {memberRisk.level} • {memberRisk.score}%
                                  </span>
                                </section>
                              </div>
                            );
                          })}
                        </div>
                      </Panel>
                    </>
                  )}
                </Panel>
              )}

              {activeTab === "register" && (
                <Panel title="ASHA Register Details" subtitle="Education, occupation, baby count, marital status and religion">
                  <form className="oh-register-form" onSubmit={saveRegisterDetails}>
                    <label>
                      Beneficiary
                      <select
                        value={registerForm.beneficiary_id}
                        onChange={(e) => {
                          setSelectedBeneficiaryId(e.target.value);
                          hydrateRegisterForm(e.target.value);
                        }}
                      >
                        {beneficiaries.map((item) => (
                          <option key={item.beneficiary_id || item.id} value={item.beneficiary_id || item.id}>
                            {item.full_name || item.name} — {item.address || "No family"}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label>
                      Education
                      <select value={registerForm.education} onChange={(e) => setRegisterForm({ ...registerForm, education: e.target.value })}>
                        <option value="">Select education</option>
                        <option value="Nil">Nil</option>
                        <option value="Primary">Primary</option>
                        <option value="5th Pass">5th Pass</option>
                        <option value="8th Pass">8th Pass</option>
                        <option value="9th Pass">9th Pass</option>
                        <option value="10th Pass">10th Pass</option>
                        <option value="12th Pass">12th Pass</option>
                        <option value="Graduate">Graduate</option>
                        <option value="Post Graduate">Post Graduate</option>
                      </select>
                    </label>

                    <label>
                      Occupation Type
                      <select value={registerForm.occupation_type} onChange={(e) => setRegisterForm({ ...registerForm, occupation_type: e.target.value })}>
                        <option value="">Select occupation</option>
                        <option value="None">None</option>
                        <option value="Student">Student</option>
                        <option value="Business">Business</option>
                        <option value="Private Job">Private Job</option>
                        <option value="Government Job">Government Job</option>
                        <option value="Farming">Farming</option>
                        <option value="Daily Wage">Daily Wage</option>
                        <option value="Homemaker">Homemaker</option>
                        <option value="Other">Other</option>
                      </select>
                    </label>

                    <label>
                      Occupation Detail
                      <input value={registerForm.occupation_detail} onChange={(e) => setRegisterForm({ ...registerForm, occupation_detail: e.target.value })} placeholder="Shop, driver, teacher, farmer" />
                    </label>

                    <label>
                      Marital Status
                      <select value={registerForm.marital_status} onChange={(e) => setRegisterForm({ ...registerForm, marital_status: e.target.value })}>
                        <option value="">Select status</option>
                        <option value="Married">Married</option>
                        <option value="Unmarried">Unmarried</option>
                        <option value="Widow">Widow</option>
                        <option value="Widower">Widower</option>
                        <option value="Separated">Separated</option>
                      </select>
                    </label>

                    <label>
                      Religion
                      <input value={registerForm.religion} onChange={(e) => setRegisterForm({ ...registerForm, religion: e.target.value })} placeholder="Hindu, Buddhist, Christian, Muslim" />
                    </label>

                    <label>
                      Babies in Family
                      <input type="number" min="0" value={registerForm.family_baby_count} onChange={(e) => setRegisterForm({ ...registerForm, family_baby_count: e.target.value })} />
                    </label>

                    <label>
                      Last Baby Birth Date
                      <input type="date" value={registerForm.last_baby_birth_date} onChange={(e) => setRegisterForm({ ...registerForm, last_baby_birth_date: e.target.value })} />
                    </label>

                    <button type="submit" disabled={loading}>
                      {loading ? "Saving..." : "Save Register Details"}
                    </button>
                  </form>

                  {selectedBeneficiary && (
                    <div className="oh-register-preview">
                      <h3>Register Preview</h3>
                      <div>
                        <p><span>Name</span><b>{selectedBeneficiary.full_name || selectedBeneficiary.name}</b></p>
                        <p><span>Family</span><b>{selectedBeneficiary.address || "N/A"}</b></p>
                        <p><span>Education</span><b>{registerForm.education || "N/A"}</b></p>
                        <p><span>Occupation</span><b>{registerForm.occupation_type || "N/A"}</b></p>
                        <p><span>Marital Status</span><b>{registerForm.marital_status || "N/A"}</b></p>
                        <p><span>Religion</span><b>{registerForm.religion || "N/A"}</b></p>
                      </div>
                    </div>
                  )}
                </Panel>
              )}
            </main>
          </div>
        </div>
      )}
    </>
  );
}

const rootId = "operations-hub-root";

if (!document.getElementById(rootId)) {
  const mount = document.createElement("div");
  mount.id = rootId;
  document.body.appendChild(mount);
  createRoot(mount).render(<OperationsHub />);
}
