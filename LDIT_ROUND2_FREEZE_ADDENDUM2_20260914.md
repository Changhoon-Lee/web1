# LDIT Round-2 Freeze Addendum 2

Committed before APiCS language-value outcomes were inspected.

The mandatory 13-Fine-atom all-coarsening envelope is replaced by the complete **source-generated partition lattice** induced by Grambank's two published cross-classifications: pooled grammar, `Main_domain`, `Finer_grouping`, and their nonempty `Main_domain × Finer_grouping` common refinement. Every Phase-3 triplet-common comparison is evaluated on identical A∩B∩C primitive support under all four representations. A comparison is source-lattice direction-identified only if all four yield the same strict overall direction; otherwise it is source-lattice ambiguous.

Reason: Bell(13) brute force is computationally infeasible at the full 457,649,784-triplet scale, and although Gal & Klots (1995) prove a polynomial optimizer for the weighted sum-of-group-averages problem, the public materials inspected before holdout did not expose sufficient algorithmic detail for an independently auditable implementation. A direct weighted counterexample shows the simpler unweighted top-k formula is invalid for unequal atom support weights. No unverified optimizer will be used.

The Fine-atom all-coarsening envelope is therefore optional and may be added only after a separately verified exact weighted implementation with exhaustive small-n tests. This amendment changes no APiCS primary holdout rule; the optional APiCS all-coarsening secondary analysis is also removed from the required holdout.
