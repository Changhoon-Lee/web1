# FCPL ECG local source-fetch failure

Date: 2026-08-13 (Asia/Singapore)

Design commit: `162a406d97f86ff45135daec2ba7b631dcfcb68f`

After the design was publicly committed, the first call to `scipy.datasets.electrocardiogram()` attempted to download `ecg.dat` from the official repository `scipy/dataset-ecg`. The local execution environment had no DNS/network access and failed before any ECG byte was read:

`requests.exceptions.ConnectionError: Failed to resolve raw.githubusercontent.com`

No ECG sample, preprocessing statistic, factorization, leverage, threshold, mode, fixed point, trajectory, scientific parameter, or gate was observed or changed.

The campaign will fetch exactly the same official `ecg.dat` through a GitHub Actions workflow, preserve its byte hash, and retain this incident in the final failure ledger. This failure is not counted as a scientific pass or failure.
