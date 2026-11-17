// probe.js - the stuck-PDF guard (the desktop app's safe_pdf.py, in the browser).
// A small worker of its own that only opens a PDF and reads the text of every page, with MuPDF.js - the same PDF engine
// Run check uses. If a file makes the engine hang, the page stops this worker after the time limit (Worker.terminate) and
// names the file and the page it was on; Run check then leaves the file out instead of freezing.
//   page -> probe:  {bytes, passwords: [...]}
//   probe -> page:  {at: "open" | "page 7"} while working (so a hang can be placed), then {done: true, pages} or {error}
const mupdf = await import("./vendor/mupdf/mupdf.js");

onmessage = e => {
  const { bytes, passwords } = e.data;
  try {
    postMessage({ at: "open" });
    const doc = mupdf.Document.openDocument(bytes, "application/pdf");
    if (doc.needsPassword() && !(passwords || []).some(pw => doc.authenticatePassword(pw))) {
      postMessage({ done: true, pages: 0, password: true });     // can't open it: Run check says so itself
      return;
    }
    const n = doc.countPages();
    for (let i = 0; i < n; i++) {
      postMessage({ at: `page ${i + 1}` });
      const page = doc.loadPage(i);
      page.toStructuredText("preserve-whitespace").asText();
      page.destroy();
    }
    doc.destroy();
    postMessage({ done: true, pages: n });
  } catch (err) {
    postMessage({ error: String(err && err.message || err) });   // a broken file: Run check reports it, not the guard
  }
};
postMessage({ ready: true });
