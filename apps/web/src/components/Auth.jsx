import { useRef, useState } from "react";
import { authenticate, startGoogleAuth } from "../lib/http.js";
function Auth({ onAuth, onRecovery, initialError = "" }) {
  const [m, setM] = useState("login");
  const [f, setF] = useState({ name: "", email: "", pw: "" });
  const [err, setErr] = useState(initialError);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const google = async () => {
    if (submitting.current) return;
    submitting.current = true; setBusy(true);
    try {
      setErr("");
      await startGoogleAuth();
    } catch (error) {
      setErr(error.message);
      submitting.current = false; setBusy(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (submitting.current) return;
    const email = f.email.trim().toLowerCase();
    if (m === "signup" && !f.name.trim()) return setErr("Enter your full name.");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setErr("Enter a valid email address.");
    if (f.pw.length < 8) return setErr("Use a password of at least 8 characters.");
    submitting.current = true; setBusy(true);
    try {
      setErr("");
      onAuth(await authenticate(m, { email, pw: f.pw, name: f.name }));
    } catch (error) { setErr(error.message); }
    finally { submitting.current = false; setBusy(false); }
  };

  return (
    <div className="auth">
      <div className="ahead">Civis</div>
      <div className="amain">
        <div className="apitch">
          <h1>Legal help in plain language</h1>
          <p>Ask legal questions and draft contracts, letters and notices in minutes.</p>
          <ul><li>Clear answers you can act on</li><li>Ready-made templates for every document</li><li>Download your draft as a Word file</li></ul>
        </div>
        <div className="acard">
          <div className="atabs">
            <button type="button" className={"atab" + (m === "login" ? " on" : "")} onClick={() => { setM("login"); setErr(""); }}>Log in</button>
            <button type="button" className={"atab" + (m === "signup" ? " on" : "")} onClick={() => { setM("signup"); setErr(""); }}>Sign up</button>
          </div>
          <button type="button" className="agbtn" disabled={busy} onClick={google}>
            <svg className="gi" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.19-2.27H12v4.51h6.47c-.29 1.48-1.14 2.73-2.4 3.58v3h3.86c2.26-2.09 3.56-5.17 3.56-8.82z" />
              <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.86-3c-1.08.72-2.45 1.16-4.07 1.16-3.13 0-5.78-2.11-6.73-4.96H1.29v3.09C3.26 21.3 7.31 24 12 24z" />
              <path fill="#FBBC05" d="M5.27 14.29c-.25-.72-.38-1.49-.38-2.29s.13-1.57.38-2.29V6.62H1.29C.47 8.24 0 10.06 0 12s.47 3.76 1.29 5.38l3.98-3.09z" />
              <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.26 2.7 1.29 6.62l3.98 3.09c.95-2.85 3.6-4.96 6.73-4.96z" />
            </svg>
            Continue with Google
          </button>
          <div className="aor"><span>or continue with email</span></div>
          <div className="af" onKeyDown={(e) => { if (e.key === "Enter" && e.target.tagName === "INPUT") submit(e); }}>
            {m === "signup" && <label><span>Full name</span><input value={f.name} onChange={set("name")} autoComplete="name" /></label>}
            <label><span>Email</span><input type="email" value={f.email} onChange={set("email")} autoComplete="email" /></label>
            <label><span>Password</span><input type="password" value={f.pw} onChange={set("pw")} autoComplete={m === "signup" ? "new-password" : "current-password"} /></label>
            <p className="aerr" role="alert">{err}</p>
            <button className="abtn" disabled={busy} type="button" onClick={submit}>{m === "signup" ? "Create account" : "Log in"}</button>
          </div>
          <p className="aswap">
            {m === "signup" ? "Already have an account? " : "New to Civis? "}
            <button type="button" onClick={() => { setM(m === "signup" ? "login" : "signup"); setErr(""); }}>{m === "signup" ? "Log in" : "Create an account"}</button>
          </p>
          <p className="aswap"><button type="button" onClick={onRecovery}>Forgot password?</button></p>
        </div>
      </div>
    </div>
  );
}

export default Auth;
