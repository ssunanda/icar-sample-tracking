"""
Snapshot the register sheet into the (otherwise unused) summary file
----------------------------------------------------------------------
There's no delete button anywhere in this app (on purpose, see
USER_GUIDE.md), and Google Sheets' own version history isn't a real
backup strategy for "someone doesn't notice a mistake for weeks."
This creates a recovery point.

NOTE - this is a ROLLING single backup, not dated history: it
overwrites SUMMARY_FILE_ID's content every run (renaming it to show
the date), not a growing pile of dated files. Tried creating a fresh
dated file instead first, but Google service accounts have no Drive
storage quota of their own and can't create new files outside a
Shared Drive - confirmed live 2026-09-27, `files.create` and
`files.copy` both 403 with "Service Accounts do not have storage
quota." SUMMARY_FILE_ID already exists and the service account
already has Editor access to it (shared when the app was first set
up), and setup.md already flagged it as unused/safe to repurpose -
so updating its content sidesteps the quota problem entirely, at the
cost of only ever having the single most recent snapshot. If real
dated history matters later, the fix is a Shared Drive (see TODO.md).

Run manually for now (no scheduled job set up yet - see TODO.md),
from the repo root:

    python3 scripts/backup_register.py

Questions or issues? Contact sunanda@exsitu.bio
"""

import io
import sys
from datetime import date
from pathlib import Path

from googleapiclient.http import MediaIoBaseUpload

# odr_common.py lives at the repo root, one level up from scripts/ -
# Python only auto-adds the *script's own* directory to sys.path, not
# its parent, so this needs to be explicit.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odr_common import REGISTER_FILE_ID, SUMMARY_FILE_ID, get_drive_service, read_csv  # noqa: E402


def main():
    df = read_csv(REGISTER_FILE_ID)
    service = get_drive_service()

    media = MediaIoBaseUpload(
        io.BytesIO(df.to_csv(index=False).encode("utf-8-sig")),
        mimetype="text/csv",
        resumable=False,
    )
    filename = f"register_backup_(rolling, as of {date.today().isoformat()}).csv"
    service.files().update(fileId=SUMMARY_FILE_ID, body={"name": filename}, media_body=media).execute()

    print(f"Backed up {len(df)} row(s) into the rolling backup file, renamed to '{filename}'.")


if __name__ == "__main__":
    main()
