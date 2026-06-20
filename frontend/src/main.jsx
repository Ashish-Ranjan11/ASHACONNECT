import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./dashboard.css";
import { api } from "./api";
import LoginPage from "./components/LoginPage";

const todayISO = new Date().toISOString().slice(0, 10);

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: "📊" },
  { id: "beneficiaries", label: "Beneficiaries", icon: "👥" },
  { id: "pregnancy", label: "Pregnancy", icon: "🤰" },
  { id: "immunization", label: "Immunization", icon: "💉" },
  { id: "appointments", label: "Appointments", icon: "📅" },
  { id: "events", label: "Events", icon: "🏥" },
  { id: "notices", label: "Notices", icon: "📢" },
  { id: "reports", label: "Reports", icon: "📄" },
  { id: "sos", label: "SOS", icon: "🚨" },
];

const defaultSummary = {
  beneficiaries_total: 0,
  pregnancies_total: 0,
  immunizations_total: 0,
  appointments_total: 0,
  events_total: 0,
  reports_total: 0,
  category_breakdown: {
    pregnant: 0,
    child: 0,
    elderly: 0,
    general: 0,
  },
  clinical_risk: {
    high_risk_pregnancies: 0,
    low_hb_cases: 0,
    missed_immunizations: 0,
    overdue_appointments: 0,
  },
  care_pipeline: [
    { label: "Beneficiaries", value: 0, target: 1 },
    { label: "Pregnancy Records", value: 0, target: 1 },
    { label: "Immunizations", value: 0, target: 1 },
    { label: "Appointments", value: 0, target: 1 },
  ],
  upcoming: [],
  recent_notices: [],
  worker: null,
};

function asArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.data)) return data.data;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.reports)) return data.reports;
  return [];
}

function getId(item) {
  return (
    item?.id ||
    item?.beneficiary_id ||
    item?.record_id ||
    item?.appointment_id ||
    item?.event_id ||
    item?.notice_id ||
    item?.report_id ||
    item?.alert_id
  );
}

function formatDate(value) {
  if (!value) return "N/A";
  try {
    return new Date(value).toLocaleDateString();
  } catch {
    return value;
  }
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [currentUser, setCurrentUser] = useState(null);

  const [email, setEmail] = useState("asha@example.com");
  const [password, setPassword] = useState("password123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [activePage, setActivePage] = useState("dashboard");
  const [message, setMessage] = useState("");

  const [summary, setSummary] = useState(defaultSummary);
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [pregnancyRecords, setPregnancyRecords] = useState([]);
  const [immunizationRecords, setImmunizationRecords] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [events, setEvents] = useState([]);
  const [notices, setNotices] = useState([]);
  const [reports, setReports] = useState([]);
  const [sosAlerts, setSosAlerts] = useState([]);

  const [beneficiaryForm, setBeneficiaryForm] = useState({
    name: "",
    age: "",
    gender: "female",
    phone: "",
    village: "",
    category: "general",
    address: "",
  });

  const [pregnancyForm, setPregnancyForm] = useState({
    beneficiary_id: "",
    trimester: "first",
    hb_level: "",
    bp: "",
    edd: todayISO,
    status: "normal",
    notes: "",
  });

  const [immunizationForm, setImmunizationForm] = useState({
    beneficiary_id: "",
    vaccine_name: "",
    due_date: todayISO,
    given_date: "",
    status: "due",
    notes: "",
  });

  const [appointmentForm, setAppointmentForm] = useState({
    beneficiary_id: "",
    title: "",
    appointment_date: todayISO,
    appointment_time: "10:00",
    location: "",
    status: "scheduled",
  });

  const [eventForm, setEventForm] = useState({
    title: "",
    description: "",
    event_date: todayISO,
    start_time: "10:00",
    location: "",
    category: "awareness",
  });

  const [noticeForm, setNoticeForm] = useState({
    title: "",
    message: "",
    priority: "normal",
  });

  const [sosForm, setSosForm] = useState({
    message: "Emergency assistance required",
    location: "",
    severity: "high",
  });

  const beneficiaryMap = useMemo(() => {
    const map = {};
    beneficiaries.forEach((item) => {
      map[item.beneficiary_id || item.id] = item.name;
    });
    return map;
  }, [beneficiaries]);

  useEffect(() => {
    if (token) {
      loadAllData();
    }
  }, [token]);

  async function safeLoad(path, fallback) {
    try {
      return await api(path);
    } catch {
      return fallback;
    }
  }

  async function loadAllData() {
    const [
      meData,
      summaryData,
      beneficiaryData,
      pregnancyData,
      immunizationData,
      appointmentData,
      eventData,
      noticeData,
      reportData,
      sosData,
    ] = await Promise.all([
      safeLoad("/api/auth/me", null),
      safeLoad("/api/dashboard/summary", defaultSummary),
      safeLoad("/api/beneficiaries", []),
      safeLoad("/api/pregnancy-records", []),
      safeLoad("/api/immunization-records", []),
      safeLoad("/api/appointments", []),
      safeLoad("/api/events", []),
      safeLoad("/api/notices", []),
      safeLoad("/api/reports", []),
      safeLoad("/api/sos", []),
    ]);

    setCurrentUser(meData?.worker || meData || null);

    setSummary({
      ...defaultSummary,
      ...(summaryData || {}),
      category_breakdown: {
        ...defaultSummary.category_breakdown,
        ...(summaryData?.category_breakdown || {}),
      },
      clinical_risk: {
        ...defaultSummary.clinical_risk,
        ...(summaryData?.clinical_risk || {}),
      },
      care_pipeline: summaryData?.care_pipeline || defaultSummary.care_pipeline,
      upcoming: summaryData?.upcoming || [],
      recent_notices: summaryData?.recent_notices || [],
    });

    setBeneficiaries(asArray(beneficiaryData));
    setPregnancyRecords(asArray(pregnancyData));
    setImmunizationRecords(asArray(immunizationData));
    setAppointments(asArray(appointmentData));
    setEvents(asArray(eventData));
    setNotices(asArray(noticeData));
    setReports(asArray(reportData));
    setSosAlerts(asArray(sosData));
  }

  async function handleLogin(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      const receivedToken = data.access_token || data.token;

      if (!receivedToken) {
        throw new Error("Login failed. Token not received.");
      }

      localStorage.setItem("token", receivedToken);
      setToken(receivedToken);
      setCurrentUser(data.worker || null);
      setMessage("Login successful.");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("token");
    setToken("");
    setCurrentUser(null);
    setActivePage("dashboard");
    setMessage("");
  }

  async function submitData(event, path, payload, resetCallback, successMessage) {
    event.preventDefault();

    try {
      await api(path, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setMessage(successMessage);
      resetCallback?.();
      await loadAllData();
    } catch (err) {
      setMessage(err.message || "Something went wrong.");
    }
  }

  async function generateReport() {
    try {
      const data = await api("/api/reports/generate", {
        method: "POST",
      });

      setMessage(data.message || "Monthly report generated successfully.");
      await loadAllData();
    } catch (err) {
      setMessage(err.message || "Failed to generate report.");
    }
  }

  async function downloadReportPDF() {
    try {
      const currentToken = localStorage.getItem("token");

      const response = await fetch("http://127.0.0.1:8000/api/reports/download-pdf", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${currentToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to download PDF report.");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = "ashaconnect-monthly-report.pdf";
      document.body.appendChild(link);
      link.click();

      link.remove();
      window.URL.revokeObjectURL(url);

      setMessage("PDF report downloaded.");
    } catch (err) {
      setMessage(err.message || "Failed to download PDF report.");
    }
  }

  async function triggerSOS(event) {
    event.preventDefault();

    try {
      await api("/api/sos", {
        method: "POST",
        body: JSON.stringify(sosForm),
      });

      setMessage("SOS alert triggered successfully.");
      setSosForm({
        message: "Emergency assistance required",
        location: "",
        severity: "high",
      });

      await loadAllData();
    } catch (err) {
      setMessage(err.message || "Failed to trigger SOS.");
    }
  }

  const workerName =
    currentUser?.name ||
    summary?.worker?.name ||
    "ASHA Worker";

  const workerRole =
    currentUser?.role ||
    summary?.worker?.role ||
    "asha_worker";

  const workerPHC =
    currentUser?.phc?.name ||
    currentUser?.phc ||
    summary?.worker?.phc ||
    "Primary Health Centre";

  if (!token) {
    return (
      <LoginPage
        email={email}
        setEmail={setEmail}
        password={password}
        setPassword={setPassword}
        onSubmit={handleLogin}
        error={error}
        loading={loading}
      />
    );
  }

  function renderDashboard() {
    return (
      <section className="pageGrid">
        <div className="topHeader">
          <div>
            <p className="eyebrow">ASHACONNECT COMMAND CENTER</p>
            <h1>Healthcare Workflow Dashboard</h1>
            <p>
              Manage ASHA field work, beneficiary records, pregnancy tracking,
              immunization follow-ups, appointments, community events, reports and
              emergency alerts from one place.
            </p>
          </div>

          <div className="headerActions">
            <button onClick={loadAllData}>Refresh Data</button>
            <button className="dangerBtn" onClick={() => setActivePage("sos")}>
              Trigger SOS
            </button>
          </div>
        </div>

        <div className="statsGrid">
          <StatCard
            icon="👥"
            label="Beneficiaries"
            value={summary.beneficiaries_total || beneficiaries.length}
            text="Total people under care"
          />
          <StatCard
            icon="🤰"
            label="Pregnancy Records"
            value={summary.pregnancies_total || pregnancyRecords.length}
            text="Maternal health records"
          />
          <StatCard
            icon="💉"
            label="Immunizations"
            value={summary.immunizations_total || immunizationRecords.length}
            text="Child vaccine tracking"
          />
          <StatCard
            icon="📅"
            label="Appointments"
            value={summary.appointments_total || appointments.length}
            text="Scheduled and completed visits"
          />
        </div>

        <div className="dashboardColumns">
          <ChartCard
            title="Beneficiary Distribution"
            subtitle="Category-wise community coverage"
            data={[
              ["Pregnant", summary.category_breakdown?.pregnant || 0],
              ["Child", summary.category_breakdown?.child || 0],
              ["Elderly", summary.category_breakdown?.elderly || 0],
              ["General", summary.category_breakdown?.general || 0],
            ]}
          />

          <ChartCard
            title="Clinical Risk Overview"
            subtitle="Risk indicators requiring attention"
            data={[
              ["High Risk", summary.clinical_risk?.high_risk_pregnancies || 0],
              ["Low Hb", summary.clinical_risk?.low_hb_cases || 0],
              ["Missed Vaccines", summary.clinical_risk?.missed_immunizations || 0],
              ["Overdue Visits", summary.clinical_risk?.overdue_appointments || 0],
            ]}
          />

          <ChartCard
            title="Workflow Progress"
            subtitle="Operational pipeline strength"
            data={(summary.care_pipeline || []).map((item) => [
              item.label,
              item.value || 0,
              item.target || 1,
            ])}
            progress
          />
        </div>

        <div className="dashboardColumns">
          <div className="panel">
            <SectionHeader
              eyebrow="Clinical Intelligence"
              title="Risk & Alert Center"
              subtitle="Cases that need attention from ASHA workers or PHC team."
            />

            <div className="alertList">
              <AlertItem
                level="high"
                title="High Risk Pregnancies"
                text={`${summary.clinical_risk?.high_risk_pregnancies || 0} cases require priority ANC follow-up.`}
              />
              <AlertItem
                level="medium"
                title="Missed Immunizations"
                text={`${summary.clinical_risk?.missed_immunizations || 0} missed vaccine follow-ups found.`}
              />
              <AlertItem
                level="normal"
                title="Upcoming Appointments"
                text={`${summary.clinical_risk?.overdue_appointments || 0} overdue appointments need checking.`}
              />
            </div>
          </div>

          <TimelinePanel
            title="Upcoming Work"
            data={
              summary.upcoming?.length
                ? summary.upcoming
                : appointments.slice(0, 5).map((item) => ({
                    title: item.title || "Appointment",
                    description:
                      beneficiaryMap[item.beneficiary_id] ||
                      item.location ||
                      "Scheduled visit",
                    date:
                      item.appointment_date ||
                      item.date ||
                      item.created_at,
                    status: item.status || "scheduled",
                  }))
            }
          />

          <TimelinePanel
            title="Recent Notices"
            data={
              summary.recent_notices?.length
                ? summary.recent_notices
                : notices.slice(0, 5).map((item) => ({
                    title: item.title,
                    description: item.message,
                    date: item.created_at,
                    status: item.priority || "normal",
                  }))
            }
          />
        </div>

        <div className="panel">
          <SectionHeader
            eyebrow="System Modules"
            title="ASHACONNECT Functional Coverage"
            subtitle="The platform connects field work, clinical records, reporting and safety workflows."
          />

          <div className="moduleGrid">
            <div className="moduleCard">
              <h3>Access Control</h3>
              <ul>
                <li>ASHA login</li>
                <li>PHC admin login</li>
                <li>Supervisor access</li>
              </ul>
            </div>

            <div className="moduleCard">
              <h3>Beneficiary Services</h3>
              <ul>
                <li>Household records</li>
                <li>Pregnancy tracking</li>
                <li>Immunization follow-up</li>
              </ul>
            </div>

            <div className="moduleCard">
              <h3>Outreach</h3>
              <ul>
                <li>Appointments</li>
                <li>Community events</li>
                <li>Notices</li>
              </ul>
            </div>

            <div className="moduleCard">
              <h3>Safety & Reports</h3>
              <ul>
                <li>SOS alerts</li>
                <li>Monthly reports</li>
                <li>PDF export</li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    );
  }

  function renderBeneficiaries() {
    return (
      <section className="pageGrid">
        <PageHeader
          eyebrow="Beneficiary Services"
          title="Beneficiary Management"
          subtitle="Add and manage village-level beneficiaries under ASHA care."
        />

        <div className="panel">
          <SectionHeader
            eyebrow="New Entry"
            title="Add Beneficiary"
            subtitle="Create a beneficiary profile for follow-up and record tracking."
          />

          <form
            className="formGrid"
            onSubmit={(event) =>
              submitData(
                event,
                "/api/beneficiaries",
                {
                  ...beneficiaryForm,
                  age: Number(beneficiaryForm.age || 0),
                },
                () =>
                  setBeneficiaryForm({
                    name: "",
                    age: "",
                    gender: "female",
                    phone: "",
                    village: "",
                    category: "general",
                    address: "",
                  }),
                "Beneficiary added successfully."
              )
            }
          >
            <input
              placeholder="Full name"
              value={beneficiaryForm.name}
              onChange={(e) =>
                setBeneficiaryForm({ ...beneficiaryForm, name: e.target.value })
              }
              required
            />

            <input
              type="number"
              placeholder="Age"
              value={beneficiaryForm.age}
              onChange={(e) =>
                setBeneficiaryForm({ ...beneficiaryForm, age: e.target.value })
              }
              required
            />

            <select
              value={beneficiaryForm.gender}
              onChange={(e) =>
                setBeneficiaryForm({ ...beneficiaryForm, gender: e.target.value })
              }
            >
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>

            <input
              placeholder="Phone"
              value={beneficiaryForm.phone}
              onChange={(e) =>
                setBeneficiaryForm({ ...beneficiaryForm, phone: e.target.value })
              }
            />

            <input
              placeholder="Village"
              value={beneficiaryForm.village}
              onChange={(e) =>
                setBeneficiaryForm({ ...beneficiaryForm, village: e.target.value })
              }
              required
            />

            <select
              value={beneficiaryForm.category}
              onChange={(e) =>
                setBeneficiaryForm({
                  ...beneficiaryForm,
                  category: e.target.value,
                })
              }
            >
              <option value="general">General</option>
              <option value="pregnant">Pregnant</option>
              <option value="child">Child</option>
              <option value="elderly">Elderly</option>
            </select>

            <input
              placeholder="Address"
              value={beneficiaryForm.address}
              onChange={(e) =>
                setBeneficiaryForm({
                  ...beneficiaryForm,
                  address: e.target.value,
                })
              }
            />

            <button type="submit">Add Beneficiary</button>
          </form>
        </div>

        <DataTable
          title="Beneficiary Records"
          columns={["Name", "Age", "Gender", "Category", "Village", "Phone"]}
          rows={beneficiaries.map((item) => [
            item.name,
            item.age,
            item.gender,
            item.category,
            item.village,
            item.phone || "N/A",
          ])}
        />
      </section>
    );
  }

  function renderPregnancy() {
    return (
      <section className="pageGrid">
        <PageHeader
          eyebrow="Clinical Records"
          title="Pregnancy Monitoring"
          subtitle="Track ANC follow-ups, hemoglobin, BP, EDD and risk status."
        />

        <div className="panel">
          <SectionHeader
            eyebrow="New Record"
            title="Add Pregnancy Record"
            subtitle="Connect pregnancy record with an existing beneficiary."
          />

          <form
            className="formGrid"
            onSubmit={(event) =>
              submitData(
                event,
                "/api/pregnancy-records",
                {
                  ...pregnancyForm,
                  beneficiary_id: Number(pregnancyForm.beneficiary_id),
                  hb_level: Number(pregnancyForm.hb_level || 0),
                },
                () =>
                  setPregnancyForm({
                    beneficiary_id: "",
                    trimester: "first",
                    hb_level: "",
                    bp: "",
                    edd: todayISO,
                    status: "normal",
                    notes: "",
                  }),
                "Pregnancy record added successfully."
              )
            }
          >
            <select
              value={pregnancyForm.beneficiary_id}
              onChange={(e) =>
                setPregnancyForm({
                  ...pregnancyForm,
                  beneficiary_id: e.target.value,
                })
              }
              required
            >
              <option value="">Select beneficiary</option>
              {beneficiaries.map((item) => (
                <option key={getId(item)} value={getId(item)}>
                  {item.name}
                </option>
              ))}
            </select>

            <select
              value={pregnancyForm.trimester}
              onChange={(e) =>
                setPregnancyForm({
                  ...pregnancyForm,
                  trimester: e.target.value,
                })
              }
            >
              <option value="first">First Trimester</option>
              <option value="second">Second Trimester</option>
              <option value="third">Third Trimester</option>
            </select>

            <input
              type="number"
              step="0.1"
              placeholder="Hb Level"
              value={pregnancyForm.hb_level}
              onChange={(e) =>
                setPregnancyForm({
                  ...pregnancyForm,
                  hb_level: e.target.value,
                })
              }
            />

            <input
              placeholder="BP"
              value={pregnancyForm.bp}
              onChange={(e) =>
                setPregnancyForm({ ...pregnancyForm, bp: e.target.value })
              }
            />

            <input
              type="date"
              value={pregnancyForm.edd}
              onChange={(e) =>
                setPregnancyForm({ ...pregnancyForm, edd: e.target.value })
              }
            />

            <select
              value={pregnancyForm.status}
              onChange={(e) =>
                setPregnancyForm({
                  ...pregnancyForm,
                  status: e.target.value,
                })
              }
            >
              <option value="normal">Normal</option>
              <option value="high_risk">High Risk</option>
              <option value="completed">Completed</option>
            </select>

            <input
              placeholder="Notes"
              value={pregnancyForm.notes}
              onChange={(e) =>
                setPregnancyForm({ ...pregnancyForm, notes: e.target.value })
              }
            />

            <button type="submit">Add Pregnancy Record</button>
          </form>
        </div>

        <DataTable
          title="Pregnancy Records"
          columns={["Beneficiary", "Trimester", "Hb", "BP", "EDD", "Status"]}
          rows={pregnancyRecords.map((item) => [
            beneficiaryMap[item.beneficiary_id] || item.beneficiary_name || "N/A",
            item.trimester,
            item.hb_level || "N/A",
            item.bp || "N/A",
            formatDate(item.edd),
            item.status,
          ])}
        />
      </section>
    );
  }

  function renderImmunization() {
    return (
      <section className="pageGrid">
        <PageHeader
          eyebrow="Child Health"
          title="Immunization Tracking"
          subtitle="Track vaccine due dates, given dates and missed immunizations."
        />

        <div className="panel">
          <SectionHeader
            eyebrow="New Record"
            title="Add Immunization Record"
            subtitle="Record vaccine status for child beneficiaries."
          />

          <form
            className="formGrid"
            onSubmit={(event) =>
              submitData(
                event,
                "/api/immunization-records",
                {
                  ...immunizationForm,
                  beneficiary_id: Number(immunizationForm.beneficiary_id),
                },
                () =>
                  setImmunizationForm({
                    beneficiary_id: "",
                    vaccine_name: "",
                    due_date: todayISO,
                    given_date: "",
                    status: "due",
                    notes: "",
                  }),
                "Immunization record added successfully."
              )
            }
          >
            <select
              value={immunizationForm.beneficiary_id}
              onChange={(e) =>
                setImmunizationForm({
                  ...immunizationForm,
                  beneficiary_id: e.target.value,
                })
              }
              required
            >
              <option value="">Select beneficiary</option>
              {beneficiaries.map((item) => (
                <option key={getId(item)} value={getId(item)}>
                  {item.name}
                </option>
              ))}
            </select>

            <input
              placeholder="Vaccine name"
              value={immunizationForm.vaccine_name}
              onChange={(e) =>
                setImmunizationForm({
                  ...immunizationForm,
                  vaccine_name: e.target.value,
                })
              }
              required
            />

            <input
              type="date"
              value={immunizationForm.due_date}
              onChange={(e) =>
                setImmunizationForm({
                  ...immunizationForm,
                  due_date: e.target.value,
                })
              }
            />

            <input
              type="date"
              value={immunizationForm.given_date}
              onChange={(e) =>
                setImmunizationForm({
                  ...immunizationForm,
                  given_date: e.target.value,
                })
              }
            />

            <select
              value={immunizationForm.status}
              onChange={(e) =>
                setImmunizationForm({
                  ...immunizationForm,
                  status: e.target.value,
                })
              }
            >
              <option value="due">Due</option>
              <option value="given">Given</option>
              <option value="missed">Missed</option>
            </select>

            <input
              placeholder="Notes"
              value={immunizationForm.notes}
              onChange={(e) =>
                setImmunizationForm({
                  ...immunizationForm,
                  notes: e.target.value,
                })
              }
            />

            <button type="submit">Add Immunization</button>
          </form>
        </div>

        <DataTable
          title="Immunization Records"
          columns={["Beneficiary", "Vaccine", "Due Date", "Given Date", "Status"]}
          rows={immunizationRecords.map((item) => [
            beneficiaryMap[item.beneficiary_id] || item.beneficiary_name || "N/A",
            item.vaccine_name,
            formatDate(item.due_date),
            formatDate(item.given_date),
            item.status,
          ])}
        />
      </section>
    );
  }

  function renderAppointments() {
    return (
      <section className="pageGrid">
        <PageHeader
          eyebrow="Outreach"
          title="Appointment Scheduling"
          subtitle="Schedule beneficiary visits and PHC follow-ups."
        />

        <div className="panel">
          <SectionHeader
            eyebrow="New Appointment"
            title="Schedule Appointment"
            subtitle="Create a follow-up visit for a beneficiary."
          />

          <form
            className="formGrid"
            onSubmit={(event) =>
              submitData(
                event,
                "/api/appointments",
                {
                  ...appointmentForm,
                  beneficiary_id: Number(appointmentForm.beneficiary_id),
                },
                () =>
                  setAppointmentForm({
                    beneficiary_id: "",
                    title: "",
                    appointment_date: todayISO,
                    appointment_time: "10:00",
                    location: "",
                    status: "scheduled",
                  }),
                "Appointment scheduled successfully."
              )
            }
          >
            <select
              value={appointmentForm.beneficiary_id}
              onChange={(e) =>
                setAppointmentForm({
                  ...appointmentForm,
                  beneficiary_id: e.target.value,
                })
              }
              required
            >
              <option value="">Select beneficiary</option>
              {beneficiaries.map((item) => (
                <option key={getId(item)} value={getId(item)}>
                  {item.name}
                </option>
              ))}
            </select>

            <input
              placeholder="Appointment title"
              value={appointmentForm.title}
              onChange={(e) =>
                setAppointmentForm({
                  ...appointmentForm,
                  title: e.target.value,
                })
              }
              required
            />

            <input
              type="date"
              value={appointmentForm.appointment_date}
              onChange={(e) =>
                setAppointmentForm({
                  ...appointmentForm,
                  appointment_date: e.target.value,
                })
              }
            />

            <input
              type="time"
              value={appointmentForm.appointment_time}
              onChange={(e) =>
                setAppointmentForm({
                  ...appointmentForm,
                  appointment_time: e.target.value,
                })
              }
            />

            <input
              placeholder="Location"
              value={appointmentForm.location}
              onChange={(e) =>
                setAppointmentForm({
                  ...appointmentForm,
                  location: e.target.value,
                })
              }
            />

            <select
              value={appointmentForm.status}
              onChange={(e) =>
                setAppointmentForm({
                  ...appointmentForm,
                  status: e.target.value,
                })
              }
            >
              <option value="scheduled">Scheduled</option>
              <option value="completed">Completed</option>
              <option value="missed">Missed</option>
            </select>

            <button type="submit">Schedule Appointment</button>
          </form>
        </div>

        <DataTable
          title="Appointments"
          columns={["Beneficiary", "Title", "Date", "Time", "Location", "Status"]}
          rows={appointments.map((item) => [
            beneficiaryMap[item.beneficiary_id] || item.beneficiary_name || "N/A",
            item.title,
            formatDate(item.appointment_date || item.date),
            item.appointment_time || item.time || "N/A",
            item.location || "N/A",
            item.status,
          ])}
        />
      </section>
    );
  }

  function renderEvents() {
    return (
      <section className="pageGrid">
        <PageHeader
          eyebrow="Community Outreach"
          title="Events Management"
          subtitle="Plan awareness sessions, health camps and village outreach activities."
        />

        <div className="panel">
          <SectionHeader
            eyebrow="New Event"
            title="Create Community Event"
            subtitle="Register outreach activity for community participation."
          />

          <form
            className="formGrid"
            onSubmit={(event) =>
              submitData(
                event,
                "/api/events",
                eventForm,
                () =>
                  setEventForm({
                    title: "",
                    description: "",
                    event_date: todayISO,
                    start_time: "10:00",
                    location: "",
                    category: "awareness",
                  }),
                "Event created successfully."
              )
            }
          >
            <input
              placeholder="Event title"
              value={eventForm.title}
              onChange={(e) =>
                setEventForm({ ...eventForm, title: e.target.value })
              }
              required
            />

            <input
              placeholder="Description"
              value={eventForm.description}
              onChange={(e) =>
                setEventForm({ ...eventForm, description: e.target.value })
              }
            />

            <input
              type="date"
              value={eventForm.event_date}
              onChange={(e) =>
                setEventForm({ ...eventForm, event_date: e.target.value })
              }
            />

            <input
              type="time"
              value={eventForm.start_time}
              onChange={(e) =>
                setEventForm({ ...eventForm, start_time: e.target.value })
              }
            />

            <input
              placeholder="Location"
              value={eventForm.location}
              onChange={(e) =>
                setEventForm({ ...eventForm, location: e.target.value })
              }
            />

            <select
              value={eventForm.category}
              onChange={(e) =>
                setEventForm({ ...eventForm, category: e.target.value })
              }
            >
              <option value="awareness">Awareness</option>
              <option value="immunization">Immunization</option>
              <option value="nutrition">Nutrition</option>
              <option value="health_camp">Health Camp</option>
            </select>

            <button type="submit">Create Event</button>
          </form>
        </div>

        <DataTable
          title="Events"
          columns={["Title", "Category", "Date", "Time", "Location"]}
          rows={events.map((item) => [
            item.title,
            item.category,
            formatDate(item.event_date || item.date),
            item.start_time || item.time || "N/A",
            item.location || "N/A",
          ])}
        />
      </section>
    );
  }

  function renderNotices() {
    return (
      <section className="pageGrid">
        <PageHeader
          eyebrow="Communication"
          title="Notices"
          subtitle="Send and manage community or PHC-level notices."
        />

        <div className="panel">
          <SectionHeader
            eyebrow="New Notice"
            title="Create Notice"
            subtitle="Publish a notice for follow-up or awareness."
          />

          <form
            className="formGrid"
            onSubmit={(event) =>
              submitData(
                event,
                "/api/notices",
                noticeForm,
                () =>
                  setNoticeForm({
                    title: "",
                    message: "",
                    priority: "normal",
                  }),
                "Notice created successfully."
              )
            }
          >
            <input
              placeholder="Notice title"
              value={noticeForm.title}
              onChange={(e) =>
                setNoticeForm({ ...noticeForm, title: e.target.value })
              }
              required
            />

            <input
              placeholder="Message"
              value={noticeForm.message}
              onChange={(e) =>
                setNoticeForm({ ...noticeForm, message: e.target.value })
              }
              required
            />

            <select
              value={noticeForm.priority}
              onChange={(e) =>
                setNoticeForm({ ...noticeForm, priority: e.target.value })
              }
            >
              <option value="normal">Normal</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>

            <button type="submit">Create Notice</button>
          </form>
        </div>

        <DataTable
          title="Notices"
          columns={["Title", "Message", "Priority", "Created"]}
          rows={notices.map((item) => [
            item.title,
            item.message,
            item.priority || "normal",
            formatDate(item.created_at),
          ])}
        />
      </section>
    );
  }

  function renderReports() {
    return (
      <section className="pageGrid">
        <PageHeader
          eyebrow="Monthly Reporting"
          title="Reports"
          subtitle="Generate monthly health workflow reports and export PDF summaries."
        />

        <div className="panel">
          <SectionHeader
            eyebrow="Report Actions"
            title="Generate Monthly Report"
            subtitle="Create a report from current beneficiary, clinical and outreach records."
          />

          <div className="reportActions">
            <button className="primaryAction" onClick={generateReport}>
              Generate Monthly Report
            </button>

            <button className="secondaryAction" onClick={downloadReportPDF}>
              Download PDF Report
            </button>
          </div>
        </div>

        <DataTable
          title="Generated Reports"
          columns={[
            "Month",
            "Year",
            "Patients",
            "Pregnancies",
            "Immunizations",
            "Appointments",
            "Status",
          ]}
          rows={reports.map((item) => [
            item.month,
            item.year,
            item.total_patients,
            item.total_pregnancies,
            item.total_immunizations,
            item.total_appointments,
            item.status,
          ])}
        />
      </section>
    );
  }

  function renderSOS() {
    return (
      <section className="pageGrid">
        <div className="sosPanel">
          <div>
            <h2>Emergency SOS Alert</h2>
            <p>
              Trigger an emergency alert when immediate PHC or supervisor attention is
              required during field work.
            </p>
          </div>

          <button onClick={() => setSosForm({ ...sosForm, severity: "critical" })}>
            Mark Critical
          </button>
        </div>

        <div className="panel">
          <SectionHeader
            eyebrow="Safety Workflow"
            title="Trigger SOS"
            subtitle="Send emergency alert with location and severity."
          />

          <form className="formGrid" onSubmit={triggerSOS}>
            <input
              placeholder="Alert message"
              value={sosForm.message}
              onChange={(e) =>
                setSosForm({ ...sosForm, message: e.target.value })
              }
              required
            />

            <input
              placeholder="Location"
              value={sosForm.location}
              onChange={(e) =>
                setSosForm({ ...sosForm, location: e.target.value })
              }
            />

            <select
              value={sosForm.severity}
              onChange={(e) =>
                setSosForm({ ...sosForm, severity: e.target.value })
              }
            >
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>

            <button className="dangerBtn" type="submit">
              Trigger SOS Alert
            </button>
          </form>
        </div>

        <DataTable
          title="SOS Alerts"
          columns={["Message", "Location", "Severity", "Status", "Created"]}
          rows={sosAlerts.map((item) => [
            item.message,
            item.location || "N/A",
            item.severity || item.priority || "N/A",
            item.status || "active",
            formatDate(item.created_at),
          ])}
        />
      </section>
    );
  }

  function renderActivePage() {
    if (activePage === "dashboard") return renderDashboard();
    if (activePage === "beneficiaries") return renderBeneficiaries();
    if (activePage === "pregnancy") return renderPregnancy();
    if (activePage === "immunization") return renderImmunization();
    if (activePage === "appointments") return renderAppointments();
    if (activePage === "events") return renderEvents();
    if (activePage === "notices") return renderNotices();
    if (activePage === "reports") return renderReports();
    if (activePage === "sos") return renderSOS();
    return renderDashboard();
  }

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brandBlock">
          <div className="brandLogo">AC</div>
          <div>
            <h1>ASHA CCONNECT</h1>
            <p>Workflow Automation & Database Management</p>
          </div>
        </div>

        <nav className="navList">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`navItem ${activePage === item.id ? "active" : ""}`}
              onClick={() => setActivePage(item.id)}
            >
              <span>{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="profileCard">
          <div className="profileAvatar">
            {workerName.slice(0, 1).toUpperCase()}
          </div>

          <div>
            <strong>{workerName}</strong>
            <p>{workerRole}</p>
            <small>{workerPHC}</small>
          </div>
        </div>

        <button className="logoutBtn" onClick={handleLogout}>
          Logout
        </button>
      </aside>

      <main className="mainContent">
        {message ? <div className="messageBox">{message}</div> : null}
        {renderActivePage()}
      </main>
    </div>
  );
}

function PageHeader({ eyebrow, title, subtitle }) {
  return (
    <div className="topHeader">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}

function SectionHeader({ eyebrow, title, subtitle }) {
  return (
    <div className="sectionHeader">
      <span>{eyebrow}</span>
      <h2>{title}</h2>
      {subtitle ? <p>{subtitle}</p> : null}
    </div>
  );
}

function StatCard({ icon, label, value, text }) {
  return (
    <div className="statCard">
      <div className="statTop">
        <span>{icon}</span>
        <small>{label}</small>
      </div>
      <strong>{value}</strong>
      <p>{text}</p>
    </div>
  );
}

function AlertItem({ level, title, text }) {
  return (
    <div className={`alertItem ${level}`}>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

function ChartCard({ title, subtitle, data, progress = false }) {
  const maxValue = Math.max(
    1,
    ...data.map((item) => {
      if (progress) return Number(item[2] || 1);
      return Number(item[1] || 0);
    })
  );

  return (
    <div className="panel chartPanel">
      <div className="chartHeader">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
      </div>

      <div className="barChart">
        {data.map((item) => {
          const label = item[0];
          const value = Number(item[1] || 0);
          const target = progress ? Number(item[2] || maxValue) : maxValue;
          const percentage = Math.min(
            100,
            Math.round((value / Math.max(target, 1)) * 100)
          );

          return (
            <div className="barRow" key={label}>
              <div className="barInfo">
                <span>{label}</span>
                <strong>
                  {value}
                  {progress ? ` / ${target}` : ""}
                </strong>
              </div>

              <div className="barTrack">
                <div className="barFill" style={{ width: `${percentage}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TimelinePanel({ title, data }) {
  return (
    <div className="panel">
      <SectionHeader
        eyebrow="Workflow"
        title={title}
        subtitle="Latest items from your field workflow."
      />

      {data && data.length > 0 ? (
        <div className="timelineList">
          {data.map((item, index) => (
            <div className="timelineItem" key={`${item.title}-${index}`}>
              <strong>{item.title || "Untitled"}</strong>
              <p>{item.description || item.message || "No description available."}</p>
              <span>{item.status || formatDate(item.date)}</span>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No items yet"
          text="New workflow items will appear here after you add data."
        />
      )}
    </div>
  );
}

function DataTable({ title, columns, rows }) {
  return (
    <div className="panel tablePanel">
      <h3>{title}</h3>

      {rows.length > 0 ? (
        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>

            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  {row.map((cell, cellIndex) => (
                    <td key={`${index}-${cellIndex}`}>{cell ?? "N/A"}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title="No records found"
          text="Add new records to display data here."
        />
      )}
    </div>
  );
}

function EmptyState({ title, text }) {
  return (
    <div className="emptyState">
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);