import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./premium-command-center.css";

const NAV_ITEMS = [
  { key: "home", label: "Command Center" },
  { key: "beneficiaries", label: "Beneficiary Registry" },
  { key: "register", label: "Register Intelligence" },
  { key: "tasks", label: "Daily Care Queue" },
  { key: "risk", label: "Risk & Supervision" },
  { key: "individual", label: "Individual Portfolio" },
  { key: "family", label: "Family Portfolio" },
  { key: "operations", label: "Field Operations" },
];

const emptyBeneficiary = {
  full_name: "",
  age: "",
  gender: "Female",
  contact_no: "",
  address: "",
  category: "general",
};

const emptyRegister = {
  beneficiary_id: "",
  education: "",
  occupation_type: "",
  occupation_detail: "",
  marital_status: "",
  religion: "",
  family_baby_count: 0,
  last_baby_birth_date: "",
};

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function riskClass(level) {
  const value = String(level || "").toLowerCase();
  if (value.includes("high")) return "high";
  if (value.includes("medium")) return "medium";
  return "low";
}

function MetricCard({ label, value, helper, tone = "default" }) {
  return (
    <div className={`pc-metric ${tone}`}>
      <span>{label}</span>
      <b>{value ?? 0}</b>
      {helper && <p>{helper}</p>}
    </div>
  );
}

function Section({ title, subtitle, children, right }) {
  return (
    <section className="pc-section">
      <div className="pc-section-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

function Empty({ title, text }) {
  return (
    <div className="pc-empty">
      <div className="pc-empty-mark" />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function PremiumCommandCenter() {
  const [loggedIn, setLoggedIn] = useState(() => Boolean(localStorage.getItem("token")));
  const [active, setActive] = useState("home");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [me, setMe] = useState(null);
  const [summary, setSummary] = useState(null);
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [families, setFamilies] = useState([]);
  const [tasks, setTasks] = useState(null);
  const [monitoring, setMonitoring] = useState(null);

  const [beneficiaryForm, setBeneficiaryForm] = useState(emptyBeneficiary);
  const [selectedBeneficiaryId, setSelectedBeneficiaryId] = useState("");
  const [selectedFamilyName, setSelectedFamilyName] = useState("");
  const [registerForm, setRegisterForm] = useState(emptyRegister);
  const [profile, setProfile] = useState(null);
  const [familyPortfolio, setFamilyPortfolio] = useState(null);

  const selectedBeneficiary = useMemo(() => {
    return beneficiaries.find(
      (item) => String(item.beneficiary_id || item.id) === String(selectedBeneficiaryId)
    );
  }, [beneficiaries, selectedBeneficiaryId]);

  async function loadEverything() {
    if (!localStorage.getItem("token")) return;

    setLoading(true);
    setMessage("");

    const requests = await Promise.allSettled([
      api("/api/auth/me"),
      api("/api/dashboard/summary"),
      api("/api/beneficiaries"),
      api("/api/families"),
      api("/api/tasks/today"),
      api("/api/monitoring/overview"),
    ]);

    if (requests[0].status === "fulfilled") setMe(requests[0].value);
    if (requests[1].status === "fulfilled") setSummary(requests[1].value);

    if (requests[2].status === "fulfilled") {
      const rows = safeArray(requests[2].value);
      setBeneficiaries(rows);

      if (rows.length && !selectedBeneficiaryId) {
        const firstId = rows[0].beneficiary_id || rows[0].id;
        setSelectedBeneficiaryId(firstId);
        hydrateRegister(firstId, rows);
      }
    }

    if (requests[3].status === "fulfilled") {
      const rows = safeArray(requests[3].value);
      setFamilies(rows);

      if (rows.length && !selectedFamilyName) {
        setSelectedFamilyName(rows[0].family_name);
      }
    }

    if (requests[4].status === "fulfilled") setTasks(requests[4].value);
    if (requests[5].status === "fulfilled") setMonitoring(requests[5].value);

    setLoading(false);
  }

  async function refreshBeneficiaries() {
    const rows = safeArray(await api("/api/beneficiaries"));
    setBeneficiaries(rows);
    return rows;
  }

  function hydrateRegister(id, source = beneficiaries) {
    const selected = source.find((item) => String(item.beneficiary_id || item.id) === String(id));

    if (!selected) {
      setRegisterForm({ ...emptyRegister, beneficiary_id: id || "" });
      return;
    }

    setRegisterForm({
      beneficiary_id: selected.beneficiary_id || selected.id,
      education: selected.education || "",
      occupation_type: selected.occupation_type || "",
      occupation_detail: selected.occupation_detail || "",
      marital_status: selected.marital_status || "",
      religion: selected.religion || "",
      family_baby_count: selected.family_baby_count || 0,
      last_baby_birth_date: selected.last_baby_birth_date || "",
    });
  }

  async function addBeneficiary(e) {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      await api("/api/beneficiaries", {
        method: "POST",
        body: JSON.stringify(beneficiaryForm),
      });

      setBeneficiaryForm(emptyBeneficiary);
      await refreshBeneficiaries();
      setMessage("Beneficiary profile created successfully.");
    } catch (err) {
      setMessage(err.message || "Could not create beneficiary.");
    } finally {
      setLoading(false);
    }
  }

  async function saveRegister(e) {
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

      const rows = await refreshBeneficiaries();
      hydrateRegister(registerForm.beneficiary_id, rows);
      setMessage("ASHA register details updated successfully.");
    } catch (err) {
      setMessage(err.message || "Could not update register details.");
    } finally {
      setLoading(false);
    }
  }

  async function openIndividualProfile(id = selectedBeneficiaryId) {
    if (!id) {
      setMessage("Select a beneficiary first.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      setProfile(await api(`/api/beneficiaries/${id}/profile`));
    } catch (err) {
      setMessage(err.message || "Could not load individual portfolio.");
    } finally {
      setLoading(false);
    }
  }

  async function openFamily(name = selectedFamilyName) {
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

  async function triggerSOS() {
    setLoading(true);
    setMessage("");

    try {
      await api("/api/sos", {
        method: "POST",
        body: JSON.stringify({}),
      });

      setMessage("Emergency SOS alert triggered successfully.");
      await loadEverything();
    } catch (err) {
      setMessage(err.message || "Could not trigger SOS.");
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.clear();
    setLoggedIn(false);
    document.body.classList.remove("pc-active");
    window.location.reload();
  }

  function openLegacyModule(label) {
    const controls = Array.from(document.querySelectorAll("button, a, [role='button']"));
    const found = controls.find((el) =>
      String(el.textContent || "").toLowerCase().includes(label.toLowerCase())
    );

    if (found) {
      document.body.classList.remove("pc-active");
      found.click();
    }
  }

  useEffect(() => {
    const check = () => {
      const state = Boolean(localStorage.getItem("token"));
      setLoggedIn(state);

      if (state) document.body.classList.add("pc-active");
      else document.body.classList.remove("pc-active");
    };

    check();

    const interval = setInterval(check, 500);
    window.addEventListener("focus", check);

    return () => {
      clearInterval(interval);
      window.removeEventListener("focus", check);
      document.body.classList.remove("pc-active");
    };
  }, []);

  useEffect(() => {
    if (loggedIn) loadEverything();
  }, [loggedIn]);

  useEffect(() => {
    if (selectedBeneficiaryId) hydrateRegister(selectedBeneficiaryId);
  }, [selectedBeneficiaryId]);

  if (!loggedIn) return null;

  const monitorSummary = monitoring?.summary || {};
  const taskSummary = tasks?.summary || {};
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
    <div className="pc-app">
      <aside className="pc-sidebar">
        <div className="pc-brand">
          <div className="pc-brand-mark">
            <span />
          </div>
          <section>
            <b>ASHA CONNECT</b>
            <p>Healthcare Operations Suite</p>
          </section>
        </div>

        <nav className="pc-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={active === item.key ? "active" : ""}
              onClick={() => setActive(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="pc-user-card">
          <span>Signed in as</span>
          <b>{me?.name || "ASHA Worker"}</b>
          <p>{me?.role || "asha"} · {me?.village || "Majitar Primary Health Centre"}</p>
        </div>

        <button className="pc-logout" type="button" onClick={logout}>
          Logout
        </button>
      </aside>

      <main className="pc-main">
        <header className="pc-topbar">
          <div>
            <span>Community Health Command Platform</span>
            <h1>
              {active === "home" && "Healthcare Operations Command Center"}
              {active === "beneficiaries" && "Beneficiary Registry"}
              {active === "register" && "ASHA Register Intelligence"}
              {active === "tasks" && "Daily Care Queue"}
              {active === "risk" && "Risk & Supervision Center"}
              {active === "individual" && "Individual Health Portfolio"}
              {active === "family" && "Family Health Portfolio"}
              {active === "operations" && "Field Operations Workspace"}
            </h1>
            <p>
              Manage community records, family health portfolios, risk indicators,
              field follow-ups and emergency workflows from one enterprise-grade system.
            </p>
          </div>

          <section>
            <button type="button" onClick={loadEverything} disabled={loading}>
              {loading ? "Syncing..." : "Sync Data"}
            </button>
            <button type="button" className="danger" onClick={triggerSOS}>
              Trigger SOS
            </button>
          </section>
        </header>

        {message && <div className="pc-message">{message}</div>}

        {active === "home" && (
          <>
            <div className="pc-metrics">
              <MetricCard label="Beneficiaries" value={monitorSummary.beneficiaries || beneficiaries.length} helper="Total people under care" />
              <MetricCard label="Families" value={families.length} helper="Household groups mapped" />
              <MetricCard label="Daily Tasks" value={taskSummary.total_tasks || 0} helper="Automated work items" />
              <MetricCard label="High Risk" value={monitorSummary.high_risk || 0} helper="Needs supervisor review" tone="danger" />
              <MetricCard label="Pending Immunization" value={monitorSummary.pending_immunizations || 0} helper="Follow-up required" tone="warning" />
              <MetricCard label="SOS Alerts" value={monitorSummary.sos_alerts || 0} helper="Emergency records" tone="danger" />
            </div>

            <div className="pc-control-grid">
              {[
                ["Beneficiary Registry", "Create and manage individual community health records.", "beneficiaries"],
                ["Register Intelligence", "Education, occupation, religion, marital and family baby data.", "register"],
                ["Daily Care Queue", "Automatically generated ASHA work plan for today.", "tasks"],
                ["Risk & Supervision", "High-risk cases, missed visits and ASHA performance.", "risk"],
                ["Individual Portfolio", "Open complete person-level digital health file.", "individual"],
                ["Family Portfolio", "View household-level risk and member health status.", "family"],
              ].map(([title, text, key]) => (
                <button className="pc-control-card" type="button" key={key} onClick={() => setActive(key)}>
                  <b>{title}</b>
                  <p>{text}</p>
                  <span>Open Module</span>
                </button>
              ))}
            </div>

            <div className="pc-two">
              <Section title="Priority Supervision Alerts" subtitle="Operational alerts generated from live records">
                {!alerts.length ? (
                  <Empty title="No active alerts" text="The system has not detected urgent operational issues." />
                ) : (
                  <div className="pc-list">
                    {alerts.slice(0, 6).map((item, index) => (
                      <div className={`pc-list-row ${item.priority || ""}`} key={index}>
                        <b>{item.type}</b>
                        <p>{item.message}</p>
                      </div>
                    ))}
                  </div>
                )}
              </Section>

              <Section title="High Risk Cases" subtitle="Beneficiaries requiring immediate follow-up">
                {!highRisk.length ? (
                  <Empty title="No high-risk cases" text="No high risk beneficiary was detected from current records." />
                ) : (
                  <div className="pc-list">
                    {highRisk.slice(0, 6).map((item) => (
                      <div className="pc-risk-row" key={item.beneficiary_id}>
                        <section>
                          <b>{item.name}</b>
                          <p>{item.village} · ASHA: {item.asha_worker_name}</p>
                        </section>
                        <span className={riskClass(item.risk?.level)}>{item.risk?.score || 0}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </Section>
            </div>
          </>
        )}

        {active === "beneficiaries" && (
          <>
            <Section title="Create Beneficiary Profile" subtitle="Register a person under ASHA care with family grouping">
              <form className="pc-form" onSubmit={addBeneficiary}>
                <input placeholder="Full name" value={beneficiaryForm.full_name} onChange={(e) => setBeneficiaryForm({ ...beneficiaryForm, full_name: e.target.value })} required />
                <input placeholder="Age" type="number" value={beneficiaryForm.age} onChange={(e) => setBeneficiaryForm({ ...beneficiaryForm, age: e.target.value })} required />
                <select value={beneficiaryForm.gender} onChange={(e) => setBeneficiaryForm({ ...beneficiaryForm, gender: e.target.value })}>
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                  <option value="Other">Other</option>
                </select>
                <input placeholder="Phone" value={beneficiaryForm.contact_no} onChange={(e) => setBeneficiaryForm({ ...beneficiaryForm, contact_no: e.target.value })} />
                <input placeholder="Family / household name" value={beneficiaryForm.address} onChange={(e) => setBeneficiaryForm({ ...beneficiaryForm, address: e.target.value })} />
                <select value={beneficiaryForm.category} onChange={(e) => setBeneficiaryForm({ ...beneficiaryForm, category: e.target.value })}>
                  <option value="general">General</option>
                  <option value="pregnant">Pregnant</option>
                  <option value="child">Child</option>
                  <option value="elderly">Elderly</option>
                </select>
                <button type="submit" disabled={loading}>{loading ? "Saving..." : "Create Beneficiary"}</button>
              </form>
            </Section>

            <Section title="Beneficiary Database" subtitle={`${beneficiaries.length} registered records`}>
              <div className="pc-table-wrap">
                <table className="pc-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Age</th>
                      <th>Gender</th>
                      <th>Category</th>
                      <th>Family</th>
                      <th>Education</th>
                      <th>Occupation</th>
                      <th>Religion</th>
                    </tr>
                  </thead>
                  <tbody>
                    {beneficiaries.map((item) => (
                      <tr key={item.beneficiary_id || item.id}>
                        <td><b>{item.full_name || item.name}</b></td>
                        <td>{item.age || "N/A"}</td>
                        <td>{item.gender || "N/A"}</td>
                        <td><span className="pc-pill">{item.category || "general"}</span></td>
                        <td>{item.address || "N/A"}</td>
                        <td>{item.education || "N/A"}</td>
                        <td>{item.occupation_type || "N/A"}</td>
                        <td>{item.religion || "N/A"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          </>
        )}

        {active === "register" && (
          <Section title="ASHA Register Details" subtitle="Structured data from physical ASHA household registers">
            <form className="pc-register-form" onSubmit={saveRegister}>
              <label>
                Beneficiary
                <select value={registerForm.beneficiary_id} onChange={(e) => {
                  setSelectedBeneficiaryId(e.target.value);
                  hydrateRegister(e.target.value);
                }}>
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
                  <option value="">Select</option>
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
                  <option value="">Select</option>
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
                  <option value="">Select</option>
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

              <button type="submit" disabled={loading}>{loading ? "Saving..." : "Save Register Details"}</button>
            </form>
          </Section>
        )}

        {active === "tasks" && (
          <Section title="Daily Care Queue" subtitle="Automated task planning for ASHA field operations">
            <div className="pc-metrics compact">
              <MetricCard label="Total Tasks" value={taskSummary.total_tasks || 0} />
              <MetricCard label="High Priority" value={taskSummary.high_priority || 0} tone="danger" />
              <MetricCard label="Medium Priority" value={taskSummary.medium_priority || 0} tone="warning" />
              <MetricCard label="Low Priority" value={taskSummary.low_priority || 0} />
            </div>

            {!taskRows.length ? (
              <Empty title="No tasks generated" text="Add appointments, pregnancy or immunization records to generate care tasks." />
            ) : (
              <div className="pc-task-list">
                {taskRows.map((item, index) => (
                  <article className={`pc-task ${item.priority}`} key={index}>
                    <section>
                      <span>{item.priority}</span>
                      <b>{item.title}</b>
                      <p>{item.reason}</p>
                    </section>
                    <aside>
                      {item.beneficiary_name && <small>Beneficiary: {item.beneficiary_name}</small>}
                      {item.due_date && <small>Due: {item.due_date}</small>}
                      <small>Action: {item.action}</small>
                    </aside>
                  </article>
                ))}
              </div>
            )}
          </Section>
        )}

        {active === "risk" && (
          <>
            <div className="pc-metrics">
              <MetricCard label="High Risk" value={monitorSummary.high_risk || 0} tone="danger" />
              <MetricCard label="Medium Risk" value={monitorSummary.medium_risk || 0} tone="warning" />
              <MetricCard label="Missed Visits" value={monitorSummary.missed_appointments || 0} tone="danger" />
              <MetricCard label="Pending Immunization" value={monitorSummary.pending_immunizations || 0} tone="warning" />
              <MetricCard label="ASHA Workers" value={monitorSummary.asha_workers || 0} />
              <MetricCard label="SOS Alerts" value={monitorSummary.sos_alerts || 0} tone="danger" />
            </div>

            <Section title="ASHA Worker Performance" subtitle="Supervisor-level operations monitoring">
              <div className="pc-table-wrap">
                <table className="pc-table">
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
                        <td><b>{worker.name}</b><small>{worker.role}</small></td>
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
            </Section>

            <Section title="Village-wise Health Distribution" subtitle="Population and risk grouped by locality">
              <div className="pc-village-grid">
                {villages.map((item) => (
                  <div className="pc-village" key={item.village}>
                    <h3>{item.village}</h3>
                    <p><span>Beneficiaries</span><b>{item.beneficiaries}</b></p>
                    <p><span>Pregnant</span><b>{item.pregnant}</b></p>
                    <p><span>Children</span><b>{item.children}</b></p>
                    <p><span>High Risk</span><b>{item.high_risk}</b></p>
                  </div>
                ))}
              </div>
            </Section>
          </>
        )}

        {active === "individual" && (
          <Section title="Individual Digital Health Portfolio" subtitle="Complete person-level care record">
            <div className="pc-control-row">
              <select value={selectedBeneficiaryId} onChange={(e) => {
                setSelectedBeneficiaryId(e.target.value);
                setProfile(null);
              }}>
                {beneficiaries.map((item) => (
                  <option key={item.beneficiary_id || item.id} value={item.beneficiary_id || item.id}>
                    {item.full_name || item.name} — {item.address || "No family"}
                  </option>
                ))}
              </select>
              <button type="button" onClick={() => openIndividualProfile()}>Open Portfolio</button>
            </div>

            {!profile ? (
              <Empty title="Open a beneficiary profile" text="Select a beneficiary to view timeline, risk, tasks and care records." />
            ) : (
              <>
                <div className="pc-profile">
                  <section>
                    <h2>{profileBeneficiary.full_name || profileBeneficiary.name}</h2>
                    <p>{profileBeneficiary.category} · {profileBeneficiary.gender} · Age {profileBeneficiary.age}</p>
                    <p>Family: {profileBeneficiary.address || "N/A"}</p>
                  </section>
                  <div className={`pc-score ${riskClass(profileRisk.level)}`}>
                    <b>{profileRisk.score || 0}%</b>
                    <span>{profileRisk.level || "Low Risk"}</span>
                  </div>
                </div>

                <div className="pc-two">
                  <Section title="Risk Reasons">
                    <ul className="pc-clean-list">
                      {safeArray(profileRisk.reasons).map((item, index) => <li key={index}>{item}</li>)}
                    </ul>
                  </Section>
                  <Section title="Recommended Actions">
                    <ul className="pc-clean-list">
                      {safeArray(profile.next_actions).map((item, index) => <li key={index}>{item}</li>)}
                    </ul>
                  </Section>
                </div>

                <Section title="Care Timeline">
                  <div className="pc-timeline">
                    {safeArray(profile.timeline).map((item, index) => (
                      <div key={index}>
                        <span>{item.type}</span>
                        <section>
                          <b>{item.title}</b>
                          <p>{item.detail}</p>
                        </section>
                        <time>{item.date || "N/A"}</time>
                      </div>
                    ))}
                  </div>
                </Section>
              </>
            )}
          </Section>
        )}

        {active === "family" && (
          <Section title="Family Health Portfolio" subtitle="Household-level care intelligence">
            <div className="pc-control-row">
              <select value={selectedFamilyName} onChange={(e) => {
                setSelectedFamilyName(e.target.value);
                setFamilyPortfolio(null);
              }}>
                {families.map((item) => (
                  <option key={item.family_name} value={item.family_name}>
                    {item.family_name} — {item.members} members
                  </option>
                ))}
              </select>
              <button type="button" onClick={() => openFamily()}>Open Family</button>
            </div>

            {!familyPortfolio ? (
              <Empty title="Open a family portfolio" text="Select a household to view family members, risk score and records." />
            ) : (
              <>
                <div className="pc-profile">
                  <section>
                    <h2>{family.family_name}</h2>
                    <p>Total Members: {family.total_members}</p>
                    <p>ASHA Worker: {family.asha_worker?.name || "N/A"}</p>
                  </section>
                  <div className={`pc-score ${riskClass(familyRisk.level)}`}>
                    <b>{familyRisk.score || 0}%</b>
                    <span>{familyRisk.level || "Low Risk"}</span>
                  </div>
                </div>

                <div className="pc-metrics compact">
                  <MetricCard label="Members" value={family.total_members || 0} />
                  <MetricCard label="Children" value={family.children || 0} />
                  <MetricCard label="Elderly" value={family.elderly || 0} />
                  <MetricCard label="Pregnant" value={family.pregnant || 0} />
                </div>

                <Section title="Family Members">
                  <div className="pc-member-grid">
                    {familyMembers.map((row) => {
                      const member = row.member || {};
                      const memberRisk = row.risk || {};

                      return (
                        <div className="pc-member" key={member.beneficiary_id}>
                          <div>{String(member.full_name || member.name || "M").charAt(0)}</div>
                          <section>
                            <b>{member.full_name || member.name}</b>
                            <p>{member.age} yrs · {member.gender} · {member.category}</p>
                            <span className={riskClass(memberRisk.level)}>{memberRisk.level} · {memberRisk.score}%</span>
                          </section>
                        </div>
                      );
                    })}
                  </div>
                </Section>
              </>
            )}
          </Section>
        )}

        {active === "operations" && (
          <Section title="Field Operations Workspace" subtitle="Quick access to operational modules">
            <div className="pc-control-grid">
              {[
                ["Appointments", "Schedule and manage ASHA follow-up visits."],
                ["Events", "Create community health camps and outreach sessions."],
                ["Notices", "Send beneficiary and family-level communication."],
                ["Pregnancy", "Maintain ANC and maternal care records."],
                ["Immunization", "Track child vaccination and pending doses."],
                ["Reports", "Generate operational reports."],
              ].map(([label, text]) => (
                <button key={label} className="pc-control-card" type="button" onClick={() => openLegacyModule(label)}>
                  <b>{label}</b>
                  <p>{text}</p>
                  <span>Open Workspace</span>
                </button>
              ))}
            </div>
          </Section>
        )}
      </main>
    </div>
  );
}

const rootId = "premium-command-center-root";

if (!document.getElementById(rootId)) {
  const mount = document.createElement("div");
  mount.id = rootId;
  document.body.appendChild(mount);
  createRoot(mount).render(<PremiumCommandCenter />);
}
