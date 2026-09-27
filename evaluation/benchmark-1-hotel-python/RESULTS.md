# Benchmark 1 — Hotel Booking App, Python (Results)



## What this benchmark is

A small Flask hotel-booking app (`app/`) with 3 postmortems (`postmortems/PM-001..003`).

The postmortems describe bugs that were fixed once. The same bug patterns were then hidden in

7 other places in the code. The list of hidden bugs was written down **before** any run and kept

outside the repo (`ANSWER\_KEY.md` in this folder).



The buggy starting point is tagged in git as `buggy-baseline`.



## Runs



| Run | Who / what | Hidden bugs found | Tests | Guardrail | Time |

|---|---|---|---|---|---|

| Manual baseline | A developer read the postmortems and searched by hand | **1 / 7** | – | – | 26 min |

| Never Twice, first run | Agent mode with the Never Twice instructions | **7 / 7** | – | – | – |

| Never Twice, demo run | Custom mode (`.bob/custom\_modes.yaml`) | **7 / 7** | 13 | 7 findings → 0 | ~6 min 22 s automated, ~10 min 48 s wall clock |

| Regression check, round 1 | Upgraded language-aware mode (global install) | found, but **failed review** | – | – | – |

| Regression check, round 2 | Upgraded mode after rule fixes | **passed** | 12 bug + 7 safety tests, 19/19 after fixes | 7 findings → 0 | – |



## Why the regression check was needed

After making Never Twice language-aware (Step 0 detection, CI templates, global install),

we re-ran it on this same app to make sure the upgrade did not break what already worked.



**Round 1 failed our review**, and we kept it in the record on purpose:

- some tests asserted the **buggy** behaviour, so they passed before the fix instead of failing;

- the guardrail used a hardcoded list of "already fixed" function names instead of detecting the pattern.



We added rules to the mode: bug tests must assert the **correct** behaviour (fail before the fix,

pass after), test counts must be reported honestly, and guardrails may not skip functions by name.



**Round 2 passed:** 3 subagents, 12 `test\_bug\_` and 7 `test\_safety\_` tests, 19/19 passing after fixes,

guardrail 7 → 0.



## Honest disclosures

- The same team built the app and Never Twice. This is why we also ran a **blind** benchmark

&#x20; in a second language — see `../benchmark-2-shop-javascript/RESULTS.md`.

- One earlier version of the guardrail was too noisy (64 findings, 57 false positives). It was replaced

&#x20; with the validated version, self-validation rules were added to the mode, and the Prevention Report

&#x20; has a "Guardrail Correction" section explaining this.



## Evidence

- `ANSWER\_KEY.md` — the hidden bug list written before the runs

- `reports/` and `tests/` at the repo root — output of the demo run (on `main`)

- `bob\_sessions/` — exported Bob sessions for every run, including both regression checks


