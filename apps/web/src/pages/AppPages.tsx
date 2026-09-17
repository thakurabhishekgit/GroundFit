import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import type { AlignmentRun, Resume, Skill } from "../lib/api";
import { latexToPreviewHtml } from "../lib/latexPreview";

type DraftSkill = {
  name: string;
  display_name?: string;
  category?: string;
  evidence: { source_type: string; summary: string }[];
};

type RightMode = "draft" | "saved";

export function AppLayout() {
  const { user, loading, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!menuRef.current?.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  if (loading) {
    return <div className="loading-center">Loading…</div>;
  }
  if (!user) return <Navigate to="/" replace />;

  const initials = (user.name || user.email || "?")
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="app-shell">
      <header className="app-nav">
        <div className="app-nav-left">
          <Link to="/app">
            <h1 className="brand">GroundFit</h1>
          </Link>
        </div>
        <nav className="nav-links">
          <NavLink to="/app" end>
            Context
          </NavLink>
          <NavLink to="/app/align">Align</NavLink>
          <div className="profile-menu" ref={menuRef}>
            <button
              type="button"
              className="avatar-btn"
              aria-label="Account menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              {user.picture_url ? (
                <img
                  src={user.picture_url}
                  alt=""
                  className="nav-avatar"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <span className="nav-avatar nav-avatar-fallback">{initials}</span>
              )}
            </button>
            {menuOpen && (
              <div className="profile-dropdown">
                <div className="profile-dropdown-head">
                  <strong>{user.name || "Account"}</strong>
                  <span className="muted">{user.email}</span>
                </div>
                <Link
                  to="/app/profile"
                  className="profile-dropdown-item"
                  onClick={() => setMenuOpen(false)}
                >
                  Profile
                </Link>
                <button
                  type="button"
                  className="profile-dropdown-item danger"
                  onClick={() => {
                    setMenuOpen(false);
                    logout();
                  }}
                >
                  Log out
                </button>
              </div>
            )}
          </div>
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
  const [resultTab, setResultTab] = useState<"warnings" | "matching" | "latex" | "preview">(
    "warnings"
  );
  const [busy, setBusy] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onAlign(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    setFlash(null);
    setRun(null);
    setResultTab("warnings");
    try {
      const { api } = await import("../lib/api");
      const created = await api.createResume(token, title, latex);
      const result = await api.align(token, created.id, jd, "strict");
      setRun(result);
      if ((result.warnings_json || []).length === 0) {
        setResultTab("latex");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Align failed");
    } finally {
      setBusy(false);
    }
  }

  async function onWarningAction(tokenName: string, user_action: string) {
    if (!token || !run) return;
    const norm = tokenName;
    setRun((prev) => {
      if (!prev) return prev;
      const warnings = (prev.warnings_json || []).map((w) =>
        w.token === norm ? { ...w, user_action, saved: true } : w
      );
      return { ...prev, warnings_json: warnings, status: "needs_review" };
    });
    try {
      const { api } = await import("../lib/api");
      const updated = await api.confirmAlign(token, run.id, [
        { token: tokenName, user_action },
      ]);
      setRun((prev) => {
        const serverWarnings = updated.warnings_json || [];
        const localMap = new Map(
          (prev?.warnings_json || [])
            .filter((w) => w.user_action)
            .map((w) => [w.token, w.user_action as string])
        );
        for (const w of serverWarnings) {
          if (w.user_action) localMap.set(w.token, w.user_action);
        }
        localMap.set(norm, user_action);
        const merged = serverWarnings.map((w) => ({
          ...w,
          user_action: localMap.get(w.token) ?? w.user_action,
          saved: Boolean(localMap.get(w.token) ?? w.user_action),
        }));
        const pending = merged.filter((w) => !w.user_action).length;
        return {
          ...updated,
          warnings_json: merged,
          status: pending ? "needs_review" : "awaiting_finalize",
        };
      });
      setFlash(
        user_action === "add_anyway"
          ? `Saved: will include “${tokenName}” on Finalize (no LaTeX regen yet).`
          : `Saved: will skip “${tokenName}” on Finalize (no LaTeX regen yet).`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save decision");
    }
  }

  async function onFinalize() {
    if (!token || !run) return;
    setFinalizing(true);
    setError(null);
    setFlash(null);
    try {
      const { api } = await import("../lib/api");
      // Persist any remaining as skip first (one batch)
      const pending = (run.warnings_json || []).filter((w) => !w.user_action);
      if (pending.length) {
        await api.confirmAlign(
          token,
          run.id,
          pending.map((w) => ({ token: w.token, user_action: "skip" }))
        );
      }
      const updated = await api.finalizeAlign(token, run.id);
      setRun(updated);
      setResultTab("preview");
      setFlash("Final resume generated once. Projects kept from your original LaTeX.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Finalize failed");
    } finally {
      setFinalizing(false);
    }
  }

  function downloadLatex() {
    if (!run?.result_latex) return;
    const blob = new Blob([run.result_latex], { type: "application/x-tex" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "groundfit-aligned.tex";
    a.click();
    URL.revokeObjectURL(url);
  }

  const report = run?.match_report_json;
  const coverageLabel =
    report?.coverage?.label ||
    (run?.coverage_score != null
      ? `Coverage ${Math.round((run.coverage_score || 0) * 100)}% of JD must-haves in your context`
      : null);
  const pendingWarnings = (run?.warnings_json || []).filter((w) => !w.user_action);
  const decidedCount = (run?.warnings_json || []).filter((w) => w.user_action).length;

  return (
    <div className="page-fixed">
      <form className="grid-2" onSubmit={onAlign}>
        <div className="card">
          <h2 className="panel-title">Resume + JD</h2>
          <p className="panel-sub muted">
            Strict mode — no new/removed projects; only rephrase existing content. Add/Skip
            saves decisions; Finalize regenerates LaTeX once.
          </p>
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
          <div className="result-head">
            <h2 className="panel-title" style={{ margin: 0 }}>
              Result
            </h2>
            {run && (
              <div className="result-tabs">
                {(
                  [
                    ["warnings", "Warnings"],
                    ["matching", "Matching"],
                    ["latex", "LaTeX"],
                    ["preview", "Preview"],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    className={`result-tab${resultTab === id ? " active" : ""}`}
                    onClick={() => setResultTab(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {!run && <p className="muted">Aligned output will show here.</p>}

          {run && (
            <>
              <div className="row" style={{ marginBottom: "0.65rem" }}>
                <span className="pill">status: {run.status}</span>
                {coverageLabel && <span className="pill">{coverageLabel}</span>}
              </div>
              {flash && <p className="saved-flash">{flash}</p>}

              {resultTab === "warnings" && (
                <>
                  <div className="panel-scroll">
                    {(run.warnings_json || []).length === 0 ? (
                      <p className="muted">No warnings — all JD must-haves were covered.</p>
                    ) : (
                      (run.warnings_json || []).map((w) => (
                        <div
                          key={w.token}
                          className={`warn-box${w.user_action ? " decided" : ""}`}
                        >
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
                            {w.user_action && (
                              <span className="pill">
                                saved · {w.user_action}
                              </span>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="panel-footer">
                    <p className="muted" style={{ margin: "0 0 0.65rem", fontSize: "0.85rem" }}>
                      Add/Skip only saves your choice ({decidedCount} saved
                      {pendingWarnings.length ? `, ${pendingWarnings.length} left` : ""}).
                      LaTeX is regenerated once when you finalize.
                    </p>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={onFinalize}
                      disabled={finalizing}
                    >
                      {finalizing
                        ? "Finalizing…"
                        : pendingWarnings.length > 0
                          ? `Finalize Resume (skip ${pendingWarnings.length} undecided)`
                          : "Finalize Resume"}
                    </button>
                  </div>
                </>
              )}

              {resultTab === "matching" && (
                <div className="panel-scroll">
                  <p className="muted" style={{ marginTop: 0 }}>
                    <strong>Coverage</strong> = share of JD <em>must-have</em> skills that
                    appear in your saved skill graph (including synonyms like jpa →
                    spring-boot). It is not an ATS score.
                  </p>
                  <h3 style={{ fontSize: "0.95rem", marginBottom: "0.35rem" }}>Matched must-haves</h3>
                  <div className="match-list">
                    {(report?.matched_must || []).length === 0 && (
                      <span className="muted">None</span>
                    )}
                    {(report?.matched_must || []).map((s) => (
                      <span key={s} className="match-chip ok">
                        {s}
                      </span>
                    ))}
                  </div>
                  <h3 style={{ fontSize: "0.95rem", marginBottom: "0.35rem" }}>Missing must-haves</h3>
                  <div className="match-list">
                    {(report?.missing_must || []).length === 0 && (
                      <span className="muted">None</span>
                    )}
                    {(report?.missing_must || []).map((s) => (
                      <span key={s} className="match-chip bad">
                        {s}
                      </span>
                    ))}
                  </div>
                  <h3 style={{ fontSize: "0.95rem", marginBottom: "0.35rem" }}>Matched nice-to-haves</h3>
                  <div className="match-list">
                    {(report?.matched_nice || []).map((s) => (
                      <span key={s} className="match-chip ok">
                        {s}
                      </span>
                    ))}
                  </div>
                  <h3 style={{ fontSize: "0.95rem", marginBottom: "0.35rem" }}>JD must-have list</h3>
                  <div className="match-list">
                    {(report?.must_have || []).map((s) => (
                      <span key={s} className="match-chip">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {resultTab === "latex" && (
                <div className="field grow" style={{ display: "flex", minHeight: 0 }}>
                  <label>Aligned LaTeX</label>
                  <textarea readOnly value={run.result_latex || ""} style={{ flex: 1 }} />
                  <div className="panel-footer">
                    <button type="button" className="btn btn-ghost" onClick={downloadLatex}>
                      Download .tex
                    </button>
                  </div>
                </div>
              )}

              {resultTab === "preview" && (
                <ResumePreview latex={run.result_latex || ""} onDownload={downloadLatex} />
              )}
            </>
          )}
        </div>
      </form>
    </div>
  );
}

export function ProfilePage() {
  const { user, token, logout } = useAuth();
  const [skillCount, setSkillCount] = useState(0);
  const [hasContext, setHasContext] = useState(false);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResume, setSelectedResume] = useState<Resume | null>(null);
  const [resumeTab, setResumeTab] = useState<"preview" | "latex">("preview");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void (async () => {
      try {
        const { api } = await import("../lib/api");
        const [ctx, resumeList] = await Promise.all([
          api.getContext(token),
          api.listResumes(token),
        ]);
        setSkills(ctx.skills);
        setSkillCount(ctx.skills.length);
        setHasContext(Boolean(ctx.context?.raw_text?.trim()));
        setResumes(resumeList);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load profile");
      }
    })();
  }, [token]);

  function downloadSelected() {
    if (!selectedResume) return;
    const blob = new Blob([selectedResume.latex_source], { type: "application/x-tex" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedResume.title.replace(/\s+/g, "-").toLowerCase() || "resume"}.tex`;
    a.click();
    URL.revokeObjectURL(url);
  }

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
          <button type="button" className="btn btn-ghost" onClick={logout}>
            Log out
          </button>
          {error && <p className="error">{error}</p>}
        </div>

        <div className="card" style={{ overflow: "hidden", minHeight: 0 }}>
          {!selectedResume ? (
            <>
              <h2 className="panel-title">Your GroundFit data</h2>
              <p className="panel-sub muted">
                Skills from your work/project context, plus saved resume versions.
              </p>
              <div className="stat-row" style={{ marginBottom: "1rem" }}>
                <div className="stat">
                  <strong>{skillCount}</strong>
                  <span>Skills in graph</span>
                </div>
                <div className="stat">
                  <strong>{resumes.length}</strong>
                  <span>Resume versions</span>
                </div>
                <div className="stat">
                  <strong>{hasContext ? "Yes" : "No"}</strong>
                  <span>Context saved</span>
                </div>
              </div>

              <h3 style={{ margin: "0 0 0.5rem", fontSize: "1rem" }}>Resume versions</h3>
              <div className="panel-scroll" style={{ maxHeight: "28%", marginBottom: "0.75rem" }}>
                {resumes.length === 0 ? (
                  <p className="muted">No resumes saved yet — create one on Align.</p>
                ) : (
                  resumes.map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      className="resume-row"
                      onClick={() => {
                        setSelectedResume(r);
                        setResumeTab("preview");
                      }}
                    >
                      <div>
                        <strong>{r.title}</strong>
                        <div className="muted" style={{ fontSize: "0.78rem" }}>
                          v{r.version}
                          {r.updated_at
                            ? ` · ${new Date(r.updated_at).toLocaleString()}`
                            : ""}
                        </div>
                      </div>
                      <span className="pill">View</span>
                    </button>
                  ))
                )}
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
            </>
          ) : (
            <>
              <div className="result-head">
                <div>
                  <h2 className="panel-title" style={{ margin: 0 }}>
                    {selectedResume.title}
                  </h2>
                  <p className="muted" style={{ margin: "0.25rem 0 0", fontSize: "0.85rem" }}>
                    Version {selectedResume.version}
                  </p>
                </div>
                <div className="result-tabs">
                  <button
                    type="button"
                    className={`result-tab${resumeTab === "preview" ? " active" : ""}`}
                    onClick={() => setResumeTab("preview")}
                  >
                    Preview
                  </button>
                  <button
                    type="button"
                    className={`result-tab${resumeTab === "latex" ? " active" : ""}`}
                    onClick={() => setResumeTab("latex")}
                  >
                    LaTeX
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setSelectedResume(null)}
                  >
                    Back
                  </button>
                </div>
              </div>
              {resumeTab === "preview" ? (
                <ResumePreview latex={selectedResume.latex_source} onDownload={downloadSelected} />
              ) : (
                <div className="field grow" style={{ display: "flex", minHeight: 0, flex: 1 }}>
                  <label>LaTeX source</label>
                  <textarea readOnly value={selectedResume.latex_source} style={{ flex: 1 }} />
                  <div className="panel-footer">
                    <button type="button" className="btn btn-ghost" onClick={downloadSelected}>
                      Download .tex
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ResumePreview({
  latex,
  onDownload,
}: {
  latex: string;
  onDownload: () => void;
}) {
  const html = useMemo(() => latexToPreviewHtml(latex), [latex]);

  return (
    <div className="preview-frame">
      <div className="preview-toolbar">
        <button type="button" className="btn btn-ghost" onClick={onDownload}>
          Download .tex
        </button>
        <span className="pill">Live resume preview</span>
      </div>
      <div
        className="preview-html"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
