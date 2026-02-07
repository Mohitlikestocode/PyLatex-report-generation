#!/usr/bin/env pwsh
# Compile report.tex using available LaTeX compiler. Use this in PowerShell.
$compilers = @("latexmk","pdflatex","xelatex","lualatex")
$found = $null
foreach ($c in $compilers) {
  if (Get-Command $c -ErrorAction SilentlyContinue) { $found = $c; break }
}
if (-not $found) { Write-Error "No LaTeX compiler found. Install MiKTeX or TeX Live and ensure pdflatex on PATH."; exit 1 }
if ($found -eq "latexmk") {
  latexmk -pdf -silent -outdir=output output\report.tex
} else {
  & $found -interaction=nonstopmode -output-directory output output\report.tex
  & $found -interaction=nonstopmode -output-directory output output\report.tex
}
if (Test-Path output\report.pdf) { Write-Host "PDF generated: output\report.pdf"; exit 0 } else { Write-Error "PDF not generated." ; exit 1 }
