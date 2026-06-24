import React from "react";
import "./login-page.css";

const imagePath = (fileName) => `${import.meta.env.BASE_URL}images/${fileName}`;

const demoAccounts = [
  {
    label: "ASHA Worker",
    email: "asha@example.com",
    role: "Field Dashboard",
  },
  {
    label: "ASHA Worker 2",
    email: "asha2@example.com",
    role: "Community Care",
  },
  {
    label: "PHC Admin",
    email: "phcadmin@example.com",
    role: "PHC Command",
  },
  {
    label: "Supervisor",
    email: "supervisor@example.com",
    role: "District Oversight",
  },
];

const featureBanners = [
  {
    title: "Pregnancy Monitoring",
    text: "Track ANC visits, hemoglobin, blood pressure, EDD and high-risk pregnancy flags.",
    icon: "🩺",
  },
  {
    title: "Immunization Follow-up",
    text: "Monitor vaccine schedules, missed doses and child health checkpoints.",
    icon: "💉",
  },
  {
    title: "Reports, Notices & SOS",
    text: "Generate monthly reports, send reminders and trigger emergency field alerts.",
    icon: "🚨",
  },
];

const communityVoices = [
  {
    quote: "I do what I do to make sure my community is safe, informed and healthy.",
    name: "Community ASHA Voice",
    role: "Frontline Health Worker",
  },
  {
    quote: "Every household visit helps identify risks early and connect families to care.",
    name: "Village Health Support",
    role: "Maternal & Child Health",
  },
  {
    quote: "Digital records reduce missed follow-ups and make community healthcare easier to track.",
    name: "PHC Care Team",
    role: "Primary Health Centre",
  },
];

const ashaFacts = [
  {
    title: "Home Visit Support",
    text: "ASHA workers connect households with maternal, child and preventive healthcare services.",
    image: imagePath("asha-home-visit.jpg"),
  },
  {
    title: "Mother & Child Care",
    text: "They help monitor pregnancy, newborn care, nutrition and immunization follow-ups.",
    image: imagePath("mother-child-care.jpg"),
  },
  {
    title: "Community Outreach",
    text: "They coordinate awareness sessions, referrals, reminders and village-level health drives.",
    image: imagePath("community-outreach.jpg"),
  },
];

export default function LoginPage({
  email,
  setEmail,
  password,
  setPassword,
  onSubmit,
  error,
  loading = false,
}) {
  return (
    <div className="cc-login-shell">
      <div className="cc-bg-orb cc-bg-orb-one" />
      <div className="cc-bg-orb cc-bg-orb-two" />
      <div className="cc-grid-lines" />

      <div className="cc-login-layout">
        <section className="cc-showcase-panel">
          <div className="cc-brand-strip">
            <div className="cc-brand-mark">AC</div>

            <div>
              <p className="cc-mini-label">ASHA CONNECT</p>
              <h1>ASHA Workers Workflow Automation and Database Management</h1>
              <p className="cc-subtitle">
                A modern digital workspace built for ASHA workers, PHC administrators
                and supervisors to manage beneficiary care, clinical records, reminders,
                reports and emergency workflows.
              </p>
            </div>
          </div>

          <div className="cc-hero-banner">
            <div className="cc-hero-copy">
              <span className="cc-live-pill">● Live Field Operations</span>

              <h2>One intelligent platform for frontline healthcare workflows.</h2>

              <p>
                Manage beneficiaries, pregnancy records, immunization schedules,
                appointments, events, notices, monthly reports and SOS alerts through a
                structured health operations dashboard.
              </p>

              <div className="cc-stat-row">
                <div className="cc-stat-card">
                  <strong>Multi Role</strong>
                  <span>ASHA • PHC Admin • Supervisor</span>
                </div>

                <div className="cc-stat-card">
                  <strong>Clinical Tracking</strong>
                  <span>Pregnancy • Immunization • Follow-up</span>
                </div>

                <div className="cc-stat-card">
                  <strong>Field Safety</strong>
                  <span>SOS Alerts • Notices • Reports</span>
                </div>
              </div>
            </div>
          </div>

          <div className="cc-feature-banner-grid">
            {featureBanners.map((item) => (
              <div className="cc-feature-banner" key={item.title}>
                <div className="cc-feature-icon">{item.icon}</div>

                <div>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="cc-community-section">
            <div className="cc-community-quote-card">
              <div className="cc-community-quote-content">
                <span className="cc-quote-mark">“</span>

                <h2>I do what I do to make sure my community is safe and healthy.</h2>

                <p>
                  ASHA workers are the bridge between rural households and public
                  healthcare services. ASHA CONNECT supports that work with digital
                  records, automated reminders, reports, and emergency assistance.
                </p>

                <div className="cc-community-person">
                  <strong>Voice from the community</strong>
                  <span>Inspired by frontline ASHA workers</span>
                </div>
              </div>

              <div className="cc-community-image-wrap">
                <img
                  src={imagePath("asha-community-voice.jpg")}
                  alt="ASHA worker community voice"
                  onError={(event) => {
                    event.currentTarget.style.display = "none";
                  }}
                />
              </div>
            </div>

            <div className="cc-voice-grid">
              {communityVoices.map((voice) => (
                <article className="cc-voice-card" key={voice.quote}>
                  <span>“</span>
                  <p>{voice.quote}</p>

                  <div>
                    <strong>{voice.name}</strong>
                    <small>{voice.role}</small>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="cc-facts-section">
            <div className="cc-facts-header">
              <div>
                <p className="cc-mini-label">FIELD WORK INSIGHTS</p>
                <h3>What ASHA workers do on the ground</h3>
              </div>

              <span className="cc-soft-badge">Human-centered public health work</span>
            </div>

            <div className="cc-facts-grid">
              {ashaFacts.map((fact) => (
                <article className="cc-fact-card" key={fact.title}>
                  <div
                    className="cc-fact-image"
                    style={{ backgroundImage: `url(${fact.image})` }}
                  />

                  <div className="cc-fact-content">
                    <h4>{fact.title}</h4>
                    <p>{fact.text}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="cc-auth-panel">
          <div className="cc-auth-card">
            <div className="cc-auth-topbar">
              <span className="cc-auth-pill">Secure Login</span>
              <span className="cc-auth-pill alt">Role Based Access</span>
            </div>

            <div className="cc-auth-heading">
              <p className="cc-mini-label dark">WELCOME BACK</p>
              <h2>Sign in to ASHA CONNECT</h2>
              <p>
                Access your personalized workspace for beneficiary care, clinical
                tracking, workflow automation, reporting and emergency safety support.
              </p>
            </div>

            <div className="cc-demo-role-grid">
              {demoAccounts.map((account) => (
                <button
                  type="button"
                  className="cc-demo-role"
                  key={account.email}
                  onClick={() => {
                    setEmail(account.email);
                    setPassword("password123");
                  }}
                >
                  <strong>{account.label}</strong>
                  <span>{account.role}</span>
                </button>
              ))}
            </div>

            <form className="cc-login-form" onSubmit={onSubmit}>
              <label>
                <span>Email Address</span>
                <input
                  type="email"
                  placeholder="Enter your work email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </label>

              <label>
                <span>Password</span>
                <input
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </label>

              {error ? <div className="cc-login-error">{error}</div> : null}

              <button type="submit" className="cc-login-button" disabled={loading}>
                {loading ? "Signing in..." : "Enter Dashboard"}
              </button>
            </form>

            <div className="cc-login-footer">
              <div className="cc-footer-card">
                <strong>Demo Password</strong>
                <span>password123</span>
              </div>

              <div className="cc-footer-card">
                <strong>System Focus</strong>
                <span>Workflow • Data • Safety</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}