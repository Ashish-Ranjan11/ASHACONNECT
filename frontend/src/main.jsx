import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./styles.css";

const today = () => new Date().toISOString().slice(0, 10);
const title = (value = "") => value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
const number = (value) => new Intl.NumberFormat("en-IN").format(Number(value || 0));
const clean = (obj) => Object.fromEntries(Object.entries(obj).map(([k, v]) => {
  if (v === "") return [k, null];
  if (["age", "beneficiary_id", "dose_number", "year"].includes(k)) return [k, Number(v)];
  if (["hemoglobin_level", "weight"].includes(k)) return [k, v === null ? null : Number(v)];
  return [k, v];
}));

const NAV = [
  { key: "Dashboard", icon: "📊", label: "Command Center" },
  { key: "Beneficiaries", icon: "👥", label: "Beneficiaries" },
  { key: "Records", icon: "🩺", label: "Clinical Records" },
  { key: "Appointments", icon: "📅", label: "Appointments" },
  { key: "Events", icon: "🏕️", label: "Events" },
  { key: "Notices", icon: "📨", label: "Notices" },
  { key: "Reports", icon: "📄", label: "Reports" },
  { key: "SOS", icon: "🚨", label: "SOS" },
];

function Login({ onLogin }) {
  const [email, setEmail] = useState("asha@example.com");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ email: email.trim(), password }) });
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("worker", JSON.stringify(data.worker));
      onLogin(data.worker);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="loginPage">
      <div className="loginVisual">
        <span className="pulseDot" />
        <div className="loginHeroCard glass">
          <b>AWAMS Live</b>
          <p>Offline-first field operations, clinical tracking, reminders, reporting and emergency escalation.</p>
          <div className="heroStats"><span>4 Modules</span><span>5 UML Layers</span><span>SOS Ready</span></div>
        </div>
      </div>
      <form className="loginCard" onSubmit={submit}>
        <div className="brandMark">A</div>
        <p className="eyebrow">ASHA Workflow Automation</p>
        <h1>Welcome to AWAMS</h1>
        <p className="loginSub">A professional command dashboard for frontline healthcare delivery.</p>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" autoComplete="email" />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" autoComplete="current-password" />
        {error && <div className="error">{error}</div>}
        <button className="primaryButton" disabled={loading}>{loading ? "Signing in..." : "Login"}</button>
        <small>Demo: asha@example.com / password123</small>
      </form>
    </div>
  );
}

function Field({ label, hint, ...props }) {
  return <label className="field"><span>{label}</span><input {...props} />{hint && <small>{hint}</small>}</label>;
}
function Select({ label, children, ...props }) {
  return <label className="field"><span>{label}</span><select {...props}>{children}</select></label>;
}
function TextArea({ label, ...props }) {
  return <label className="field wide"><span>{label}</span><textarea {...props} /></label>;
}
function BeneficiarySelect({ value, onChange, items }) {
  return (
    <Select label="Beneficiary" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">Select beneficiary</option>
      {items.map((b) => <option key={b.beneficiary_id} value={b.beneficiary_id}>{b.full_name} • {title(b.category)} #{b.beneficiary_id}</option>)}
    </Select>
  );
}

function EmptyState({ titleText = "No records yet", text = "Add a record using the form above." }) {
  return <div className="emptyState"><span>☁️</span><b>{titleText}</b><p>{text}</p></div>;
}

function Table({ rows, titleText }) {
  if (!rows?.length) return <EmptyState />;
  const keys = Object.keys(rows[0]).slice(0, 9);
  return (
    <div className="dataCard">
      {titleText && <div className="sectionHeader"><h3>{titleText}</h3><span>{rows.length} entries</span></div>}
      <div className="tableWrap">
        <table>
          <thead><tr>{keys.map((k) => <th key={k}>{title(k)}</th>)}</tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>{keys.map((k) => <td key={k}>{String(r[k] ?? "—")}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, tone = "green" }) {
  return (
    <div className={`statCard ${tone}`}>
      <div className="statIcon">{icon}</div>
      <p>{label}</p>
      <b>{number(value)}</b>
    </div>
  );
}

function ProgressBar({ label, value, target, status }) {
  const pct = Math.min(100, Math.round(((value || 0) / Math.max(target || 1, 1)) * 100));
  return (
    <div className="progressRow">
      <div><b>{label}</b><small>{status}</small></div>
      <div className="bar"><span style={{ width: `${pct}%` }} /></div>
      <strong>{value}/{target}</strong>
    </div>
  );
}

function MiniBarChart({ data }) {
  const entries = Object.entries(data || {});
  const max = Math.max(...entries.map(([, v]) => Number(v)), 1);
  return (
    <div className="miniChart">
      {entries.map(([k, v]) => (
        <div className="miniBar" key={k}>
          <div><b>{title(k)}</b><span>{v}</span></div>
          <i><em style={{ width: `${Math.round((Number(v) / max) * 100)}%` }} /></i>
        </div>
      ))}
    </div>
  );
}

function TimelineList({ titleText, icon, rows, emptyText }) {
  return (
    <div className="timelineCard">
      <div className="sectionHeader"><h3>{icon} {titleText}</h3><span>{rows?.length || 0}</span></div>
      {!rows?.length ? <EmptyState text={emptyText} /> : <div className="timelineList">
        {rows.map((item) => (
          <div className="timelineItem" key={`${titleText}-${item.id}`}>
            <span className="timelineDot" />
            <div>
              <b>{item.beneficiary || item.name || item.vaccine || item.type}</b>
              <p>{item.type || item.vaccine || item.location || item.status} {item.dose ? `• Dose ${item.dose}` : ""}</p>
            </div>
            <time>{item.date || "—"}</time>
          </div>
        ))}
      </div>}
    </div>
  );
}

function Dashboard({ tick, goTo }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api("/api/dashboard/summary").then(setData).catch((err) => setError(err.message));
  }, [tick]);

  if (error) return <div className="error big">{error}</div>;
  if (!data) return <div className="loading"><span /> Loading AWAMS intelligence...</div>;

  const c = data.cards || {};
  const riskScore = Math.min(100, (data.clinical_risk?.high_risk_pregnancies || 0) * 25 + (data.clinical_risk?.missed_immunizations || 0) * 15 + (data.clinical_risk?.overdue_appointments || 0) * 10 + (data.clinical_risk?.active_sos_alerts || 0) * 50);

  return (
    <div className="dashboardGrid">
      <section className="heroPanel">
        <div>
          <p className="eyebrow">Live field command center</p>
          <h2>{data.worker?.village || "ASHA Area"} Health Operations</h2>
          <p>Unified monitoring for beneficiaries, ANC/PNC care, immunization, PHC reporting, reminders and SOS safety.</p>
          <div className="heroActions">
            <button onClick={() => goTo("Beneficiaries")}>+ Add Beneficiary</button>
            <button onClick={() => goTo("Records")}>Add Clinical Record</button>
            <button className="dangerButton" onClick={() => goTo("SOS")}>Trigger SOS</button>
          </div>
        </div>
        <div className="workerBadge glass">
          <span>👩‍⚕️</span>
          <b>{data.worker?.name}</b>
          <p>{title(data.worker?.role)} • {data.worker?.phc || "PHC not mapped"}</p>
          <small>SOS ID: {data.worker?.sos_id || "N/A"}</small>
        </div>
      </section>

      <section className="statsGrid">
        <StatCard icon="👥" label="Beneficiaries" value={c.beneficiaries} />
        <StatCard icon="🤰" label="Pregnancies" value={c.pregnancies} tone="blue" />
        <StatCard icon="💉" label="Immunizations" value={c.immunizations} tone="purple" />
        <StatCard icon="📅" label="Upcoming Visits" value={c.upcoming_appointments} tone="orange" />
        <StatCard icon="🏕️" label="Events" value={c.events} tone="green" />
        <StatCard icon="🚨" label="Active SOS" value={c.active_sos_alerts} tone="red" />
      </section>

      <section className="panel xl">
        <div className="sectionHeader"><h3>Workflow Pipeline</h3><span>from UML + AWAMS modules</span></div>
        {(data.care_pipeline || []).map((item) => <ProgressBar key={item.label} {...item} />)}
      </section>

      <section className="panel riskPanel">
        <div className="sectionHeader"><h3>Clinical Risk Index</h3><span>{riskScore}%</span></div>
        <div className="riskDial" style={{ "--risk": `${riskScore}%` }}><b>{riskScore}</b><small>risk score</small></div>
        <div className="riskList">
          {Object.entries(data.clinical_risk || {}).map(([k, v]) => <span key={k}><b>{v}</b>{title(k)}</span>)}
        </div>
      </section>

      <section className="panel">
        <div className="sectionHeader"><h3>Beneficiary Category Split</h3><span>active population</span></div>
        <MiniBarChart data={data.category_breakdown} />
      </section>

      <section className="panel alertPanel xl">
        <div className="sectionHeader"><h3>Priority Alerts</h3><span>decision support</span></div>
        <div className="alerts">
          {(data.alerts || []).map((a, idx) => <div className={`alert ${a.level}`} key={idx}><b>{a.title}</b><p>{a.message}</p></div>)}
        </div>
      </section>

      <TimelineList titleText="Appointments" icon="📅" rows={data.upcoming?.appointments} emptyText="No appointments scheduled." />
      <TimelineList titleText="Immunizations" icon="💉" rows={data.upcoming?.immunizations} emptyText="No immunization dates available." />
      <TimelineList titleText="Events" icon="🏕️" rows={data.upcoming?.events} emptyText="No events planned." />

      <section className="panel xl">
        <div className="sectionHeader"><h3>UML Module Coverage</h3><span>system design mapped to UI</span></div>
        <div className="moduleGrid">
          {(data.uml_modules || []).map((mod) => (
            <div className="moduleCard" key={mod.module}>
              <b>{mod.module}</b>
              <ul>{mod.items.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          ))}
        </div>
      </section>

      <section className="panel xl">
        <div className="sectionHeader"><h3>System Architecture Flow</h3><span>UI → API → DB → Services</span></div>
        <div className="archFlow">
          {(data.architecture_layers || []).map((layer) => <div className="archNode" key={layer.name}><b>{layer.name}</b><p>{layer.detail}</p></div>)}
        </div>
      </section>
    </div>
  );
}

function Beneficiaries({ refresh }) {
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ full_name: "", age: "", gender: "Female", category: "general", contact_no: "", address: "" });
  const load = () => api("/api/beneficiaries").then(setRows);
  useEffect(load, []);
  async function submit(e) {
    e.preventDefault();
    await api("/api/beneficiaries", { method: "POST", body: JSON.stringify(clean(form)) });
    setForm({ full_name: "", age: "", gender: "Female", category: "general", contact_no: "", address: "" });
    load(); refresh();
  }
  return (
    <Page titleText="Beneficiary Services" subtitle="Register and maintain digital profiles for pregnant women, children, elderly and general beneficiaries.">
      <form className="panel form" onSubmit={submit}>
        <Field label="Full name" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <Field label="Age" type="number" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} />
        <Select label="Gender" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}><option>Female</option><option>Male</option><option>Other</option></Select>
        <Select label="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}><option>general</option><option>pregnant</option><option>child</option><option>elderly</option></Select>
        <Field label="Contact" value={form.contact_no} onChange={(e) => setForm({ ...form, contact_no: e.target.value })} />
        <Field label="Address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
        <button className="primaryButton">Add Beneficiary</button>
      </form>
      <Table rows={rows} titleText="Beneficiary Registry" />
    </Page>
  );
}

function Records({ refresh }) {
  const [beneficiaries, setBeneficiaries] = useState([]), [pregs, setPregs] = useState([]), [imms, setImms] = useState([]);
  const [preg, setPreg] = useState({ beneficiary_id: "", registration_date: today(), lmp_date: "", expected_delivery_date: "", hemoglobin_level: "", blood_pressure: "", weight: "", status: "active", anc_count: 0 });
  const [imm, setImm] = useState({ beneficiary_id: "", vaccine_name: "", dose_number: 1, scheduled_date: today(), status: "scheduled" });
  const load = () => { api("/api/beneficiaries").then(setBeneficiaries); api("/api/records/pregnancy").then(setPregs); api("/api/records/immunization").then(setImms); };
  useEffect(load, []);
  async function addPreg(e) { e.preventDefault(); await api("/api/records/pregnancy", { method: "POST", body: JSON.stringify(clean(preg)) }); load(); refresh(); }
  async function addImm(e) { e.preventDefault(); await api("/api/records/immunization", { method: "POST", body: JSON.stringify(clean(imm)) }); load(); refresh(); }
  return (
    <Page titleText="Clinical Records" subtitle="Structured pregnancy and immunization tracking connected to the beneficiary profile.">
      <div className="two">
        <form className="panel form compact" onSubmit={addPreg}>
          <h3>Pregnancy / ANC Record</h3>
          <BeneficiarySelect items={beneficiaries} value={preg.beneficiary_id} onChange={(v) => setPreg({ ...preg, beneficiary_id: v })} />
          <Field label="Registration" type="date" value={preg.registration_date} onChange={(e) => setPreg({ ...preg, registration_date: e.target.value })} />
          <Field label="LMP" type="date" value={preg.lmp_date} onChange={(e) => setPreg({ ...preg, lmp_date: e.target.value })} />
          <Field label="Expected Delivery" type="date" value={preg.expected_delivery_date} onChange={(e) => setPreg({ ...preg, expected_delivery_date: e.target.value })} />
          <Field label="Hemoglobin" type="number" step="0.1" value={preg.hemoglobin_level} onChange={(e) => setPreg({ ...preg, hemoglobin_level: e.target.value })} />
          <Field label="Blood Pressure" placeholder="120/80" value={preg.blood_pressure} onChange={(e) => setPreg({ ...preg, blood_pressure: e.target.value })} />
          <Field label="Weight" type="number" step="0.1" value={preg.weight} onChange={(e) => setPreg({ ...preg, weight: e.target.value })} />
          <Select label="Status" value={preg.status} onChange={(e) => setPreg({ ...preg, status: e.target.value })}><option>active</option><option>high_risk</option><option>delivered</option><option>closed</option></Select>
          <button className="primaryButton">Save Pregnancy Record</button>
        </form>
        <form className="panel form compact" onSubmit={addImm}>
          <h3>Immunization Record</h3>
          <BeneficiarySelect items={beneficiaries} value={imm.beneficiary_id} onChange={(v) => setImm({ ...imm, beneficiary_id: v })} />
          <Field label="Vaccine" required value={imm.vaccine_name} onChange={(e) => setImm({ ...imm, vaccine_name: e.target.value })} />
          <Field label="Dose" type="number" value={imm.dose_number} onChange={(e) => setImm({ ...imm, dose_number: e.target.value })} />
          <Field label="Scheduled Date" type="date" value={imm.scheduled_date} onChange={(e) => setImm({ ...imm, scheduled_date: e.target.value })} />
          <Select label="Status" value={imm.status} onChange={(e) => setImm({ ...imm, status: e.target.value })}><option>scheduled</option><option>given</option><option>missed</option><option>postponed</option></Select>
          <button className="primaryButton">Save Immunization</button>
        </form>
      </div>
      <Table rows={pregs} titleText="Pregnancy Records" />
      <Table rows={imms} titleText="Immunization Records" />
    </Page>
  );
}

function GenericForm({ titleText, subtitle, endpoint, listEndpoint, fields, defaults, needsBeneficiary, refresh, selectOptions = {} }) {
  const [rows, setRows] = useState([]), [beneficiaries, setBeneficiaries] = useState([]), [form, setForm] = useState(defaults);
  const load = () => { api(listEndpoint || endpoint).then(setRows); if (needsBeneficiary) api("/api/beneficiaries").then(setBeneficiaries); };
  useEffect(load, []);
  async function submit(e) { e.preventDefault(); await api(endpoint, { method: "POST", body: JSON.stringify(clean(form)) }); setForm(defaults); load(); refresh(); }
  const inputFor = (f) => {
    if (f === "beneficiary_id") return <BeneficiarySelect key={f} items={beneficiaries} value={form[f]} onChange={(v) => setForm({ ...form, [f]: v })} />;
    if (selectOptions[f]) return <Select key={f} label={title(f)} value={form[f]} onChange={(e) => setForm({ ...form, [f]: e.target.value })}>{selectOptions[f].map((o) => <option key={o}>{o}</option>)}</Select>;
    if (f === "description" || f === "notes" || f === "message") return <TextArea key={f} label={title(f)} value={form[f]} onChange={(e) => setForm({ ...form, [f]: e.target.value })} />;
    return <Field key={f} label={title(f)} type={f.includes("date") ? "date" : f.includes("time") ? "time" : f === "year" ? "number" : "text"} value={form[f]} onChange={(e) => setForm({ ...form, [f]: e.target.value })} />;
  };
  return <Page titleText={titleText} subtitle={subtitle}><form className="panel form" onSubmit={submit}>{fields.map(inputFor)}<button className="primaryButton">Save</button></form><Table rows={rows} titleText={`${titleText} List`} /></Page>;
}

function Appointments({ refresh }) {
  return <GenericForm titleText="Appointments" subtitle="Schedule ANC, immunization and general follow-up visits." endpoint="/api/appointments" refresh={refresh} fields={["beneficiary_id", "appointment_date", "appointment_time", "appointment_type", "notes"]} defaults={{ beneficiary_id: "", appointment_date: today(), appointment_time: "", appointment_type: "ANC Checkup", notes: "" }} needsBeneficiary />;
}
function Events({ refresh }) {
  return <GenericForm titleText="Events" subtitle="Organize health camps, nutrition drives, awareness sessions and vaccination events." endpoint="/api/events" refresh={refresh} fields={["event_name", "event_type", "event_date", "event_time", "location", "description"]} defaults={{ event_name: "", event_type: "nutrition", event_date: today(), event_time: "", location: "", description: "" }} selectOptions={{ event_type: ["vaccination", "nutrition", "awareness", "checkup", "other"] }} />;
}
function Notices({ refresh }) {
  return <GenericForm titleText="Notices & Reminders" subtitle="Send SMS, push, or combined reminders to beneficiaries." endpoint="/api/notices" refresh={refresh} fields={["beneficiary_id", "message", "delivery_method"]} defaults={{ beneficiary_id: "", message: "Reminder: Please attend your scheduled health check-up.", delivery_method: "sms" }} needsBeneficiary selectOptions={{ delivery_method: ["sms", "push", "both"] }} />;
}
function Reports({ refresh }) {
  return <GenericForm titleText="Monthly Reports" subtitle="Generate monthly performance reports for PHC review." endpoint="/api/reports/generate" listEndpoint="/api/reports" refresh={refresh} fields={["month", "year", "notes"]} defaults={{ month: new Date().toLocaleString("default", { month: "long" }), year: new Date().getFullYear(), notes: "Auto generated report" }} />;
}

function SOS() {
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  async function trigger() {
    setBusy(true); setMsg("Capturing location and sending SOS...");
    const send = async (body) => {
      try { setMsg((await api("/api/sos/trigger", { method: "POST", body: JSON.stringify(body) })).message); }
      catch (err) { setMsg(err.message); }
      finally { setBusy(false); }
    };
    navigator.geolocation ? navigator.geolocation.getCurrentPosition((p) => send({ latitude: p.coords.latitude, longitude: p.coords.longitude }), () => send({})) : send({});
  }
  return (
    <Page titleText="Emergency SOS" subtitle="High-priority field safety trigger that records worker ID, location and alert status.">
      <div className="sosHero">
        <div><span>🚨</span><h3>Emergency Escalation</h3><p>Use only when immediate help is required. The backend will create an active SOS record and simulate notification to PHC/admin/emergency contacts.</p></div>
        <button className="sosButton" onClick={trigger} disabled={busy}>{busy ? "Sending..." : "TRIGGER SOS"}</button>
      </div>
      {msg && <div className="successBox">{msg}</div>}
    </Page>
  );
}

function Page({ titleText, subtitle, children }) {
  return <div className="page"><div className="pageTitle"><p className="eyebrow">AWAMS Module</p><h2>{titleText}</h2><span>{subtitle}</span></div>{children}</div>;
}

function Topbar({ worker }) {
  return (
    <header className="topbar">
      <div><p className="eyebrow">Realtime dashboard</p><h2>ASHAConnect / AWAMS</h2></div>
      <div className="topbarRight"><span className="syncBadge">● Online Sync</span><div className="avatar">{worker?.name?.[0] || "A"}</div></div>
    </header>
  );
}

function App() {
  const [worker, setWorker] = useState(() => JSON.parse(localStorage.getItem("worker") || "null"));
  const [page, setPage] = useState("Dashboard");
  const [tick, setTick] = useState(0);
  const refresh = () => setTick((t) => t + 1);
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  }, []);

  if (!worker) return <Login onLogin={setWorker} />;

  const pages = {
    Dashboard: <Dashboard tick={tick} goTo={setPage} />,
    Beneficiaries: <Beneficiaries refresh={refresh} />,
    Records: <Records refresh={refresh} />,
    Appointments: <Appointments refresh={refresh} />,
    Events: <Events refresh={refresh} />,
    Notices: <Notices refresh={refresh} />,
    Reports: <Reports refresh={refresh} />,
    SOS: <SOS />,
  };

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="logoBlock"><div className="logo">A</div><div><b>AWAMS</b><small>ASHAConnect</small></div></div>
        <div className="userChip"><span>👩‍⚕️</span><div><b>{greeting}</b><small>{worker.name}</small></div></div>
        <nav>{NAV.map((item) => <button className={page === item.key ? "active" : ""} key={item.key} onClick={() => setPage(item.key)}><span>{item.icon}</span>{item.label}</button>)}</nav>
        <button className="logout" onClick={() => { localStorage.clear(); location.reload(); }}>Logout</button>
      </aside>
      <main className="content"><Topbar worker={worker} />{pages[page]}</main>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
