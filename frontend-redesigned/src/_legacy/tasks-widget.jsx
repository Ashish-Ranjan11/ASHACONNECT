import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./tasks-widget.css";

function priorityIcon(priority) {
  if (priority === "high") return "🔴";
  if (priority === "medium") return "🟠";
  return "🟢";
}

function SmartTasksWidget() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(localStorage.getItem("token")));

  async function loadTasks() {
    setLoading(true);
    setMessage("");

    try {
      const result = await api("/api/tasks/today");
      setData(result);
    } catch (err) {
      setMessage(err.message || "Could not load today's tasks.");
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
      loadTasks();
    }
  }, [open, isLoggedIn]);

  if (!isLoggedIn) {
    return null;
  }

  const summary = data?.summary || {};
  const tasks = data?.tasks || [];

  return (
    <>
      <button className="tasksFloatButton" type="button" onClick={() => setOpen(true)}>
        ✅ Today's Tasks
      </button>

      {open && (
        <div className="tasksOverlay">
          <div className="tasksPanel">
            <div className="tasksTop">
              <div>
                <p>Smart ASHA Automation</p>
                <h2>Today's Work Plan</h2>
                <span>{data?.date || "Today"}</span>
              </div>

              <button
                type="button"
                className="tasksClose"
                onClick={() => {
                  setOpen(false);
                  setData(null);
                  setMessage("");
                }}
              >
                ×
              </button>
            </div>

            <div className="tasksActions">
              <button type="button" onClick={loadTasks} disabled={loading}>
                {loading ? "Generating..." : "Generate Today's Tasks"}
              </button>
            </div>

            {message && <div className="tasksMessage">{message}</div>}

            {!data ? (
              <div className="tasksEmpty">
                <span>✅</span>
                <h3>{loading ? "Generating daily tasks..." : "Generate today's ASHA tasks"}</h3>
                <p>
                  The system will automatically collect appointments, pregnancy
                  follow-ups, missed visits, immunization reminders and SOS follow-ups.
                </p>
              </div>
            ) : (
              <>
                <div className="tasksStatsGrid">
                  <div>
                    <b>{summary.total_tasks || 0}</b>
                    <span>Total Tasks</span>
                  </div>

                  <div className="taskHigh">
                    <b>{summary.high_priority || 0}</b>
                    <span>High Priority</span>
                  </div>

                  <div className="taskMedium">
                    <b>{summary.medium_priority || 0}</b>
                    <span>Medium Priority</span>
                  </div>

                  <div className="taskLow">
                    <b>{summary.low_priority || 0}</b>
                    <span>Low Priority</span>
                  </div>
                </div>

                <section className="tasksCard">
                  <div className="tasksSectionHead">
                    <h3>Automated Task List</h3>
                    <span>{tasks.length} generated</span>
                  </div>

                  {!tasks.length ? (
                    <div className="tasksEmptySmall">
                      <span>🎉</span>
                      <b>No pending task for today</b>
                      <p>Everything looks clear from current records.</p>
                    </div>
                  ) : (
                    <div className="taskList">
                      {tasks.map((item, index) => (
                        <div className={`taskItem ${item.priority}`} key={index}>
                          <div className="taskIcon">{priorityIcon(item.priority)}</div>

                          <div className="taskContent">
                            <div className="taskTitleRow">
                              <b>{item.title}</b>
                              <span>{item.priority}</span>
                            </div>

                            <p>{item.reason}</p>

                            <div className="taskMeta">
                              {item.beneficiary_name && (
                                <small>Beneficiary: {item.beneficiary_name}</small>
                              )}

                              {item.beneficiary_phone && (
                                <small>Phone: {item.beneficiary_phone}</small>
                              )}

                              {item.village && (
                                <small>Village: {item.village}</small>
                              )}

                              {item.due_date && (
                                <small>Due: {item.due_date}</small>
                              )}

                              <small>Action: {item.action}</small>
                            </div>
                          </div>
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

const rootId = "tasks-widget-root";

if (!document.getElementById(rootId)) {
  const mount = document.createElement("div");
  mount.id = rootId;
  document.body.appendChild(mount);
  createRoot(mount).render(<SmartTasksWidget />);
}
