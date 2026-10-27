"""Build every diagram and plot in figures/ as its own PDF, in docs/diagrams/.

    python make-diagrams.py [--tectonic PATH]

Each figure file is wrapped in a standalone LaTeX page with figure-style.tex, so
the PDF is cropped to the drawing and keeps it sharp at any size. A file named
figNN-<name>.tex or plotNN-<name>.tex becomes orbibot-v1-<name>.pdf. PNG copies
for web pages are made from these PDFs separately (see docs/diagrams/README.md).
"""
import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "diagrams"

WRAPPER = r"""\documentclass[border=10pt]{standalone}
\input{figure-style}
\setlength{\textwidth}{16cm}
\begin{document}
\input{figures/%s}
\end{document}
"""


def main():
    parser = argparse.ArgumentParser(description="Build each figure as its own cropped PDF.")
    parser.add_argument("--tectonic", default=shutil.which("tectonic") or str(Path.home() / "tools/tectonic/tectonic.exe"))
    args = parser.parse_args()

    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copy(HERE / "figure-style.tex", tmp)
        shutil.copytree(HERE / "figures", tmp / "figures")
        for figure in sorted((HERE / "figures").glob("*.tex")):
            name = re.sub(r"^(fig|plot)\d+-", "", figure.stem)
            source = tmp / f"orbibot-v1-{name}.tex"
            source.write_text(WRAPPER % figure.stem, encoding="utf-8")
            subprocess.run([args.tectonic, "-X", "compile", "--outdir", str(OUT), str(source)],
                           check=True, capture_output=True)
            print("made", f"orbibot-v1-{name}.pdf")


if __name__ == "__main__":
    main()
