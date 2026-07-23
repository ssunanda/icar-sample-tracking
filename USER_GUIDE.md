# DELIMIT — User Guide

Two things you can do here: **register a sample** (new or a subsample
of one you already registered) or **log an action** on a sample that's
already registered (shipped, received, modified, data collected).

## Open the app

`https://delimit-sample-registration-592241394536.us-central1.run.app`
— enter the team password. Don't have it? Ask sunanda@exsitu.bio.

---

## Register a sample

Have on hand:
- A brief description (10 words or fewer)
- Your name, email, and ICAR institution (point of contact)
- Where the sample physically is right now

The form only covers the basics needed to create the record and print
a label — everything else (subtype, biotic/abiotic, origin, and other
detailed taxonomy) gets filled in directly on the ODR record afterward,
not through this form.

**Steps:**

1. Pick **New sample** or **Subsample of an existing sample** at the
   top. For a subsample, enter the parent's sample ID — the app
   checks it exists and generates the next letter suffix
   (`<parent-id>-A`, `-B`, ...) for you.

2. Pick the sample's **category** — `Organism`, `Rock`, `Blob`, `Ice`,
   `Mixed`, or `Extract`.

3. Fill in the rest: description, who's registering it (point of
   contact name/email/institution), source institution and link if
   there is one, where it is now, and any optional notes.

4. Click **Register Sample**. You get:
   - A unique sample ID (three words, like `eager-bullmastiff-of-tact`)
   - A printable label with that ID, a QR code linking to the sample's
     real ODR record, and blank spots to fill in status/mass by hand
   - Step-by-step instructions and a **Download label PNG** button —
     download it, print it, and stick it on the physical sample

Behind the scenes: registering also creates the sample's ODR record
and its first history entry ("Register"), and attaches the label
image to that record. Once you have the ODR link, go fill in any
additional detail about the sample there directly.

---

## Log an action

Use this once a sample's already registered and something happens to
it — shipped, received, modified/processed, data collected, or
anything else.

1. Search for the sample by its ID. (You can find any sample's ID by
   looking it up on the Open Data Repository if you don't have it
   handy.)
2. You'll see its history so far.
3. Pick the action type, fill in who/where/when (today's date is
   automatic) and any notes, and submit. It gets added to that
   sample's history in ODR.

---

## Troubleshooting

- **"Too many incorrect attempts, locked out for 15 minutes"** —
  mistyped the password too many times in a row. Just wait 15 minutes
  and try again with the correct password (double-check with
  sunanda@exsitu.bio if unsure) — no need to email about this one
  unless it's still locked after waiting.
- **"Please fill in: ..."** — a required field (marked `*`) is
  blank; the message says which one.
- **"Brief description must be 10 words or fewer"** — shorten it and
  resubmit, nothing was saved yet.
- **Subsample parent ID not found** — double check the parent sample's
  ID is spelled exactly right (it's case-sensitive).
- **Anything else looks wrong** — email sunanda@exsitu.bio with what
  you were doing when it happened.
