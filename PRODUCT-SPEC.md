# Product Spec: Secretless AWS Lambda → SharePoint Read Access via APIM

**Status:** Draft
**Owner:** _TBD_
**Last updated:** 2026-09-27

---

## 1. Summary

An existing AWS Lambda function reads files and folders from a SharePoint site
by calling the Microsoft Graph API. Today it authenticates with a **username and
password** (ROPC flow), which is being retired. The customer's IT department has
mandated **no client secrets, no certificates, and no stored passwords** in AWS.

This spec defines a **secretless, certless** design in which the Lambda presents
a short-lived AWS-issued OIDC token to **Azure API Management (APIM)**. APIM
validates the token and, if valid, calls Microsoft Graph using **its own managed
identity**, which holds a scoped, read-only `Sites.Selected` permission on the
target SharePoint site(s).

The design deliberately minimizes change to the AWS team's code.

---

## 2. Goals

- **G1.** Remove the username/password (ROPC) credential from the Lambda.
- **G2.** Store **no** client secret, certificate, or password in AWS.
- **G3.** Grant **read-only** access, scoped to **specific SharePoint sites** only.
- **G4.** Restrict trust to **exactly one AWS identity** (the specific Lambda).
- **G5.** Keep the AWS-side code change **as small as possible**.
- **G6.** Provide an auditable, IT-approvable authentication chain.

## 3. Non-Goals

- Write access to SharePoint (read only).
- Broad tenant-wide Graph permissions (`Sites.Read.All` is explicitly avoided in
  favor of `Sites.Selected`).
- Replacing the Lambda's runtime or business logic.
- Human/interactive user sign-in (this is machine-to-machine only).

---

## 4. Current State

```
Lambda ──(username + password, ROPC)──▶ Microsoft Graph ──▶ SharePoint
```

- Authentication: resource-owner password credentials (a stored user + password).
- Problems: stored credential in AWS, violates IT policy, user-tied, brittle.

---

## 5. Proposed Design

```
Lambda
  │  1. GetOpenIdToken (Amazon Cognito Identity Pool)  → short-lived signed JWT
  │
  └──▶ APIM  (public endpoint / facade)
         │  2. validate-jwt against Cognito JWKS
         │     - verify signature, issuer, audience
         │     - pin subject to the one allowed Cognito identity
         │
         └──▶ 3. APIM managed identity acquires a Graph token
                  (authentication-managed-identity, resource = Graph)
                  │
                  └──▶ 4. Microsoft Graph  (Sites.Selected, read)
                            └──▶ SharePoint site(s)
```

### Chosen pattern

**APIM facade + inbound OIDC validation + APIM managed identity to Graph.**

- APIM **authenticates/authorizes** the AWS caller by validating its Cognito
  OIDC JWT.
- The actual Graph call is made **as APIM's managed identity** holding
  `Sites.Selected` (read). Graph/SharePoint audit logs attribute access to
  APIM's MI, not the AWS identity — acceptable and expected for a facade.

### Why this pattern

- **Secretless / certless:** the Lambda fetches a short-lived, Cognito-signed JWT
  on demand. Nothing durable is stored in AWS.
- **Minimal Lambda change:** replace the ROPC user/password call with a single
  `GetOpenIdToken` call, then send that token to APIM instead of calling Graph
  directly.
- **Least privilege:** `Sites.Selected` + `read` limits access to named sites.
- **IT-approvable:** no client secret, no certificate, no password.

---

## 6. Alternatives Considered

| Option | Secret/Cert? | Verdict |
|---|---|---|
| **A. App registration + client secret** (client-credentials, MSAL) | Client secret in AWS Secrets Manager | ❌ Rejected — IT forbids client secrets. Simplest otherwise. |
| **B. mTLS client certificate to APIM** | Certificate | ❌ Rejected — customer wants to avoid certs. |
| **C. Workload Identity Federation directly to Entra app** (Lambda → Cognito JWT → Entra federated credential → Graph) | None | ✅ Viable and fully secretless; drops APIM. Less control/observability at the gateway; the Lambda calls Graph directly. |
| **D. APIM facade + Cognito JWT + APIM MI to Graph** (this spec) | None | ✅ **Chosen** — secretless, centralizes validation/policy at the gateway, minimal Lambda change. |

> **Note — what's "common" vs. "novel" here (and why it needs a PoC):**
>
> The term **token bridge** refers to how an AWS Lambda gets a **JWT that Azure
> will accept**. A Lambda has no native OIDC/JWT — it authenticates with its IAM
> role via SigV4, which Azure can't read. A **Cognito Identity Pool**
> (`GetOpenIdToken`) mints that JWT, "bridging" the AWS workload to Azure.
>
> - **Common / well-supported:** the general frameworks — Workload Identity
>   Federation to Entra (Option C) and APIM `validate-jwt` + managed identity
>   (Option D). Both are mainstream, Microsoft-documented patterns.
> - **Uncommon / less-documented:** using **Cognito as the token source** for
>   either one. This specific hop is rarely documented end-to-end.
>
> **Both Options C and D depend on this same Cognito hop**, so the novelty does
> **not** favor one over the other — it is shared. Because it's under-documented,
> validate it with a small **proof-of-concept before committing**, confirming:
>   1. The Cognito `GetOpenIdToken` JWT **validates in APIM / is accepted by
>      Entra** — Cognito's OpenID discovery document is non-standard, so
>      auto-discovery may need the JWKS URL supplied directly (see §7.5).
>   2. The token's actual `iss`, `aud`, and `sub` claims match what you pin.
>   3. (Option C only) Entra accepts the Cognito issuer/subject as a federated
>      credential.
>
> This is a **risk callout, not a blocker** — spend a day proving the Cognito hop
> early rather than discovering a surprise late. The rollout plan (§11) puts this
> chain first for exactly this reason.

---

## 7. Detailed Components

### 7.1 AWS — Cognito Identity Pool (token issuer)

> **What is Cognito?** Amazon Cognito is an **AWS** identity service. It has two
> parts: a **User Pool** (a directory of human users — *not* used here) and an
> **Identity Pool** / "federated identities" (issues temporary signed tokens to
> identities, including AWS workloads). We use the **Identity Pool**. It exists
> because a Lambda natively authenticates with its IAM role via SigV4 and has
> **no JWT** to present; Cognito mints one that Azure/APIM can verify.

- A **dedicated** Cognito Identity Pool used by nothing else.
- Issues a short-lived signed JWT via `GetOpenIdToken`.
- Issuer: `https://cognito-identity.amazonaws.com`.
- The token's `sub` is the **Cognito identity ID** (not the Lambda role ARN).

### 7.2 AWS — Lambda (minimal change)

- Add one call: `GetOpenIdToken` (Cognito Identity) to mint the JWT.
- Send the JWT to the APIM endpoint (bearer) instead of authenticating to Graph.
- Remove the stored username/password and the direct Graph auth call.

### 7.3 Azure — APIM (facade + policy)

- Inbound policy `validate-jwt`:
  - Validate against Cognito **JWKS**.
  - Enforce expected **issuer** and **audience**.
  - **Pin the `sub`** claim to the single allowed Cognito identity.
- `authentication-managed-identity` to acquire a Microsoft Graph token.
- Forward the read request to Graph; return the result to the Lambda.

### 7.4 Azure — Entra app / managed identity + Graph permission (granularity)

`Sites.Selected` began as **site-collection level only**, but Microsoft has since
added finer-grained "Selected" scopes. Access can now be scoped down to a
specific library, folder, or file — which better matches "grant read to a given
directory."

| Scope | Granularity |
|---|---|
| `Sites.Selected` | Whole site collection |
| `Lists.SelectedOperations.Selected` | A specific list / document library |
| `ListItems.SelectedOperations.Selected` | A specific **folder** / list item |
| `Files.SelectedOperations.Selected` | A specific file / library folder |

- Grant the APIM **managed identity's application** a **read** role at the
  chosen level (prefer folder/library for least privilege).
- The grant is stored as a tuple: **appId (APIM MI) → role (read) → resource
  (library/folder)**.

**Who can create the grant** — our design uses the delegated **Owner** path only,
which requires **no** high-privilege or full-control permission:

| Granting at… | Requires (our read-only path) |
|---|---|
| List / library | `Sites.Selected+Owner` (signed-in site Owner) |
| Folder / file | `Lists.SelectedOperations.Selected+Owner` (signed-in Owner) |

The "Selected" scopes support **delegated mode**, so a signed-in site **Owner**
can create library/folder-level **read** grants themselves — no admin, no
full-control permission. This delegated-Owner capability is what makes the
self-service portal (§13) viable and least-privilege. This design intentionally
**does not use any full-control or write permission**; whole-site grants are out
of scope (see §13.6).

### 7.5 How APIM validates the Cognito token

Validation happens entirely at the **gateway, inbound, before any Graph call**,
using the built-in `validate-jwt` policy. No shared secret is involved — it is
pure public-key cryptography against Cognito's published keys.

**Flow:**

1. **Lambda sends the JWT** to APIM as a bearer token
   (`Authorization: Bearer <cognito-jwt>`).
2. **APIM fetches Cognito's public signing keys (JWKS)** from the well-known
   OpenID endpoint and **caches** them:
   ```
   https://cognito-identity.amazonaws.com/.well-known/openid-configuration
     → jwks_uri → https://cognito-identity.amazonaws.com/.well-known/jwks_uri
   ```
3. **APIM verifies the signature.** The JWT header names a key ID (`kid`); APIM
   finds the matching public key in the JWKS and cryptographically verifies the
   token was signed by Cognito's private key and not tampered with. **This is
   the core trust step** — only Cognito holds the private key, so a valid
   signature proves Cognito issued it.
4. **APIM checks the claims** — issuer, audience, expiry, and the pinned subject.

**Policy:**

```xml
<validate-jwt header-name="Authorization" failed-validation-httpcode="401"
              failed-validation-error-message="Invalid or unauthorized token">

  <!-- Where APIM gets Cognito's public keys to check the signature -->
  <openid-config url="https://cognito-identity.amazonaws.com/.well-known/openid-configuration" />

  <!-- Issuer must be Cognito -->
  <issuers>
    <issuer>https://cognito-identity.amazonaws.com</issuer>
  </issuers>

  <!-- Audience: your identity pool / app -->
  <audiences>
    <audience>us-east-1:YOUR-IDENTITY-POOL-ID</audience>
  </audiences>

  <!-- Layer 2 trust pin: only THIS Cognito identity is allowed -->
  <required-claims>
    <claim name="sub" match="all">
      <value>us-east-1:THE-ONE-ALLOWED-COGNITO-IDENTITY-ID</value>
    </claim>
  </required-claims>
</validate-jwt>
```

**What each check buys you:**

| Check | Proves |
|---|---|
| **Signature** (via JWKS) | Cognito really issued it; not forged or altered |
| **`iss` issuer** | Came from Cognito, not another issuer |
| **`aud` audience** | Minted for *your* identity pool, not reused elsewhere |
| **`exp` expiry** | Token is still fresh (short-lived, auto-enforced) |
| **`sub` subject** | It's **your one Lambda's** identity — the trust pin |

If **any** check fails, APIM returns `401` and never reaches the
managed-identity/Graph step.

**Caveat (validate in PoC):** Cognito's `GetOpenIdToken` JWT is signed and
exposes a JWKS, but its OpenID discovery document is less conventional than a
full OIDC provider's. If APIM's `<openid-config>` auto-discovery does not resolve
cleanly, the fallback is to point `validate-jwt` at the JWKS URL directly. This
is exactly the "less-trodden Lambda+Cognito bridge" risk — validate early.

### 7.6 Implementation sketch & division of labor

**Lambda code (the only code you write)** — mint the token, send it to APIM:

```python
import boto3, urllib.request

cognito = boto3.client("cognito-identity")

# 1. Get a Cognito identity ID (or reuse the pinned one)
identity = cognito.get_id(IdentityPoolId="us-east-1:YOUR-POOL-ID")

# 2. Ask Cognito to mint a short-lived signed JWT
jwt = cognito.get_open_id_token(IdentityId=identity["IdentityId"])["Token"]

# 3. Send it to APIM instead of calling Graph with user/password
req = urllib.request.Request(
    "https://your-apim.azure-api.net/sharepoint/read?path=...",
    headers={"Authorization": f"Bearer {jwt}"},
)
result = urllib.request.urlopen(req).read()
```

That is the entire AWS change: replace the old ROPC user/password Graph call
with `get_open_id_token` + a request to APIM.

**APIM does the validation for you — you do not build or host a validator.**
`validate-jwt` (see §7.5) is a declarative, built-in gateway policy. On success,
the next policy step (`authentication-managed-identity`) acquires a Graph token
as APIM's managed identity and forwards the read request.

**Division of labor:**

| Where | What | Who provides it |
|---|---|---|
| **AWS Lambda** | Mint token (`get_open_id_token`) + call APIM | **You (code)** |
| **APIM inbound** | Validate the token (`validate-jwt`) | **You (policy config, nothing to host)** |
| **APIM backend** | Get Graph token via managed identity, call Graph | **You (policy config)** |
| **Cognito / Graph / Entra** | Issue token / serve JWKS keys / enforce `Sites.Selected` | **AWS + Azure (managed services)** |

Mental model: **APIM validates, but you never build a validator** — your only
real code lives in the Lambda.

---

## 8. Trust Scoping — restricting to one Lambda (defense in depth)

The Cognito token's `sub` is the Cognito identity ID, so "this Lambda function"
can't be named directly. Enforcement happens in two layers:

- **Layer 1 (AWS):** a dedicated identity pool whose credentials/tokens are
  obtainable **only** by the specific Lambda's execution role.
- **Layer 2 (Azure):** APIM `validate-jwt` pins the token `sub` to that single
  Cognito identity ID.

Together these ensure only the intended Lambda can traverse the chain.

---

## 9. Security Considerations

- **No durable secrets** anywhere in AWS (token is short-lived, minted on demand).
- **Least privilege:** `Sites.Selected` + read; named sites only.
- **Token lifetime:** rely on Cognito's short-lived JWT; no caching of long-lived
  credentials in the Lambda.
- **Audit attribution:** Graph/SharePoint logs show APIM's MI. If per-caller
  attribution is required at the Graph layer, note this limitation and capture
  caller identity in APIM logs/telemetry instead.
- **Gateway hardening:** APIM endpoint should be protected (rate limits, IP or
  network restrictions as appropriate) since it is the trust boundary.

---

## 10. Open Questions

- **Q1.** Which SharePoint site(s) / document libraries / folders must be readable?
- **Q2.** Lambda runtime/language (for the exact MSAL/SDK snippet and `GetOpenIdToken` call)?
- **Q3.** APIM instance: existing or new? SKU/networking (public vs. VNet-integrated)?
- **Q4.** Is APIM-level (not Graph-level) audit attribution acceptable to IT/compliance?
- **Q5.** Token/JWKS caching and rotation expectations?
- **Q6.** Expected request volume (for APIM sizing and rate limits)?
- **Q7.** Self-service portal: direct owner self-service, or an admin-approval workflow?
- **Q8.** Granularity offered in the portal — library only, or folder-level too?
- **Q9.** Are whole-**site** grants ever needed (requires admin path), or is directory-level sufficient?
- **Q10.** Portal hosting (App Service, Container Apps, Static Web App + API) and its own sign-in/Entra app registration?
- **Q11.** Grant lifecycle: expiration, periodic recertification, and revocation SLA?
- **Q12.** Grant registry/datastore: is one needed at all? SharePoint (the permission objects) is the source of truth, so the portal can list/inventory grants via live Graph reads and emit grant/revoke audit events to App Insights — no datastore required. Add a **Cosmos DB** collection only if we later need approval-workflow state, grant-expiry scheduling, or a central cross-owner catalog/reporting view. (Local SQLite on App Service is explicitly rejected — ephemeral disk, no scale-out.)

---

## 11. Rollout Plan

1. **PoC** the Lambda → Cognito `GetOpenIdToken` → APIM `validate-jwt` chain
   (highest-risk, less-trodden piece) against a single test site.
2. Grant APIM MI `Sites.Selected` read on the test site; validate an end-to-end
   read.
3. Lock trust: dedicated identity pool + `sub` pinning in APIM.
4. Cut the production Lambda over from ROPC to the APIM endpoint.
5. Decommission the username/password credential.

---

## 12. Acceptance Criteria

- [ ] Lambda reads target SharePoint content with **no** stored secret, cert, or password.
- [ ] Only the designated Lambda/Cognito identity can traverse APIM to Graph.
- [ ] Graph permission is a **Selected** scope + read, scoped to named sites/libraries/folders (least privilege).
- [ ] ROPC username/password fully removed and decommissioned.
- [ ] End-to-end read verified in a non-prod environment before cutover.
- [ ] Self-service portal lets a site **Owner** sign in, see only resources they own, and grant **read** to the APIM MI at directory level.
- [ ] Portal can only ever grant to the **one** pinned APIM MI, read-only.
- [ ] Every grant is logged, viewable, and revocable through the portal.

---

## 13. Self-Service Access Portal

### 13.1 Why the portal exists — two separate permission systems

A SharePoint site has **two independent permission systems**, and they do not
overlap:

| Who wants access | Mechanism | Targets | Has a UI? |
|---|---|---|---|
| A **human** | SharePoint "Share" button / site permissions | Users, M365/security groups, sharing links | ✅ Built-in |
| An **app / managed identity** | Microsoft Graph "Selected" permissions | An application (appId / service principal) | ❌ **None** |

```
Human wants access   →  SharePoint "Share" UI       →  grants a USER
App/MI wants access   →  Graph "Selected" permission →  grants an APPLICATION
                          (API only — no built-in UI)
```

The SharePoint sharing UI can **only** target people and groups — you cannot type
an application or managed identity into it. Granting an app/MI access is an
**API-only** operation (`POST /sites/{id}/permissions` and the list/folder-level
equivalents). **Microsoft ships no UI for it.**

**The portal is that missing UI.** It signs in the site Owner and calls the Graph
"Selected permissions" API on their behalf to create the app grant — the
front-end SharePoint never provided.

### 13.2 Goal

Let a SharePoint site **Owner** self-serve: sign in, see the sites/libraries/
folders they own, and grant the **APIM managed identity** read access to a chosen
directory — no ticket, no admin (for directory-level grants).

### 13.3 Enabler

The newer "Selected" scopes support **delegated mode** (`Sites.Selected+Owner`,
`Lists.SelectedOperations.Selected+Owner`). A signed-in Owner can therefore
create **library/folder-level** grants themselves. The portal acts in delegated
mode on the Owner's behalf, so it never needs any tenant-wide or full-control
permission — only the delegated read-grant capability an Owner already has.

### 13.4 Architecture

```
Owner ──sign in (Entra, delegated)──▶ Self-Service Portal
                                          │
   1. Enumerate sites / libraries / folders the user OWNS   (Graph, delegated)
   2. Owner picks a directory + "read"
   3. Portal calls Graph (delegated, on the Owner's behalf) to CREATE
      a Selected permission grant:  APIM-MI-appId  →  read  →  /that/folder
   4. Record the grant (who / what / when) + allow Revoke
                                          │
                                          ▼
                      SharePoint folder now readable by APIM's MI
```

### 13.5 Guardrails (required)

1. **Pin the target.** The portal may grant to **exactly one** identity — the
   APIM managed identity's application (`appId` hard-coded). Never allow an
   arbitrary app to be selected.
2. **Read-only.** Only ever request the `read` role. No write path in the UI.
3. **Directory granularity.** Default to `ListItems.SelectedOperations.Selected`
   (folder) / `Files.SelectedOperations.Selected` (library folder) or library
   level — never whole-site by default.
4. **Ownership-scoped enumeration.** Show only resources the signed-in user
   actually owns; they cannot grant on resources they don't control.
5. **Audit + revoke + recertify.** Log every grant, list current grants,
   one-click revoke, and periodic re-attestation/expiration.

### 13.6 Out of scope — whole-site grants

This design covers **list / library / folder**-level **read** grants only, via the
delegated Owner path. Whole-**site** grants are **out of scope** because they would
require an elevated admin-level permission that conflicts with our read-only,
least-privilege goal. If a whole-site need ever arises, handle it as a separate,
admin-owned exception rather than through this self-service portal.

### 13.7 Alternatives considered for the portal

- **Off-the-shelf SharePoint governance tools** — over-serve this need and tend
  to reintroduce broad permissions. ❌
- **Admin-approval workflow** (owner requests → admin one-click approves) — good
  if security wants a human in the loop; higher friction. ➖ Optional variation.
- **Direct owner self-service** (this design) — lowest friction and still
  least-privilege thanks to delegated Owner scopes. ✅ **Chosen.**
