import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./care-automation.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function getToken() {
  return (
    localStorage.getItem("token") ||
    localStorage.getItem("authToken") ||
    localStorage.getItem("access_token")
  );
}

async function api(path, options = {}) {
  const token = getToken();

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

function arr(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.items)) return value.items;
  if (Array.isArray(value?.data)) return value.data;
  return [];
}

function CareAutomation() {
  const [visible, setVisible] = useState(Boolean(getToken()));
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("reports");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [beneficiaries, setBeneficiaries] = useState([]);
  const [families, setFamilies] = useState([]);
  const [reports, setReports] = useState([]);
  const [messages, setMessages] = useState([]);

  const [beneficiaryId, setBeneficiaryId] = useState("");
  const [familyName, setFamilyName] = useState("");
  const [reportType, setReportType] = useState("monthly");
  const [notes, setNotes] = useState("");

  async function loadData() {
    if (!getToken()) return;

    setLoading(true);

    try {
      const [b, f, r, m] = await Promise.allSettled([
        api("/api/care-automation/beneficiaries"),
        api("/api/care-automation/families"),
        api("/api/care-automation/reports"),
        api("/api/care-automation/messages"),
      ]);

      if (b.status === "fulfilled") {
        const rows = arr(b.value);
        setBeneficiaries(rows);
        if (rows.length && !beneficiaryId) {
          setBeneficiaryId(String(rows[0].beneficiary_id));
        }
      }

      if (f.status === "fulfilled") {
        const rows = arr(f.value);
        setFamilies(rows);
        if (rows.length && !familyName) {
          setFamilyName(rows[0].family_name);
        }
      }

      if (r.status === "fulfilled") setReports(arr(r.value));
      if (m.status === "fulfilled") setMessages(arr(m.value));
    } catch (err) {
      setMessage(err.message || "Unable to load care automation.");
    } finally {
      setLoading(false);
    }
  }

  async function generateIndividual(send = false) {
    if (!beneficiaryId) {
      setMessage("Select a beneficiary first.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const result = await api("/api/care-automation/reports/individual", {
        method: "POST",
        body: JSON.stringify({
          beneficiary_id: Number(beneficiaryId),
          report_type: reportType,
          notes,
          send_to_beneficiary: send,
        }),
      });

      await loadData();

      setMessage(
        send
          ? "Individual report generated and beneficiary message added to Message Queue."
          : "Individual report generated successfully."
      );

      if (result.download_url) {
        window.open(`${API_BASE}${result.download_url}`, "_blank");
      }

      if (send) setTab("messages");
    } catch (err) {
      setMessage(err.message || "Could not generate individual report.");
    } finally {
      setLoading(false);
    }
  }

  async function generateFamily(sendFamily = false, sendPhc = false) {
    if (!familyName) {
      setMessage("Select a family first.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const result = await api("/api/care-automation/reports/family", {
        method: "POST",
        body: JSON.stringify({
          family_name: familyName,
          report_type: reportType,
          notes,
          send_to_family: sendFamily,
          send_copy_to_phc: sendPhc,
        }),
      });

      await loadData();

      setMessage(
        sendFamily || sendPhc
          ? "Family report generated. Family and PHC copy messages added to Message Queue."
          : "Family report generated successfully."
      );

      if (result.download_url) {
        window.open(`${API_BASE}${result.download_url}`, "_blank");
      }

      if (sendFamily || sendPhc) setTab("messages");
    } catch (err) {
      setMessage(err.message || "Could not generate family report.");
    } finally {
      setLoading(false);
    }
  }

  async function generatePhcSummary() {
    setLoading(true);
    setMessage("");

    try {
      const result = await api("/api/care-automation/reports/all-families-phc-summary", {
        method: "POST",
        body: JSON.stringify({
          report_type: reportType,
          notes,
          send_copy_to_phc: true,
        }),
      });

      await loadData();

      setMessage("All-families PHC summary generated and PHC message added to Message Queue.");

      if (result.download_url) {
        window.open(`${API_BASE}${result.download_url}`, "_blank");
      }

      setTab("messages");
    } catch (err) {
      setMessage(err.message || "Could not generate PHC summary.");
    } finally {
      setLoading(false);
    }
  }

  async function runReminderScan() {
    setLoading(true);
    setMessage("");

    try {
      const result = await api("/api/care-automation/reminders/auto-run-now", {
        method: "POST",
        body: JSON.stringify({}),
      });

      await loadData();

      if (result.created_messages > 0) {
        setMessage(`${result.created_messages} reminder message(s) created and added to Message Queue.`);
      } else {
        setMessage("Reminder scan completed. No appointment, vaccination or pregnancy reminder is due right now.");
      }

      setTab("messages");
    } catch (err) {
      setMessage(err.message || "Could not run reminder scan.");
    } finally {
      setLoading(false);
    }
  }

  async function markSent(id) {
    try {
      await api(`/api/care-automation/messages/${id}/mark-sent`, {
        method: "POST",
        body: JSON.stringify({}),
      });

      setMessage("Message marked as sent.");
      await loadData();
    } catch (err) {
      setMessage(err.message || "Could not update message.");
    }
  }

  useEffect(() => {
    const check = () => setVisible(Boolean(getToken()));
    check();

    const timer = setInterval(check, 700);
    window.addEventListener("focus", check);

    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", check);
    };
  }, []);

  useEffect(() => {
    if (open) loadData();
  }, [open]);

  if (!visible) return null;

  return (
    <>
      <button className="careAutomationButton" type="button" onClick={() => setOpen(true)}>
        <span />
        <section>
          <b>Care Automation</b>
          <small>Reports & reminders</small>
        </section>
      </button>

      {open && (
        <div className="careOverlay">
          <section className="careDialog">
            <aside className="careSidebar">
              <div className="careBrand">
                <div />
                <section>
                  <b>Care Automation</b>
                  <span>One-click ASHA workflow</span>
                </section>
              </div>

              <nav>
                <button className={tab === "reports" ? "active" : ""} onClick={() => setTab("reports")}>
                  Generate Reports
                </button>
                <button className={tab === "reminders" ? "active" : ""} onClick={() => setTab("reminders")}>
                  Send Reminders
                </button>
                <button className={tab === "messages" ? "active" : ""} onClick={() => setTab("messages")}>
                  Message Queue
                </button>
                <button className={tab === "history" ? "active" : ""} onClick={() => setTab("history")}>
                  Report History
                </button>
              </nav>

              <div className="careStatus">
                <span>Automation Status</span>
                <b>{loading ? "Working..." : "Ready"}</b>
                <p>Generate reports and prepare beneficiary reminders from ASHA records.</p>
              </div>
            </aside>

            <main className="careMain">
              <button className="careClose" type="button" onClick={() => setOpen(false)}>
                ×
              </button>

              <header className="careHero">
                <p>ASHA Workflow Automation</p>
                <h2>
                  {tab === "reports" && "One-Click Report Generation"}
                  {tab === "reminders" && "Send Due Reminders"}
                  {tab === "messages" && "Message Queue"}
                  {tab === "history" && "Generated Report History"}
                </h2>
                <span>
                  ASHA worker can generate beneficiary reports, family reports, PHC summaries and reminder messages without manual register work.
                </span>
              </header>

              {message && <div className="careMessage">{message}</div>}

              {tab === "reports" && (
                <>
                  <section className="carePanel">
                    <div className="carePanelHead">
                      <div>
                        <h3>Report Details</h3>
                        <p>Select report type, beneficiary/family and add optional ASHA or doctor notes.</p>
                      </div>
                    </div>

                    <div className="careFormGrid">
                      <label>
                        Report Type
                        <select value={reportType} onChange={(e) => setReportType(e.target.value)}>
                          <option value="routine">Routine Checkup</option>
                          <option value="weekly">Weekly Report</option>
                          <option value="monthly">Monthly Report</option>
                        </select>
                      </label>

                      <label>
                        Beneficiary
                        <select value={beneficiaryId} onChange={(e) => setBeneficiaryId(e.target.value)}>
                          {beneficiaries.map((item) => (
                            <option key={item.beneficiary_id} value={item.beneficiary_id}>
                              {item.name} — {item.family_name || "No family"}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label>
                        Family
                        <select value={familyName} onChange={(e) => setFamilyName(e.target.value)}>
                          {families.map((item) => (
                            <option key={item.family_name} value={item.family_name}>
                              {item.family_name} — {item.members} members
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="careFull">
                        ASHA / Doctor Notes
                        <textarea
                          value={notes}
                          onChange={(e) => setNotes(e.target.value)}
                          placeholder="Example: Routine checkup completed. Follow-up required after 7 days."
                        />
                      </label>
                    </div>
                  </section>

                  <div className="careActionGrid">
                    <button type="button" onClick={() => generateIndividual(false)} disabled={loading}>
                      <b>Generate Individual Report</b>
                      <span>Create PDF for selected beneficiary.</span>
                    </button>

                    <button type="button" onClick={() => generateIndividual(true)} disabled={loading}>
                      <b>Generate Individual Report + Add Message</b>
                      <span>Create PDF and add beneficiary message to queue.</span>
                    </button>

                    <button type="button" onClick={() => generateFamily(false, false)} disabled={loading}>
                      <b>Generate Family Report</b>
                      <span>Create full family health PDF.</span>
                    </button>

                    <button type="button" onClick={() => generateFamily(true, true)} disabled={loading}>
                      <b>Generate Family Report + Send Copies</b>
                      <span>Add family and PHC admin copy to queue.</span>
                    </button>

                    <button type="button" onClick={generatePhcSummary} disabled={loading}>
                      <b>Generate All-Families PHC Summary</b>
                      <span>Monthly/weekly ASHA summary for PHC admin.</span>
                    </button>
                  </div>
                </>
              )}

              {tab === "reminders" && (
                <>
                  <section className="carePanel">
                    <div className="carePanelHead">
                      <div>
                        <h3>One-Click Reminder Automation</h3>
                        <p>
                          This checks today and tomorrow’s appointments, vaccination records and pregnancy follow-ups.
                          If anything is due, messages are added to the Message Queue.
                        </p>
                      </div>
                    </div>

                    <div className="careActionGrid">
                      <button type="button" onClick={runReminderScan} disabled={loading}>
                        <b>{loading ? "Checking Records..." : "Send Due Reminders Now"}</b>
                        <span>Find due healthcare events and create reminder messages.</span>
                      </button>

                      <button type="button" onClick={() => setTab("messages")}>
                        <b>Open Message Queue</b>
                        <span>View reminders and report messages ready for WhatsApp.</span>
                      </button>

                      <button type="button" onClick={loadData} disabled={loading}>
                        <b>Refresh Automation Data</b>
                        <span>Reload reports, beneficiaries, families and messages.</span>
                      </button>
                    </div>
                  </section>

                  <section className="carePanel">
                    <div className="carePanelHead">
                      <div>
                        <h3>What Happens After One Click?</h3>
                        <p>No template editing. No confusing settings. The system uses standard ASHA reminder messages.</p>
                      </div>
                    </div>

                    <div className="careFlowGrid">
                      <article>
                        <b>1. System scans records</b>
                        <p>Appointments, vaccination dates and pregnancy follow-up dates are checked.</p>
                      </article>
                      <article>
                        <b>2. Reminder is created</b>
                        <p>If a beneficiary has a due event, a message is created automatically.</p>
                      </article>
                      <article>
                        <b>3. Message Queue updates</b>
                        <p>ASHA worker can open WhatsApp-ready message and mark it as sent.</p>
                      </article>
                    </div>
                  </section>
                </>
              )}

              {tab === "messages" && (
                <section className="carePanel">
                  <div className="carePanelHead">
                    <div>
                      <h3>Outbound Message Queue</h3>
                      <p>Report messages and reminder messages ready for beneficiary communication.</p>
                    </div>
                    <button type="button" onClick={loadData}>Refresh</button>
                  </div>

                  {!messages.length ? (
                    <div className="careEmpty">
                      <h3>No messages queued</h3>
                      <p>Generate a report or click Send Due Reminders Now to create messages.</p>
                    </div>
                  ) : (
                    <div className="careMessageList">
                      {messages.map((item) => (
                        <article className="careMessageCard" key={item.id}>
                          <section>
                            <b>{item.recipient_name || "Recipient"}</b>
                            <p>{item.message}</p>
                            <small>{item.channel} · {item.status} · {item.recipient_phone || "No phone"}</small>
                          </section>

                          <div>
                            {item.whatsapp_link && (
                              <a href={item.whatsapp_link} target="_blank" rel="noreferrer">
                                Open WhatsApp
                              </a>
                            )}
                            {item.related_report_uid && (
                              <a href={`${API_BASE}/api/care-automation/reports/${item.related_report_uid}/download`} target="_blank" rel="noreferrer">
                                Download PDF
                              </a>
                            )}
                            {item.status !== "sent" && (
                              <button type="button" onClick={() => markSent(item.id)}>
                                Mark Sent
                              </button>
                            )}
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </section>
              )}

              {tab === "history" && (
                <section className="carePanel">
                  <div className="carePanelHead">
                    <div>
                      <h3>Generated Reports</h3>
                      <p>All reports generated by this ASHA worker account.</p>
                    </div>
                    <button type="button" onClick={loadData}>Refresh</button>
                  </div>

                  {!reports.length ? (
                    <div className="careEmpty">
                      <h3>No reports generated</h3>
                      <p>Create an individual or family report to see history here.</p>
                    </div>
                  ) : (
                    <div className="careTableWrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Title</th>
                            <th>Scope</th>
                            <th>Type</th>
                            <th>Created</th>
                            <th>Download</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reports.map((report) => (
                            <tr key={report.report_uid}>
                              <td><b>{report.title}</b><small>{report.family_name || "Individual/PHC"}</small></td>
                              <td>{report.scope}</td>
                              <td>{report.report_type}</td>
                              <td>{report.created_at}</td>
                              <td>
                                <a href={`${API_BASE}/api/care-automation/reports/${report.report_uid}/download`} target="_blank" rel="noreferrer">
                                  PDF
                                </a>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              )}
            </main>
          </section>
        </div>
      )}
    </>
  );
}

const rootId = "care-automation-root";

if (!document.getElementById(rootId)) {
  const mount = document.createElement("div");
  mount.id = rootId;
  document.body.appendChild(mount);
  createRoot(mount).render(<CareAutomation />);
}
