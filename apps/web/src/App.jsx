import { useEffect, useState } from "react";
import { completeGoogleAuth, http } from "./lib/http.js";
import Auth from "./components/Auth.jsx";
import Shell from "./components/Shell.jsx";
import AccountRecovery from "./components/AccountRecovery.jsx";
export default function App() {
  const [user, setUser] = useState(null);
  const [dark, setDark] = useState(false);
  const [session, setSession] = useState(0);
  const [booting, setBooting] = useState(true);
  const [authError, setAuthError] = useState("");
  const [googleCallback] = useState(() => window.location.pathname === "/auth/callback/google");
  const [recovery, setRecovery] = useState(["/auth/reset-password", "/auth/verify-email"].includes(window.location.pathname));
  const acceptUser = (profile) => {
    setUser(profile);
    setDark(profile.preferences.theme === "dark");
    setAuthError("");
  };
  useEffect(() => {
    // Remove legacy demo credentials; all sessions now use provider httpOnly cookies.
    for (const key of ["civis-session", "civis-accounts"]) {
      try { localStorage.removeItem(key); } catch { /* Storage may be unavailable. */ }
    }
    const channel = typeof BroadcastChannel === "function" ? new BroadcastChannel("civis-auth") : null;
    const unauthenticated = () => { setUser(null); setSession((s) => s + 1); };
    const navigation = () => setRecovery(["/auth/reset-password", "/auth/verify-email"].includes(window.location.pathname));
    if (channel) channel.onmessage = (event) => { if (event.data === "logout") unauthenticated(); };
    window.addEventListener("popstate", navigation);
    window.addEventListener("civis:unauthenticated", unauthenticated);
    const initAuth = window.location.pathname === "/auth/callback/google"
      ? completeGoogleAuth().then(acceptUser).catch((e) => setAuthError(e.message))
      : http("/v1/me").then(acceptUser).catch(() => {});
    initAuth.finally(() => setBooting(false));
    return () => { channel?.close(); window.removeEventListener("civis:unauthenticated", unauthenticated); window.removeEventListener("popstate", navigation); };
  }, []);
  const logout = async () => {
    await http("/auth/signout", { method: "POST", headers: { rid: "session" }, retry: false });
    if (typeof BroadcastChannel === "function") {
      const channel = new BroadcastChannel("civis-auth");
      channel.postMessage("logout");
      channel.close();
    }
    setUser(null);
    setSession((s) => s + 1);
  };
  const changeDark = async (value) => {
    await http("/v1/me", { method: "PATCH", body: { preferences: { theme: value ? "dark" : "light" } } });
    setDark(value);
  };
  return (
    <div className={"cv" + (dark ? " dark" : "")}>
      {booting && !recovery ? (
        <div className="splash" role="status" aria-live="polite">
          <div className="mk splash-mk">C</div>
          <div className="brand" style={{ padding: 0 }}>Civis</div>
          <div className="dots"><span /><span /><span /></div>
          <p className="splash-txt">{googleCallback ? "Signing in with Google\u2026" : "Loading your workspace\u2026"}</p>
        </div>
      ) : recovery || (user?.verification_required && !user.verified)
        ? <AccountRecovery verification={!!user?.verification_required && !user?.verified} onLogout={user ? async () => { await logout(); setRecovery(false); window.history.replaceState(null, "", "/"); } : undefined} onComplete={(profile) => { setRecovery(false); if (profile) acceptUser(profile); else setUser(null); }} />
        : user
        ? <Shell key={session} user={user} dark={dark} setDark={changeDark} onLogout={logout} />
        : <Auth initialError={authError} onAuth={acceptUser} onRecovery={() => { window.history.pushState(null, "", "/auth/reset-password"); setRecovery(true); }} />}
    </div>
  );
}
