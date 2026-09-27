import { useEffect, useState } from "react";
import { api, signIn, signOut, getAccount } from "./api";

const box = { maxWidth: 820, margin: "40px auto", fontFamily: "system-ui, sans-serif" };
const card = { border: "1px solid #ddd", borderRadius: 8, padding: 16, marginBottom: 16 };
const btn = { padding: "6px 12px", borderRadius: 6, border: "1px solid #0078d4", background: "#0078d4", color: "#fff", cursor: "pointer" };
const ghost = { ...btn, background: "#fff", color: "#0078d4" };

export default function App() {
  const [account, setAccount] = useState(getAccount());
  const [config, setConfig] = useState(null);
  const [sites, setSites] = useState([]);
  const [search, setSearch] = useState("");
  const [grants, setGrants] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.config().then(setConfig).catch(() => {});
  }, []);

  useEffect(() => {
    if (account) refreshGrants();
  }, [account]);

  async function refreshGrants() {
    try {
      setGrants(await api.grants());
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleSignIn() {
    setError("");
    try {
      setAccount(await signIn());
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleSearch() {
    setError("");
    setBusy(true);
    try {
      setSites(await api.sites(search || "*"));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleGrant(site) {
    setError("");
    setBusy(true);
    try {
      await api.grant(site.id, site.displayName || site.webUrl);
      await refreshGrants();
      alert(`Granted READ to ${config?.grantsTo} on "${site.displayName}".`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke(g) {
    setBusy(true);
    try {
      await api.revoke(g.permission_id, g.site_id);
      await refreshGrants();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!account) {
    return (
      <div style={box}>
        <h1>SharePoint Access Portal</h1>
        <p>Grant read access to <b>{config?.grantsTo ?? "the reader service"}</b> for sites you own.</p>
        <button style={btn} onClick={handleSignIn}>Sign in</button>
        {error && <p style={{ color: "crimson" }}>{error}</p>}
      </div>
    );
  }

  return (
    <div style={box}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>SharePoint Access Portal</h1>
        <div>
          <span style={{ marginRight: 12 }}>{account.name}</span>
          <button style={ghost} onClick={() => { signOut(); setAccount(null); }}>Sign out</button>
        </div>
      </div>

      <p>
        Grants <b>read-only</b> access to <b>{config?.grantsTo}</b>. You can only
        grant on sites you own.
      </p>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <div style={card}>
        <h3>1. Find a site you own</h3>
        <input
          value={search}
          placeholder="Search sites (blank = all)"
          onChange={(e) => setSearch(e.target.value)}
          style={{ padding: 6, width: 300, marginRight: 8 }}
        />
        <button style={btn} disabled={busy} onClick={handleSearch}>Search</button>
        <ul>
          {sites.map((s) => (
            <li key={s.id} style={{ margin: "8px 0" }}>
              <b>{s.displayName}</b> <small>{s.webUrl}</small>{" "}
              <button style={ghost} disabled={busy} onClick={() => handleGrant(s)}>
                Grant read
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div style={card}>
        <h3>2. Current grants</h3>
        {grants.length === 0 && <p>No active grants.</p>}
        <ul>
          {grants.map((g) => (
            <li key={g.id} style={{ margin: "8px 0" }}>
              <b>{g.resource_desc}</b> — {g.role} → {g.granted_to}{" "}
              <small>by {g.granted_by}</small>{" "}
              <button style={ghost} disabled={busy} onClick={() => handleRevoke(g)}>
                Revoke
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
