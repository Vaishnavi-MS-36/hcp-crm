const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function sendChatMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Chat request failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchCurrentInteraction(sessionId) {
  const res = await fetch(`${API_BASE}/api/interactions/${sessionId}/current`);
  if (!res.ok) throw new Error("Failed to load current interaction");
  return res.json();
}
export async function updateInteractionFields(sessionId, updates) {
  const res = await fetch(`${API_BASE}/api/interactions/${sessionId}/fields`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Field update failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function startNewInteraction(sessionId) {
  const res = await fetch(`${API_BASE}/api/interactions/${sessionId}/new`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to start new interaction");
  return res.json();
}
