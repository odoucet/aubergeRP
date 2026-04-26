/**
 * api.js — Thin wrappers around fetch for all aubergeRP REST endpoints.
 * All functions return the parsed JSON (or throw on HTTP errors).
 */

async function apiFetch(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Health ──────────────────────────────────────────────────────────────────

export function fetchHealth() {
  return apiFetch('/api/health/');
}

// ── Characters ──────────────────────────────────────────────────────────────

export function fetchCharacters() {
  return apiFetch('/api/characters/');
}

export function fetchCharacter(id) {
  return apiFetch(`/api/characters/${id}`);
}

// ── Conversations ────────────────────────────────────────────────────────────

export function fetchConversations(characterId) {
  const qs = characterId ? `?character_id=${encodeURIComponent(characterId)}` : '';
  return apiFetch(`/api/conversations/${qs}`);
}

export function fetchConversation(id) {
  return apiFetch(`/api/conversations/${id}`);
}

export function createConversation(characterId) {
  return apiFetch('/api/conversations/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id: characterId }),
  });
}

export function deleteConversation(id) {
  return apiFetch(`/api/conversations/${id}`, { method: 'DELETE' });
}

// ── Chat (returns a raw Response for SSE streaming) ──────────────────────────

export async function sendMessage(conversationId, content) {
  const res = await fetch(`/api/chat/${conversationId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res; // caller reads .body
}
