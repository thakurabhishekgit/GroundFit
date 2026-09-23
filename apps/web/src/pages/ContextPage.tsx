import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "../lib/auth";
import type { ExperienceRole, PersonalProject, RoleWorkItem, Skill } from "../lib/api";

type DraftSkill = {
  name: string;
  display_name?: string;
  category?: string;
  evidence: { source_type: string; summary: string }[];
};

type LeftPage = "experience" | "projects";
type RightPage = "preview" | "skills";
type SkillsView = "draft" | "saved";

type RoleForm = {
  title: string;
  org: string;
  ownership: string;
  description: string;
};

type WorkForm = {
  name: string;
  summary: string;
  technical: string;
  tech: string;
};

type ProjectForm = {
  name: string;
  problem: string;
  architecture: string;
  description: string;
  tech: string;
};

const emptyRole = (): RoleForm => ({
  title: "",
  org: "",
  ownership: "owned",
  description: "",
});

const emptyWork = (): WorkForm => ({
  name: "",
  summary: "",
  technical: "",
  tech: "",
});

const emptyProject = (): ProjectForm => ({
  name: "",
  problem: "",
  architecture: "",
  description: "",
  tech: "",
});

function parseTech(raw: string): string[] {
  return raw
    .split(/[,|\n]/)
    .map((t) => t.trim())
    .filter(Boolean);
}

export function ContextPage() {
  const { token } = useAuth();
  const [leftPage, setLeftPage] = useState<LeftPage>("experience");
  const [rightPage, setRightPage] = useState<RightPage>("preview");
  const [roles, setRoles] = useState<ExperienceRole[]>([]);
  const [projects, setProjects] = useState<PersonalProject[]>([]);
  const [savedSkills, setSavedSkills] = useState<Skill[]>([]);
  const [draftSkills, setDraftSkills] = useState<DraftSkill[]>([]);
  const [skillsView, setSkillsView] = useState<SkillsView>("saved");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  const [roleForm, setRoleForm] = useState<RoleForm>(emptyRole);
  const [editingRoleId, setEditingRoleId] = useState<string | null>(null);
  const [workForm, setWorkForm] = useState<WorkForm>(emptyWork);
  const [workRoleId, setWorkRoleId] = useState<string | null>(null);
  const [editingWorkId, setEditingWorkId] = useState<string | null>(null);

  const [projectForm, setProjectForm] = useState<ProjectForm>(emptyProject);
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const { api } = await import("../lib/api");
      const data = await api.getContext(token);
      setRoles(data.roles || []);
      setProjects(data.projects || []);
      setSavedSkills(data.skills || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load context");
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  function switchLeft(page: LeftPage) {
    setLeftPage(page);
    setError(null);
    setFlash(null);
    setEditingRoleId(null);
    setRoleForm(emptyRole());
    setWorkRoleId(null);
    setEditingWorkId(null);
    setWorkForm(emptyWork());
    setEditingProjectId(null);
    setProjectForm(emptyProject());
  }

  async function saveRole(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const { api } = await import("../lib/api");
      const body = {
        title: roleForm.title.trim(),
        org: roleForm.org.trim() || null,
        ownership: roleForm.ownership || null,
        description: roleForm.description.trim() || null,
      };
      if (editingRoleId) {
        await api.updateRole(token, editingRoleId, body);
        setFlash("Experience updated");
      } else {
        await api.createRole(token, body);
        setFlash("Experience added");
      }
      setRoleForm(emptyRole());
      setEditingRoleId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveWork(e: FormEvent) {
    e.preventDefault();
    if (!token || !workRoleId) return;
    setBusy(true);
    setError(null);
    try {
      const { api } = await import("../lib/api");
      const body = {
        name: workForm.name.trim(),
        summary: workForm.summary.trim() || undefined,
        technical: workForm.technical.trim() || undefined,
        tech: parseTech(workForm.tech),
      };
      if (editingWorkId) {
        await api.updateWorkItem(token, editingWorkId, body);
        setFlash("Company project updated");
      } else {
        await api.createWorkItem(token, workRoleId, body);
        setFlash("Company project added");
      }
      setWorkForm(emptyWork());
      setEditingWorkId(null);
      setWorkRoleId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveProject(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const { api } = await import("../lib/api");
      const body = {
        name: projectForm.name.trim(),
        problem: projectForm.problem.trim() || undefined,
        architecture: projectForm.architecture.trim() || undefined,
        description: projectForm.description.trim() || undefined,
        tech: parseTech(projectForm.tech),
      };
      if (editingProjectId) {
        await api.updateProject(token, editingProjectId, body);
        setFlash("Project updated");
      } else {
        await api.createProject(token, body);
        setFlash("Project added");
      }
      setProjectForm(emptyProject());
      setEditingProjectId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onExtractSkills() {
    if (!token) return;
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      const { api } = await import("../lib/api");
      const preview = await api.extractContext(token, "");
      setDraftSkills(preview.skills);
      setSkillsView("draft");
      setRightPage("skills");
      setFlash(
        preview.notes ||
          `Extracted ${preview.skills.length} skills — review then confirm.`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extract failed");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirmSkills() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const { api } = await import("../lib/api");
      const skills = await api.confirmContext(token, draftSkills);
      setSavedSkills(skills);
      setSkillsView("saved");
      setRightPage("skills");
      setFlash(`Merged into your graph — ${skills.length} skills total.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    } finally {
      setBusy(false);
    }
  }

  function startEditRole(role: ExperienceRole) {
    setLeftPage("experience");
    setRightPage("preview");
    setEditingRoleId(role.id);
    setRoleForm({
      title: role.title,
      org: role.org || "",
      ownership: role.ownership || "owned",
      description: role.description || "",
    });
  }

  function startEditWork(roleId: string, item: RoleWorkItem) {
    setLeftPage("experience");
    setRightPage("preview");
    setWorkRoleId(roleId);
    setEditingWorkId(item.id);
    setWorkForm({
      name: item.name,
      summary: item.summary || "",
      technical: item.technical || "",
      tech: (item.tech || []).join(", "),
    });
  }

  function startEditProject(p: PersonalProject) {
    setLeftPage("projects");
    setRightPage("preview");
    setEditingProjectId(p.id);
    setProjectForm({
      name: p.name,
      problem: p.problem || "",
      architecture: p.architecture || "",
      description: p.description || "",
      tech: (p.tech || []).join(", "),
    });
  }

  return (
    <div className="page-fixed">
      <div className="grid-2">
        {/* Left: page nav + form */}
        <div className="card context-left">
          <nav className="ctx-page-nav" aria-label="Context sections">
            <button
              type="button"
              className={`ctx-page-link${leftPage === "experience" ? " active" : ""}`}
              onClick={() => switchLeft("experience")}
            >
              Experience
            </button>
            <button
              type="button"
              className={`ctx-page-link${leftPage === "projects" ? " active" : ""}`}
              onClick={() => switchLeft("projects")}
            >
              Personal projects
            </button>
          </nav>

          {error && <p className="error">{error}</p>}
          {flash && <p className="muted">{flash}</p>}

          <div className="panel-scroll context-left-scroll">
            {leftPage === "experience" ? (
              <>
                <h2 className="panel-title">
                  {editingRoleId ? "Edit experience" : "Add experience"}
                </h2>
                <p className="panel-sub muted">
                  Company / role narrative. After saving, add products you shipped there on the
                  right under Company projects.
                </p>
                <form className="ctx-inline-form bare" onSubmit={saveRole}>
                  <div className="field">
                    <label>Title</label>
                    <input
                      value={roleForm.title}
                      onChange={(e) => setRoleForm((f) => ({ ...f, title: e.target.value }))}
                      placeholder="Role title"
                      required
                    />
                  </div>
                  <div className="field-row">
                    <div className="field">
                      <label>Company / org</label>
                      <input
                        value={roleForm.org}
                        onChange={(e) => setRoleForm((f) => ({ ...f, org: e.target.value }))}
                        placeholder="Company name"
                      />
                    </div>
                    <div className="field">
                      <label>Ownership</label>
                      <select
                        value={roleForm.ownership}
                        onChange={(e) =>
                          setRoleForm((f) => ({ ...f, ownership: e.target.value }))
                        }
                      >
                        <option value="owned">Owned</option>
                        <option value="led">Led</option>
                        <option value="contributed">Contributed</option>
                      </select>
                    </div>
                  </div>
                  <div className="field grow">
                    <label>What you did (detailed)</label>
                    <textarea
                      value={roleForm.description}
                      onChange={(e) =>
                        setRoleForm((f) => ({ ...f, description: e.target.value }))
                      }
                      placeholder="Describe the role, stack, ownership, impact…"
                      rows={8}
                    />
                  </div>
                  <div className="row">
                    <button className="btn btn-primary" type="submit" disabled={busy}>
                      {editingRoleId ? "Update experience" : "Add experience"}
                    </button>
                    {editingRoleId && (
                      <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={() => {
                          setEditingRoleId(null);
                          setRoleForm(emptyRole());
                        }}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </form>

                {workRoleId && (
                  <form className="ctx-nested-form" onSubmit={saveWork}>
                    <h4>
                      {editingWorkId ? "Edit company project" : "Add company project"}
                    </h4>
                    <input
                      value={workForm.name}
                      onChange={(e) => setWorkForm((f) => ({ ...f, name: e.target.value }))}
                      placeholder="Product or initiative name"
                      required
                    />
                    <textarea
                      value={workForm.summary}
                      onChange={(e) =>
                        setWorkForm((f) => ({ ...f, summary: e.target.value }))
                      }
                      placeholder="What it does / your ownership"
                      rows={2}
                    />
                    <textarea
                      value={workForm.technical}
                      onChange={(e) =>
                        setWorkForm((f) => ({ ...f, technical: e.target.value }))
                      }
                      placeholder="Technical details"
                      rows={3}
                    />
                    <input
                      value={workForm.tech}
                      onChange={(e) => setWorkForm((f) => ({ ...f, tech: e.target.value }))}
                      placeholder="Comma-separated skills"
                    />
                    <div className="row">
                      <button className="btn btn-primary" type="submit" disabled={busy}>
                        Save company project
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={() => {
                          setWorkRoleId(null);
                          setEditingWorkId(null);
                          setWorkForm(emptyWork());
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}
              </>
            ) : (
              <>
                <h2 className="panel-title">
                  {editingProjectId ? "Edit personal project" : "Add personal project"}
                </h2>
                <p className="panel-sub muted">
                  Side / resume projects — not products you shipped at a company.
                </p>
                <form className="ctx-inline-form bare" onSubmit={saveProject}>
                  <div className="field">
                    <label>Name</label>
                    <input
                      value={projectForm.name}
                      onChange={(e) =>
                        setProjectForm((f) => ({ ...f, name: e.target.value }))
                      }
                      required
                    />
                  </div>
                  <div className="field">
                    <label>What it does</label>
                    <textarea
                      value={projectForm.problem}
                      onChange={(e) =>
                        setProjectForm((f) => ({ ...f, problem: e.target.value }))
                      }
                      rows={3}
                    />
                  </div>
                  <div className="field">
                    <label>Technical / architecture</label>
                    <textarea
                      value={projectForm.architecture}
                      onChange={(e) =>
                        setProjectForm((f) => ({ ...f, architecture: e.target.value }))
                      }
                      rows={3}
                    />
                  </div>
                  <div className="field">
                    <label>More details</label>
                    <textarea
                      value={projectForm.description}
                      onChange={(e) =>
                        setProjectForm((f) => ({ ...f, description: e.target.value }))
                      }
                      rows={2}
                    />
                  </div>
                  <div className="field">
                    <label>Tech</label>
                    <input
                      value={projectForm.tech}
                      onChange={(e) =>
                        setProjectForm((f) => ({ ...f, tech: e.target.value }))
                      }
                      placeholder="Comma-separated skills"
                    />
                  </div>
                  <div className="row">
                    <button className="btn btn-primary" type="submit" disabled={busy}>
                      {editingProjectId ? "Update project" : "Add project"}
                    </button>
                    {editingProjectId && (
                      <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={() => {
                          setEditingProjectId(null);
                          setProjectForm(emptyProject());
                        }}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              </>
            )}
          </div>

          <div className="panel-footer">
            <button
              type="button"
              className="btn btn-primary"
              disabled={busy}
              onClick={() => void onExtractSkills()}
            >
              {busy ? "Working…" : "Extract skill graph"}
            </button>
            <button
              type="button"
              className={`pill pill-btn${rightPage === "skills" ? " active" : ""}`}
              onClick={() => {
                setRightPage("skills");
                setSkillsView("saved");
              }}
            >
              {savedSkills.length} skills saved · view
            </button>
          </div>
        </div>

        {/* Right: preview | skill graph pages */}
        <div className="card context-right">
          <nav className="ctx-page-nav" aria-label="Preview sections">
            <button
              type="button"
              className={`ctx-page-link${rightPage === "preview" ? " active" : ""}`}
              onClick={() => setRightPage("preview")}
            >
              {leftPage === "experience" ? "Your experience" : "Your projects"}
            </button>
            <button
              type="button"
              className={`ctx-page-link${rightPage === "skills" ? " active" : ""}`}
              onClick={() => setRightPage("skills")}
            >
              Saved skill graph
              {savedSkills.length > 0 ? ` (${savedSkills.length})` : ""}
            </button>
          </nav>

          <div className="panel-scroll context-right-scroll">
            {rightPage === "preview" ? (
              <section className="ctx-preview">
                <p className="panel-sub muted" style={{ marginTop: 0 }}>
                  Preview of what you’ve added — edit or delete anytime.
                </p>

                {leftPage === "experience" ? (
                  roles.length === 0 ? (
                    <p className="muted">Nothing yet — add a role on the left.</p>
                  ) : (
                    roles.map((role) => (
                      <article key={role.id} className="ctx-card">
                        <div className="ctx-card-top">
                          <div>
                            <h3 className="ctx-card-heading">{role.title}</h3>
                            <p className="muted">
                              {role.org || "—"}
                              {role.ownership ? ` · ${role.ownership}` : ""}
                            </p>
                          </div>
                          <div className="row">
                            <button
                              type="button"
                              className="btn btn-ghost"
                              onClick={() => startEditRole(role)}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="btn btn-ghost danger-text"
                              onClick={() =>
                                void (async () => {
                                  if (!token || !window.confirm("Delete this experience?"))
                                    return;
                                  const { api } = await import("../lib/api");
                                  await api.deleteRole(token, role.id);
                                  await load();
                                })()
                              }
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                        {role.description && (
                          <p className="ctx-body">{role.description}</p>
                        )}

                        <div className="ctx-subhead">
                          <strong>Company projects</strong>
                          <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={() => {
                              setLeftPage("experience");
                              setRightPage("preview");
                              setWorkRoleId(role.id);
                              setEditingWorkId(null);
                              setWorkForm(emptyWork());
                            }}
                          >
                            + Add
                          </button>
                        </div>

                        {(role.work_items || []).map((item) => (
                          <div key={item.id} className="ctx-nested">
                            <div className="ctx-card-top">
                              <strong>{item.name}</strong>
                              <div className="row">
                                <button
                                  type="button"
                                  className="btn btn-ghost"
                                  onClick={() => startEditWork(role.id, item)}
                                >
                                  Edit
                                </button>
                                <button
                                  type="button"
                                  className="btn btn-ghost danger-text"
                                  onClick={() =>
                                    void (async () => {
                                      if (
                                        !token ||
                                        !window.confirm("Delete this work item?")
                                      )
                                        return;
                                      const { api } = await import("../lib/api");
                                      await api.deleteWorkItem(token, item.id);
                                      await load();
                                    })()
                                  }
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                            {item.summary && <p>{item.summary}</p>}
                            {item.technical && <p className="muted">{item.technical}</p>}
                            {!!item.tech?.length && (
                              <p className="ctx-tech">{item.tech.join(" · ")}</p>
                            )}
                          </div>
                        ))}
                      </article>
                    ))
                  )
                ) : projects.length === 0 ? (
                  <p className="muted">Nothing yet — add a project on the left.</p>
                ) : (
                  projects.map((p) => (
                    <article key={p.id} className="ctx-card">
                      <div className="ctx-card-top">
                        <h3 className="ctx-card-heading">{p.name}</h3>
                        <div className="row">
                          <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={() => startEditProject(p)}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            className="btn btn-ghost danger-text"
                            onClick={() =>
                              void (async () => {
                                if (!token || !window.confirm("Delete this project?"))
                                  return;
                                const { api } = await import("../lib/api");
                                await api.deleteProject(token, p.id);
                                await load();
                              })()
                            }
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                      {p.problem && <p className="ctx-body">{p.problem}</p>}
                      {p.architecture && <p className="muted">{p.architecture}</p>}
                      {p.description && <p className="muted">{p.description}</p>}
                      {!!p.tech?.length && (
                        <p className="ctx-tech">{p.tech.join(" · ")}</p>
                      )}
                    </article>
                  ))
                )}
              </section>
            ) : (
              <section className="ctx-skills-block">
                <div className="ctx-block-head">
                  <h2 className="panel-title" style={{ margin: 0 }}>
                    {skillsView === "saved" ? "Saved skill graph" : "Review draft"}
                  </h2>
                  {skillsView === "saved" && draftSkills.length > 0 && (
                    <button
                      type="button"
                      className="btn btn-ghost"
                      onClick={() => setSkillsView("draft")}
                    >
                      Back to draft
                    </button>
                  )}
                </div>
                <p className="panel-sub muted" style={{ marginTop: 0 }}>
                  Skills extracted from your experience and personal projects.
                </p>

                {skillsView === "draft" ? (
                  draftSkills.length === 0 ? (
                    <p className="muted">
                      Extracted skills will appear here for confirmation.
                    </p>
                  ) : (
                    <>
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
                      <div className="row" style={{ marginTop: "0.75rem" }}>
                        <button
                          className="btn btn-primary"
                          type="button"
                          onClick={() => void onConfirmSkills()}
                          disabled={busy}
                        >
                          {busy ? "Saving…" : "Confirm & merge into graph"}
                        </button>
                      </div>
                    </>
                  )
                ) : savedSkills.length === 0 ? (
                  <p className="muted">
                    No skills saved yet. Add experience/projects, then extract.
                  </p>
                ) : (
                  savedSkills.map((skill) => (
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
                  ))
                )}
              </section>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
