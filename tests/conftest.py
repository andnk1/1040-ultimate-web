"""Shows how much of each answer key is checked (initials in the Checked column) at the end of run_tests.bat."""
import harness as h


def pytest_terminal_summary(terminalreporter):
    tr = terminalreporter
    tr.section("Answer keys")
    for c in h.case_dirs():
        p = c / h.KEY_NAME
        if not p.exists():
            tr.write_line(f"{c.name}: no answer key")
            continue
        key = h.load_key(p)
        rows = [x for s, _ in h.SHEETS for x in key[s]]
        done = sum(1 for x in rows if x["checked"])
        tr.write_line(f"{c.name}: {done} of {len(rows)} rows checked" + ("" if done == len(rows) else " (draft — not all checked)"))
