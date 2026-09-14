# FROZEN ROUND-2 ADDENDUM 4
## Secondary cross-variety replication: eWAVE v3.0

**Date:** 2026-09-14  
**Timing:** frozen before inspection of eWAVE language-value outcomes.

This secondary replication is not allowed to redefine or rescue the already-reported APiCS holdout. It asks whether source-defined ontology sensitivity also exists within a single-language family/regime: varieties of English.

## Source lock

- Repository: `cldf-datasets/ewave`
- Release: `v3.0`
- Commit: `6f74fdd4abc7214e26c2de577086f689becf3f58`
- Zenodo DOI: `10.5281/zenodo.3712132`
- Published source metadata: 235 features in 12 grammatical domains.

Only metadata/schema (`parameters.csv`, `featurecategories.csv`, `codes.csv`, ValueTable header) was inspected before this freeze. No language-value row was inspected.

## Primitive features and source ontology

Use all parameters with integer IDs 1–235 exactly once.

The source ontology is the published `Category_ID` mapping to the 12 feature categories in `featurecategories.csv`.

Representations:
1. pooled 235-feature representation;
2. equal-category representation over the 12 published grammatical domains.

## Per-feature value metric

The published code scale is ordinal:
- A / Number 1: pervasive or obligatory
- B / Number 2: intermediate
- C / Number 3: extremely rare
- D / Number 4: attested absence
- X / Number 5: structurally not applicable
- ? / Number 6: no information

For A–D only, define normalized scalar state `s=(Number-1)/3` in `{0,1/3,2/3,1}`.

Primitive feature distance is `|s_f(A)-s_f(B)|`.

Codes X and ? are treated as missing, not as linguistic endpoints. If a language-feature has no unique A–D code after excluding X/?, it is missing. If multiple distinct A–D codes occur for the same language-feature, the pair is treated as missing for that feature; no post-hoc disambiguation is allowed.

## Pair eligibility

Primary:
- at least 118 pair-common usable features (>=50% of 235);
- at least one pair-common usable feature in each of the 12 published categories.

Secondary strict:
- at least 177 pair-common usable features (>=75%);
- pair-common usable support in every category >=50% of that category's published feature count.

Anchor eligibility: at least two eligible candidates.

The same pair-common primitive support is used for pooled and category representations. No imputation.

## Distances

Pooled distance is the mean primitive feature distance over pair-common usable support.

Category distance is the equal mean of the 12 category-specific mean primitive distances, provided every category has positive support.

Nearest-set equality tolerance: absolute `1e-12`.

## Primary estimand

`R_disjoint` = fraction of eligible anchors whose pooled and category nearest sets have empty intersection.

Also report nearest-set intersection nonempty rate, identical-set rate, unique-same rate, candidate-pool sizes, and winner/runner-up distinct-distance gaps for changed and unchanged anchors.

## Frozen interpretation map

- no eligible anchors: secondary replication inconclusive;
- eligible anchors and disjoint rate = 0: no cross-variety activation detected;
- 0 < disjoint rate < 0.5: cross-variety existence replication;
- disjoint rate >= 0.5: source-defined ontology changes nearest sets for a majority of eligible eWAVE varieties; `pervasive in the eligible eWAVE sample` permitted.

No result licenses inference to all English varieties or all languages.

## Run rule

Execute once. Any bug correction requires a logged protocol-violation/erratum statement and a complete rerun. No outcome-dependent code or threshold changes are allowed.
