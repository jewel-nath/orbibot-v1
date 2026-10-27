# Technical report

**OrbiBot V1: A Mecanum Mobile Robot with Microcontroller-Level Real-Time
Control, a ROS 2 Navigation Stack, and a Tool-Using LLM Agent — Design and
Bench Evaluation.** Version 1.0, October 2026.

[Read the PDF](orbibot-v1-report.pdf) (19 pages, one column).

It describes the hardware, the firmware, the ROS 2 software, the web
dashboard and the AI agent, and reports the bench tests made with the wheels
off the ground. A "Results at a glance" box near the start says what was
measured and what wasn't. Every number comes from [docs/status.md](../status.md)
and the [firmware test report](../../src/orbibot_rosmaster_firmware/test-report.md).

Every diagram is also in [docs/diagrams/](../diagrams/README.md) as its own
PDF and PNG, for reuse.

## Files

| Path | What it is |
|---|---|
| `orbibot-v1-report.tex` | The report |
| `style.tex` | The page layout: one column, 11 pt, coloured headings and summary boxes |
| `figure-style.tex` | Fonts, the colour palette and the TikZ styles every figure shares |
| `references.bib` | The references; every DOI was checked at doi.org |
| `figures/` | One file per diagram (`figNN-*.tex`, TikZ) or plot (`plotNN-*.tex`, pgfplots, with the measured data in the file) |
| `make-diagrams.py` | Builds each figure as its own cropped PDF in `docs/diagrams/` |
| `orbibot-v1-report.pdf` | The built report |

The photos come from [docs/media/](../media/).

## Build it

With [Tectonic](https://tectonic-typesetting.github.io), which fetches the
LaTeX packages and the TeX Gyre fonts it needs on the first run:

```bash
cd docs/report
tectonic -X compile orbibot-v1-report.tex
python make-diagrams.py
```

The style uses `fontspec`, so another TeX distribution needs XeLaTeX or
LuaLaTeX (`latexmk -xelatex orbibot-v1-report.tex`).
