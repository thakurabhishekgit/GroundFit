import { GoogleLogin } from "@react-oauth/google";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

/**
 * Home / landing — explains GroundFit in plain language, then Google sign-in.
 */
export function LandingPage() {
  const { user, loading, loginWithGoogleToken } = useAuth();
  const [error, setError] = useState<string | null>(null);

  if (!loading && user) return <Navigate to="/app" replace />;

  return (
    <div className="landing">
      <header className="landing-nav">
        <span className="brand">GroundFit</span>
        <a className="btn btn-ghost" href="#signin">
          Get started
        </a>
      </header>

      <section className="landing-hero">
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
          <p className="landing-note">Continue with Google · Built for you and friends applying to jobs</p>
        </div>
        {error && (
          <p className="error" style={{ marginTop: "1rem" }}>
            {error}
          </p>
        )}
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
        <ul className="landing-points">
          <li>
            <strong>Match the JD</strong> using skills that already show up in your
            experience
          </li>
          <li>
            <strong>Rewrite Summary, Experience, and Skills</strong> in your own LaTeX
            format — projects stay as you wrote them
          </li>
          <li>
            <strong>Warn you</strong> if the JD asks for something you never used —
            add it only if you choose to
          </li>
        </ul>
      </section>

      <section className="landing-section landing-section-last" aria-labelledby="flow-title">
        <h2 id="flow-title" className="landing-h2">
          How it works
        </h2>
        <ol className="landing-steps">
          <li>
            <span className="step-num">1</span>
            <div>
              <strong>Tell your story</strong>
              <p>Paste a detailed write-up of your work. Confirm the skill list.</p>
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
              <p>See matches, decide on gaps, then generate the aligned resume once.</p>
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
