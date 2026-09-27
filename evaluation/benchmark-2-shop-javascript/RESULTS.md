# Benchmark 2 — Blind JavaScript Shop (Results)

## Why this benchmark exists
Benchmark 1 (hotel app, Python) was built by the same team that built Never Twice, so it could have been tuned to it.
Benchmark 2 tests the opposite: a **different language** (JavaScript / Node / Jest), a **different app** (online shop),
and a **blind setup** — one teammate built the app, the bugs, the decoys and the answer key; the other teammate ran
Never Twice without seeing the answer key or the builder's Bob session.

| Role | Person | Bob session export |
|---|---|---|
| Builder (app, postmortems, hidden bugs, decoys, answer key) | Aluvala Sai Shailu Sri | `bob_sessions/benchmark-js-build.md` |
| Runner (ran Never Twice, reviewed the checkpoint) | Rusheek G | `bob_sessions/benchmark-js-run.md` |

Never Twice was used from the **global install** (`scripts/install_never_twice.py`), not copied into the project.

## Setup
- 3 postmortems (PM-2xx), one per bug type: **G** loose equality, **H** unhandled promise, **I** missing null check
- 6 hidden bugs (2 per type), 3 already-fixed examples, 3 decoys — see `ANSWER_KEY.md`
- Node v24, Jest 29

## Score

| Measure | Result |
|---|---|
| Language detected by Step 0 | JavaScript + Jest (correct) |
| Subagents spawned | 3 (one per bug type) |
| Answer-key bugs flagged at the first checkpoint | **6 / 6** |
| Answer-key bugs proven with a failing test | **5 / 6** (G2 — see below) |
| Decoys wrongly flagged | **0 / 3** |
| Already-fixed locations wrongly flagged | **0 / 3** |
| Real bugs found that the answer key missed | **1** |
| Tests written | 16 (6 `test_bug_`, 10 `test_safety_`) |
| Tests after fixes | 16 / 16 passing |
| Guardrail (`guardrails/check_patterns.js`) | 6 findings → 0 after fixes |
| Time | ~16 min automated + ~21 min human review ≈ 37 min |

### Bug by bug

| ID | Location | Flagged | Proven by failing test | Fixed |
|---|---|---|---|---|
| G1 | `cart.js` `addToCart` (`==`) | ✅ | ✅ | ✅ |
| G2 | `orders.js` `cancelOrder` (`!=`) | ✅ | ❌ reclassified | ✅ (as code-quality fix) |
| H1 | `orders.js` `placeOrder` (unawaited confirmation) | ✅ | ✅ | ✅ |
| H2 | `users.js` `updateUserEmail` (unawaited alert) | ✅ | ✅ | ✅ |
| I1 | `discounts.js` `applyDiscount` (no null check → TypeError) | ✅ | ✅ | ✅ |
| I2 | `inventory.js` `getProductDetails` (`Object.assign({}, undefined)` → `{}`) | ✅ | ✅ | ✅ |
| Extra | `orders.js` `cancelOrder` (unawaited `sendOrderCancellationNotice`) | ✅ | ✅ | ✅ |

### About G2
The answer key says `cancelOrder(1001, "2")` passes the ownership check because `2 != "2"` is `false`.
That is true — but user `"2"` **is** the owner (user 2), so allowing the cancel is the correct result.
No realistic input made a *different* user pass the check, so no test could show a wrong result.
Following the mode's rule ("no failing test → not a confirmed bug"), the human reviewer moved G2 to the safe list
at the checkpoint. Bob still changed it to `!==` with `Number(userId)` as a consistency fix.
We report this as **flagged, not proven** rather than counting it as a win.

### Extra bug the answer key missed
`cancelOrder` also calls `notify.sendOrderCancellationNotice(...)` without `await` — the same Type H pattern as H1/H2.
When the notifier fails, the order is cancelled and `success: true` is returned, but the customer is never told.
Never Twice proved it with a failing test and fixed it. The answer key lists 2 Type H bugs; the code actually had 3.

## Issues found in the benchmark itself
1. **PM-201 points at the wrong place.** Its "Code Before / Code After" describes `cancelOrder` as the fixed location,
   but `cancelOrder` still had `!=`, and the answer key says the already-fixed Type G example is `reserveStock`.
2. **3 Type H bugs in the code, 2 in the answer key** (see "Extra bug" above).

## Honest disclosures
- **Runner saw part of the answer.** While helping with setup, the runner accidentally saw the two Type H locations.
  To limit the effect, the runner only typed the standard prompt and rule-based review messages to Bob
  (no hints about locations). The Type G and Type I bugs were not seen in advance.
- **Two review rounds at the checkpoint.** In round 1 Bob had kept G2 as a confirmed bug without a failing test;
  the reviewer sent it back under the mode's own rule and it was moved to the safe list.
- **Node 24 crash.** Node 24 turns unhandled rejections into process crashes, so the first Jest run crashed.
  Bob first added `cross-env NODE_OPTIONS=--unhandled-rejections=warn` to `package.json`; the reviewer asked for it
  to be reverted because it hides exactly the bug type being hunted. Bob then contained the rejections inside the tests.
- **Guardrail narrowed.** The first guardrail flagged too much; it was narrowed to flag only `==`/`!=` in ID comparisons
  (so the `code == null` decoy stays allowed), with no hardcoded function-name skips.
- **Answer key location.** Bob could only write inside the workspace, so the builder's `ANSWER_KEY.md` was created
  in the project root and moved out before the run. The runner did not open it until scoring.

## Files in this folder
- `src/`, `postmortems/`, `package.json` — the shop app **after** Never Twice applied its fixes (no `node_modules`). The original buggy code is shown in `bob_sessions/benchmark-js-build.md`
- `ANSWER_KEY.md` — the builder's hidden answer key
- `reports/` — Never Twice output (patterns, findings, prevention report, proposed CI)
- `tests/never_twice.test.js`, `guardrails/check_patterns.js` — generated by Never Twice

