import { FormEvent, useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import type { AlignmentRun } from "../lib/api";

export function AppLayout() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="app-shell">
        <p className="muted">Loading…</p>
      </div>
    );
  }
  if (!user) return <Navigate to="/" replace />;

  return (
    <div className="app-shell">
      <header className="nav">
        <div>
          <Link to="/app" style={{ textDecoration: "none" }}>
            <h1 className="brand">GroundFit</h1>
          </Link>
          <p className="muted" style={{ margin: "0.25rem 0 0" }}>
            Signed in as {user.name || user.email}
          </p>
        </div>
        <nav className="nav-links">
          <NavLink to="/app" end>
            Context
          </NavLink>
          <NavLink to="/app/align">Align</NavLink>
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Log out
          </button>
        </nav>
      </header>
      <Outlet />
    </div>
  );
}

export function ContextPage() {
  const { token } = useAuth();
  const [rawText, setRawText] = useState("");
  const [draftSkills, setDraftSkills] = useState<
    {
      name: string;
      display_name?: string;
      category?: string;
      evidence: { source_type: string; summary: string }[];
    }[]
  >([]);
  const [savedCount, setSavedCount] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void (async () => {
      try {
        const { api } = await import("../lib/api");
        const data = await api.getContext(token);
        setRawText(data.context?.raw_text || "");
        setSavedCount(data.skills.length);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load context");
      }
    })();
  }, [token]);

  async function onExtract(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const { api } = await import("../lib/api");
      const preview = await api.extractContext(token, rawText);
      setDraftSkills(preview.skills);
      setMessage(
        preview.notes || `Extracted ${preview.skills.length} skills — review then confirm.`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extract failed");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirm() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const { api } = await import("../lib/api");
      const skills = await api.confirmContext(token, draftSkills);
      setSavedCount(skills.length);
      setMessage(`Saved ${skills.length} skills to your graph.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid-2">
      <form className="card" onSubmit={onExtract}>
        <h2 style={{ marginTop: 0 }}>Experience context</h2>
        <p className="muted">
          Paste detailed roles, projects, and where/why you used each technology. This
          becomes the source of truth for alignment.
        </p>
        <div className="field">
          <label htmlFor="raw">Raw narrative</label>
          <textarea
            id="raw"
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="e.g. At Newmark Freshdesk agent I used Redis to cache processed ticket IDs…"
            required
          />
        </div>
        <div className="row">
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Working…" : "Extract skill graph"}
          </button>
          <span className="pill">{savedCount} skills saved</span>
        </div>
        {message && <p className="muted">{message}</p>}
        {error && <p className="error">{error}</p>}
      </form>

      <div className="card stack">
        <h2 style={{ marginTop: 0 }}>Review draft</h2>
        {draftSkills.length === 0 ? (
          <p className="muted">Extracted skills will appear here for confirmation.</p>
        ) : (
          <>
            <div className="stack">
              {draftSkills.map((skill) => (
                <div
                  key={skill.name}
                  style={{ borderBottom: "1px solid var(--line)", paddingBottom: "0.75rem" }}
                >
                  <strong>{skill.display_name || skill.name}</strong>
                  <span className="muted"> · {skill.category || "skill"}</span>
                  <ul style={{ margin: "0.4rem 0 0", paddingLeft: "1.1rem" }}>
                    {skill.evidence?.map((ev, i) => (
                      <li key={i} className="muted">
                        {ev.summary}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <button className="btn btn-primary" type="button" onClick={onConfirm} disabled={busy}>
              Confirm & save graph
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export function AlignPage() {
  const { token } = useAuth();
  const [title, setTitle] = useState("Base resume");
  const [latex, setLatex] = useState(
    `\\documentclass{article}\n\\begin{document}\n\\section{Summary}\nSoftware engineer.\n\\section{Experience}\n\\begin{itemize}\n  \\item Built services with Java and Spring Boot.\n\\end{itemize}\n\\section{Projects}\n\\begin{itemize}\n  \\item Freshdesk agent with Redis cache.\n\\end{itemize}\n\\section{Skills}\nJava, Spring Boot, Redis\n\\end{document}`
  );
  const [jd, setJd] = useState("");
  const [run, setRun] = useState<AlignmentRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onAlign(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    setRun(null);
    try {
      const { api } = await import("../lib/api");
      const created = await api.createResume(token, title, latex);
      const result = await api.align(token, created.id, jd, "strict");
      setRun(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Align failed");
    } finally {
      setBusy(false);
    }
  }

  async function onWarningAction(tokenName: string, user_action: string) {
    if (!token || !run) return;
    const { api } = await import("../lib/api");
    const updated = await api.confirmAlign(token, run.id, [
      { token: tokenName, user_action },
    ]);
    setRun(updated);
  }

  return (
    <form className="grid-2" onSubmit={onAlign}>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>Resume + JD</h2>
        <div className="field">
          <label htmlFor="title">Resume title</label>
          <input id="title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="latex">LaTeX source</label>
          <textarea id="latex" value={latex} onChange={(e) => setLatex(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="jd">Job description</label>
          <textarea id="jd" value={jd} onChange={(e) => setJd(e.target.value)} required />
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Aligning…" : "Align (strict)"}
        </button>
        {error && <p className="error">{error}</p>}
      </div>

      <div className="card stack">
        <h2 style={{ marginTop: 0 }}>Result</h2>
        {!run && <p className="muted">Aligned LaTeX and warnings will show here.</p>}
        {run && (
          <>
            <div className="row">
              <span className="pill">status: {run.status}</span>
              {run.coverage_score != null && (
                <span className="pill">coverage: {run.coverage_score}</span>
              )}
            </div>
            {(run.warnings_json || []).map((w) => (
              <div key={w.token} className="warn-box">
                <strong>{w.token}</strong>
                <div className="muted">{w.reason}</div>
                <div className="row" style={{ marginTop: "0.5rem" }}>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => onWarningAction(w.token, "add_anyway")}
                  >
                    Add anyway
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => onWarningAction(w.token, "skip")}
                  >
                    Skip
                  </button>
                  {w.user_action && <span className="pill">{w.user_action}</span>}
                </div>
              </div>
            ))}
            <div className="field">
              <label>Aligned LaTeX</label>
              <textarea readOnly value={run.result_latex || ""} />
            </div>
          </>
        )}
      </div>
    </form>
  );
}
