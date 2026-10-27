# Technical report

**OrbiBot V1: A Mecanum Mobile Robot with Microcontroller-Level Real-Time
Control, a ROS 2 Navigation Stack, and a Tool-Using LLM Agent — Design and
Bench Evaluation.** Version 1.0, October 2026.

[Read the PDF](orbibot-v1-report.pdf) (9 pages).

It describes the hardware, the firmware, the ROS 2 software, the web
dashboard and the AI agent, and reports the bench tests made with the wheels
off the ground. Every number in it comes from [docs/status.md](../status.md)
and the [firmware test report](../../src/orbibot_rosmaster_firmware/test-report.md).
Floor tests (drift, Nav2 success rate, the agent's task success) come in the
next version.

## Files

| Path | What it is |
|---|---|
| `orbibot-v1-report.tex` | The report (IEEEtran) |
| `style.tex` | Packages, the colour palette and the TikZ styles every figure shares |
| `references.bib` | The references; every DOI was checked at doi.org |
| `figures/` | One file per diagram (`figNN-*.tex`, TikZ) or plot (`plotNN-*.tex`, pgfplots, with the measured data in the file) |
| `orbibot-v1-report.pdf` | The built report |

The photos come from [docs/media/](../media/).

## Build it

With [Tectonic](https://tectonic-typesetting.github.io), which fetches the
LaTeX packages it needs on the first run:

```bash
cd docs/report
tectonic -X compile orbibot-v1-report.tex
```

Any TeX distribution with `IEEEtran`, TikZ and pgfplots works too
(`latexmk -pdf orbibot-v1-report.tex`).
