import type { Domain, RecommendResponse, Schema, SearchHit } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, init);
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try {
      const j = await r.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j);
    } catch { /* keep default message */ }
    throw new Error(msg);
  }
  return r.json() as Promise<T>;
}

export const getDomains = () =>
  req<{ domains: Domain[] }>("/domains/").then((r) => r.domains);

export const getSchema = (domain: string) =>
  req<Schema>(`/domains/${domain}/schema/`);

export const search = (domain: string, q: string, limit = 6) =>
  req<{ results: SearchHit[] }>(
    `/domains/${domain}/search/?q=${encodeURIComponent(q)}&limit=${limit}`
  ).then((r) => r.results);

export const recommend = (
  domain: string,
  body: { item_id: string; k: number; diversity: number; filters?: Record<string, unknown> }
) =>
  req<RecommendResponse>(`/domains/${domain}/recommend/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });