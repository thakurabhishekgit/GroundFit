import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../lib/auth";
import type { JobLink } from "../lib/api";

type FormState = {
  subject: string;
  url: string;
  about: string;
  expireDate: string;
  expireTime: string;
  applied: boolean;
};

const emptyForm = (): FormState => ({
  subject: "",
  url: "",
  about: "",
  expireDate: "",
  expireTime: "23:59",
  applied: false,
});

const pad = (n: number) => String(n).padStart(2, "0");

function toDateParts(iso: string | null | undefined): { date: string; time: string } {
  if (!iso) return { date: "", time: "23:59" };
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { date: "", time: "23:59" };
  return {
    date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
    time: `${pad(d.getHours())}:${pad(d.getMinutes())}`,
  };
}

function combineToIso(date: string, time: string): string | null {
  if (!date.trim()) return null;
  const t = time.trim() || "23:59";
  const d = new Date(`${date}T${t}`);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

function formatExpiry(iso: string | null | undefined): string {
  if (!iso) return "No deadline";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "No deadline";
  return d.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function hoursUntil(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return (d.getTime() - Date.now()) / (1000 * 60 * 60);
}

function formatTimeRemaining(iso: string | null | undefined, nowMs: number): string | null {
  if (!iso) return null;
  const end = new Date(iso).getTime();
  if (Number.isNaN(end)) return null;
  const diffMs = end - nowMs;
  const abs = Math.abs(diffMs);
  const totalMins = Math.floor(abs / 60000);
  const days = Math.floor(totalMins / (60 * 24));
  const hours = Math.floor((totalMins % (60 * 24)) / 60);
  const mins = totalMins % 60;

  let chunk: string;
  if (days > 0) chunk = `${days}d ${hours}h`;
  else if (hours > 0) chunk = `${hours}h ${mins}m`;
  else chunk = `${Math.max(mins, 0)}m`;

  if (diffMs < 0) return `${chunk} overdue`;
  return `${chunk} left`;
}

function addDaysAt(days: number, hour = 23, minute = 59): { date: string; time: string } {
  const d = new Date();
  d.setDate(d.getDate() + days);
  d.setHours(hour, minute, 0, 0);
  return {
    date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
    time: `${pad(d.getHours())}:${pad(d.getMinutes())}`,
  };
}

export function ListsPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<JobLink[]>([]);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setNowMs(Date.now()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  const expiryPreview = useMemo(() => {
    const iso = combineToIso(form.expireDate, form.expireTime);
    if (!iso) return null;
    return formatExpiry(iso);
  }, [form.expireDate, form.expireTime]);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const { api } = await import("../lib/api");
      const rows = await api.listJobLinks(token);
      setItems(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load lists");
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  function startEdit(item: JobLink) {
    const parts = toDateParts(item.expires_at);
    setEditingId(item.id);
    setForm({
      subject: item.subject,
      url: item.url,
      about: item.about || "",
      expireDate: parts.date,
      expireTime: parts.time,
      applied: item.applied,
    });
    setFlash(null);
    setError(null);
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm());
  }

  function applyPreset(days: number) {
    const parts = addDaysAt(days);
    setForm((f) => ({ ...f, expireDate: parts.date, expireTime: parts.time }));
  }

  function clearExpiry() {
    setForm((f) => ({ ...f, expireDate: "", expireTime: "23:59" }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    setFlash(null);
    try {
      const { api } = await import("../lib/api");
      const expiresIso = combineToIso(form.expireDate, form.expireTime);
      const payload = {
        subject: form.subject.trim(),
        url: form.url.trim(),
        about: form.about.trim() || null,
        applied: form.applied,
        ...(expiresIso ? { expires_at: expiresIso } : {}),
      };
      if (editingId) {
        await api.updateJobLink(token, editingId, {
          ...payload,
          clear_expires_at: !expiresIso,
          expires_at: expiresIso,
        });
        setFlash("Updated");
      } else {
        await api.createJobLink(token, payload);
        setFlash("Saved to Lists");
      }
      cancelEdit();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    if (!token) return;
    if (!window.confirm("Delete this link?")) return;
    setBusy(true);
    setError(null);
    try {
      const { api } = await import("../lib/api");
      await api.deleteJobLink(token, id);
      if (editingId === id) cancelEdit();
      await load();
      setFlash("Deleted");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleApplied(item: JobLink) {
    if (!token) return;
    try {
      const { api } = await import("../lib/api");
      const updated = await api.updateJobLink(token, item.id, {
        applied: !item.applied,
      });
      setItems((prev) => prev.map((row) => (row.id === item.id ? updated : row)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  return (
    <div className="page-fixed lists-page">
      <div className="lists-layout">
        <section className="card lists-form-card">
          <h2 className="panel-title">{editingId ? "Edit link" : "Add to Lists"}</h2>
          <p className="panel-sub muted">
            Bookmark job posts with a deadline. If not marked Applied, you get an email ~12 hours
            before expiry (when SMTP is enabled).
          </p>
          <form onSubmit={onSubmit}>
            <div className="field">
              <label htmlFor="list-subject">Subject</label>
              <input
                id="list-subject"
                value={form.subject}
                onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
                placeholder="e.g. Backend engineer — Acme"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="list-url">Link</label>
              <input
                id="list-url"
                type="text"
                value={form.url}
                onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
                placeholder="https://…"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="list-about">What this is about</label>
              <textarea
                id="list-about"
                value={form.about}
                onChange={(e) => setForm((f) => ({ ...f, about: e.target.value }))}
                placeholder="Notes, role focus, why you saved it…"
                rows={3}
              />
            </div>
            <div className="field">
              <span className="field-label-text">Deadline</span>
              <div className="lists-deadline">
                <div className="lists-deadline-row">
                  <label className="lists-sublabel" htmlFor="list-expire-date">
                    Date
                  </label>
                  <input
                    id="list-expire-date"
                    className="lists-date-input"
                    type="date"
                    value={form.expireDate}
                    onChange={(e) => setForm((f) => ({ ...f, expireDate: e.target.value }))}
                  />
                </div>
                <div className="lists-deadline-row">
                  <label className="lists-sublabel" htmlFor="list-expire-time">
                    Time
                  </label>
                  <input
                    id="list-expire-time"
                    className="lists-date-input"
                    type="time"
                    value={form.expireTime}
                    onChange={(e) => setForm((f) => ({ ...f, expireTime: e.target.value }))}
                    disabled={!form.expireDate}
                  />
                </div>
              </div>
              <div className="lists-presets" role="group" aria-label="Deadline shortcuts">
                <button type="button" className="lists-preset" onClick={() => applyPreset(1)}>
                  Tomorrow
                </button>
                <button type="button" className="lists-preset" onClick={() => applyPreset(3)}>
                  +3 days
                </button>
                <button type="button" className="lists-preset" onClick={() => applyPreset(7)}>
                  +1 week
                </button>
                <button
                  type="button"
                  className="lists-preset lists-preset-clear"
                  onClick={clearExpiry}
                >
                  No deadline
                </button>
              </div>
              <p className="lists-deadline-hint muted">
                {expiryPreview
                  ? `Reminder ~12h before · ${expiryPreview}`
                  : "Optional — leave empty if there’s no closing date"}
              </p>
            </div>
            <label className="lists-check">
              <input
                type="checkbox"
                checked={form.applied}
                onChange={(e) => setForm((f) => ({ ...f, applied: e.target.checked }))}
              />
              Already applied?
            </label>
            <div className="panel-footer lists-form-actions">
              <button className="btn btn-primary" type="submit" disabled={busy}>
                {busy ? "Saving…" : editingId ? "Update" : "Add"}
              </button>
              {editingId && (
                <button className="btn btn-ghost" type="button" onClick={cancelEdit}>
                  Cancel
                </button>
              )}
            </div>
            {error && <p className="error">{error}</p>}
            {flash && <p className="muted">{flash}</p>}
          </form>
        </section>

        <section className="lists-cards">
          <div className="lists-cards-head">
            <h2 className="panel-title" style={{ margin: 0 }}>
              Saved ({items.length})
            </h2>
          </div>
          {items.length === 0 ? (
            <p className="muted">No links yet — add a job posting to remember later.</p>
          ) : (
            <div className="lists-grid">
              {items.map((item) => {
                const hrs = hoursUntil(item.expires_at);
                const remaining = formatTimeRemaining(item.expires_at, nowMs);
                const urgent =
                  !item.applied && hrs != null && hrs >= 0 && hrs <= 12;
                const expired = !item.applied && hrs != null && hrs < 0;
                return (
                  <article
                    key={item.id}
                    className={`lists-card${item.applied ? " applied" : ""}${urgent ? " urgent" : ""}${expired ? " expired" : ""}`}
                  >
                    <div className="lists-card-top">
                      <h3 className="lists-card-title">{item.subject}</h3>
                      <span className={`lists-badge${item.applied ? " ok" : ""}`}>
                        {item.applied ? "Applied" : "Open"}
                      </span>
                    </div>
                    {item.about && <p className="lists-card-about">{item.about}</p>}
                    <a
                      className="lists-card-link"
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {item.url}
                    </a>
                    <p className="lists-card-meta muted">
                      Expires: {formatExpiry(item.expires_at)}
                      {urgent && " · reminder window"}
                      {expired && " · past deadline"}
                    </p>
                    {remaining && (
                      <p
                        className={`lists-card-remaining${urgent ? " urgent" : ""}${expired ? " expired" : ""}`}
                      >
                        {remaining}
                      </p>
                    )}
                    <div className="lists-card-actions">
                      <button
                        type="button"
                        className="btn btn-ghost"
                        onClick={() => void toggleApplied(item)}
                      >
                        {item.applied ? "Mark not applied" : "Mark applied"}
                      </button>
                      <button type="button" className="btn btn-ghost" onClick={() => startEdit(item)}>
                        Edit
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost danger-text"
                        onClick={() => void onDelete(item.id)}
                        disabled={busy}
                      >
                        Delete
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
