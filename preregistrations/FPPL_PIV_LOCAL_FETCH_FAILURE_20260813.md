# FPPL PIV local source-fetch failure

Date: 2026-08-13 (Asia/Singapore)

Design commit: `d21524c164f848926d614ffd55a616d6f94c40bf`

After the design was publicly committed, the first call to `skimage.data.vortex()` attempted to fetch the immutable scikit-image data files from GitLab commit `2cdc5ce89b334d28f06a58c9f0ca21aa6992a5ba`. The local execution environment had no DNS/network access and failed before reading any image byte:

`requests.exceptions.ConnectionError: Failed to resolve gitlab.com`

No image, preprocessing statistic, factor, leverage, threshold, mode, fixed point, trajectory, parameter, or gate was observed or changed. The campaign will fetch exactly the same two immutable source files through a GitHub Actions workflow and preserve their byte hashes. This incident is retained in the final failure ledger and is not counted as a scientific failure or pass.
