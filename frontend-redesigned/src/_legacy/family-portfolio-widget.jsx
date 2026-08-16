import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./family-portfolio-widget.css";

function riskClass(level) {
  const value = String(level || "").toLowerCase();

  if (value.includes("high")) return "high";
  if (value.includes("medium")) return "medium";

  return "low";
}

function FamilyPortfolioWidget() {
  const [open, setOpen] = useState(false);
  const [families, setFamilies] = useState([]);
  const [selectedFamily, setSelectedFamily] = useState("");
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(localStorage.getItem("token")));

  async function loadFamilies() {
    try {
      const rows = await api("/api/families");
      const list = Array.isArray(rows) ? rows : [];

      setFamilies(list);

      if (list.length && !selectedFamily) {
        setSelectedFamily(list[0].family_name);
      }
    } catch (err) {
      setMessage(err.message || "Could not load families.");
    }
  }

  async function loadPortfolio(name = selectedFamily) {
    if (!name) {
      setMessage("Select a family first.");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const data = await api(`/api/families/${encodeURIComponent(name)}/portfolio`);
      setPortfolio(data);
    } catch (err) {
      setMessage(err.message || "Could not load family portfolio.");
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
      loadFamilies();
    }
  }, [open, isLoggedIn]);

  if (!isLoggedIn) {
    return null;
  }

  const family = portfolio?.family || {};
  const risk = portfolio?.family_risk || {};
  const stats = portfolio?.stats || {};

  return (
    <>
      <button
        className="familyFloatButton"
        type="button"
        onClick={() => setOpen(true)}
      >
        👨‍👩‍�� Family Portfolio
      </button>

      {open && (
        <div className="familyOverlay">
          <div className="familyPanel">
            <div className="familyTop">
              <div>
                <p>Family-wise Health Portfolio</p>
                <h2>Household Care Dashboard</h2>
                <span>View family members, risk, records and ASHA actions together.</span>
              </div>

              <button
                type="button"
                className="familyClose"
                onClick={() => {
                  setOpen(false);
                  setPortfolio(null);
                  setMessage("");
                }}
              >
                ×
              </button>
            </div>

            <div className="familyControls">
              <select
                value={selectedFamily}
                onChange={(e) => setSelectedFamily(e.target.value)}
              >
                {families.length === 0 ? (
                  <option value="">No family groups found</option>
                ) : (
                  families.map((item) => (
                    <option key={item.family_name} value={item.family_name}>
                      {item.family_name} — {item.members} members
                    </option>
                  ))
                )}
              </select>

              <button
                type="button"
                onClick={() => loadPortfolio()}
                disabled={loading || !selectedFamily}
              >
                {loading ? "Opening..." : "View Family"}
              </button>
            </div>

            {message && <div className="familyMessage">{message}</div>}

            {!portfolio ? (
              <div className="familyEmpty">
                <span>👨‍👩‍👧</span>
                <h3>Select a family</h3>
                <p>
                  Open a household portfolio to see all members, children,
                  elderly, pregnancy care, immunization, appointments and family risk.
                </p>
              </div>
            ) : (
              <>
                <div className="familyHero">
                  <div className="familyIdentity">
                    <div className="familyAvatar">FH</div>

                    <div>
                      <h3>{family.family_name}</h3>
                      <p>Total Members: {family.total_members}</p>
                      <p>ASHA Worker: {family.asha_worker?.name || "N/A"}</p>
                      <p>Village: {family.asha_worker?.village || "N/A"}</p>
                    </div>
                  </div>

                  <div className={`familyRisk ${riskClass(risk.level)}`}>
                    <span>{risk.level || "Low Risk"}</span>
                    <b>{risk.score || 0}%</b>
                    <small>family risk score</small>
                  </div>
                </div>

                <div className="familyStats">
                  <div><b>{family.total_members || 0}</b><span>Members</span></div>
                  <div><b>{family.children || 0}</b><span>Children</span></div>
                  <div><b>{family.elderly || 0}</b><span>Elderly</span></div>
                  <div><b>{family.pregnant || 0}</b><span>Pregnant</span></div>
                  <div><b>{stats.appointments || 0}</b><span>Appointments</span></div>
                  <div><b>{stats.immunization_records || 0}</b><span>Immunization</span></div>
                </div>

                <div className="familyGrid">
                  <section className="familyCard">
                    <h3>Family Risk Reasons</h3>
                    <ul>
                      {(risk.reasons || []).map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </section>

                  <section className="familyCard">
                    <h3>Recommended ASHA Actions</h3>
                    <ul>
                      {(portfolio.next_actions || []).map((item, index) => (
                        <li key={index}>{item}</li>
                      ))}
                    </ul>
                  </section>
                </div>

                <section className="familyCard">
                  <div className="familySectionHead">
                    <h3>Family Members</h3>
                    <span>{portfolio.members?.length || 0} members</span>
                  </div>

                  <div className="familyMemberGrid">
                    {(portfolio.members || []).map((item) => {
                      const m = item.member || {};
                      const r = item.risk || {};

                      return (
                        <div className="familyMemberCard" key={m.beneficiary_id}>
                          <div className="memberAvatar">
                            {String(m.full_name || m.name || "M").charAt(0)}
                          </div>

                          <div>
                            <h4>{m.full_name || m.name}</h4>
                            <p>{m.age} yrs • {m.gender} • {m.category}</p>
                            <span className={`memberRisk ${riskClass(r.level)}`}>
                              {r.level} • {r.score}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>

                <section className="familyCard">
                  <div className="familySectionHead">
                    <h3>Family Care Timeline</h3>
                    <span>{portfolio.timeline?.length || 0} records</span>
                  </div>

                  {!portfolio.timeline?.length ? (
                    <p className="familyMuted">No family records yet.</p>
                  ) : (
                    <div className="familyTimeline">
                      {portfolio.timeline.map((item, index) => (
                        <div className="familyTimelineItem" key={index}>
                          <div className="familyTimelineType">{item.type}</div>

                          <div>
                            <b>{item.title}</b>
                            <p>{item.member} — {item.detail}</p>
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

const rootId = "family-portfolio-widget-root";

if (!document.getElementById(rootId)) {
  const mount = document.createElement("div");
  mount.id = rootId;
  document.body.appendChild(mount);
  createRoot(mount).render(<FamilyPortfolioWidget />);
}
