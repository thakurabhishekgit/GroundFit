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
  created_at?: string;
  updated_at?: string;
};

export type AlignmentRun = {
  id: string;
  resume_id: string;
  jd_text: string;
  mode: string;
  result_latex?: string | null;
  warnings_json?: {
    token: string;
    reason: string;
    user_action?: string | null;
    saved?: boolean;
  }[] | null;
  match_report_json?: {
    must_have?: string[];
    nice_to_have?: string[];
    matched_must?: string[];
    missing_must?: string[];
    matched_nice?: string[];
    missing_nice?: string[];
    coverage?: { matched: number; total: number; score: number; label: string };
  } | null;
  changelog_json?: unknown;
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
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((e: { loc?: unknown[]; msg?: string }) => {
            const where = Array.isArray(e.loc) ? e.loc.slice(1).join(".") : "";
            return where ? `${where}: ${e.msg}` : e.msg || JSON.stringify(e);
          })
          .join("; ");
      } else if (body.detail != null) {
        detail = JSON.stringify(body.detail);
      } else {
        detail = JSON.stringify(body);
      }
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

  confirmContext: (token: string, skills: unknown[], replace_existing = false) =>
    request<Skill[]>("/api/v1/context/confirm", {
      method: "POST",
      token,
      body: JSON.stringify({ skills, replace_existing }),
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

  finalizeAlign: (token: string, run_id: string) =>
    request<AlignmentRun>(`/api/v1/align/${run_id}/finalize`, {
      method: "POST",
      token,
    }),

  listJobLinks: (token: string) =>
    request<JobLink[]>("/api/v1/lists", { token }),

  createJobLink: (
    token: string,
    body: {
      subject: string;
      url: string;
      about?: string | null;
      expires_at?: string | null;
      applied?: boolean;
    }
  ) =>
    request<JobLink>("/api/v1/lists", {
      method: "POST",
      token,
      body: JSON.stringify(body),
    }),

  updateJobLink: (
    token: string,
    id: string,
    body: {
      subject?: string;
      url?: string;
      about?: string | null;
      expires_at?: string | null;
      applied?: boolean;
      clear_expires_at?: boolean;
    }
  ) =>
    request<JobLink>(`/api/v1/lists/${id}`, {
      method: "PATCH",
      token,
      body: JSON.stringify(body),
    }),

  deleteJobLink: (token: string, id: string) =>
    request<void>(`/api/v1/lists/${id}`, {
      method: "DELETE",
      token,
    }),
};

export type JobLink = {
  id: string;
  subject: string;
  url: string;
  about?: string | null;
  expires_at?: string | null;
  applied: boolean;
  reminder_sent_at?: string | null;
  created_at: string;
  updated_at: string;
};
