import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./operations-hub.css";

const tabs = [
  ["overview", "Overview"],
  ["tasks", "Care Queue"],
  ["risk", "Risk Monitor"],
  ["individual", "Individual Portfolio"],
  ["family", "Family Portfolio"],
  ["register", "Register Details"],
  ["actions", "Quick Actions"],
];

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

function arr(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.data)) return value.data;
  if (Array.isArray(value?.items)) return value.items;
  return [];
}

function riskClass(level) {
  const value = String(level || "").toLowerCase();
  if (value.includes("high")) return "high";
  if (value.includes("medium")) return "medium";
  return "low";
}

function loggedIn() {
  return Boolean(
    localStorage.getItem("token") ||
      localStorage.getItem("authToken") ||
      localStorage.getItem("access_token")
  );
}

function Metric({ label, value, tone = "" }) {
  return (
    <div className={`hubMetric ${tone}`}>
      <span>{label}</span>
      <b>{value ?? 0}</b>
    </div>
  );
}

function Empty({ title, text }) {
  return (
    <div className="hubEmpty">
      <div />
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function jumpTo(label) {
  const controls = Array.from(document.querySelectorAll("button, a, [role='button']"));
  const found = controls.find((el) =>
    String(el.textContent || "").toLowerCase().includes(label.toLowerCase())
  );
  if (found) found.click();
}

function OperationsHub() {
  const [visible, setVisible] = useState(loggedIn());
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("overview");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [tasks, setTasks] = useState(null);
  const [monitoring, setMonitoring] = useState(null);
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [families, setFamilies] = useState([]);
  const [profile, setProfile] = useState(null);
  const [familyProfile, setFamilyProfile] = useState(null);

  const [selectedBeneficiaryId, setSelectedBeneficiaryId] = useState("");
  const [selectedFamily, setSelectedFamily] = useState("");
  const [registerForm, setRegisterForm] = useState(emptyRegister);

  const selectedBeneficiary = useMemo(() => {
    return beneficiaries.find(
      (b) => String(b.beneficiary_id || b.id) === String(selectedBeneficiaryId)
    );
  }, [beneficiaries, selectedBeneficiaryId]);

  function hydrateRegister(id, source = beneficiaries) {
    const item = source.find((b) => String(b.beneficiary_id || b.id) === String(id));

    if (!item) {
      setRegisterForm({ ...emptyRegister, beneficiary_id: id || "" });
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

  async function syncHub() {
    setLoading(true);
    setMessage("");

    const results = await Promise.allSettled([
      api("/api/tasks/today"),
      api("/api/monitoring/overview"),
      api("/api/beneficiaries"),
      api("/api/families"),
    ]);

    if (results[0].status === "fulfilled") setTasks(results[0].value);
    if (results[1].status === "fulfilled") setMonitoring(results[1].value);

    if (results[2].status === "fulfilled") {
      const rows = arr(results[2].value);
      setBeneficiaries(rows);

      if (rows.length && !selectedBeneficiaryId) {
        const firstId = rows[0].beneficiary_id || rows[0].id;
        setSelectedBeneficiaryId(firstId);
        hydrateRegister(firstId, rows);
      }
    }

    if (results[3].status === "fulfilled") {
      const rows = arr(results[3].value);
      setFamilies(rows);

      if (rows.length && !selectedFamily) {
        setSelectedFamily(rows[0].family_name);
      }
    }

    if (results.every((r) => r.status === "rejected")) {
      setMessage("Backend not reachable. Start FastAPI on port 8000.");
    }

    setLoading(false);
  }

  async function openIndividual(id = selectedBeneficiaryId) {
    if (!id) return setMessage("Select a beneficiary first.");

    setLoading(true);
    setMessage("");

    try {
      setProfile(await api(`/api/beneficiaries/${id}/profile`));
    } catch (err) {
      setMessage(err.message || "Could not open beneficiary portfolio.");
    } finally {
      setLoading(false);
    }
  }

  async function openFamily(name = selectedFamily) {
    if (!name) return setMessage("Select a family first.");

    setLoading(true);
    setMessage("");

    try {
      setFamilyProfile(await api(`/api/families/${encodeURIComponent(name)}/portfolio`));
    } catch (err) {
      setMessage(err.message || "Could not open family portfolio.");
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

      const rows = arr(await api("/api/beneficiaries"));
      setBeneficiaries(rows);
      hydrateRegister(registerForm.beneficiary_id, rows);
      setMessage("Register details saved successfully.");
    } catch (err) {
      setMessage(err.message || "Could not save register details.");
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
      await syncHub();
    } catch (err) {
      setMessage(err.message || "Could not trigger SOS.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const check = () => setVisible(loggedIn());
    check();

    const timer = setInterval(check, 500);
    window.addEventListener("focus", check);

    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", check);
    };
  }, []);

  useEffect(() => {
    if (open && visible) syncHub();
  }, [open, visible]);

  useEffect(() => {
    if (selectedBeneficiaryId) hydrateRegister(selectedBeneficiaryId);
  }, [selectedBeneficiaryId]);

  if (!visible) return null;

  const taskSummary = tasks?.summary || {};
  const taskRows = arr(tasks?.tasks);

  const monitorSummary = monitoring?.summary || {};
  const alerts = arr(monitoring?.smart_alerts);
  const highRisk = arr(monitoring?.high_risk_cases);
  const workers = arr(monitoring?.worker_performance);
  const villages = arr(monitoring?.village_summary);

  const person = profile?.beneficiary || {};
  const personRisk = profile?.risk || {};
  const family = familyProfile?.family || {};
  const familyRisk = familyProfile?.family_risk || {};
  const familyMembers = arr(familyProfile?.members);

  return (
    <>
      <button
        className="hubLauncher"
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(true)}
      >
        <span className="hubOrb" aria-hidden="true" />
        <span>
          <b>Operations Hub</b>
          <small>Care intelligence</small>
        </span>
      </button>

      {open && (
        <div className="hubOverlay">
          <section className="hubDialog" role="dialog" aria-modal="true">
            <aside className="hubSide">
              <div className="hubBrand">
                <div />
                <section>
                  <b>ASHA CONNECT</b>
                  <span>Operations Intelligence</span>
                </section>
              </div>

              <nav>
                {tabs.map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    className={tab === id ? "active" : ""}
                    onClick={() => setTab(id)}
                  >
                    {label}
                  </button>
                ))}
              </nav>

              <div className="hubStatus">
                <span>System Status</span>
                <b>Live</b>
                <p>Backend-connected operations layer.</p>
              </div>
            </aside>

            <main className="hubMain">
              <header className="hubHeader">
                <div>
                  <p>Healthcare Operations Intelligence</p>
                  <h2>
                    {tab === "overview" && "Command Overview"}
                    {tab === "tasks" && "Daily Care Queue"}
                    {tab === "risk" && "Risk Monitor"}
                    {tab === "individual" && "Individual Portfolio"}
                    {tab === "family" && "Family Portfolio"}
                    {tab === "register" && "Register Details"}
                    {tab === "actions" && "Quick Actions"}
                  </h2>
                  <span>
                    A premium operational layer for daily tasks, risk supervision,
                    family records, register data and beneficiary intelligence.
                  </span>
                </div>

                <section>
                  <button type="button" onClick={syncHub} disabled={loading}>
                    {loading ? "Syncing..." : "Sync Data"}
                  </button>
                  <button type="button" className="danger" onClick={triggerSOS}>
                    Trigger SOS
                  </button>
                  <button type="button" className="ghost" onClick={() => setOpen(false)}>
                    Close
                  </button>
                </section>
              </header>

              {message && <div className="hubMessage">{message}</div>}

              {tab === "overview" && (
                <>
                  <div className="hubMetrics">
                    <Metric label="Beneficiaries" value={monitorSummary.beneficiaries || beneficiaries.length} />
                    <Metric label="Families" value={families.length} />
                    <Metric label="Daily Tasks" value={taskSummary.total_tasks || 0} />
                    <Metric label="High Risk" value={monitorSummary.high_risk || 0} tone="danger" />
                    <Metric label="Pending Immunization" value={monitorSummary.pending_immunizations || 0} tone="warning" />
                    <Metric label="SOS Alerts" value={monitorSummary.sos_alerts || 0} tone="danger" />
                  </div>

                  <div className="hubModules">
                    {[
                      ["tasks", "Care Queue", "Automated work plan for today."],
                      ["risk", "Risk Monitor", "PHC and supervisor-level risk view."],
                      ["individual", "Individual Portfolio", "Open complete beneficiary health file."],
                      ["family", "Family Portfolio", "Household-level health intelligence."],
                      ["register", "Register Details", "Education, occupation, marriage and religion data."],
                      ["actions", "Quick Actions", "Jump to normal dashboard workspaces."],
                    ].map(([id, title, text]) => (
                      <button key={id} className="hubModule" type="button" onClick={() => setTab(id)}>
                        <b>{title}</b>
                        <p>{text}</p>
                        <span>Open</span>
                      </button>
                    ))}
                  </div>

                  <div className="hubTwo">
                    <section className="hubPanel">
                      <div className="hubPanelHead">
                        <h3>Priority Alerts</h3>
                        <span>{alerts.length}</span>
                      </div>
                      {!alerts.length ? (
                        <Empty title="No active alerts" text="No urgent operational alerts found right now." />
                      ) : (
                        <div className="hubList">
                          {alerts.slice(0, 6).map((item, index) => (
                            <article className={`hubListItem ${item.priority || ""}`} key={index}>
                              <b>{item.type}</b>
                              <p>{item.message}</p>
                            </article>
                          ))}
                        </div>
                      )}
                    </section>

                    <section className="hubPanel">
                      <div className="hubPanelHead">
                        <h3>High Risk Beneficiaries</h3>
                        <span>{highRisk.length}</span>
                      </div>
                      {!highRisk.length ? (
                        <Empty title="No high-risk cases" text="Current records do not show high-risk beneficiaries." />
                      ) : (
                        <div className="hubList">
                          {highRisk.slice(0, 6).map((item) => (
                            <article className="hubRiskRow" key={item.beneficiary_id}>
                              <section>
                                <b>{item.name}</b>
                                <p>{item.village} · ASHA: {item.asha_worker_name}</p>
                              </section>
                              <span className={riskClass(item.risk?.level)}>{item.risk?.score || 0}%</span>
                            </article>
                          ))}
                        </div>
                      )}
                    </section>
                  </div>
                </>
              )}

              {tab === "tasks" && (
                <section className="hubPanel">
                  <div className="hubPanelHead">
                    <div>
                      <h3>Automated Daily Care Queue</h3>
                      <p>Generated from appointments, pregnancy, immunization, SOS and events.</p>
                    </div>
                    <button type="button" onClick={syncHub}>Regenerate</button>
                  </div>

                  <div className="hubMetrics compact">
                    <Metric label="Total" value={taskSummary.total_tasks || 0} />
                    <Metric label="High" value={taskSummary.high_priority || 0} tone="danger" />
                    <Metric label="Medium" value={taskSummary.medium_priority || 0} tone="warning" />
                    <Metric label="Low" value={taskSummary.low_priority || 0} />
                  </div>

                  {!taskRows.length ? (
                    <Empty title="No daily tasks" text="Add appointments, pregnancy or immunization records to generate tasks." />
                  ) : (
                    <div className="hubTaskList">
                      {taskRows.map((item, index) => (
                        <article className={`hubTask ${item.priority}`} key={index}>
                          <section>
                            <span>{item.priority}</span>
                            <b>{item.title}</b>
                            <p>{item.reason}</p>
                          </section>
                          <aside>
                            {item.beneficiary_name && <small>{item.beneficiary_name}</small>}
                            {item.village && <small>{item.village}</small>}
                            {item.due_date && <small>{item.due_date}</small>}
                            <small>{item.action}</small>
                          </aside>
                        </article>
                      ))}
                    </div>
                  )}
                </section>
              )}

              {tab === "risk" && (
                <>
                  <div className="hubMetrics">
                    <Metric label="High Risk" value={monitorSummary.high_risk || 0} tone="danger" />
                    <Metric label="Medium Risk" value={monitorSummary.medium_risk || 0} tone="warning" />
                    <Metric label="Missed Visits" value={monitorSummary.missed_appointments || 0} tone="danger" />
                    <Metric label="Pending Immunization" value={monitorSummary.pending_immunizations || 0} tone="warning" />
                    <Metric label="ASHA Workers" value={monitorSummary.asha_workers || 0} />
                    <Metric label="SOS Alerts" value={monitorSummary.sos_alerts || 0} tone="danger" />
                  </div>

                  <section className="hubPanel">
                    <div className="hubPanelHead">
                      <h3>ASHA Worker Performance</h3>
                      <span>{workers.length}</span>
                    </div>

                    <div className="hubTableWrap">
                      <table>
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
                          {workers.map((w) => (
                            <tr key={w.worker_id}>
                              <td><b>{w.name}</b><small>{w.role}</small></td>
                              <td>{w.village}</td>
                              <td>{w.beneficiaries}</td>
                              <td>{w.appointments}</td>
                              <td>{w.missed_appointments}</td>
                              <td>{w.sos_alerts}</td>
                              <td>{w.high_risk_cases}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>

                  <section className="hubPanel">
                    <div className="hubPanelHead">
                      <h3>Village-wise Summary</h3>
                      <span>{villages.length}</span>
                    </div>

                    <div className="hubVillageGrid">
                      {villages.map((v) => (
                        <article className="hubVillage" key={v.village}>
                          <h4>{v.village}</h4>
                          <p><span>Beneficiaries</span><b>{v.beneficiaries}</b></p>
                          <p><span>Pregnant</span><b>{v.pregnant}</b></p>
                          <p><span>Children</span><b>{v.children}</b></p>
                          <p><span>High Risk</span><b>{v.high_risk}</b></p>
                        </article>
                      ))}
                    </div>
                  </section>
                </>
              )}

              {tab === "individual" && (
                <section className="hubPanel">
                  <div className="hubPanelHead">
                    <div>
                      <h3>Individual Digital Health Portfolio</h3>
                      <p>Complete person-level record and risk profile.</p>
                    </div>
                    <button type="button" onClick={() => openIndividual()}>Open Profile</button>
                  </div>

                  <div className="hubControl">
                    <select
                      value={selectedBeneficiaryId}
                      onChange={(e) => {
                        setSelectedBeneficiaryId(e.target.value);
                        setProfile(null);
                      }}
                    >
                      {beneficiaries.map((b) => (
                        <option key={b.beneficiary_id || b.id} value={b.beneficiary_id || b.id}>
                          {b.full_name || b.name} — {b.address || b.village || "No family"}
                        </option>
                      ))}
                    </select>
                  </div>

                  {!profile ? (
                    <Empty title="Open a beneficiary profile" text="Select a beneficiary and open portfolio to view risk, timeline and actions." />
                  ) : (
                    <>
                      <div className="hubProfileHero">
                        <section>
                          <h3>{person.full_name || person.name}</h3>
                          <p>{person.category} · {person.gender} · Age {person.age}</p>
                          <p>Family: {person.address || person.village || "N/A"}</p>
                          <p>ASHA Worker: {profile.asha_worker?.name || "N/A"}</p>
                        </section>
                        <div className={`hubScore ${riskClass(personRisk.level)}`}>
                          <b>{personRisk.score || 0}%</b>
                          <span>{personRisk.level || "Low Risk"}</span>
                        </div>
                      </div>

                      <div className="hubTwo">
                        <section className="hubSubPanel">
                          <h4>Risk Reasons</h4>
                          <ul>{arr(personRisk.reasons).map((x, i) => <li key={i}>{x}</li>)}</ul>
                        </section>
                        <section className="hubSubPanel">
                          <h4>Recommended Actions</h4>
                          <ul>{arr(profile.next_actions).map((x, i) => <li key={i}>{x}</li>)}</ul>
                        </section>
                      </div>

                      <div className="hubTimeline">
                        {arr(profile.timeline).map((x, i) => (
                          <article key={i}>
                            <span>{x.type}</span>
                            <section>
                              <b>{x.title}</b>
                              <p>{x.detail}</p>
                            </section>
                            <time>{x.date || "N/A"}</time>
                          </article>
                        ))}
                      </div>
                    </>
                  )}
                </section>
              )}

              {tab === "family" && (
                <section className="hubPanel">
                  <div className="hubPanelHead">
                    <div>
                      <h3>Family Health Portfolio</h3>
                      <p>Household-level members, risk, records and recommended ASHA action.</p>
                    </div>
                    <button type="button" onClick={() => openFamily()}>Open Family</button>
                  </div>

                  <div className="hubControl">
                    <select
                      value={selectedFamily}
                      onChange={(e) => {
                        setSelectedFamily(e.target.value);
                        setFamilyProfile(null);
                      }}
                    >
                      {families.map((f) => (
                        <option key={f.family_name} value={f.family_name}>
                          {f.family_name} — {f.members} members
                        </option>
                      ))}
                    </select>
                  </div>

                  {!familyProfile ? (
                    <Empty title="Open a family portfolio" text="Select a household to view family risk and member health status." />
                  ) : (
                    <>
                      <div className="hubProfileHero">
                        <section>
                          <h3>{family.family_name}</h3>
                          <p>Total Members: {family.total_members}</p>
                          <p>ASHA Worker: {family.asha_worker?.name || "N/A"}</p>
                        </section>
                        <div className={`hubScore ${riskClass(familyRisk.level)}`}>
                          <b>{familyRisk.score || 0}%</b>
                          <span>{familyRisk.level || "Low Risk"}</span>
                        </div>
                      </div>

                      <div className="hubMetrics compact">
                        <Metric label="Members" value={family.total_members || 0} />
                        <Metric label="Children" value={family.children || 0} />
                        <Metric label="Elderly" value={family.elderly || 0} />
                        <Metric label="Pregnant" value={family.pregnant || 0} />
                      </div>

                      <div className="hubMemberGrid">
                        {familyMembers.map((row) => {
                          const m = row.member || {};
                          const r = row.risk || {};
                          return (
                            <article className="hubMember" key={m.beneficiary_id}>
                              <div>{String(m.full_name || m.name || "M").charAt(0)}</div>
                              <section>
                                <b>{m.full_name || m.name}</b>
                                <p>{m.age} yrs · {m.gender} · {m.category}</p>
                                <span className={riskClass(r.level)}>{r.level} · {r.score}%</span>
                              </section>
                            </article>
                          );
                        })}
                      </div>
                    </>
                  )}
                </section>
              )}

              {tab === "register" && (
                <section className="hubPanel">
                  <div className="hubPanelHead">
                    <div>
                      <h3>ASHA Register Details</h3>
                      <p>Education, occupation, marital status, religion and family baby information.</p>
                    </div>
                  </div>

                  <form className="hubRegisterForm" onSubmit={saveRegister}>
                    <label>
                      Beneficiary
                      <select
                        value={registerForm.beneficiary_id}
                        onChange={(e) => {
                          setSelectedBeneficiaryId(e.target.value);
                          hydrateRegister(e.target.value);
                        }}
                      >
                        {beneficiaries.map((b) => (
                          <option key={b.beneficiary_id || b.id} value={b.beneficiary_id || b.id}>
                            {b.full_name || b.name} — {b.address || b.village || "No family"}
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
                      <input value={registerForm.occupation_detail} onChange={(e) => setRegisterForm({ ...registerForm, occupation_detail: e.target.value })} placeholder="Shop, teacher, driver, farmer" />
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
                    <div className="hubRegisterPreview">
                      <h4>Register Preview</h4>
                      <div>
                        <p><span>Name</span><b>{selectedBeneficiary.full_name || selectedBeneficiary.name}</b></p>
                        <p><span>Family</span><b>{selectedBeneficiary.address || selectedBeneficiary.village || "N/A"}</b></p>
                        <p><span>Education</span><b>{registerForm.education || "N/A"}</b></p>
                        <p><span>Occupation</span><b>{registerForm.occupation_type || "N/A"}</b></p>
                        <p><span>Marital Status</span><b>{registerForm.marital_status || "N/A"}</b></p>
                        <p><span>Religion</span><b>{registerForm.religion || "N/A"}</b></p>
                      </div>
                    </div>
                  )}
                </section>
              )}

              {tab === "actions" && (
                <section className="hubPanel">
                  <div className="hubPanelHead">
                    <div>
                      <h3>Quick Workspace Access</h3>
                      <p>Open the normal redesigned dashboard modules without clutter.</p>
                    </div>
                  </div>

                  <div className="hubModules">
                    {[
                      ["Dashboard", "Live overview workspace."],
                      ["Beneficiaries", "Beneficiary management."],
                      ["Pregnancy", "Maternal care records."],
                      ["Immunization", "Vaccine tracking."],
                      ["Appointments", "Scheduling workspace."],
                      ["Events", "Community outreach."],
                      ["Notices", "Communication module."],
                      ["Reports", "Reporting workspace."],
                    ].map(([label, text]) => (
                      <button
                        className="hubModule"
                        key={label}
                        type="button"
                        onClick={() => {
                          setOpen(false);
                          setTimeout(() => jumpTo(label), 120);
                        }}
                      >
                        <b>{label}</b>
                        <p>{text}</p>
                        <span>Go</span>
                      </button>
                    ))}
                  </div>
                </section>
              )}
            </main>
          </section>
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
