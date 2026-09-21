import re, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.normpath(os.path.join(HERE, ".."))
text = "\n".join(open(os.path.join(HERE, f"pre_part{i}.md"), encoding="utf-8").read() for i in (1, 2))
text = text.replace("(specification item V8)", "(specification chapter 10)")

lines = text.split("\n")
ids = []
stage = collections.Counter()
per_step = collections.Counter()
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
                problems.append((start + 1, ncols, len(cells), b[:80]))
            if re.match(r"^PRE-[A-Z]+-\d+$", cells[0]):
                ids.append(cells[0])
                st = cells[4] if len(cells) == 7 else cells[5]
                stage[st] += 1
                per_step[cells[0].split("-")[1]] += 1
        continue
    i += 1

dups = [k for k, v in collections.Counter(ids).items() if v > 1]
defined = set(ids)

# expand ranges "PRE-XX-04 to PRE-XX-08" and check singles
referenced = set()
for m in re.finditer(r"(PRE-([A-Z]+)-(\d+)) to (PRE-([A-Z]+)-(\d+))", text):
    a, b = int(m.group(3)), int(m.group(6))
    for n in range(a, b + 1):
        referenced.add("PRE-%s-%02d" % (m.group(2), n))
for m in re.finditer(r"PRE-[A-Z]+-\d+", text):
    referenced.add(m.group(0))
missing = sorted(r for r in referenced if r not in defined)

tot = len(ids)
totals = ("**Size:** %d prerequisites in total: %d needed for the proof of concept only, %d needed for production only, %d needed for both. "
          "By step: GOV %d, SN %d, SG %d, CA %d, MID %d, NET %d, WIN %d, LNX %d, JVA %d, LAB %d, PIL %d, SCR %d."
          % (tot, stage["POC"], stage["PROD"], stage["both"], per_step["GOV"], per_step["SN"], per_step["SG"], per_step["CA"], per_step["MID"],
             per_step["NET"], per_step["WIN"], per_step["LNX"], per_step["JVA"], per_step["LAB"], per_step["PIL"], per_step["SCR"]))
assert "{{TOTALS}}" in text
text = text.replace("{{TOTALS}}", totals)

out = os.path.join(SPEC, "CDM_Prerequisites_and_Readiness.md")
with open(out, "w", encoding="utf-8") as fh:
    fh.write(text)
print("wrote", out, len(text), "chars,", len(text.split("\n")), "lines")
print(totals)
print("table problems:", problems)
print("duplicate ids:", dups)
print("referenced but undefined:", missing)
print("images:", len(re.findall(r"!\[", text)))
