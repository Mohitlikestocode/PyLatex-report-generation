import os
import sys
import logging
from pathlib import Path
import numpy as np
import shutil
import subprocess
import pandas as pd
from PIL import Image, ImageDraw
from pylatex import Document, Section, Subsection, Command, Figure, NoEscape, Tabular, NewPage
from pylatex.errors import CompilerError

# configure simple logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# Simple automation: read point loads from Excel and produce a LaTeX PDF report
# Assumptions:
# - Excel file at data/forces.xlsx with two columns: position (m) and magnitude (N)
#   If column names differ, the script will try to infer them.
# - Beam is simply supported at x=0 and x=L (L either provided or computed)
# - All loads are vertical point loads (positive downward)


def ensure_dirs():
    Path("output").mkdir(parents=True, exist_ok=True)


def read_forces(excel_path="data/forces.xlsx"):
    # Read Excel and try to detect position and magnitude columns.
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        raise FileNotFoundError(f"Could not read Excel file at '{excel_path}': {e}")
    cols = [c.lower() for c in df.columns]
    # heuristics
    pos_candidates = [c for c in cols if any(k in c for k in ("pos", "x", "dist", "location", "a"))]
    mag_candidates = [c for c in cols if any(k in c for k in ("load", "force", "p", "w", "magnitude"))]
    if pos_candidates and mag_candidates:
        pos_col = df.columns[cols.index(pos_candidates[0])]
        mag_col = df.columns[cols.index(mag_candidates[0])]
    else:
        # fallback to first two columns
        pos_col = df.columns[0]
        mag_col = df.columns[1]
    forces = df[[pos_col, mag_col]].copy()
    forces.columns = ["pos", "mag"]
    # ensure numeric
    forces = forces.dropna()
    try:
        forces["pos"] = forces["pos"].astype(float)
        forces["mag"] = forces["mag"].astype(float)
    except Exception:
        raise ValueError("Position and magnitude columns must be numeric.")
    # convention: positive downward loads (keeps signs consistent)
    return forces.sort_values("pos").reset_index(drop=True)


def validate_forces(forces: pd.DataFrame):
    if forces.empty:
        raise ValueError("No force data found in the Excel file.")
    if (forces["pos"] < 0).any():
        raise ValueError("All positions must be non-negative.")
    if (forces["mag"].isnull()).any():
        raise ValueError("Some load magnitudes are missing.")


def compute_reactions(forces: pd.DataFrame, L: float):
    # Reaction forces at supports A(0) and B(L)
    total_load = forces["mag"].sum()
    # Sum moments about A to get RB
    moment_about_A = (forces["mag"] * forces["pos"]).sum()
    RB = moment_about_A / L
    RA = total_load - RB
    return float(RA), float(RB)


def sample_sfd_bmd(forces: pd.DataFrame, L: float, RA: float, num=201):
    # Sample along beam length and compute shear and moment
    x = np.linspace(0, L, num=num)
    shear = np.zeros_like(x)
    moment = np.zeros_like(x)
    for i, xi in enumerate(x):
        # start with reaction at A
        V = RA
        M = RA * xi
        # subtract contributions from point loads located at <= xi
        for _, row in forces.iterrows():
            a = row["pos"]
            P = row["mag"]
            if a <= xi + 1e-12:
                V -= P
                M -= P * (xi - a)
        shear[i] = V
        moment[i] = M
    return x, shear, moment


def pgfplots_coordinates(x, y):
    # Format coordinates for pgfplots: (x,y) pairs
    pairs = [f"({float(xi):.3f},{float(yi):.3f})" for xi, yi in zip(x, y)]
    # return newline-separated coordinate pairs (safe to embed in pgfplots)
    return "\n            ".join(pairs)


def make_document(forces: pd.DataFrame, L: float, RA: float, RB: float, x, shear, moment):
    geometry_options = {"margin": "1in"}
    doc = Document("report", geometry_options=geometry_options)
    # ensure LaTeX can find images when compiling from output/ by adding
    # a graphicspath that points to the assets folder one level up
    doc.preamble.append(NoEscape(r"\graphicspath{{../assets/}}"))
    # Packages for tikz/pgfplots and nicer tables
    doc.packages.append(NoEscape("\\usepackage{tikz}"))
    doc.packages.append(NoEscape("\\usepackage{pgfplots}"))
    doc.packages.append(NoEscape("\\pgfplotsset{compat=1.18}"))
    doc.packages.append(NoEscape("\\usepackage{booktabs}"))
    doc.packages.append(NoEscape("\\usepackage{caption}"))
    doc.packages.append(NoEscape("\\usepackage{siunitx}"))

    doc.preamble.append(Command("title", "Simply Supported Beam Analysis Report"))
    doc.preamble.append(Command("author", "Automated PyLaTeX Generator"))
    doc.preamble.append(Command("date", NoEscape("\\today")))

    doc.append(NoEscape("\\maketitle"))
    doc.append(NoEscape("\\tableofcontents\\newpage"))

    with doc.create(Section("Introduction")):
        doc.append("This report presents a simple structural analysis of a simply supported beam subjected to point loads. The reactions, shear force diagram (SFD), and bending moment diagram (BMD) are computed and plotted using pgfplots.")

    with doc.create(Section("Beam Description")):
        doc.append("Beam supports: simple supports at x=0 and x=L. Units are consistent (e.g., meters and Newtons).")
        img_path = Path("assets/beam.png")
        # ensure assets dir exists (do not auto-generate a placeholder image)
        img_path.parent.mkdir(parents=True, exist_ok=True)
        if img_path.exists():
            with doc.create(Figure(position="h!")) as fig:
                # include only the filename; LaTeX will search ../assets/ via graphicspath
                fig.add_image("beam.png", width=NoEscape("0.8\\textwidth"))
                fig.add_caption("Simply supported beam schematic")
        else:
            # Informative inline note when the image is missing; do not create a dummy image
            doc.append(NoEscape("\\textit{Beam image not found at assets/beam.png - please add the schematic to include it in the report.}"))

    with doc.create(Section("Data Source")):
        doc.append("Input data read from the Excel file data/forces.xlsx. The following table reproduces the input data used for analysis.")

    with doc.create(Section("Input Data")):
        # create a LaTeX table from the dataframe using booktabs
        # place the table inline (non-floating) so it appears immediately after the heading
        doc.append(NoEscape("\\captionof{table}{Point loads read from Excel (position in m, load in N)}"))
        with doc.create(Tabular("lr")) as table:
            table.append(NoEscape("\\toprule"))
            table.add_row((NoEscape("\\textbf{Position (m)}"), NoEscape("\\textbf{Load (N)}")))
            table.append(NoEscape("\\midrule"))
            for _, row in forces.iterrows():
                table.add_row((f"{row['pos']:.3f}", f"{row['mag']:.3f}"))
            table.append(NoEscape("\\bottomrule"))

    with doc.create(Section("Analysis")):
        with doc.create(Subsection("Support Reactions")):
            # present reactions using math formatting
            doc.append(NoEscape(rf"Reaction at A (x=0): $R_A = {RA:.3f}\ \mathrm{{N}}$\\"))
            doc.append(NoEscape(rf"Reaction at B (x=L): $R_B = {RB:.3f}\ \mathrm{{N}}$\\"))

        with doc.create(Subsection("Shear Force Diagram (SFD)")):
            # generate pgfplots code for shear
            coords_sfd = pgfplots_coordinates(x, shear)
            tikz_sfd = NoEscape(r"""
\begin{tikzpicture}
  \begin{axis}[
    width=0.9\textwidth,
    height=6cm,
    xlabel={x (m)},
    ylabel={Shear (N)},
    grid=both,
    axis lines=middle,
  ]
    \addplot+[no markers, thick] coordinates {
            %s
    };
    \addlegendentry{Shear}
  \end{axis}
\end{tikzpicture}
""" % coords_sfd)
            doc.append(tikz_sfd)

        with doc.create(Subsection("Bending Moment Diagram (BMD)")):
            coords_bmd = pgfplots_coordinates(x, moment)
            tikz_bmd = NoEscape(r"""
\begin{tikzpicture}
    \begin{axis}[
        width=0.9\textwidth,
        height=6cm,
        xlabel={x (m)},
        ylabel={Moment (N\,m)},
        grid=both,
        axis lines=middle,
        legend style={at={(1.02,1)},anchor=north west},
    ]
    \addplot+[no markers, thick, color=red] coordinates {
            %s
    };
    \addlegendentry{Moment}
  \end{axis}
\end{tikzpicture}
""" % coords_bmd)
            doc.append(tikz_bmd)

        # Summary: key values and brief explanations
        with doc.create(Subsection("Summary")):
            # compute extrema
            max_shear_idx = int(np.argmax(np.abs(shear)))
            max_shear_val = float(shear[max_shear_idx])
            max_shear_x = float(x[max_shear_idx])
            max_moment_idx = int(np.argmax(np.abs(moment)))
            max_moment_val = float(moment[max_moment_idx])
            max_moment_x = float(x[max_moment_idx])
            doc.append(NoEscape("Key results:"))
            doc.append(NoEscape(rf"Maximum shear: {max_shear_val:.3f} N at x = {max_shear_x:.3f} m\\"))
            doc.append(NoEscape(rf"Maximum moment: {max_moment_val:.3f} N\,m at x = {max_moment_x:.3f} m\\"))
            # Clear, engineering-focused narration (no equations)
            doc.append("\n")
            doc.append("A Shear Force Diagram (SFD) represents the internal shear force distribution along the beam as a function of position. It shows how shear changes where loads are applied and at supports; abrupt jumps correspond to point loads or reactions.")
            doc.append("\n\n")
            doc.append("A Bending Moment Diagram (BMD) represents the internal bending moment distribution along the beam. It indicates where the beam experiences the largest bending effects; these locations are critical for section design and checks.")

    return doc


def find_latex_compiler():
    # Prefer latexmk, fall back to pdflatex
    for c in ("latexmk", "pdflatex", "xelatex", "lualatex"):
        if shutil.which(c):
            return c
    return None


def main():
    ensure_dirs()
    excel_path = "data/forces.xlsx"
    if not Path(excel_path).exists():
        logging.error("Expected input Excel at %s", excel_path)
        raise FileNotFoundError(f"Expected input Excel at {excel_path}")

    forces = read_forces(excel_path)
    try:
        validate_forces(forces)
    except Exception as e:
        logging.error("Invalid force data: %s", e)
        raise
    # Beam length: use max position or a fixed value if user provides none.
    L = max(forces["pos"].max() * 1.2, forces["pos"].max() + 1.0) if not forces.empty else 10.0
    # simple choice: set L as either last load position plus margin
    L = float(L)

    RA, RB = compute_reactions(forces, L)
    x, shear, moment = sample_sfd_bmd(forces, L, RA, num=401)

    doc = make_document(forces, L, RA, RB, x, shear, moment)
    # Compile to PDF in output/
    out_path = Path("output/report")
    # Try to compile to PDF. If a LaTeX compiler is not available, fall back
    # to writing the .tex file so the user can compile manually.
    # attempt to detect a LaTeX compiler and use it if present
    compiler = find_latex_compiler()
    if compiler:
        logging.info("Detected LaTeX compiler: %s — attempting PDF build", compiler)
        try:
            if compiler == "latexmk":
                # force latexmk to run in PDF mode to handle PNG images
                texfile = str(out_path) + ".tex"
                # write tex first
                doc.generate_tex(str(out_path))
                # copy assets/beam.png into output/ so pdflatex can find it when compiling
                src_img = Path("assets/beam.png")
                dst_img = out_path.parent / "beam.png"
                try:
                    if src_img.exists():
                        shutil.copy2(src_img, dst_img)
                except Exception as e:
                    logging.warning("Failed to copy beam image to build folder: %s", e)
                # use -f to force latexmk to complete when previous runs left files behind
                cmd = [compiler, "-pdf", "-f", "--interaction=nonstopmode", texfile]
                subprocess.run(cmd, check=True)
                logging.info("Successfully compiled PDF to %s.pdf using latexmk -pdf", out_path)
                return
            else:
                doc.generate_pdf(str(out_path), clean_tex=False, compiler=compiler)
                logging.info("Successfully compiled PDF to %s.pdf using %s", out_path, compiler)
                return
        except subprocess.CalledProcessError as e:
            logging.warning("latexmk failed: %s", e)
        except CompilerError as e:
            logging.warning("LaTeX compile failed: %s", e)
    else:
        logging.info("No LaTeX compiler detected — writing .tex only")
    # fallback: write tex only
    tex_path = Path(str(out_path) + ".tex")
    try:
        doc.generate_tex(str(out_path))
        logging.info("Wrote TeX file to %s", tex_path)
    except Exception as e:
        logging.error("Failed to write TeX file: %s", e)
        raise


if __name__ == "__main__":
    try:
        main()
        logging.info("Done — see output/report.tex (or report.pdf if compiled).")
    except Exception as exc:
        logging.error("Script failed: %s", exc)
        sys.exit(1)
