# Sprint Plan: Secretless Lambda → SharePoint Read (PoC → Production)

**Companion to:** `PRODUCT-SPEC.md`
**Chosen design:** Option D — Lambda → Cognito JWT → APIM `validate-jwt` → APIM
managed identity → Microsoft Graph (`Selected` read) → SharePoint.
**Sequencing principle:** de-risk the novel **Cognito hop first**, then build the
read path, then harden, then add the self-service portal, then cut over.

> Each sprint below is a **vertical slice with a demoable outcome and a go/no-go
> gate**. Sprint 0 is a throwaway spike — do not proceed until it passes.

---

## Sprint 0 — Spike: prove the Cognito → Azure token hop (highest risk)

**Goal:** Confirm the one uncommon, under-documented piece works before investing
in anything else. Throwaway code is fine.

**Tasks**
- [ ] Create a **dedicated** Cognito Identity Pool (used by nothing else).
- [ ] Write a minimal Lambda that calls `get_id` + `get_open_id_token` and prints
      the JWT.
- [ ] Decode the JWT and record its real `iss`, `aud`, `sub`, `exp` claims.
- [ ] Stand up (or reuse) a test APIM instance with a `validate-jwt` policy
      pointing at Cognito.
- [ ] Confirm APIM **accepts** a valid token and **rejects** a tampered/expired one.
- [ ] Resolve the discovery caveat: if `<openid-config>` auto-discovery fails,
      wire `validate-jwt` to the **JWKS URL directly**. Document which worked.

**Exit / Go-No-Go gate**
- ✅ APIM returns 200 for a valid Cognito token, 401 for an invalid one.
- ✅ Documented: discovery vs. direct-JWKS, and the exact claim values to pin.
- ❌ If the token cannot be validated at all → revisit token source (see spec §6
      note) before continuing.

**Risks addressed:** the entire "less-trodden Cognito bridge" risk (spec §6, §7.5).

---

## Sprint 1 — End-to-end read path (thin slice)

**Goal:** A Lambda reads one test folder through APIM using the MI — the core
value path working end to end.

**Tasks**
- [ ] Create/identify the **APIM managed identity** (system- or user-assigned).
- [ ] Register the Entra app / expose the MI's application to Graph.
- [ ] Grant the MI a **`Selected` read** role on **one test library/folder**
      (via Graph, done manually for now).
- [ ] APIM policy: `validate-jwt` (from Sprint 0) → `authentication-managed-identity`
      (resource = Graph) → forward read request to Graph → return result.
- [ ] Update the spike Lambda to send the token to APIM and read the folder.
- [ ] Demo: Lambda lists/reads files in the test folder; no secret anywhere.

**Exit / Go-No-Go gate**
- ✅ Lambda reads the target folder content via APIM with **no** secret/cert/password.
- ✅ Access confirmed limited to the granted folder (reading elsewhere fails).

**Depends on:** Sprint 0.

---

## Sprint 2 — Trust hardening & least privilege

**Goal:** Lock the path down to exactly one caller, read-only, directory-scoped.

**Tasks**
- [ ] Pin APIM `validate-jwt` `sub` to the **single** allowed Cognito identity.
- [ ] Ensure the Cognito identity is **only** obtainable by the intended Lambda
      role (dedicated pool + role scoping).
- [ ] Confirm the Graph grant uses a **directory-level** `Selected` scope
      (`ListItems.SelectedOperations.Selected` / `Files.SelectedOperations.Selected`),
      read role only — no full-control, no write.
- [ ] Add APIM hardening: rate limits, request logging, IP/network restrictions
      as appropriate.
- [ ] Negative tests: a different identity / different folder / expired token all
      fail with 401/403.

**Exit / Go-No-Go gate**
- ✅ Only the designated Lambda identity can traverse APIM to Graph.
- ✅ Access is read-only and scoped to the named directory; negative tests pass.

**Depends on:** Sprint 1.

---

## Sprint 3 — Self-service access portal

**Goal:** A site **Owner** can sign in and grant the APIM MI read access to a
directory they own — no admin, no ticket. (Spec §13.)

**Tasks**
- [ ] Register the **portal's** Entra app with **delegated** Graph permissions
      (Selected scopes + what's needed to enumerate owned resources).
- [ ] Portal: Entra sign-in (delegated, on the Owner's behalf).
- [ ] Enumerate **only** sites/libraries/folders the signed-in user **owns**.
- [ ] Grant flow: create a `Selected` **read** grant targeting the **pinned**
      APIM MI `appId` at the chosen directory.
- [ ] Guardrails (all required):
      - [ ] Target hard-pinned to the one APIM MI (no arbitrary apps).
      - [ ] Read role only; no write path in UI.
      - [ ] Directory granularity by default (never whole-site).
      - [ ] Ownership-scoped enumeration.
- [ ] Grant registry: log who/what/when; list current grants; **one-click revoke**.

**Exit / Go-No-Go gate**
- ✅ An Owner grants read to a folder via the portal; the Sprint-2 Lambda then
      reads it end to end.
- ✅ Portal cannot grant to any other identity, cannot grant write, cannot grant
      on resources the user doesn't own.
- ✅ Grant is visible and revocable; revoke removes access.

**Depends on:** Sprint 2. **Note:** whole-site grants are out of scope (spec §13.6).

---

## Sprint 4 — Production hardening & cutover

**Goal:** Move the real Lambda off the username/password and retire it.

**Tasks**
- [ ] Observability: APIM telemetry/alerts, capture caller identity in logs
      (Graph audit shows the MI — spec §9).
- [ ] Load/scale check against expected request volume; tune APIM SKU/limits.
- [ ] Grant lifecycle: expiration and periodic recertification of Selected grants.
- [ ] Migrate the **production** Lambda from ROPC to the APIM endpoint (small
      code change: mint token + call URL).
- [ ] Verify in non-prod, then production, with rollback plan.
- [ ] **Decommission** the username/password credential and remove the ROPC path.

**Exit / Go-No-Go gate (matches spec §12 Acceptance Criteria)**
- ✅ Production Lambda reads SharePoint with no stored secret/cert/password.
- ✅ ROPC credential fully removed and decommissioned.
- ✅ Monitoring, revocation, and recertification in place.

**Depends on:** Sprint 3 (or Sprint 2 if portal ships later).

---

## Dependency map

```
Sprint 0 (spike) ──▶ Sprint 1 (read path) ──▶ Sprint 2 (harden) ──┬──▶ Sprint 3 (portal)
                                                                   └──▶ Sprint 4 (cutover)
```

Sprints 3 and 4 can run in parallel after Sprint 2 if staffed; Sprint 4 can ship
before the portal (grants made manually) if you want the Lambda off ROPC sooner.

---

## Open items to confirm before Sprint 0 (from spec §10)

- **Sprint sizing / team:** cadence (1- or 2-week?), who owns AWS vs. Azure vs. portal.
- **Q1/Q8:** exact test site + directory granularity to target.
- **Q2:** Lambda runtime/language (for the token snippet).
- **Q3:** APIM instance — existing or new? SKU / networking.
- **Q7/Q11:** portal — direct self-service vs. approval; grant expiration/recert policy.

---

## Definition of Done (whole effort)

- [ ] All Sprint 0–4 gates passed.
- [ ] `PRODUCT-SPEC.md` acceptance criteria (§12) fully met.
- [ ] Runbook: how to grant/revoke access and how to rotate/operate the pieces.
