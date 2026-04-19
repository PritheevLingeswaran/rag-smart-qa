import { useState } from "react";
import "./AuthView.css";

interface Props {
  mode: "login" | "signup";
  onModeChange: (mode: "login" | "signup") => void;
}

export default function AuthView({ mode, onModeChange }: Props) {
  const [submitted, setSubmitted] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const isLogin = mode === "login";

  return (
    <section className="auth-view">
      <div className="auth-card">
        <div className="auth-logo-shell">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="auth-logo">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="currentColor" opacity="0.8" />
            <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        
        <div className="auth-header">
          <h1>{isLogin ? "Welcome back" : "Create an account"}</h1>
          <p>{isLogin ? "Sign in to your SmartQA workspace" : "Get started with grounded AI document intelligence."}</p>
        </div>

        <button className="auth-social-btn" onClick={() => setSubmitted(true)}>
          <GoogleIcon />
          <span>Continue with Google</span>
        </button>

        <div className="auth-divider">
          <span>or continue with email</span>
        </div>

        <form
          className="auth-form"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(true);
          }}
        >
          {!isLogin && (
            <div className="auth-field">
              <label htmlFor="nameStr">Full name</label>
              <input id="nameStr" type="text" placeholder="John Doe" />
            </div>
          )}

          <div className="auth-field">
            <label htmlFor="emailStr">Email address</label>
            <input 
              id="emailStr" 
              type="email" 
              placeholder="you@company.com" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
          </div>

          <div className="auth-field">
            <label htmlFor="passStr">Password</label>
            <input 
              id="passStr" 
              type="password" 
              placeholder="••••••••" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
          </div>

          <button type="submit" className="auth-submit">
            {isLogin ? "Sign In" : "Create Account"}
          </button>
        </form>

        <div className="auth-footer">
          <span>{isLogin ? "Don't have an account?" : "Already have an account?"}</span>
          <button
            type="button"
            className="auth-switch"
            onClick={() => {
              setSubmitted(false);
              setEmail("");
              setPassword("");
              onModeChange(isLogin ? "signup" : "login");
            }}
          >
            {isLogin ? "Sign up" : "Log in"}
          </button>
        </div>

        {submitted && (
          <div className="auth-notice">
            UI is ready! Hook this to your backend auth API.
          </div>
        )}
      </div>
    </section>
  );
}

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </svg>
  );
}
