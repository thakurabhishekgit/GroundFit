import { GoogleLogin } from "@react-oauth/google";
import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

export function LoginPage() {
  const { user, loading, loginWithGoogleToken } = useAuth();
  const [error, setError] = useState<string | null>(null);

  if (!loading && user) return <Navigate to="/app" replace />;

  return (
    <div className="login-hero">
      <div className="card login-panel stack">
        <h1 className="brand">GroundFit</h1>
        <p className="muted">
          Align resumes to job descriptions using only skills proven in your experience
          context — with warnings when something isn’t grounded.
        </p>
        <div style={{ display: "flex", justifyContent: "center" }}>
          <GoogleLogin
            onSuccess={async ( cred ) => {
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
          />
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </div>
  );
}
