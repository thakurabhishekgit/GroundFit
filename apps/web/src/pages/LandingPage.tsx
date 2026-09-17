import { GoogleLogin } from "@react-oauth/google";
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

const SCENES = [
  {
    id: "jd",
    label: "JD in",
    eyebrow: "Paste job description",
    title: "Backend Engineer",
  },
  {
    id: "context",
    label: "Match",
    eyebrow: "Your experience graph",
    title: "Evidence first",
  },
  {
    id: "warn",
    label: "Gap",
    eyebrow: "Honest gap check",
    title: "Kafka isn’t proven",
  },
  {
    id: "out",
    label: "Out",
    eyebrow: "Aligned resume",
    title: "Same LaTeX · sharper fit",
  },
] as const;

/**
 * Landing — brand + CTA on the left, animated product scenario on the right.
 */
export function LandingPage() {
  const { user, loading, loginWithGoogleToken } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [scene, setScene] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    const id = window.setInterval(() => {
      setScene((s) => (s + 1) % SCENES.length);
    }, 3800);
    return () => window.clearInterval(id);
  }, [paused]);

  if (!loading && user) return <Navigate to="/app" replace />;

  const active = SCENES[scene];

  return (
    <div className="landing">
      <header className="landing-nav">
        <span className="brand">GroundFit</span>
        <a className="btn btn-ghost" href="#signin">
          Get started
        </a>
      </header>

      <section className="landing-hero-grid">
        <div className="landing-hero-copy">
          <p className="landing-kicker">Resume alignment that stays honest</p>
          <h1 className="brand-lg">GroundFit</h1>
          <p className="landing-lead">
            Paste a job description and your LaTeX resume. GroundFit rewrites Summary,
            Experience, and Skills to fit the role — grounded in your real work and
            project experience, not invented keywords.
          </p>
          <div className="landing-cta" id="signin">
            <GoogleLogin
              onSuccess={async (cred) => {
                if (!cred.credential) {
                  setError("Google did not return a credential");
                  return;
                }
                try {
                  setError(null);
                  await loginWithGoogleToken(cred.credential);
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Login failed");
                }
              }}
              onError={() => setError("Google login failed")}
              useOneTap={false}
              theme="filled_black"
              shape="pill"
              text="continue_with"
            />
            <p className="landing-note">
              Continue with Google · Built for you and friends applying to jobs
            </p>
          </div>
          {error && (
            <p className="error" style={{ marginTop: "1rem" }}>
              {error}
            </p>
          )}
        </div>

        <div
          className="landing-stage"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
        >
          <div className="stage-glow" />

          <div className={`stage-float stage-float-a scene-${active.id}`}>
            <span className="chip ok">Redis · matched</span>
          </div>
          <div className={`stage-float stage-float-b scene-${active.id}`}>
            <span className={`chip ${active.id === "warn" ? "warn" : "ok"}`}>
              {active.id === "warn" ? "Kafka · warn" : "Spring · matched"}
            </span>
          </div>

          <div className="stage-panel">
            <div className="stage-chrome">
              <span className="stage-dot-win" />
              <span className="stage-dot-win" />
              <span className="stage-dot-win" />
              <span className="stage-chrome-label">GroundFit · align</span>
            </div>

            <div className="stage-tabs">
              {SCENES.map((s, i) => (
                <button
                  key={s.id}
                  type="button"
                  className={`stage-tab${i === scene ? " active" : ""}`}
                  onClick={() => setScene(i)}
                >
                  {s.label}
                </button>
              ))}
            </div>

            <div key={active.id} className="stage-scene">
              <p className="stage-eyebrow">{active.eyebrow}</p>
              <h2 className="stage-title">{active.title}</h2>

              {active.id === "jd" && (
                <div className="mock-jd">
                  <div className="mock-jd-bar">
                    <span>job_description.txt</span>
                    <span className="mock-pulse">analyzing…</span>
                  </div>
                  <div className="mock-jd-body">
                    <p>
                      We’re hiring a <mark>Backend Engineer</mark> with strong{" "}
                      <mark>Java</mark> / <mark>Spring Boot</mark>.
                    </p>
                    <p>
                      You’ll own APIs, caching with <mark>Redis</mark>, and data in{" "}
                      <mark>SQL Server</mark>.
                    </p>
                    <p className="muted-line">
                      Nice to have: Azure App Service, CI/CD, <mark className="warn-mark">Kafka</mark>
                    </p>
                  </div>
                  <div className="mock-tags">
                    <span>Java</span>
                    <span>Spring Boot</span>
                    <span>Redis</span>
                    <span className="tag-warn">Kafka?</span>
                  </div>
                </div>
              )}

              {active.id === "context" && (
                <div className="mock-evidence">
                  <article className="evidence-card" style={{ animationDelay: "0ms" }}>
                    <header>
                      <strong>Redis</strong>
                      <span className="pill-ok">proven</span>
                    </header>
                    <p>Freshdesk ticket-ID cache · reduced lookup latency</p>
                  </article>
                  <article className="evidence-card" style={{ animationDelay: "90ms" }}>
                    <header>
                      <strong>Spring Boot</strong>
                      <span className="pill-ok">proven</span>
                    </header>
                    <p>Ticket360 owned end-to-end · APIs + deploy</p>
                  </article>
                  <article className="evidence-card" style={{ animationDelay: "180ms" }}>
                    <header>
                      <strong>Azure DevOps</strong>
                      <span className="pill-ok">proven</span>
                    </header>
                    <p>App Service pipelines · CI/CD for releases</p>
                  </article>
                </div>
              )}

              {active.id === "warn" && (
                <div className="mock-warn">
                  <div className="mock-warn-icon">!</div>
                  <div className="mock-warn-body">
                    <strong>Kafka</strong>
                    <span className="code-tag">not_in_context</span>
                    <p>
                      This keyword isn’t backed by your projects. GroundFit won’t invent
                      usage — you choose.
                    </p>
                    <div className="mock-warn-actions">
                      <button type="button" className="ghost-btn">
                        Add anyway
                      </button>
                      <button type="button" className="accent-btn">
                        Skip
                      </button>
                      <button type="button" className="ghost-btn">
                        Suggest Redis pub/sub
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {active.id === "out" && (
                <div className="mock-resume">
                  <div className="mock-resume-paper">
                    <div className="paper-name">Abhishek Thakur</div>
                    <div className="paper-rule" />
                    <div className="paper-section">SUMMARY</div>
                    <div className="paper-line accent-line" />
                    <div className="paper-line" />
                    <div className="paper-line short" />
                    <div className="paper-section">EXPERIENCE</div>
                    <div className="paper-line" />
                    <div className="paper-line mid" />
                    <div className="paper-line" />
                    <div className="paper-section">SKILLS</div>
                    <div className="paper-skills">
                      <span>Java</span>
                      <span>Spring Boot</span>
                      <span>Redis</span>
                      <span>SQL Server</span>
                    </div>
                  </div>
                  <ul className="mock-resume-notes">
                    <li>Projects left untouched</li>
                    <li>LaTeX template preserved</li>
                    <li>Ready to download</li>
                  </ul>
                </div>
              )}
            </div>

            <div className="stage-progress">
              {SCENES.map((s, i) => (
                <button
                  key={s.id}
                  type="button"
                  aria-label={`Show ${s.label}`}
                  className={`stage-dot${i === scene ? " active" : ""}`}
                  onClick={() => setScene(i)}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section" aria-labelledby="problem-title">
        <h2 id="problem-title" className="landing-h2">
          The usual AI resume trick
        </h2>
        <p className="landing-copy">
          Drop a JD into ChatGPT and it floods your resume with keywords. Half of them
          you barely know. Even when you do know them, the model has no idea{" "}
          <em>where</em> you used them — which project, what you owned, what actually
          shipped. Fixing that by hand is exhausting.
        </p>
      </section>

      <section className="landing-section" aria-labelledby="does-title">
        <h2 id="does-title" className="landing-h2">
          What GroundFit does
        </h2>
        <p className="landing-copy">
          You save your story once: roles, projects, and the tech you really used (and
          why). That becomes your personal context. When you align to a new JD,
          GroundFit pulls from that — not from a keyword wish-list.
        </p>
        <div className="landing-feature-row">
          <article className="feature-tile">
            <h3>Match from experience</h3>
            <p>
              JD skills intersect your graph — Redis only if Freshdesk/Ticket360 proves
              it.
            </p>
          </article>
          <article className="feature-tile">
            <h3>Keep your LaTeX</h3>
            <p>
              Same template and project blocks. Only Summary, Experience, and Skills
              move.
            </p>
          </article>
          <article className="feature-tile">
            <h3>Warn before inventing</h3>
            <p>
              Missing Kafka? You get a clear choice — add, skip, or use something you
              actually used.
            </p>
          </article>
        </div>
      </section>

      <section className="landing-section landing-section-last" aria-labelledby="flow-title">
        <h2 id="flow-title" className="landing-h2">
          How it works
        </h2>
        <ol className="landing-steps">
          <li>
            <span className="step-num">1</span>
            <div>
              <strong>Capture work &amp; projects</strong>
              <p>Paste a detailed write-up. Confirm the skill list.</p>
            </div>
          </li>
          <li>
            <span className="step-num">2</span>
            <div>
              <strong>Add JD + resume</strong>
              <p>Paste the job description and your LaTeX resume.</p>
            </div>
          </li>
          <li>
            <span className="step-num">3</span>
            <div>
              <strong>Review &amp; finalize</strong>
              <p>See matches, decide on gaps, generate the aligned resume once.</p>
            </div>
          </li>
        </ol>
        <p className="landing-foot">
          GroundFit doesn’t invent fake projects or tools. It helps you emphasize the
          work and project experience you already have — tuned to the role you’re
          applying for.
        </p>
        <a className="btn btn-primary" href="#signin">
          Start with Google
        </a>
      </section>
    </div>
  );
}

export function LoginPage() {
  return <LandingPage />;
}
