# Brief 2026-11-24 — K-1s as documents (K-1 tabs in the Document inventory)

Written in Cowork with Lady, 2026-11-24. My intent, not a script: if something doesn't fit the code or there's a better
way, say so before building. **Order: after the Verify return plain conversion (conversion_plan step 4, part 1), before
Verify return's K-1 section.** Work step by step; stop and report after each step. `tests\run_tests.bat` passes after every
step. Decisions and results go to BUILD_NOTES.md; update `design\conversion_plan.md` (pages 6–8, intended differences) and
`design\k1_prep.md` (K-1 UT) to match.

## Decisions (Lady, 2026-11-24)
- **A K-1 is a document like any other:** read → its form tab (the only place its numbers change) → the Income Summary,
  automatically. No more "Add to Income Summary" step, no K-1 package that can go stale.
- **K-1 tabs in the Document inventory:** **K-1 1065** and **K-1 1120-S**, built on the form-tab machinery (8 K-1s per tab,
  `K-1 1065_2`, `_3` … + Total column; shown only when the client has one).
- **K-1 UT stays its own page — read-only for numbers.** It is the "ready for UltraTax" document: what the bot enters,
  what is typed by hand, what is still open. Notes, ticks, partner, UT #, bot / by hand stay editable there.
- **Two ticks, two meanings:** *Verified* (against the document) on top of each K-1 column in the tab; *checked for
  UltraTax* per line on K-1 UT.
- **The K-1 Interpreter (now "K-1 Verification") stays, information only:** its K-1 view, its totals page (the detailed
  income split — Lady wants to keep it) and its Excel summary all stay. **It feeds nothing** — no Add to Income Summary, no
  input that reaches the Summary or the export. Its numbers come from the K-1 tab.
- **The K-1s page goes away** (brief 2026-11-21): its job moves to the inventory.
- **1120-S:** tab with view + corrections now; **not** fed to the Income Summary yet (no routing rules) — the tab says so.

---

## Step 1 — K-1 tabs in the Document inventory
1. **One column per K-1** (a PDF with several K-1s → one column each: #13a, #13b …, each linking to its own page). Header:
   partnership name, EIN, document name + link (as the other tabs), SSN last 4.
2. **Rows, top to bottom:**
   - **Part II items:** G, H1, J (profit / loss / capital %), K (liabilities), L (capital account), M, N — correctable.
   - **Part III box lines** in box order, with their codes (11A, 13ZZ, 20Z …): a line shows when any K-1 on the tab has it
     (like W-2 box 12). Code descriptions from `k1_codes.py`.
   - **"See statement" lines** (STMT, no amount): description + orange "See statement" (as `k1_prep.md`); **+** adds a line
     under it (box, code dropdown pre-set to the printed code, amount); **STMT warning** "Missing amount — see statement"
     until a line is added. "+ Add line" at the bottom for a line the K-1 face doesn't show.
   - **Per-column rows for decisions that change the Summary:** duplicates ("same partnership, different amounts":
     Count / Don't count) and the **11 ZZ → Schedule E** tick.
3. **Verified tick on top of each column** (like Schedule E), not ticks on the left.
4. **Corrections** follow the form-tab rules: kept apart from what was read; the K-1's result is worked out again by the
   **existing** K-1 → Summary rules (`core\k1v\handoff.py` / `prep.py` — the code that built the package on Add),
   moved into one "boxes → Summary" function and called on every change. No second calculation.
5. **Buttons on the K-1 tab:** **K-1 UT** and **K-1 Verification** (the Interpreter) — both open in the K-1 browser tab
   already built (brief 2026-11-21, step 5).
6. **State K-1s** (e.g. the New York K-1 in K-1_Sample): stay in the inventory as documents, no column ("no federal K-1 read").

## Step 2 — Income Summary from the K-1 tab
- The Summary's K-1 section is filled from the K-1 tab's corrected K-1s, automatically (same rows and keys as the package
  today: EIN + line), on every change. The "Add to Income Summary" button and the "changed since added — add again" flag go.
- K-1 amounts on the Summary are **locked** like other tab amounts ("Change this in the K-1 1065 tab", link to the column).
- **Manual lines stay manual:** "minus losses carried over from prior years", "Add back disallowed losses" (passive /
  basis), and + lines.
- Same results: on Sample and K-1_Sample, the Summary after the switch = the Summary after Add today. Any difference: list
  it with the reason before going on.

## Step 3 — K-1 UT: read-only numbers
- **Read-only:** every amount (per document, corrected, statement lines), which lines exist, duplicates, 11 ZZ. A click on
  an amount: "Change this in the K-1 tab" + link to the K-1's column. A STMT line with no amount: "Missing amount — add the
  statement line in the K-1 tab".
- **Editable:** notes / comments, the per-line "checked for UltraTax" tick, partner (Taxpayer / Spouse), UT #, Entry
  (bot / by hand) override.
- Status banner as today: K-1s · ready · still to verify · problems · by hand. "Still to verify" counts K-1s not Verified in
  the tab and lines not checked for UltraTax.
- **Export for UT data entry** and **By-hand list** (Excel / PDF) unchanged — **the export format must not change**
  (`design\ut_export_format.md`, `tests\test_ut_export_format.py`; the CSV byte for byte the same on K-1_Sample).

## Step 4 — K-1 Verification (the Interpreter): information only
- Reads the K-1 tab's corrected values. Keeps: the K-1 view (incl. the "as tabs" view), the **totals page** (the detailed
  income split) and the **Excel summary**. A line at the top: "Information only — the Income Summary is the official total."
- Removes: Add to Income Summary, statement-amount inputs, 11 S / 11 ZZ ticks and corrections (they live in the K-1 tab).
  Partnership comments may stay (they feed nothing).

## Step 5 — Remove the K-1s page; carry over saved work
- Remove the K-1s page (home), its routes and the Summary's "Open K-1 Tab" / K-1 box buttons that only led there; the K-1
  box on the Summary becomes the K-1 section of the Summary. Adding K-1 PDFs = the inventory's "Add more documents…".
- **Saved work (older files):** statement amounts, ticks, comments, UT #, partner, corrections from the K-1 work file →
  carried into the K-1 tab / K-1 UT once, when opened. The old K-1 package is not used any more; if the new Summary's K-1
  totals differ from the old package's, flag it on the Summary (don't change silently).
- Tests: the K-1 tests (`test_k1prep`, `test_k1route`, `test_ut_entry`) follow the new path; the K-1 reader tests unchanged.
  Archive / answer-key differences from this change: list them as intended differences (dated 2026-11-24), don't
  refresh the reference to hide one.

## Later (not in this brief)
- Verify return's K-1 section, built on the K-1 tab.
- 1120-S → Income Summary routing rules.
