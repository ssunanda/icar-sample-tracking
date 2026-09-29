"""
One-off maintenance utility for removing a row from the register
sheet by sample ID - the case in USER_GUIDE.md's "Deleting
a record or a logged action": someone with ODR access deletes/corrects
the record in ODR directly, then needs the corresponding register
sheet row cleaned up to match. This does the second half.

Usage, from the repo root:
    python3 scripts/remove_register_row.py <sampleID>

Only removes an exact sampleID match (a subsample's own suffixed ID,
e.g. cool-buffalo-water-A, or a top-level sample's bare ID) - it does
NOT cascade-delete subsamples if you pass a parent's ID, since that's
a judgment call the caller should make explicitly rather than have
made for them silently.

Questions or issues? Contact sunanda@exsitu.bio
"""

import sys
from pathlib import Path

import pandas as pd

# odr_common.py lives at the repo root, one level up from scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odr_common import REGISTER_FILE_ID, read_csv, write_csv  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/remove_register_row.py <sampleID>")
        sys.exit(1)

    sample_id = sys.argv[1]

    reg = read_csv(REGISTER_FILE_ID)
    if "sampleID" not in reg.columns:
        print("Register sheet has no sampleID column - nothing to do.")
        sys.exit(1)

    match = reg[reg["sampleID"] == sample_id]
    if match.empty:
        print(f'No row found with sampleID "{sample_id}". Nothing removed.')
        sys.exit(1)

    print(f'Found {len(match)} row(s) with sampleID "{sample_id}":')
    print(match.to_string(index=False))

    subsamples = reg[reg["parent_sample_id"] == sample_id] if "parent_sample_id" in reg.columns else pd.DataFrame()
    if not subsamples.empty:
        print(f'\nNOTE: {len(subsamples)} row(s) list "{sample_id}" as their parent_sample_id. '
              "These are NOT being removed - if they should be too, re-run this script with their own sampleID(s).")

    confirm = input(f'\nRemove {len(match)} row(s) with sampleID "{sample_id}" from the register sheet? [y/N] ')
    if confirm.strip().lower() != "y":
        print("Aborted, nothing changed.")
        sys.exit(0)

    reg = reg[reg["sampleID"] != sample_id]
    write_csv(REGISTER_FILE_ID, reg)
    print(f'Removed. Register sheet now has {len(reg)} row(s).')


if __name__ == "__main__":
    main()
