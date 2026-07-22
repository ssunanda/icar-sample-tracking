# DELIMIT Sample Tracking

Streamlit app for registering ICAR physical samples: fill in a short
form, get a unique sample ID + printable QR label, and a real record
gets created in [ODR](https://odr.io) at the same time. Also handles
subsamples and logging what happens to a sample afterward (shipped,
received, modified, data collected).

## Status

Everything's built and deployed, ready for pilot set:
- Register a new physical sample or a subsample of one and get a digital ODR record + printout label with QR code
- Label auto-attaches to the ODR record too, not just downloadable
- "Log an action" page for a sample's history after registration
- DELIMIT branding (colors, fonts, logo)

Live at `https://delimit-sample-registration-592241394536.us-central1.run.app`
— gated by a shared team password, ask Sunanda for it.

## Setup

See `setup.md` for local dev, secrets, and deployment. See
`USER_GUIDE.md` if you're just using the app. See `TESTING.md` if
you're changing it.

## History

Replaces a [Colab notebook](https://colab.research.google.com/drive/1xLY10hTnXOqVGIKaZ8Hp2E2BoBiHkNVj?usp=sharing)
+ Google Sheet workflow used until June 2026, dropped for not being
user friendly and could not use for generating QR codes and sample IDs. 

Contact: sunanda@exsitu.bio
