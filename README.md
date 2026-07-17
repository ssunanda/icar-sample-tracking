# ICAR Sample Tracking

Streamlit app for registering ICAR physical samples: fills in a short
form, generates a unique sample ID, and prints a QR label. Branded as
DELIMIT (the ICAR project team name) (see `brand/`).

## Status

Working today: registration form, Google Sheet-backed register/summary
CSVs, unique sample ID + printable label.

Not yet built: pushing a real record into [ODR](https://odr.io) on
submit (currently just generates a placeholder URL/QR code), subsample
registration, and action/event history logging. See `setup.md` for
current ODR integration status.

## Setup

See `setup.md` for local setup, secrets format, and the register CSV
field reference.

## History

Replaces a [Colab notebook](https://colab.research.google.com/drive/1xLY10hTnXOqVGIKaZ8Hp2E2BoBiHkNVj?usp=sharing)
+ Google Sheet workflow used until June 2026, dropped for not being
user friendly.

Contact: sunanda@exsitu.bio