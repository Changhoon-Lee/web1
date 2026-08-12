# SCMC retina fixed-step amendment

Date: 2026-08-12 (Asia/Singapore)

Design commit: `00c02f7374f67ad4b30a116b5339118f0f560f4c`
T2 scope amendment: `b494a634db433a609dd4aa0df68ad621b324f5f7`

This amendment is committed before loading or inspecting the retina pixel array.

The original design omitted the numerical value of the gradient step `beta` while freezing a continuation only in the cross-sector coherence parameter `theta`. The omission is corrected by fixing

`beta = 2.0`

for every raw, safe, fail, and coherence-repaired retina operator.

The bridge strength remains `eta=1.0`, and every other design choice remains unchanged. The builder may not move beta after seeing the data. If the theta path on `[0,1]` does not contain a certified stable-to-unstable crossing at beta 2, the prospective retina campaign fails.
