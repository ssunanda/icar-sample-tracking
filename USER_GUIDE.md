# DELIMIT — User Guide

DELIMIT is a website you use to keep track of physical samples (like
a piece of rock, a culture of bacteria, or a vial of something). When
you register a sample, you get a printed sticker with a code on it
that you put on the physical sample, and the website keeps a digital
record of it that anyone on the team can look up later.

There are two things you can do here:
- **Register a sample**: do this once, when you first get a new
  sample (or a piece cut/split off an existing one).
- **Log an action**: do this any time something happens to a sample
  that's already registered: it gets shipped somewhere, someone
  receives it, it gets processed or altered, or data gets collected
  from it.

## Opening the website

Open a web browser (Chrome, Safari, Edge, whatever you normally use)
and go to:

`https://delimit-sample-registration-592241394536.us-central1.run.app`

It'll ask for a password before showing anything else. This is a
shared password for the whole team, not tied to your personal
account. If you don't have it, ask Sunanda (sunanda@exsitu.bio).

Tip: bookmark this page so you don't have to ask for the link again.

---

## Registering a new sample

Before you start, have these ready:

- A short description of the sample (10 words or fewer, just enough
  that someone could recognize it, e.g. "Bacteria on an agar plate
  from soil core")
- Your name and email
- Where the sample physically is right now (e.g. "Fridge 2, Berkeley
  lab")

You don't need to know everything about the sample up front. This
form only asks for the basics needed to create a record and print a
label. Anyone with more detailed scientific information about the
sample (what type of organism, how it was formed, etc.) can add that
directly to the sample's record later, in a separate system called
ODR (more on that below).

**Step by step:**

1. **Choose New sample or Subsample.** If this is a totally new
   sample, pick "New sample." If it's a piece taken from a sample
   that's already been registered (like cutting a smaller piece off a
   rock), pick "Subsample of an existing sample" and type in the
   original sample's ID. The website will check that ID is real and
   figure out the next letter to add to it for you (so if the
   original was `cool-buffalo-water`, your subsample might become
   `cool-buffalo-water-A`).

2. **Pick a category** for the sample: Organism, Rock, Blob, Ice,
   Mixed, or Extract. Just pick whichever one fits best; more detail
   isn't needed here. If you pick Mixed or Extract, one more question
   appears asking which of Organism/Rock/Blob/Ice are involved (see
   the worked example below).

3. **Fill in the rest of the boxes**: a short description, your name
   and email, where the sample came from (if it's not your own),
   where it physically is right now, any notes you want to add, and
   photos of the sample if you have any (all optional). Every box has
   a small "?" next to it you can hover or tap for a longer
   explanation and an example.

4. **Click the "Register sample" button.**

That's it. The page will show you:

- A unique ID made of three words (like `eager-bullmastiff-of-tact`),
  this is your sample's permanent name
- A picture of a printable sticker/label with that ID and a QR code
  on it (a small square barcode a phone camera can scan)
- A **"Download label PNG" button**

**What to do with the label:** click "Download label PNG," print it
out, and stick it on the physical sample. The QR code on it links
back to the sample's digital record, so anyone can scan it later to
pull up more information.

**One thing to know:** scanning the QR code, or clicking the link
shown on screen, currently asks you to log into a separate website
called ODR. If you don't have an ODR login yet, ask Sunanda. This is
a known gap that's being worked on, not something wrong on your end.

### Worked example

Say a rock sample arrived from a colleague at Purdue, and you're the
one registering it.

- **Registration type**: New sample (it's never been registered before)
- **Sample category**: Rock
- **Brief description**: `Basalt fragment, Purdue field site`
- **Point of contact: full name**: `Jordan Lee`
- **Point of contact: email address**: `jlee@example.edu`
- **Point of contact: institution**: `Purdue University`
- **Source institution**: `Purdue University` (same as above, since it
  came from your own team's fieldwork - leave blank if it's the same,
  it's optional)
- **Current physical location**: `Shelf 3, Rock Lab, Berkeley`
- **Source link**: (left blank - no existing catalog record for this one)
- **Notes**: `Collected 2026-07-15, field notebook #12`

Click "Register Sample." You get an ID like `patient-falcon-of-wisdom`,
a label to print, and the ODR record is created automatically behind
the scenes.

**A Mixed-category example:** if instead this were a soil sample with
both mineral grains and visible microbial growth, you'd pick **Mixed**
as the category, and a new question would appear: "Which categories
make up this mixed sample?" - you'd check both **Rock** and
**Organism**, since the sample is a physical combination of the two.
Everything else in the form works the same way.

---

## Logging an action on a sample that's already registered

Use this whenever something happens to a sample after it's already
been registered: it ships somewhere, someone receives it, it gets
processed or altered, or data gets collected from it.

1. Type in the sample's ID and click "Find sample." (If you don't
   know the ID off-hand, someone with ODR access can look it up
   there.)
2. You'll see a list of everything that's already happened to that
   sample.
3. Fill in what kind of action this is, who's doing it, where, and
   any notes. You can also attach files (e.g. instrument data - if a
   file is in a proprietary format, note that in "File format notes"
   and include an open-format version too if you have one) and
   photos, both optional. Then submit. Today's date gets added
   automatically. This gets added to the sample's history, so anyone
   can see the full timeline later.

**Worked example:** the `patient-falcon-of-wisdom` sample from above
just got shipped to Carnegie for further analysis. You'd type in its
ID, click "Find sample," see its "Register" event from before, then
fill in: Event type = `Ship`, Location = `In transit, Berkeley to
Carnegie`, Recorded by = your name/email/institution, Notes = `Shipped
via FedEx, tracking 1234 5678 9012`. Submit, and it's added to that
sample's timeline right below the Register event.

---

## If something goes wrong

- **It asks you to log into ODR when you click the sample's link**:
  expected right now if you don't have an ODR account. Ask Sunanda.
- **It logged you out and asked for the password again**: normal,
  this happens automatically after an hour of not using the page.
  Just enter the password again.
- **"Too many incorrect attempts, locked out for 15 minutes"**: you
  (or someone else on this network) typed the wrong password too many
  times in a row. Wait 15 minutes, then try again with the correct
  password. Double-check with Sunanda if you're not sure you have the
  right one.
- **"Please fill in: ..."**: you left a required box empty; the
  message tells you which one(s).
- **"Brief description must be 10 words or fewer"**: your description
  is too long, just shorten it and try again. Nothing was lost.
- **"No existing sample with that ID found"**: double-check you typed
  the ID exactly right (it's case-sensitive, so capital and lowercase
  letters matter).
- **Anything else looks broken or confusing**: email Sunanda
  (sunanda@exsitu.bio) and describe what you were doing when it
  happened. You won't break anything by asking.
