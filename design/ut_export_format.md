# UT data entry export — the file format (the contract with UT Data Entry)

The browser app only **produces** this file. UT Data Entry is a separate app on Lady's computer: it reads the file, types the
`bot` rows into UltraTax Source Data Entry and skips the `hand` rows. The file is the only link between the two apps
(`APPS_ARCHITECTURE.md`, rule 3). A change here is agreed with Lady and built in both apps together.

The test `tests\test_ut_export_format.py` reads the two tables below and checks the export against them (column names and
order, Part II items, every rule in "Rules per column"). Change this file and the code together, or the test fails.

Today the export covers K-1s (1065) from the K-1 UT page ("Export for UT data entry"). Other forms come later (pending list:
generic export per form tab; consolidated statements split by form).

## File
- CSV, UTF-8, comma-separated, a header row, then one row per line of one form. Fields with commas are quoted (standard CSV).
- Only verified data: the corrected amount when there is one, else the amount on the document. A copy of the same form is
  exported once. Only K-1s marked Ready on the K-1 UT page are exported.

## Columns

| Column | Example | What it holds |
|---|---|---|
| `form` | 1065 | the form type: 1065 today (later 1120S / W2 / …) |
| `doc_id` | 3f9a1c0b2d4e5f60#2 | one form: the file's fingerprint (16 characters) `#` the page of that K-1 in its file — the bot groups lines by it |
| `payer_ein` | 12-3456789 | partnership / employer / payer EIN as printed |
| `payer_name` | DEMO PARTNERS LP | as printed |
| `recipient_id` | XXX-XX-1234 | partner / employee ID as printed (K-1 box E) |
| `box` | 20 | the box number, or a Part II item (table below) |
| `code` | A | the box code; blank for boxes without codes and for Part II items |
| `amount` | 63.00 | a box line: the amount with cents (UT Data Entry rounds), or `X` for a ticked check box. A Part II item: its value as text. `K1_…`: the ending amount with cents |
| `valid_in_ut` | Y | `Y` / `N` from the 1040's code list; blank for boxes without codes and for Part II items |
| `entry` | bot | `bot` = the bot types it; `hand` = typed by hand in UltraTax, the bot skips it. Blank when the `ut_entry` setting is off |
| `entry_reason` | Only 3 rows in Source Data Entry | why `hand`; blank for `bot` |
| `note` | see statement | free text, ignored by the bot (`from statement` / `added line` for lines added on the K-1 pages) |

## Part II items (K-1 1065)

Exported before the K-1's box lines, one row each, value as printed. An item not read is left out (`N` when every amount is 0).

| Item | Entry | `amount` example |
|---|---|---|
| `G` | hand | `Limited` / `General` |
| `H1` | hand | `Domestic` / `Foreign` |
| `J` | hand | `Profit 0.718528% -> 0.665511%; Loss …; Capital …` (beginning -> ending) |
| `K1_nonrecourse` | bot | `67.00` (ending; a 0 is left out) |
| `K1_qualified` | bot | `0.00` is never exported (a 0 is left out) |
| `K1_recourse` | bot | `12.50` |
| `L` | hand | `36588 -> 23164` (beginning -> ending) |
| `M` | hand | `Yes` / `No` |
| `N` | hand | `0 -> 691058` (beginning -> ending) |

## Rules per column (what the test checks)
1. The header row is exactly the column names above, in that order.
2. `form` is `1065`.
3. `doc_id` is 16 lowercase hex characters, `#`, a page number.
4. `box` is a box number (digits, sometimes with a letter, e.g. `9a`, `13`) or one of the Part II items above.
5. A Part II item row: `code` and `valid_in_ut` blank; `K1_…` rows have an amount with two decimals, not 0.
6. A box line: `amount` has two decimals (a minus sign for a loss) or is `X`; `valid_in_ut` is `Y` / `N` when the line has
   a code, blank when it doesn't.
7. `entry` is `bot`, `hand` or blank; `entry_reason` is filled for `hand` and blank for `bot`. The Part II items take the
   entry shown in the table above.
8. Every row of one `doc_id` has the same `payer_ein`, `payer_name` and `recipient_id`.
