# Brief — 2026-11-17 (Lady): page links — where they go

The test from `design\brief_2026-11-17.md` item 3 worked: the same tab is reused and it jumps to the page. But the links
were put in the wrong place. This brief says how I want it, and it's a go to build.

## What's wrong now
The test links (`p.3 p.1`) sit next to each document on the **Document inventory**. That's not what I meant.

## What I want

**Document inventory: no page links.**
- Remove the `p.N` links from the inventory.
- The document's name stays a link that opens the whole document (page 1), as before.
- Keep the same-tab behaviour: a document that's already open isn't opened again. The tab comes to the front.

**Income and Deduction Summary: every document name is a link to its page.**
- Each document name in the summary's rows becomes a link.
- Clicking it opens the source PDF **at the page where that row's amount was read**.
- If the PDF is already open in a tab, the same tab jumps to that page. No second copy, same as in the test.
- So two rows from the same composite (e.g. DIV on page 3, INT on page 1) both use one tab, each jumping to its own page.

## What this needs
- **The parsers must keep the page number** with the amounts they read (they already read page by page and currently
  drop it). It goes with the amounts into the run and the work in progress, so it's still there after reopening.
- Order: W-2, 1099-R and the other single forms first. Then the 1099 composites, where the page where each section (DIV,
  INT, B summary, …) starts is enough. Then K-1s (the page where that partnership's K-1 starts).
- **Rows with no page** (typed-in amounts, AI amounts, Schedule C / E from spreadsheets, non-PDF files): the name still
  opens the document as now, at page 1 for a PDF or with the Drive link for other files. No error, no page number shown.
- Keep the parser changes readable (comments say what the page is for), and the results must stay the same as the archive
  on the sample clients. Only the page is new, and the amounts must not change.

Add the decision to BUILD_NOTES.md when done.
