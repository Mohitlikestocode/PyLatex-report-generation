# PyLaTeX Beam Report Generator — polished

This repository contains a small Python tool that reads point-load data from `data/forces.xlsx` and produces an engineering report (LaTeX source and — if a TeX engine is available — a compiled PDF). The report includes:

- Title page and Table of Contents
- Introduction and embedded beam schematic (in `assets/beam.png`)
- Recreated input force table as selectable LaTeX text (booktabs)
- Analysis: support reactions, Shear Force Diagram (SFD) and Bending Moment Diagram (BMD) plotted using TikZ/pgfplots
- Summary with key results (max shear and max moment locations)

Files
- `generate_report.py` — main script. Run to generate `output/report.tex` (and `output/report.pdf` if a TeX engine is found).
- `data/forces.xlsx` — input Excel file (sample provided).
- `assets/beam.png` — schematic image (auto-created if missing).
- `requirements.txt` — Python dependencies.
- `output/` — folder where `report.tex` (and PDF when compiled) are saved.

Quick start (Windows PowerShell)

```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
& .\.venv\Scripts\python.exe generate_report.py
```

Notes
- If a LaTeX engine (`latexmk`, `pdflatex`, `xelatex`, or `lualatex`) is on your PATH the script will attempt to compile `output/report.tex` to `output/report.pdf`. If not, the script writes `output/report.tex` for manual compilation.
- To compile manually (after installing MiKTeX or TeX Live):

```powershell
pdflatex -interaction=nonstopmode -output-directory output output\report.tex
```

Polish and design choices
- Tables use `booktabs` for a professional appearance.
- Plots are produced with `pgfplots` so they remain vector graphics and scale well in the PDF.
- A small summary section reports numerical maxima (useful for quick checks).

Submission tips
- The generated `output/report.tex` and `assets/beam.png` are ready to be included in a ZIP for submission.

If you'd like, I can:
- Produce the ZIP package containing all project files.
- Attempt to run a local compile here (requires installing a LaTeX distribution).
- Add unit tests or small CLI options (bonus points).
