const API_BASE =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";


export function getAuthToken() {
  return (
    localStorage.getItem("token") ||
    localStorage.getItem("authToken") ||
    localStorage.getItem("access_token") ||
    ""
  );
}


export function clearAuthSession() {
  localStorage.removeItem("token");
  localStorage.removeItem("authToken");
  localStorage.removeItem("access_token");
}


export async function api(path, options = {}) {

  const token = getAuthToken();

  const headers = {
    ...(options.body
      ? { "Content-Type": "application/json" }
      : {}),
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization =
      `Bearer ${token}`;
  }

  let response;

  try {

    response = await fetch(
      `${API_BASE}${path}`,
      {
        ...options,
        headers,
      }
    );

  } catch (error) {

    throw new Error(
      "Unable to reach ASHA Connect backend."
    );
  }


  const text = await response.text();

  let data = null;

  try {
    data = text
      ? JSON.parse(text)
      : null;
  } catch {
    data = text;
  }


  // =========================================================
  // CENTRAL AUTH EXPIRY HANDLING
  // =========================================================

  if (response.status === 401) {

    clearAuthSession();

    window.dispatchEvent(
      new CustomEvent(
        "asha-auth-expired",
        {
          detail: {
            path,
          },
        }
      )
    );

    throw new Error(
      "Your session has expired. Please sign in again."
    );
  }


  if (!response.ok) {

    const message =
      data?.detail ||
      data?.message ||
      data ||
      `Request failed: ${response.status}`;

    throw new Error(
      typeof message === "string"
        ? message
        : JSON.stringify(message)
    );
  }


  return data;
}
