import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig, graphScopes, API_BASE } from "./authConfig";

export const msal = new PublicClientApplication(msalConfig);

let _initialized = false;
async function ensureInit() {
  if (!_initialized) {
    await msal.initialize();
    _initialized = true;
  }
}

export async function signIn() {
  await ensureInit();
  const result = await msal.loginPopup(graphScopes);
  msal.setActiveAccount(result.account);
  return result.account;
}

export function signOut() {
  msal.logoutPopup();
}

export function getAccount() {
  return msal.getActiveAccount() ?? msal.getAllAccounts()[0] ?? null;
}

// A DELEGATED Microsoft Graph token, acquired silently where possible.
async function getGraphToken() {
  await ensureInit();
  const account = getAccount();
  if (!account) throw new Error("Not signed in");
  try {
    const res = await msal.acquireTokenSilent({ ...graphScopes, account });
    return res.accessToken;
  } catch {
    const res = await msal.acquireTokenPopup(graphScopes);
    return res.accessToken;
  }
}

// The backend uses the user's Graph token as-is to call Graph on their behalf.
async function call(path, options = {}) {
  const token = await getGraphToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  config: () => fetch(`${API_BASE}/api/config`).then((r) => r.json()),
  me: () => call("/api/me"),
  sites: (search = "*") => call(`/api/sites?search=${encodeURIComponent(search)}`),
  grant: (siteId, resourceDescription) =>
    call("/api/grants", {
      method: "POST",
      body: JSON.stringify({ siteId, resourceDescription }),
    }),
  grants: () => call("/api/grants"),
  revoke: (permissionId, siteId) =>
    call(`/api/grants/${permissionId}?siteId=${encodeURIComponent(siteId)}`, {
      method: "DELETE",
    }),
};
