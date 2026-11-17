// mupdf_bridge.mjs - MuPDF.js behind the browser version's PDF door (web/py/pymupdf_js.py calls these functions).
// Turns MuPDF.js output into what PyMuPDF gives the readers: same text, same words, same positions.
// The rules were proven page by page against PyMuPDF with tools/mupdfjs_test (2_read_mupdfjs.mjs is where they come from):
//   settings preserve-whitespace, preserve-ligatures, clip, use-cid-for-unknown-unicode;
//   positions on the page as stored (not turned), PyMuPDF's word rules including its quirks.
// Used by web/worker.js (browser) and tools/web_check (Node) - one copy.
export function makeBridge(mupdf) {
  const docs = new Map();
  let next = 1;
  const doc = id => { const d = docs.get(id); if (!d) throw new Error("PDF is closed"); return d; };
  const STEXT = "preserve-whitespace,preserve-ligatures,clip,use-cid-for-unknown-unicode";

  // the page as MuPDF.js shows it (turned when it has a rotation) -> the page as stored, top-left origin (PyMuPDF's)
  function geometry(page) {
    const [a, b, c, d, e, f] = page.getTransform ? page.getTransform() : [1, 0, 0, -1, 0, 0];
    const det = a * d - b * c;
    const toPdf = (x, y) => [(d * (x - e) - c * (y - f)) / det, (a * (y - f) - b * (x - e)) / det];
    const pb = page.getBounds();
    const k1 = toPdf(pb[0], pb[1]), k2 = toPdf(pb[2], pb[3]);
    const bx0 = Math.min(k1[0], k2[0]), by1 = Math.max(k1[1], k2[1]);
    const un = (x, y) => { const [u, v] = toPdf(x, y); return [u - bx0, by1 - v]; };
    return { un, shown: [pb[0], pb[1], pb[2], pb[3]], stored: [0, 0, Math.abs(k2[0] - k1[0]), Math.abs(k2[1] - k1[1])] };
  }

  // PyMuPDF's own rule for a character's box (its JM_char_quad): when the font's ascender - descender is less than 1, the
  // box is made exactly one font size high (same proportions); a font with no ascender gets 0.9 / -0.1; a box with no
  // width gets the character's advance. The font's ascender / descender are read back from the box MuPDF made with them
  // (box height = (ascender - descender) x the text's vertical scale; k = that scale / the font size, from fontScales).
  // quad = [ul.x, ul.y, ur.x, ur.y, ll.x, ll.y, lr.x, lr.y] on the page as shown; dir = the line's direction (cos, sin).
  const EPS = 1.1920929e-7;
  function charQuad(quad, origin, font, size, dir, ch, k) {
    if (!size) return quad;
    const c = dir[0], s = dir[1];
    const d1 = c === -1 ? 1 : c;                               // de-rotate: (c, -s, s, c); left-right flip keeps y
    const de = (x, y) => [(x - origin[0]) * c + (y - origin[1]) * s, -(x - origin[0]) * s + (y - origin[1]) * d1];
    const re = (x, y) => [x * c - y * s + origin[0], x * s + y * d1 + origin[1]];
    const ul = de(quad[0], quad[1]), ur = de(quad[2], quad[3]), ll = de(quad[4], quad[5]), lr = de(quad[6], quad[7]);
    const flip = c === 1 && ul[1] > 0;                         // up-down flip
    let asc = (flip ? ul[1] : -ul[1]) / size / k, dsc = (flip ? ll[1] : -ll[1]) / size / k;
    let ad = asc - dsc + EPS;
    if (ad >= 1 - 1e-4) return quad;                           // no problem (the scale is rounded: a little tolerance)
    if (asc < 1e-3) { dsc = -0.1; asc = 0.9; ad = 1.0; }       // probably a Tesseract glyphless font
    if (ad < 1) { dsc /= ad; asc /= ad; }
    ad = asc - dsc;
    asc = asc * size / ad;
    dsc = dsc * size / ad;
    ul[1] = ur[1] = flip ? asc : -asc;
    ll[1] = lr[1] = flip ? dsc : -dsc;
    if (ll[0] < 0) { ll[0] = 0; ul[0] = 0; }
    if (lr[0] - ll[0] < EPS && font) {
      const glyph = font.encodeCharacter(ch);
      if (glyph) { lr[0] = ll[0] + font.advanceGlyph(glyph, 0) * size; ur[0] = lr[0]; }
    }
    return [...re(ul[0], ul[1]), ...re(ur[0], ur[1]), ...re(ll[0], ll[1]), ...re(lr[0], lr[1])];
  }

  // PyMuPDF reads a turned page with the turn taken off (so lines and blocks are grouped as on the stored page), then
  // puts it back. Same here: fn(page as stored, size as shown [w, h]).
  function withPage(d, i, fn) {
    let obj = null, rot = 0;
    try {
      obj = d.findPage(i);
      const r = obj.getInheritable("Rotate");
      rot = r && r.isNumber() ? ((r.asNumber() % 360) + 360) % 360 : 0;
    } catch (e) { obj = null; }
    if (!obj || !rot) {
      const page = d.loadPage(i);
      try { const b = page.getBounds(); return fn(page, [b[2] - b[0], b[3] - b[1]]); } finally { page.destroy(); }
    }
    const own = obj.get("Rotate"), had = own && own.isNumber(), was = had ? own.asNumber() : 0;
    obj.put("Rotate", 0);
    try {
      const page = d.loadPage(i);
      try {
        const b = page.getBounds(), w = b[2] - b[0], h = b[3] - b[1];
        return fn(page, rot % 180 ? [h, w] : [w, h]);
      } finally { page.destroy(); }
    } finally {
      if (had) obj.put("Rotate", was); else obj.delete("Rotate");
    }
  }

  // Text can be stretched (wider or narrower than high): for each font + size on the page, its vertical scale / size.
  // MuPDF.js doesn't give a font's ascender / descender; with this scale they can be read back from a character's box.
  const fkey = (font, size) => (font ? font.pointer : 0) + "|" + Math.round(size * 50);
  function fontScales(page) {
    const m = new Map();
    const walk = (text, ctm) => text.walk({
      beginSpan(font, t) {
        const c = t[2] * ctm[0] + t[3] * ctm[2], d = t[2] * ctm[1] + t[3] * ctm[3];
        const a = t[0] * ctm[0] + t[1] * ctm[2], b = t[0] * ctm[1] + t[1] * ctm[3];
        const size = Math.sqrt(Math.abs(a * d - b * c));
        if (size > 0) m.set(fkey(font, size), Math.hypot(c, d) / size);
      },
    });
    const dev = new mupdf.Device({
      fillText(text, ctm) { walk(text, ctm); },
      strokeText(text, stroke, ctm) { walk(text, ctm); },
      clipText(text, ctm) { walk(text, ctm); },
      clipStrokeText(text, stroke, ctm) { walk(text, ctm); },
      ignoreText(text, ctm) { walk(text, ctm); },
    });
    page.run(dev, [1, 0, 0, 1, 0, 0]);
    try { dev.close(); } catch (e) { /* nothing to close */ }
    return m;
  }

  // every character of the page: blocks -> lines -> characters {c, code, b (box on the stored page), font, size}
  function read(page, g) {
    const st = page.toStructuredText(STEXT);
    const scales = fontScales(page);
    const blocks = [];
    let blk = null, cur = null, wmode = 0, dir = [1, 0];
    st.walk({
      beginTextBlock() { blk = []; blocks.push(blk); },
      beginLine(bbox, wm, d) {
        cur = []; wmode = wm; dir = d || [1, 0];
        const p = g.un(bbox[0], bbox[1]), q = g.un(bbox[2], bbox[3]);
        cur.box = [Math.min(p[0], q[0]), Math.min(p[1], q[1]), Math.max(p[0], q[0]), Math.max(p[1], q[1])];   // MuPDF's line box
        if (!blk) { blk = []; blocks.push(blk); }
      },
      onChar(c, origin, font, size, quad) {   // box = smallest rectangle around the 4 corners (also for turned text)
        const q = wmode ? quad : charQuad(quad, origin, font, size, dir, c, scales.get(fkey(font, size)) || 1);
        const pts = [g.un(q[0], q[1]), g.un(q[2], q[3]), g.un(q[4], q[5]), g.un(q[6], q[7])];
        const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
        const b = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
        if (wmode && b[3] < b[1] + size) b[1] = b[3] - size;
        cur.push({ c, code: c.codePointAt(0), b, font: font ? font.getName() : "", size });
      },
      endLine() { blk.push(cur); },
      endTextBlock() { blk = null; },
    });
    return blocks;
  }

  const NONE = [Infinity, Infinity, -Infinity, -Infinity];
  const empty = r => r[0] >= r[2] || r[1] >= r[3];
  const valid = r => r[0] <= r[2] && r[1] <= r[3];
  const union = (p, q) => !valid(q) ? p : !valid(p) ? q.slice()
    : [Math.min(p[0], q[0]), Math.min(p[1], q[1]), Math.max(p[2], q[2]), Math.max(p[3], q[3])];

  // plain text + words exactly like PyMuPDF's (rule by rule, including its quirks): split at codes <= 32, 160 and
  // 0x202A-0x202E; skip characters outside the page; a word whose box has no size is dropped, and its box carries over
  // into the next word of the same block (PyMuPDF only resets the box after a word and at a new block)
  function textAndWords(blocks, g) {
    const [px0, py0, px1, py1] = g.stored;
    const delim = k => k <= 32 || k === 160 || (k >= 0x202a && k <= 0x202e);
    const off = r => px0 >= r[2] || py0 >= r[3] || px1 <= r[0] || py1 <= r[1];
    let text = "";
    const words = [];
    let wb = NONE, t = "";
    blocks.forEach((lines, bn) => {
      let ln = 0;
      wb = NONE;                                               // (the carry-over stays inside one block)
      for (const line of lines) {
        text += line.map(o => o.c).join("") + "\n";
        let wn = 0;
        const emit = () => { words.push([wb[0], wb[1], wb[2], wb[3], t, bn, ln, wn]); wn++; wb = NONE; };
        t = "";
        for (const o of line) {
          if (off(o.b)) continue;
          if (!t && o.code === 0x200d) continue;
          if (delim(o.code)) {
            if (!t) continue;
            if (!empty(wb)) emit();
            t = "";
            continue;
          }
          t += o.c;
          wb = union(wb, o.b);
        }
        if (t && !empty(wb)) emit();
        ln++;
      }
    });
    return { text, words };
  }

  // PyMuPDF's get_text("blocks"): [x0, y0, x1, y1, text, block number]. Its rules: characters outside the page are left
  // out; a line ends with a new line only when its box has a size; a block with no box at all is left out.
  function asBlocks(blocks, g) {
    const [px0, py0, px1, py1] = g.stored;
    const off = r => px0 >= r[2] || py0 >= r[3] || px1 <= r[0] || py1 <= r[1];
    const out = [];
    blocks.forEach((lines, bn) => {
      let text = "", last = 0, br = NONE;
      for (const line of lines) {
        let lr = NONE;
        for (const o of line) {
          if (off(o.b)) continue;
          text += o.c;
          last = o.code;
          lr = union(lr, o.b);
        }
        if (last !== 10 && !empty(lr)) text += "\n";
        br = union(br, lr);
      }
      if (valid(br)) out.push([br[0], br[1], br[2], br[3], text, bn]);
    });
    return out;
  }

  // PyMuPDF's get_text("dict"), the part the readers use: blocks -> lines {bbox, spans: [{text, font, size, bbox}]}.
  // Its rules: a line whose own box doesn't reach the page (or the clip) is left out - so is a line with no width;
  // characters outside the page (or the clip) are left out.
  function asDict(blocks, g, clip) {
    const tp = clip || g.stored;
    const off = r => tp[0] >= r[2] || tp[1] >= r[3] || tp[2] <= r[0] || tp[3] <= r[1];
    const reach = r => Math.max(tp[0], r[0]) < Math.min(tp[2], r[2]) && Math.max(tp[1], r[1]) < Math.min(tp[3], r[3]);
    const out = [];
    for (const lines of blocks) {
      const ls = [];
      let bb = NONE;
      for (const line of lines) {
        if (!reach(line.box)) continue;
        const spans = [];
        let sp = null, lb = NONE;
        for (const o of line) {
          if (off(o.b) || (o.code < 32 && empty(o.b))) continue;   // (a control character with no width is not in PyMuPDF's "dict")
          if (!sp || sp.font !== o.font || sp.size !== o.size) { sp = { text: "", font: o.font, size: o.size, bbox: NONE }; spans.push(sp); }
          sp.text += o.c;
          sp.bbox = union(sp.bbox, o.b);
          lb = union(lb, o.b);
        }
        ls.push({ bbox: valid(lb) ? lb : line.box, spans });
        bb = union(bb, lb);
      }
      out.push({ type: 0, bbox: valid(bb) ? bb : [0, 0, 0, 0], lines: ls });
    }
    return out;
  }

  const rgb = (cs, color) => {
    const n = color.length;
    if (n === 1) return [color[0], color[0], color[0]];
    if (n === 4) return [0, 1, 2].map(i => 1 - Math.min(1, color[i] + color[3]));      // CMYK the way MuPDF converts it
    return [color[0], color[1], color[2]];
  };

  return {
    // bytes of a PDF -> a number for the open document; no bytes -> a new, empty PDF
    open(bytes) {
      const d = bytes ? mupdf.Document.openDocument(bytes, "application/pdf") : new mupdf.PDFDocument();
      docs.set(next, d);
      return next++;
    },
    close(id) { const d = docs.get(id); docs.delete(id); try { d && d.destroy(); } catch (e) { /* already gone */ } },
    needsPass(id) { return !!doc(id).needsPassword(); },
    authenticate(id, pw) { return doc(id).authenticatePassword(pw) ? 1 : 0; },
    pageCount(id) { return doc(id).countPages(); },
    meta(id, key) { try { return doc(id).getMetaData(key) || ""; } catch (e) { return ""; } },
    // one page: its size as shown, plain text and words ({w, h, text, words}) as JSON
    page(id, i) {
      return withPage(doc(id), i, (page, shown) => {
        const g = geometry(page);
        const r = textAndWords(read(page, g), g);
        r.w = shown[0];
        r.h = shown[1];
        return JSON.stringify(r);
      });
    },
    // get_text("dict") blocks as JSON; clip = [x0, y0, x1, y1] or null
    dict(id, i, clip) {
      return withPage(doc(id), i, page => {
        const g = geometry(page);
        return JSON.stringify(asDict(read(page, g), g, clip ? Array.from(clip) : null));
      });
    },
    // get_text("blocks") as JSON: [[x0, y0, x1, y1, text, block number], ...]
    blocks(id, i) {
      return withPage(doc(id), i, page => {
        const g = geometry(page);
        return JSON.stringify(asBlocks(read(page, g), g));
      });
    },
    // get_drawings(), the part the readers use: every filled shape's colour (RGB) and rectangle, as JSON
    drawings(id, i) {
      return withPage(doc(id), i, page => {
        const g = geometry(page);
        const out = [];
        const dev = new mupdf.Device({
          fillPath(path, evenOdd, ctm, cs, color) {
            let r = NONE;
            const at = (x, y) => {
              const [u, v] = g.un(ctm[0] * x + ctm[2] * y + ctm[4], ctm[1] * x + ctm[3] * y + ctm[5]);
              r = union(r, [u, v, u, v]);
            };
            path.walk({ moveTo: at, lineTo: at, curveTo(a, b, c, d, e, f) { at(a, b); at(c, d); at(e, f); } });
            if (valid(r)) out.push({ fill: rgb(cs, color), rect: r });
          },
        });
        page.run(dev, [1, 0, 0, 1, 0, 0]);
        try { dev.close(); } catch (e) { /* nothing to close */ }
        return JSON.stringify(out);
      });
    },
    // pages from..to of another open PDF, added at the end (splitting a brokerage package by account)
    insertPages(id, srcId, from, to) {
      const d = doc(id), s = doc(srcId);
      for (let i = from; i <= to; i++) d.graftPage(-1, s, i);
    },
    select(id, pages) { doc(id).rearrangePages(Array.from(pages)); },
    save(id, options) { return doc(id).saveToBuffer(options || "").asUint8Array().slice(); },
  };
}
