# MCGR Motorcycle disparity-coordinate authority correction

Date: 2026-08-12 (Asia/Singapore)

Design commit: `314f3d04281758464768a943f3196f31d9da163e`
Prediction commit: `ec4cfff51a8a926e5124e81325689b7e9e51e3ae`
Confirmatory-result commit: `e0a5500f20f3ce84fdb652a555013f62b6d18326`

## Defect

The packaged `skimage.data.stereo_motorcycle()` disparity array follows the example convention in which the array is indexed at a right-image coordinate and identifies the corresponding left coordinate. The first MCGR builder instead sampled that array at its frozen left anchor and applied `c_right=c_left-disparity`. That is not the documented physical-coordinate interpretation of the packaged map.

## Preserved numerical authority

The public prediction and trajectory remain valid for the sealed 512-dimensional operator actually built. Their input/operator hashes, high-rank completion, response determinant, safe/fail/repair spectral values, winding counts, fixed points, and trajectory rates are not changed.

## Demoted claim

The first campaign is not retained as a clean ground-truth stereo-correspondence validation. Its two anchor coordinates are treated only as deterministically data-derived coordinates in the sealed operator. The native disparity-consistency metric used the right-indexed convention and remains a descriptive metric, not a rescue of the anchor interpretation.

## Clean replacement

The clean Adirondack replication was designed and committed after this defect was found. It uses the official Middlebury `disp0.pfm`, which is explicitly left-view disparity, independently parses its PFM bytes, applies `c_right=c_left-disp0(left)`, publicly freezes every prediction before trajectories, and then confirms the frozen phase and repair.

No Motorcycle parameter or result is retrospectively changed or relabeled.
