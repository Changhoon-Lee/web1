# FPPL PIV source-workflow dependency failure

Date: 2026-08-13 (Asia/Singapore)

Design commit: `d21524c164f848926d614ffd55a616d6f94c40bf`
Local fetch incident: `c1ad5fa2ba7aecebfbb26ce11ad81643526bab7b`
Failed workflow commit: `4e9aded2b76a8191b28648ee1d624dd41c679479`
Workflow run: `31622383135`

The GitHub Actions runner successfully downloaded both immutable 256-KiB TIFF files from the frozen scikit-image data commit. The job then failed before artifact upload because the optional metadata step imported Pillow, which was not installed:

`ModuleNotFoundError: No module named 'PIL'`

No source artifact was transferred to the research environment, and no image byte was numerically inspected. The corrected workflow removes only the nonessential Pillow metadata step, retains the identical URLs and data commit, and uploads byte hashes and sizes. No scientific design or gate changes.
