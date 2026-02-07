@echo off
REM Compile LaTeX to PDF using pdflatex (run twice for references)
if not exist output mkdir output
pdflatex -interaction=nonstopmode -output-directory output output\report.tex
pdflatex -interaction=nonstopmode -output-directory output output\report.tex
if exist output\report.pdf (
  echo PDF generated: output\report.pdf
  exit /b 0
) else (
  echo Failed to generate PDF. Ensure MiKTeX or TeX Live is installed and pdflatex is on PATH.
  exit /b 1
)
