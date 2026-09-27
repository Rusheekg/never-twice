# Evaluation



How we checked that Never Twice actually works — and where it didn't.



| | Benchmark 1 | Benchmark 2 |

|---|---|---|

| App | Hotel booking | Online shop |

| Language | Python (Flask, pytest) | JavaScript (Node, Jest) |

| Who built it | Same team as Never Twice | Teammate, **blind** — runner never saw the answer key |

| Hidden bugs | 7 | 6 (+ 3 decoys, 3 already-fixed traps) |

| Found by Never Twice | 7 / 7 | 6 / 6 flagged, 5 / 6 proven by failing test |

| False alarms on decoys | – | 0 / 3 |

| Bugs found that the answer key missed | – | 1 |

| Details | [benchmark-1-hotel-python](benchmark-1-hotel-python/RESULTS.md) | [benchmark-2-shop-javascript](benchmark-2-shop-javascript/RESULTS.md) |



## Rules we followed

1. The answer key was written **before** each run and not shown to Bob.

2. A bug only counts as **proven** if a test fails before the fix and passes after it.

3. We report failures too: a failed regression round, a bug that could not be proven, and a moment

&#x20;  where the runner accidentally saw part of an answer key are all written down in the results.



## What this does not prove

- Two languages were tested (Python and JavaScript). Step 0 is built to detect others, but they are not verified yet.

- Both apps are small (under 10 source files). Large codebases are not tested yet.



## New-developer setup test
A teammate followed the main README from a fresh clone on a second Windows laptop (Python 3.12): setup, 13/13 tests passing, guardrail clean, global install with `Verification: PASS`, and the Never Twice mode appeared in an unrelated empty project in Bob. Time taken: about 4 minutes.
