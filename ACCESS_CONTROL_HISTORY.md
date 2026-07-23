# Access control history

Why this app is gated by a shared password and not Google-account
login (IAP), and everything that was actually tried before landing
there. Written 2026-07-22 so this doesn't need re-litigating later
without knowing what's already been ruled out.

## Current state

**Shared team password**, checked in `app.py` before anything else
loads. The Cloud Run service itself is public
(`--allow-unauthenticated`) — the password is the only gate. See
`setup.md` "Deploy to Google Cloud Run" for the actual deploy steps.

## Timeline

1. **Started with a shared password.** Reason: the ~20 people who
   need access span several institutions (NASA, Carnegie, Howard,
   Purdue, Rutgers, ex situ bio) and nobody knew upfront how
   consistent Google account coverage was across all of them.
2. **Switched to IAP** once it looked like Google-account coverage was
   actually fine (people without one could just self-create a free
   Google account tied to any email in a couple minutes) — IAP gives
   real per-account gating and an audit trail, a genuinely better
   security posture than a shared secret.
3. **Switched back to password, 2026-07-22**, after IAP proved
   unreliable in a way that resisted every diagnostic available
   without direct Google backend access (see below). Real
   per-person attribution already happens at the data layer anyway —
   every registration/event captures the actual person's name and
   email — so the login step's only real job is keeping random
   passersby off the URL, which a shared password does fine.

## The IAP failure, and everything checked before giving up

**Symptom:** some people who were confirmed, correctly granted
`roles/iap.httpsResourceAccessor` still got IAP's own "You don't have
access" page — not a Google consent-screen error, IAP's own denial,
troubleshooting info and all. `sunanda@exsitu.bio` and
`hans@exsitu.bio` (both `exsitu.bio` Workspace accounts) worked fine;
`aprabhu@carnegiescience.edu`, `ssharma11@carnegiescience.edu` (tested
directly by the account owner), and `hans.m.pech@gmail.com` (a
personal Gmail, unrelated to any Workspace) did not — despite all
being in the granted list.

Everything checked, in the order tried, all confirmed fine:

- **IAP IAM policy** (`gcloud iap web get-iam-policy`) — all 10
  expected emails present, correct role, no conditions attached.
- **IAP → Cloud Run binding** (`gcloud run services get-iam-policy`)
  — the IAP service agent
  (`service-<PROJECT_NUMBER>@gcp-sa-iap.iam.gserviceaccount.com`) had
  `roles/run.invoker`, as required.
- **Org policy** (`iam.allowedPolicyMemberDomains`) — confirmed still
  `allowAll: true` from the earlier fix, not reverted.
- **Wrong-account / cached-session theories** — ruled out: confirmed
  the exact signed-in account matched the exact granted account,
  character for character; tried fresh incognito windows; checked
  [myaccount.google.com/permissions](https://myaccount.google.com/permissions)
  and found the app had never even appeared there (meaning IAP was
  rejecting before Google's own consent flow ever ran for that
  account — ruling out a stale OAuth grant needing revocation).
- **OAuth consent screen ("Google Auth Platform") Audience setting**
  — found it was effectively unconfigured ("not configured yet"),
  which was a real, plausible culprit (a Workspace-owned project can
  default new IAP setups to Internal-only, which would exactly explain
  "only exsitu.bio works"). Configured it properly as **External**,
  Testing publishing status, added all 10 people as test users.
  **Did not fix it** — same failure afterward, including for
  `sunanda`'s own second Carnegie account.
- **IAP re-provisioning** — toggled IAP off and back on
  (`--no-iap` then `--iap`) on the Cloud Run service, in case it was
  still bound to a stale/original OAuth client from whenever it was
  first auto-created. No change.
- **OAuth 2.0 Client IDs page** (APIs & Services → Credentials) — checked
  whether IAP's auto-created client actually exists there at all.
  Found **nothing listed.** Inconclusive on its own — Cloud Run's IAP
  integration may not surface its client the same way older
  App Engine/Compute Engine IAP setups do — but consistent with
  something being genuinely mis-provisioned.
- **Cloud Run request logs** — checked for the actual denial event.
  Found nothing relevant, because IAP rejects requests *before* they
  ever reach the Cloud Run container, so its own access decisions
  never show up in the app's request logs at all.
- **IAP's own audit logs (Data Access)** — this would have shown the
  real reason, but Data Access logging for `iap.googleapis.com` is off
  by default and doesn't retroactively cover past attempts. Enabling
  it means hand-editing the project's IAM audit config, which carries
  real risk of misconfiguring project-wide logging if rushed. Not
  attempted, given the decision to drop IAP for now.

**Net result:** every piece of configuration we could inspect said
this should have worked. It didn't, for reasons that would need
direct Google-side visibility into IAP's internals to actually
diagnose (i.e., a support case) — not something fixable by us from
outside.

## If IAP gets revisited later

Don't re-try the theories above — they're ruled out. The productive
next step would be opening a Google Cloud support case (if there's a
support plan on the billing account) so someone can look at IAP's
actual internal decision for a specific failing request, since that's
the one piece of information we never managed to get access to.
