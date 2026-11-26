// Small fetch wrapper: every call goes to the Python FastAPI server.
// Errors come back as { detail: "..." }, which we turn into readable messages.

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 204) return null;

  let body = null;
  try {
    body = await response.json();
  } catch {
    // non-JSON (e.g. the server is not running behind the proxy)
  }
  if (!response.ok) {
    const message =
      typeof body?.detail === "string"
        ? body.detail
        : response.status >= 500 || !body
          ? "Can't reach the JobHunt server. Is `jobhunt serve` running?"
          : `Request failed (${response.status})`;
    throw new Error(message);
  }
  return body;
}

export const api = {
  sources: () => request("/api/sources"),

  search: (params) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== "" && value !== null && value !== undefined && value !== false) {
        query.set(key, String(value));
      }
    });
    return request(`/api/search?${query}`);
  },

  job: (id) => request(`/api/jobs/${encodeURIComponent(id)}`),

  applications: () => request("/api/applications"),
  transitions: () => request("/api/transitions"),
  report: () => request("/api/report"),

  saveJob: (job) => request("/api/applications", { method: "POST", body: JSON.stringify(job) }),

  updateStatus: (id, status, note) =>
    request(`/api/applications/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ status, note: note || null }),
    }),

  remove: (id) => request(`/api/applications/${encodeURIComponent(id)}`, { method: "DELETE" }),
};
