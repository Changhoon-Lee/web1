# FCPL ECG source-workflow dependency failure

Date: 2026-08-13 (Asia/Singapore)

Design commit: `162a406d97f86ff45135daec2ba7b631dcfcb68f`
Local fetch incident: `2a588f626a5d4621d88cc043b2233d360ab41ac4`
Failed workflow commit: `0867e8367a229ab787d6c5d9336f5b5eb25f2e4d`
Workflow run: `31648046719`

The GitHub Actions runner successfully downloaded the official 116-KiB `ecg.dat` file from `scipy/dataset-ecg`, but the optional array-metadata step failed before artifact upload because NumPy was not installed on the minimal runner Python:

`ModuleNotFoundError: No module named 'numpy'`

No source artifact was transferred to the research environment, and no ECG sample was numerically inspected. The corrected workflow removes only the optional NumPy metadata step, retains the identical source URL and byte stream, and uploads SHA-256, file size, and generic file metadata. Array-format validation will occur in the sealed local scientific environment after transfer.

No scientific design, theorem, operator, factorization, parameter, or gate changes.
