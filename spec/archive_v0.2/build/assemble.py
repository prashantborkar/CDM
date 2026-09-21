import re, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.normpath(os.path.join(HERE, ".."))
parts = [open(os.path.join(HERE, f"md_part{i}.md"), encoding="utf-8").read() for i in (1, 2, 3)]
text = "\n".join(parts)

lines = text.split("\n")
fr = {"P1": 0, "P2": 0, "P3": 0}
pri = {"M": 0, "S": 0, "C": 0}
counts = {"AD": 0, "NFR": 0, "PRD": 0}
defined = set()
in_code = False
problems = []
i = 0
while i < len(lines):
    ln = lines[i]
    if ln.startswith("```"):
        in_code = not in_code
    if not in_code and ln.startswith("|"):
        # a table block
        start = i
        block = []
        while i < len(lines) and lines[i].startswith("|"):
            block.append(lines[i])
            i += 1
        ncols = len(block[0].strip().strip("|").split("|"))
        for b in block:
            n = len(b.strip().strip("|").split("|"))
            if n != ncols:
                problems.append((start + 1, ncols, n, b[:80]))
            cells = [c.strip() for c in b.strip().strip("|").split("|")]
            m = re.match(r"^(FR|AD|NFR|PRD)-[A-Z0-9]+-?\d*", cells[0])
            if m:
                defined.add(cells[0])
                if cells[0].startswith("FR-") and len(cells) == 5:
                    fr[cells[3]] += 1
                    pri[cells[2]] += 1
                elif cells[0].startswith("AD-"):
                    counts["AD"] += 1
                elif cells[0].startswith("NFR-"):
                    counts["NFR"] += 1
                elif cells[0].startswith("PRD-") and len(cells) == 5:
                    counts["PRD"] += 1
        continue
    i += 1

frt = sum(fr.values())
summary = ("%d functional requirements (P1 MVP: %d, P2: %d, P3: %d; Must: %d, Should: %d, Could: %d), %d platform adapter requirements, "
           "%d non-functional requirements, %d product and commercial requirements, 16 open questions with defaults, 20 acceptance tests."
           % (frt, fr["P1"], fr["P2"], fr["P3"], pri["M"], pri["S"], pri["C"], counts["AD"], counts["NFR"], counts["PRD"]))
text = text.replace("{{COUNTS}}", summary)

# ID references that are not defined
refs = set(re.findall(r"\b(?:FR-[A-Z]+-\d{3}|AD-[A-Z0-9]+-\d{2}|NFR-[A-Z]+-\d{2}|PRD-\d{3})\b", text))
missing = sorted(r for r in refs if r not in defined)

out = os.path.join(SPEC, "CDM_Product_Specification.md")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(text)
print("wrote", out, len(text), "chars,", len(text.split("\n")), "lines")
print(summary)
print("table problems:", problems)
print("referenced but undefined IDs:", missing)
