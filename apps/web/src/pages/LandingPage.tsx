import { GoogleLogin } from "@react-oauth/google";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

/**
 * Public landing page — brand-first hero + Google sign-in.
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
          Sign in
        </a>
      </header>

      <section className="landing-hero">
        <p className="landing-kicker">Evidence-based resume alignment</p>
        <h1 className="brand-lg">GroundFit</h1>
        <p className="landing-lead">
          Align your resume to any JD using only skills proven in your own experience —
          with clear warnings when something isn’t grounded.
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
          <p className="landing-note">Google account required · Free for you and friends</p>
        </div>
        {error && <p className="error" style={{ marginTop: "1rem" }}>{error}</p>}
      </section>
    </div>
  );
}

/** @deprecated — route now uses LandingPage */
export function LoginPage() {
  return <LandingPage />;
}
