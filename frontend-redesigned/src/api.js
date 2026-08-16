const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function api(path, options = {}) {
  const token =
    localStorage.getItem("token") ||
    localStorage.getItem("authToken") ||
    localStorage.getItem("access_token");

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const text = await response.text();

  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.message ||
      data ||
      `Request failed: ${response.status}`;
    throw new Error(message);
  }

  return data;
}
