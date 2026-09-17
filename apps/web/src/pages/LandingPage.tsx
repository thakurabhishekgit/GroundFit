import { GoogleLogin } from "@react-oauth/google";
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

const SCENES = [
  {
    id: "jd",
    label: "1 · Job description",
    title: "Backend Engineer — Java / Spring",
    lines: [
      "Must: Java, Spring Boot, Redis, SQL Server",
      "Nice: Azure App Service, CI/CD",
      "Kafka mentioned — check your context",
    ],
  },
  {
    id: "context",
    label: "2 · Your experience",
    title: "Evidence from your work",
    lines: [
      "✓ Redis — Freshdesk ticket-ID cache",
      "✓ Spring Boot — Ticket360 owned end-to-end",
      "✓ Azure DevOps — App Service deploy",
    ],
  },
  {
    id: "warn",
    label: "3 · Honest gap check",
    title: "Kafka not in your context",
    lines: [
      "Proposed keyword isn’t proven in your projects",
      "[ Add anyway ]  [ Skip ]  [ Suggest Redis pub/sub ]",
      "You decide — GroundFit won’t invent it",
    ],
  },
  {
    id: "out",
    label: "4 · Aligned resume",
    title: "LaTeX kept · content sharpened",
    lines: [
      "Summary / Experience / Skills rewritten",
      "Projects unchanged (your real work stays)",
      "Ready to download · same template format",
    ],
  },
] as const;

/**
 * Landing — brand + CTA on the left, animated product scenario on the right.
 */
export function LandingPage() {
  const { user, loading, loginWithGoogleToken } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [scene, setScene] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setScene((s) => (s + 1) % SCENES.length);
    }, 3200);
    return () => window.clearInterval(id);
  }, []);

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

        <div className="landing-stage" aria-hidden={false}>
          <div className="stage-glow" />
          <div className="stage-panel">
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
              <p className="stage-eyebrow">Live scenario</p>
              <h2 className="stage-title">{active.title}</h2>
              <ul className="stage-lines">
                {active.lines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>

              {active.id === "warn" && (
                <div className="stage-warn">
                  <strong>Kafka</strong>
                  <span>not_in_context</span>
                  <div className="stage-warn-actions">
                    <span>Add anyway</span>
                    <span className="on">Skip</span>
                  </div>
                </div>
              )}

              {active.id === "out" && (
                <div className="stage-resume">
                  <div className="stage-resume-line wide" />
                  <div className="stage-resume-line" />
                  <div className="stage-resume-line mid" />
                  <div className="stage-resume-block" />
                  <div className="stage-resume-block short" />
                </div>
              )}
            </div>

            <div className="stage-progress">
              {SCENES.map((s, i) => (
                <span key={s.id} className={`stage-dot${i === scene ? " active" : ""}`} />
              ))}
            </div>
          </div>

          <div className="stage-float stage-float-a">
            <span className="chip ok">Redis · matched</span>
          </div>
          <div className="stage-float stage-float-b">
            <span className="chip warn">Kafka · warn</span>
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
            <p>JD skills intersect your graph — Redis only if Freshdesk/Ticket360 proves it.</p>
          </article>
          <article className="feature-tile">
            <h3>Keep your LaTeX</h3>
            <p>Same template and project blocks. Only Summary, Experience, and Skills move.</p>
          </article>
          <article className="feature-tile">
            <h3>Warn before inventing</h3>
            <p>Missing Kafka? You get a clear choice — add, skip, or use something you actually used.</p>
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
