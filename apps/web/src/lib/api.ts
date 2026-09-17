/**
 * Thin API client for GroundFit backend (port 7000).
 */

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:7000";

export type User = {
  id: string;
  email: string;
  name?: string | null;
  picture_url?: string | null;
  google_sub: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
};

export type Skill = {
  id: string;
  name: string;
  display_name?: string | null;
  category?: string | null;
  evidence: { id: string; summary: string; verified: boolean }[];
};

export type Resume = {
  id: string;
  title: string;
  latex_source: string;
  version: number;
};

export type AlignmentRun = {
  id: string;
  resume_id: string;
  jd_text: string;
  mode: string;
  result_latex?: string | null;
  warnings_json?: { token: string; reason: string; user_action?: string | null }[] | null;
  changelog_json?: unknown[] | null;
  coverage_score?: number | null;
  status: string;
  error_message?: string | null;
};

function authHeaders(token: string | null): HeadersInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string | null } = {}
): Promise<T> {
  const { token = null, ...init } = options;
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(token), ...(init.headers || {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  googleLogin: (id_token: string) =>
    request<{ access_token: string; user: User }>("/api/v1/auth/google", {
      method: "POST",
      body: JSON.stringify({ id_token }),
    }),

  me: (token: string) => request<User>("/api/v1/auth/me", { token }),

  getContext: (token: string) =>
    request<{
      context: { raw_text: string } | null;
      skills: Skill[];
    }>("/api/v1/context", { token }),

  saveContext: (token: string, raw_text: string) =>
    request("/api/v1/context", {
      method: "PUT",
      token,
      body: JSON.stringify({ raw_text }),
    }),

  extractContext: (token: string, raw_text: string) =>
    request<{
      skills: {
        name: string;
        display_name?: string;
        category?: string;
        evidence: { source_type: string; summary: string }[];
      }[];
      notes?: string;
    }>("/api/v1/context/extract", {
      method: "POST",
      token,
      body: JSON.stringify({ raw_text }),
    }),

  confirmContext: (token: string, skills: unknown[]) =>
    request<Skill[]>("/api/v1/context/confirm", {
      method: "POST",
      token,
      body: JSON.stringify({ skills, replace_existing: true }),
    }),

  listResumes: (token: string) => request<Resume[]>("/api/v1/resumes", { token }),

  createResume: (token: string, title: string, latex_source: string) =>
    request<Resume>("/api/v1/resumes", {
      method: "POST",
      token,
      body: JSON.stringify({ title, latex_source }),
    }),

  align: (token: string, resume_id: string, jd_text: string, mode = "strict") =>
    request<AlignmentRun>("/api/v1/align", {
      method: "POST",
      token,
      body: JSON.stringify({ resume_id, jd_text, mode }),
    }),

  confirmAlign: (
    token: string,
    run_id: string,
    actions: { token: string; user_action: string }[]
  ) =>
    request<AlignmentRun>(`/api/v1/align/${run_id}/confirm`, {
      method: "POST",
      token,
      body: JSON.stringify({ actions }),
    }),
};
