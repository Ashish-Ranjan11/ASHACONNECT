import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./register-details-widget.css";

const emptyForm = {
  beneficiary_id: "",
  education: "",
  occupation_type: "",
  occupation_detail: "",
  marital_status: "",
  religion: "",
  family_baby_count: 0,
  last_baby_birth_date: "",
};

function RegisterDetailsWidget() {
  const [open, setOpen] = useState(false);
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [message, setMessage] = useState("");
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(localStorage.getItem("token")));

  async function loadBeneficiaries() {
    try {
      const rows = await api("/api/beneficiaries");
      const list = Array.isArray(rows) ? rows : [];
      setBeneficiaries(list);

      if (list.length) {
        selectBeneficiary(list[0].beneficiary_id || list[0].id, list);
      }
    } catch (err) {
      setMessage(err.message || "Could not load beneficiaries.");
    }
  }

  function selectBeneficiary(id, source = beneficiaries) {
    const selected = source.find((item) => String(item.beneficiary_id || item.id) === String(id));

    if (!selected) {
      setForm({ ...emptyForm, beneficiary_id: id });
      return;
    }

    setForm({
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

  async function saveDetails(e) {
    e.preventDefault();

    if (!form.beneficiary_id) {
      setMessage("Select a beneficiary first.");
      return;
    }

    try {
      await api(`/api/beneficiaries/${form.beneficiary_id}`, {
        method: "PUT",
        body: JSON.stringify(form),
      });

      setMessage("ASHA register details updated successfully.");
      await loadBeneficiaries();
    } catch (err) {
      setMessage(err.message || "Could not update register details.");
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

  if (!isLoggedIn) return null;

  const selectedBeneficiary = beneficiaries.find(
    (item) => String(item.beneficiary_id || item.id) === String(form.beneficiary_id)
  );

  return (
    <>
      <button className="registerFloatButton" type="button" onClick={() => setOpen(true)}>
        🧾 Register Details
      </button>

      {open && (
        <div className="registerOverlay">
          <div className="registerPanel">
            <div className="registerTop">
              <div>
                <p>ASHA Register Extension</p>
                <h2>Education, Occupation, Marriage & Family Data</h2>
                <span>Add the extra columns from the handwritten ASHA register.</span>
              </div>

              <button
                className="registerClose"
                type="button"
                onClick={() => {
                  setOpen(false);
                  setMessage("");
                }}
              >
                ×
              </button>
            </div>

            {message && <div className="registerMessage">{message}</div>}

            <form className="registerForm" onSubmit={saveDetails}>
              <label>
                Beneficiary
                <select
                  value={form.beneficiary_id}
                  onChange={(e) => selectBeneficiary(e.target.value)}
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
                <select
                  value={form.education}
                  onChange={(e) => setForm({ ...form, education: e.target.value })}
                >
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
                <select
                  value={form.occupation_type}
                  onChange={(e) => setForm({ ...form, occupation_type: e.target.value })}
                >
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
                <input
                  value={form.occupation_detail}
                  onChange={(e) => setForm({ ...form, occupation_detail: e.target.value })}
                  placeholder="Example: shop, driver, teacher, farmer"
                />
              </label>

              <label>
                Marital Status
                <select
                  value={form.marital_status}
                  onChange={(e) => setForm({ ...form, marital_status: e.target.value })}
                >
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
                <input
                  value={form.religion}
                  onChange={(e) => setForm({ ...form, religion: e.target.value })}
                  placeholder="Example: Hindu, Buddhist, Christian, Muslim"
                />
              </label>

              <label>
                Number of Babies in Family
                <input
                  type="number"
                  min="0"
                  value={form.family_baby_count}
                  onChange={(e) => setForm({ ...form, family_baby_count: e.target.value })}
                />
              </label>

              <label>
                Last Baby Birth Date
                <input
                  type="date"
                  value={form.last_baby_birth_date}
                  onChange={(e) => setForm({ ...form, last_baby_birth_date: e.target.value })}
                />
              </label>

              <button className="registerSaveButton" type="submit">
                Save Register Details
              </button>
            </form>

            {selectedBeneficiary && (
              <div className="registerPreview">
                <h3>Current Register Preview</h3>

                <div className="registerPreviewGrid">
                  <div><span>Name</span><b>{selectedBeneficiary.full_name || selectedBeneficiary.name}</b></div>
                  <div><span>Family</span><b>{selectedBeneficiary.address || "N/A"}</b></div>
                  <div><span>Education</span><b>{form.education || "N/A"}</b></div>
                  <div><span>Occupation</span><b>{form.occupation_type || "N/A"}</b></div>
                  <div><span>Marital Status</span><b>{form.marital_status || "N/A"}</b></div>
                  <div><span>Religion</span><b>{form.religion || "N/A"}</b></div>
                  <div><span>Babies in Family</span><b>{form.family_baby_count || 0}</b></div>
                  <div><span>Last Baby Date</span><b>{form.last_baby_birth_date || "N/A"}</b></div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

const rootId = "register-details-widget-root";

if (!document.getElementById(rootId)) {
  const mount = document.createElement("div");
  mount.id = rootId;
  document.body.appendChild(mount);
  createRoot(mount).render(<RegisterDetailsWidget />);
}
