import { FormEvent, useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import type { AlignmentRun, Skill } from "../lib/api";

type DraftSkill = {
  name: string;
  display_name?: string;
  category?: string;
  evidence: { source_type: string; summary: string }[];
};

type RightMode = "draft" | "saved";

export function AppLayout() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return <div className="loading-center">Loading…</div>;
  }
  if (!user) return <Navigate to="/" replace />;

  return (
    <div className="app-shell">
      <header className="app-nav">
        <div className="app-nav-left">
          <Link to="/app">
            <h1 className="brand">GroundFit</h1>
          </Link>
          <span className="app-nav-user">{user.name || user.email}</span>
        </div>
        <nav className="nav-links">
          <NavLink to="/app" end>
            Context
          </NavLink>
          <NavLink to="/app/align">Align</NavLink>
          <NavLink to="/app/profile">Profile</NavLink>
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Log out
          </button>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

export function ContextPage() {
  const { token } = useAuth();
  const [rawText, setRawText] = useState("");
  const [draftSkills, setDraftSkills] = useState<DraftSkill[]>([]);
  const [savedSkills, setSavedSkills] = useState<Skill[]>([]);
  const [rightMode, setRightMode] = useState<RightMode>("draft");
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
        setSavedSkills(data.skills);
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
      setRightMode("draft");
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
      setSavedSkills(skills);
      setRightMode("saved");
      setMessage(`Saved ${skills.length} skills to your graph.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    } finally {
      setBusy(false);
    }
  }

  function showSaved() {
    setRightMode("saved");
  }

  function showDraft() {
    setRightMode("draft");
  }

  return (
    <div className="page-fixed">
      <div className="grid-2">
        <form className="card" onSubmit={onExtract}>
          <h2 className="panel-title">Experience context</h2>
          <p className="panel-sub muted">
            Paste roles, projects, and where/why you used each technology. This is the
            source of truth for alignment.
          </p>
          <div className="field grow">
            <label htmlFor="raw">Raw narrative</label>
            <textarea
              id="raw"
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="e.g. At Newmark Freshdesk agent I used Redis to cache processed ticket IDs…"
              required
            />
          </div>
          <div className="panel-footer">
            <div className="row">
              <button className="btn btn-primary" type="submit" disabled={busy}>
                {busy ? "Working…" : "Extract skill graph"}
              </button>
              <button
                type="button"
                className={`pill pill-btn${rightMode === "saved" ? " active" : ""}`}
                onClick={showSaved}
                title="View saved skill graph"
              >
                {savedSkills.length} skills saved · view
              </button>
            </div>
            {message && <p className="muted" style={{ margin: "0.65rem 0 0" }}>{message}</p>}
            {error && <p className="error" style={{ marginTop: "0.65rem" }}>{error}</p>}
          </div>
        </form>

        <div className="card">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: "0.5rem" }}>
            <h2 className="panel-title" style={{ margin: 0 }}>
              {rightMode === "saved" ? "Saved skill graph" : "Review draft"}
            </h2>
            {rightMode === "saved" && draftSkills.length > 0 && (
              <button type="button" className="btn btn-ghost" onClick={showDraft}>
                Back to draft
              </button>
            )}
          </div>

          {rightMode === "draft" ? (
            draftSkills.length === 0 ? (
              <p className="muted">Extracted skills will appear here for confirmation.</p>
            ) : (
              <>
                <div className="panel-scroll">
                  {draftSkills.map((skill) => (
                    <div className="skill-item" key={skill.name}>
                      <strong>{skill.display_name || skill.name}</strong>
                      <span className="muted"> · {skill.category || "skill"}</span>
                      <ul>
                        {skill.evidence?.map((ev, i) => (
                          <li key={i} className="muted">
                            {ev.summary}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
                <div className="panel-footer">
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={onConfirm}
                    disabled={busy}
                  >
                    Confirm & save graph
                  </button>
                </div>
              </>
            )
          ) : savedSkills.length === 0 ? (
            <p className="muted">No skills saved yet. Extract and confirm a graph first.</p>
          ) : (
            <div className="panel-scroll">
              {savedSkills.map((skill) => (
                <div className="skill-item" key={skill.id}>
                  <strong>{skill.display_name || skill.name}</strong>
                  <span className="muted"> · {skill.category || "skill"}</span>
                  <ul>
                    {skill.evidence?.map((ev) => (
                      <li key={ev.id} className="muted">
                        {ev.summary}
                        {ev.verified ? " ✓" : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
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
    <div className="page-fixed">
      <form className="grid-2" onSubmit={onAlign}>
        <div className="card">
          <h2 className="panel-title">Resume + JD</h2>
          <p className="panel-sub muted">Strict mode — no invented skills without a warning.</p>
          <div className="field">
            <label htmlFor="title">Resume title</label>
            <input id="title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="field grow">
            <label htmlFor="latex">LaTeX source</label>
            <textarea
              id="latex"
              value={latex}
              onChange={(e) => setLatex(e.target.value)}
              required
            />
          </div>
          <div className="field grow">
            <label htmlFor="jd">Job description</label>
            <textarea id="jd" value={jd} onChange={(e) => setJd(e.target.value)} required />
          </div>
          <div className="panel-footer">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "Aligning…" : "Align (strict)"}
            </button>
            {error && <p className="error" style={{ marginTop: "0.65rem" }}>{error}</p>}
          </div>
        </div>

        <div className="card">
          <h2 className="panel-title">Result</h2>
          {!run && <p className="muted">Aligned LaTeX and warnings will show here.</p>}
          {run && (
            <>
              <div className="row" style={{ marginBottom: "0.75rem" }}>
                <span className="pill">status: {run.status}</span>
                {run.coverage_score != null && (
                  <span className="pill">coverage: {run.coverage_score}</span>
                )}
              </div>
              <div className="panel-scroll">
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
                <div className="field" style={{ minHeight: "200px", display: "flex" }}>
                  <label>Aligned LaTeX</label>
                  <textarea readOnly value={run.result_latex || ""} style={{ flex: 1 }} />
                </div>
              </div>
            </>
          )}
        </div>
      </form>
    </div>
  );
}

export function ProfilePage() {
  const { user, token } = useAuth();
  const [skillCount, setSkillCount] = useState(0);
  const [resumeCount, setResumeCount] = useState(0);
  const [hasContext, setHasContext] = useState(false);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void (async () => {
      try {
        const { api } = await import("../lib/api");
        const [ctx, resumes] = await Promise.all([
          api.getContext(token),
          api.listResumes(token),
        ]);
        setSkills(ctx.skills);
        setSkillCount(ctx.skills.length);
        setHasContext(Boolean(ctx.context?.raw_text?.trim()));
        setResumeCount(resumes.length);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load profile");
      }
    })();
  }, [token]);

  if (!user) return null;

  return (
    <div className="page-fixed">
      <div className="profile-grid">
        <div className="card stack">
          {user.picture_url ? (
            <img className="avatar" src={user.picture_url} alt="" referrerPolicy="no-referrer" />
          ) : (
            <div className="avatar" />
          )}
          <div>
            <h2 className="panel-title">{user.name || "User"}</h2>
            <p className="muted" style={{ margin: 0 }}>
              {user.email}
            </p>
          </div>
          <div className="stack" style={{ gap: "0.35rem" }}>
            <span className="pill">Google linked</span>
            <span className="pill">{user.is_active ? "Active" : "Inactive"}</span>
          </div>
          <p className="muted" style={{ fontSize: "0.8rem", wordBreak: "break-all" }}>
            ID {user.id}
          </p>
          {error && <p className="error">{error}</p>}
        </div>

        <div className="card" style={{ overflow: "hidden" }}>
          <h2 className="panel-title">Your GroundFit data</h2>
          <p className="panel-sub muted">Account snapshot from your saved context and resumes.</p>
          <div className="stat-row" style={{ marginBottom: "1rem" }}>
            <div className="stat">
              <strong>{skillCount}</strong>
              <span>Skills in graph</span>
            </div>
            <div className="stat">
              <strong>{resumeCount}</strong>
              <span>Resume versions</span>
            </div>
            <div className="stat">
              <strong>{hasContext ? "Yes" : "No"}</strong>
              <span>Context saved</span>
            </div>
          </div>
          <h3 style={{ margin: "0 0 0.5rem", fontSize: "1rem" }}>Skill inventory</h3>
          <div className="panel-scroll">
            {skills.length === 0 ? (
              <p className="muted">No skills yet — add them on the Context page.</p>
            ) : (
              skills.map((s) => (
                <div className="skill-item" key={s.id}>
                  <strong>{s.display_name || s.name}</strong>
                  <span className="muted"> · {s.category || "skill"}</span>
                  <span className="muted"> · {s.evidence?.length || 0} evidence</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
