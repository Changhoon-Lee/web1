# LDIT Round-2 Freeze Record

Frozen before inspection of APiCS language-value outcomes.

Full local protocol snapshot SHA-256:
`21ef6754f27277444cf68c31a16b89081540501b007c2a88615f0393937c5814`

Primary untouched holdout:
- APiCS v2013
- repository `cldf-datasets/apics`
- tag `v2013`
- commit `4ed59b5e5b6f6c666e9fa3c2e55e9e59863e70d9`
- Zenodo DOI `10.5281/zenodo.3823888`

Frozen primary holdout metric:
- parameters: numeric IDs 1–130, Type=primary, nonempty published Area
- language-feature representation: normalized source Frequency distribution when available; otherwise uniform over listed attested values
- primitive distance: total-variation distance on feature-value distributions
- pooled distance: mean primitive feature distance over pair-common support
- ontology distance: equal mean of published APiCS Area-specific means
- primary pair eligibility: >=65 common primary features and >=1 common feature in every published Area
- primary anchor eligibility: >=2 eligible candidates
- primary estimand: rate of anchors whose pooled and Area nearest sets are disjoint; nearest sets are used rather than lexicographic tie-breaking
- secondary strict-coverage rule: >=98 common features and >=50% common support within every Area

Frozen claim map:
- no eligible anchors: inconclusive
- eligible and disjoint-NN rate=0: external activation fails
- 0<rate<0.5: external existence replication only; exact finite-resource rate reported
- rate>=0.5: allowed wording is `pervasive in the eligible APiCS sample`
- no world-language prevalence claim under any outcome

Development-side corrections frozen before holdout:
- WALS is not a holdout because it was previously analyzed
- all-partition primitive envelope is a maximal-ignorance boundary, not an empirical prevalence finding
- Grambank Main_domain and Finer_grouping are cross-classifications, not a hierarchy
- Pareto-nondominated and positive-linear-weight-supported candidate sets are distinct; the latter is to be computed by LP
- Gal & Klots (1995) receives mathematical priority for weighted-average partition optimization
- source-defined Grambank code, margin analysis, exact support, driver attribution, constrained source-atom envelope, and priority rewrite are mandatory hardening steps

No new primary metric, support threshold, ontology, or claim category may be introduced after APiCS outcomes are inspected. Bug fixes require an explicit erratum log.
