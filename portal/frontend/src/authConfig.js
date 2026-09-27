// MSAL configuration — public SPA client (Auth Code + PKCE, NO secret).
//
// Set these from your portal's Entra app registration (SPA platform):
//   VITE_CLIENT_ID  — the portal app registration (client) id
//   VITE_TENANT_ID  — your tenant id
//
// Delegated Graph scopes:
//   Sites.Read.All   — enumerate sites the user can see
//   Sites.Selected   — create the delegated Selected grant (works only if Owner)
export const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_CLIENT_ID ?? "REPLACE_WITH_PORTAL_CLIENT_ID",
    authority: `https://login.microsoftonline.com/${
      import.meta.env.VITE_TENANT_ID ?? "REPLACE_WITH_TENANT_ID"
    }`,
    redirectUri: window.location.origin,
  },
  cache: { cacheLocation: "sessionStorage" },
};

export const graphScopes = {
  scopes: ["User.Read", "Sites.Read.All", "Sites.Selected"],
};

export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
