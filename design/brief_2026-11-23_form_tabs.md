# Brief 2026-11-23 — Form tabs for every document type (in one go)

Written in Cowork with Lady, 2026-11-23. My intent, not a script: if something doesn't fit the code or there's a better
way, say so before building. **Exception to "stop after each step": build this whole brief in one go**, then stop and
report once (what was built, what is view-only and why, what couldn't be tested). `tests\run_tests.bat` passes at the end.
Add the decisions and the result to BUILD_NOTES.md (short, plain language). Remove "Form view for the other forms" from
BUILD_NOTES' pending items once done (replace it with whatever is left).

## Decisions (Lady, 2026-11-23)
- **Every form tab in `core\formview.py` `TABS` / `TABS_IF` gets its form view**, like W2 and 1098-M (`BUILT`). No more
  "Form view coming soon" for a form the program reads.
- **A tab shows what the reader already keeps** — no new reading work in this brief. If a reader keeps only some boxes
  (SSA: box 5; 1098-E: boxes 1–2), the tab shows those; teaching readers more boxes is for later.
- **1099-Comp, 1099-B, 1099-DA: totals, not transactions** — the same information the Income Summary carries.

## Decisions after the review (Lady, 2026-11-23, in Claude Code)
- **One column per form, never added together** — also 1099-R, 1098-E, 1099-INT, NEC, MISC (their readers keep each
  different form, not only the total). This replaces "one column per document … n forms — added together" in section 2.
  Brokerage composites stay one column per statement.
- **Copies vs different forms = the W-2 rule everywhere:** two forms in one file are the same form (copies, merged — each
  fills in boxes the other missed, the first copy's amounts stay) when their federal key boxes match; state / local boxes
  never count. Key boxes: W-2 1, 2, 3, 5 · 1099-R 1, 2a, 4, code · MISC 1, 2, 3, 4 · NEC 1, 4 · INT 1, 3, 4 · 1099-SA 1, 2 ·
  SSA 5, 4 · 1098-T 1, 5 · 1095-A line 33 column C. **Built first, on its own** (see BUILD_NOTES, 2026-11-23).
- **SSA-1099, 1098-T, 1095-A:** no per-form reading now — read the first form as today. If other pages carry the same form
  title with different key amounts, add the note "This file seems to hold more than one <form> — check." Per-form reading
  for these three = later (BUILD_NOTES pending list).

## What to build
Same machinery as W2 / 1098-M: one column per form (6 per tab, `_2`, `_3` …, Total column), the column header
(person · payer), corrections kept apart from what was read, ticks, the refresh banner. Each form = a `DEFS` entry + its
`FORMS` functions (read → row keys, row keys → read, the document's result again).

### 1. Single-form documents (one column per form)
| Tab | Reader | Rows |
|---|---|---|
| 1099-R | `parse_1099r` (`detail.boxes`, gross, taxable, code) | boxes 1, 2a, 2b checks, 3, 4, 5, 7 code + IRA/SEP/SIMPLE, state boxes if kept |
| 1098-T | `parse_1098t` (`detail.boxes`, checks) | the boxes kept (1, 5, …) and the check boxes |
| 1099-SA | `parse_1099sa` (`detail.forms`) | per form as kept (gross, code …) |
| 1098-E | `parse_1098e` | box 1, box 2 |
| SSA-1099 | `parse_ssa` | box 5 (+ withholding if kept) |
| 1095-A | `parse_1095a` | what is kept (line 33 col C / APTC); memo only |

### 2. Single 1099s — INT, DIV, NEC, MISC, OID (and G / K only if a reader exists)
- `parse_1099_form` adds the copies in a file together (`detail.boxes` = totals, `forms` = how many). **One column per
  document**, not per copy; when `forms > 1` the header says "n forms — added together". Don't change the reader.
- 1099-INT / 1099-DIV / 1099-OID can come from different readers (`parse_1099`, `parse_1099int_rows`, `parse_box_rows`,
  `parse_box_list`) with different `detail` shapes. **Write one small translator per reader output → the form's row keys**
  (e.g. `int_1` and the INT-rows reader's box 1 both → row `b1`). Rows = the IRS box numbers and names of that form.
- 1099-G and 1099-K: `parse_document` has no reader for them today — their tabs list the documents with an "open the
  document" link and "not read by the program", no amounts. Same for 5498. Tell me in the report.

### 3. 1099-Comp, 1099-B, 1099-DA (one column per statement)
Reader: `parse_1099` → `_amounts_1099` (`detail` = the form fields + `b_st` / `b_lt` / `b_und`; `parts` = by 8949 box).
Sections in the column, each only when the statement has it:
- **1099-INT:** boxes 1, 3, 6, 8 (+ OID box 1 if read)
- **1099-DIV:** 1a, 1b, 2a, 3, 7, 12
- **1099-MISC:** 2, 3, 8
- **1099-B totals:** Short-term / Long-term / Term unknown — proceeds, cost, market discount, wash sale, gain
- **1099-B by Form 8949 box:** one row per box found (A, B, D, E …) — a repeatable group like W-2 box 12
- **§1256 (Form 6781):** box 11
No transaction lists. 1099-DA uses the same column.

### 4. Corrections → Income Summary
- A correction must give the same Summary as if the reader had read that value. **Get the document's result again by
  calling the existing result function** with the corrected values (`_amounts_1099`, `_r_result`, `m1098_result`-style …),
  never by recalculating the Summary amounts separately. For the composite that matters: DIV 2a also moves LT; §1256 splits
  60/40; 8949 box rows must still add up to the term total.
- `_amounts_1099` also uses the page text (which sections are printed): keep what it needs from the first read so the
  re-run gives the same notes / checks.
- If a form has no clean way to get its result again, make that tab **view-only** (no inputs, a short note "corrections
  not available yet") rather than guessing. List those in the report.
- `effective_docs()` keeps working for every form; Verify return / AI report / Excel use the corrected values as today.

### 5. Tests and same results
- No amount on the Summary changes unless a correction is typed: the answer-key check and the archive check give the same
  results as before.
- A test per new form definition on the samples that have that form (`tests\samples\Sample`: 1099-R, 1099-SA, 1098,
  composites / 1099-DIV / 1099-INT, Wealthfront, Fidelity, Morgan Stanley …): every value the Summary uses appears in the
  tab, and a typed correction gives the same Summary as the re-run reader.
- Forms with **no sample** (likely 1098-E, SSA-1099, 1095-A, 1099-NEC, 1099-MISC, 1099-OID, 1099-DA, 1099-G/K, 5498):
  build them from the reader's output shape, test with a made-up parsed result, and list them in BUILD_NOTES as
  "built, not tried on a real document".
- Lady tries the tabs in Chrome on the Sample case afterwards.
