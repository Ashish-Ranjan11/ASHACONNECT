import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./portfolio-widget.css";

function riskClass(level) {
  const value = String(level || "").toLowerCase();

  if (value.includes("high")) return "high";
  if (value.includes("medium")) return "medium";

  return "low";
}

function PortfolioWidget() {
  const [open, setOpen] = useState(false);
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(localStorage.getItem("token")));

  async function loadBeneficiaries() {
    try {
      const rows = await api("/api/beneficiaries");
      const list = Array.isArray(rows) ? rows : [];

      setBeneficiaries(list);

      if (list.length && !selectedId) {
        setSelectedId(list[0].beneficiary_id || list[0].id);
      }
    } catch (err) {
      setMessage(err.message || "Login first, then open portfolio.");
    }
  }

  async function loadProfile(id = selectedId) {
    if (!id) {
      setMessage("Please select a beneficiary first.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const data = await api(`/api/beneficiaries/${id}/profile`);
      setProfile(data);
    } catch (err) {
      setMessage(err.message || "Could not load health portfolio.");
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
      loadBeneficiaries();
    }
  }, [open, isLoggedIn]);

  if (!isLoggedIn) {
    return null;
  }

  const b = profile?.beneficiary || {};
  const risk = profile?.risk || {};
  const stats = profile?.stats || {};

  return (
    <>
      <button
        className="portfolioFloatButton"
        type="button"
        onClick={() => setOpen(true)}
      >
        🩺 Health Portfolio
      </button>

      {open && (
        <div className="portfolioWidgetOverlay">
          <div className="portfolioWidgetPanel">
            <div className="portfolioWidgetTop">
              <div>
                <p>Beneficiary Digital Health Portfolio</p>
                <h2>Complete Care Profile</h2>
              </div>

              <button
                className="portfolioClose"
                type="button"
                onClick={() => {
                  setOpen(false);
                  setProfile(null);
                  setMessage("");
                }}
              >
                ×
              </button>
            </div>

            <div className="portfolioControls">
              <select
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
              >
                {beneficiaries.length === 0 ? (
                  <option value="">No beneficiaries found</option>
                ) : (
                  beneficiaries.map((item) => (
                    <option
                      key={item.beneficiary_id || item.id}
                      value={item.beneficiary_id || item.id}
                    >
                      {item.full_name || item.name || "Unnamed Beneficiary"}
                    </option>
                  ))
                )}
              </select>

              <button
                type="button"
                onClick={() => loadProfile()}
                disabled={loading || !selectedId}
              >
                {loading ? "Opening..." : "View Profile"}
              </button>
            </div>

            {message && <div className="portfolioMessage">{message}</div>}

            {!profile ? (
              <div className="portfolioEmpty">
                <span>📁</span>
                <h3>Select a beneficiary</h3>
                <p>
                  Click View Profile to see pregnancy records, immunization,
                  appointments, notices, risk score and next ASHA actions.
                </p>
              </div>
            ) : (
              <>
                <div className="portfolioHeroBox">
                  <div className="portfolioPerson">
                    <div className="portfolioAvatar">
                      {String(b.full_name || b.name || "B").charAt(0)}
                    </div>

                    <div>
                      <h3>{b.full_name || b.name}</h3>
                      <p>
                        {b.category || "general"} • {b.gender || "N/A"} • Age{" "}
                        {b.age || "N/A"}
                      </p>
                      <p>{b.address || b.village || "Address not added"}</p>
                      <p>Contact: {b.contact_no || b.phone || "N/A"}</p>
                      <p>ASHA Worker: {profile.asha_worker?.name || "N/A"}</p>
                    </div>
                  </div>

                  <div className={`portfolioRisk ${riskClass(risk.level)}`}>
                    <span>{risk.level || "Low Risk"}</span>
                    <b>{risk.score || 0}%</b>
                    <small>care risk score</small>
                  </div>
                </div>

                <div className="portfolioStatsGrid">
                  <div>
                    <b>{stats.pregnancy_records || 0}</b>
                    <span>Pregnancy</span>
                  </div>
                  <div>
                    <b>{stats.immunization_records || 0}</b>
                    <span>Immunization</span>
                  </div>
                  <div>
                    <b>{stats.appointments || 0}</b>
                    <span>Appointments</span>
                  </div>
                  <div>
                    <b>{stats.notices || 0}</b>
                    <span>Notices</span>
                  </div>
                </div>

                <div className="portfolioTwoGrid">
                  <section className="portfolioCard">
                    <h3>Risk Reasons</h3>
                    <ul>
                      {(risk.reasons || []).map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </section>

                  <section className="portfolioCard">
                    <h3>Next ASHA Actions</h3>
                    <ul>
                      {(profile.next_actions || []).map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </section>
                </div>

                <section className="portfolioCard">
                  <div className="portfolioSectionHead">
                    <h3>Care Timeline</h3>
                    <span>{profile.timeline?.length || 0} records</span>
                  </div>

                  {!profile.timeline?.length ? (
                    <p className="portfolioMuted">No timeline records yet.</p>
                  ) : (
                    <div className="portfolioTimeline">
                      {profile.timeline.map((item, index) => (
                        <div className="portfolioTimelineItem" key={index}>
                          <div className="portfolioTimelineType">
                            {item.type}
                          </div>

                          <div>
                            <b>{item.title}</b>
                            <p>{item.detail}</p>
                          </div>

                          <time>{item.date || "N/A"}</time>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

const rootId = "portfolio-widget-root";

if (!document.getElementById(rootId)) {
  const mount = document.createElement("div");
  mount.id = rootId;
  document.body.appendChild(mount);
  createRoot(mount).render(<PortfolioWidget />);
}
