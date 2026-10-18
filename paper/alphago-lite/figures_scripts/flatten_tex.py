"""Make the single-file source AAAI requires: inline every \\input{...} and replace
\\bibliography{...} with the compiled main.bbl. Writes <venue>/submission/main.tex plus the
figure PDFs it uses.

    python flatten_tex.py ../aaai27      (compile the paper first so main.bbl exists)
"""
import re
import shutil
import sys
from pathlib import Path

venue = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "aaai27").resolve()


def inline(path):
    text = path.read_text()

    def repl(m):
        name = m.group(1)
        target = venue / (name if name.endswith(".tex") else name + ".tex")
        return inline(target).rstrip("\n")

    # skip commented-out lines; inline \input{...} everywhere else
    lines = []
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("%"):
            lines.append(line)
        else:
            lines.append(re.sub(r"\\input\{([^}]+)\}", repl, line))
    return "".join(lines)


flat = inline(venue / "main.tex")
bbl = (venue / "main.bbl").read_text()
flat = re.sub(r"\\bibliography\{[^}]+\}", lambda _: bbl.rstrip("\n"), flat)
out = venue / "submission"
if out.exists():
    shutil.rmtree(out)
(out / "figures").mkdir(parents=True)
(out / "main.tex").write_text(flat)
for pdf in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", flat):
    shutil.copy(venue / pdf, out / pdf)
for f in ("aaai2027.sty", "aaai2027.bst"):
    shutil.copy(venue / "template" / f, out / f)
print(f"wrote {out / 'main.tex'} ({len(flat.splitlines())} lines)")
