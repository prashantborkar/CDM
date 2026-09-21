import re, os

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.normpath(os.path.join(HERE, ".."))
text = "\n".join(open(os.path.join(HERE, f"e2e_part{i}.md"), encoding="utf-8").read() for i in (1, 2, 3))

lines = text.split("\n")
fr = {"P1": 0, "P2": 0, "P3": 0}
pri = {"M": 0, "S": 0, "C": 0}
ad = nfr = 0
defined = set()
problems = []
in_code = False
i = 0
while i < len(lines):
    ln = lines[i]
    if ln.startswith("```"):
        in_code = not in_code
    if not in_code and ln.startswith("|"):
        start = i
        block = []
        while i < len(lines) and lines[i].startswith("|"):
            block.append(lines[i])
            i += 1
        ncols = len(block[0].strip().strip("|").split("|"))
        for b in block:
            cells = [c.strip() for c in b.strip().strip("|").split("|")]
            if len(cells) != ncols:
                problems.append((start + 1, ncols, len(cells), b[:90]))
            if re.match(r"^(FR|AD|NFR)-[A-Z]+-\d+$", cells[0]):
                defined.add(cells[0])
                if cells[0].startswith("FR-") and len(cells) == 5:
                    fr[cells[3]] += 1
                    pri[cells[2]] += 1
                elif cells[0].startswith("AD-"):
                    ad += 1
                elif cells[0].startswith("NFR-"):
                    nfr += 1
        continue
    i += 1

frt = sum(fr.values())
counts = ("**Size of this specification.** %d functional requirements (P1: %d, P2: %d, P3: %d; Must %d, Should %d, Could %d), %d adapter requirements, "
          "%d non-functional requirements, 20 acceptance tests, 10 items to verify.\n\n" % (frt, fr["P1"], fr["P2"], fr["P3"], pri["M"], pri["S"], pri["C"], ad, nfr))
marker = "---\n\n## 1. Problem statement"
assert marker in text
text = text.replace(marker, counts + marker, 1)

refs = set(re.findall(r"\b(?:FR-[A-Z]+-\d{3}|AD-[A-Z]+-\d{2}|NFR-[A-Z]+-\d{2})\b", text))
missing = sorted(r for r in refs if r not in defined)
img = len(re.findall(r"!\[", text))

out = os.path.join(SPEC, "CDM_End_to_End_Specification.md")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(text)
print("wrote", out, len(text), "chars,", len(text.split("\n")), "lines")
print(counts)
print("table problems:", problems)
print("referenced but undefined:", missing)
print("images:", img)
# range references like FR-KEY-002 to FR-KEY-009 are covered by the check above
