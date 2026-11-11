import { useEffect, useRef, useState } from "react";
import { http } from "../lib/http.js";

export default function AccountRecovery({ onComplete, onLogout, verification = false }) {
  const [token, setToken] = useState(() => new URLSearchParams(window.location.search).get("token") || "");
  useEffect(() => { window.history.replaceState(null, "", window.location.pathname); }, []);
  const verifying = verification || window.location.pathname === "/auth/verify-email";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const locked = useRef(false);
  const submit = async (event) => {
    event.preventDefault();
    if (locked.current) return;
    locked.current = true; setBusy(true); setMessage("");
    try {
      const path = verifying
        ? `/auth/user/email/verify${token ? "" : "/token"}`
        : `/auth/user/password/reset${token ? "" : "/token"}`;
      const body = verifying ? (token ? { token: token } : {})
        : { ...(token ? { token: token } : {}), formFields: [
          { id: token ? "password" : "email", value: token ? password : email.trim() },
        ] };
      const result = await http(path, { body, retry: false, headers: { rid: verifying ? "emailverification" : "emailpassword" } });
      if (result.status !== "OK" && result.status !== "EMAIL_ALREADY_VERIFIED_ERROR") {
        throw new Error(result.formFields?.[0]?.error || "This link is invalid or has expired. Request a new email.");
      }
      if (!token) { setMessage("Check your email for the link."); return; }
      setToken("");
      window.history.replaceState(null, "", "/");
      if (verifying) {
        let profile;
        try { profile = await http("/v1/me"); } catch (error) { if (error.status !== 401) throw error; }
        onComplete(profile || null);
      }
      else { setPassword(""); onComplete(null); }
    } catch (error) { setMessage(error.message); }
    finally { locked.current = false; setBusy(false); }
  };
  const back = () => { window.history.replaceState(null, "", "/"); onComplete(null); };
  return <div className="auth"><div className="ahead">Civis</div><div className="amain"><div className="acard">
    <h2>{verifying ? "Verify your email" : "Reset your password"}</h2>
    <form className="af" onSubmit={submit}>
      {!verifying && (token
        ? <label><span>New password</span><input type="password" minLength={8} required autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        : <label><span>Email</span><input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>)}
      <p className="aerr" role="status">{message}</p>
      <button className="abtn" disabled={busy}>{verifying ? (token ? "Verify email" : "Send verification email") : (token ? "Save password" : "Send reset link")}</button>
    </form>
    {token && <p className="aswap"><button type="button" disabled={busy} onClick={() => { setToken(""); setMessage(""); }}>Request a new email</button></p>}
    <p className="aswap"><button type="button" onClick={onLogout || back}>{onLogout ? "Log out" : "Back to log in"}</button></p>
  </div></div></div>;
}
