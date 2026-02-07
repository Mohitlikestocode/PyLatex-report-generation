import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def find_columns(df):
    # map possible column names to standard keys
    cols = {c.lower().strip(): c for c in df.columns}
    key_map = {}
    # X
    for k in ("x", "position", "pos"):
        if k in cols:
            key_map['X'] = cols[k]
            break
    # Shear
    for k in ("shear force", "shear_force", "shear", "shearforce"):
        if k in cols:
            key_map['Shear'] = cols[k]
            break
    # Moment
    for k in ("bending moment", "bending_moment", "moment", "bendingmoment"):
        if k in cols:
            key_map['Moment'] = cols[k]
            break
    return key_map


def load_data(path="data/forces.xlsx"):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")
    df = pd.read_excel(p)
    cmap = find_columns(df)
    if set(cmap.keys()) != {'X', 'Shear', 'Moment'}:
        raise ValueError("Excel must contain columns for X, Shear and Moment (names may be 'X','Shear force','Bending Moment' or similar).")
    data = df[[cmap['X'], cmap['Shear'], cmap['Moment']]].copy()
    data.columns = ['X', 'Shear', 'Moment']
    data = data.dropna()
    data['X'] = data['X'].astype(float)
    data['Shear'] = data['Shear'].astype(float)
    data['Moment'] = data['Moment'].astype(float)
    data = data.sort_values('X').reset_index(drop=True)
    return data


def make_contour_plot(x, values, title, units, outpath, cmap='RdBu_r', symmetric=True):
    # create a thin 2D image by repeating the 1D series vertically
    H = 120  # vertical resolution for the band
    Z = np.tile(values.reshape(1, -1), (H, 1))

    # force supports to zero for moments if user desires visual zero at ends
    # (do not alter source data file)
    if title.lower().find('moment') >= 0:
        Z[:, 0] = 0.0
        Z[:, -1] = 0.0

    fig, ax = plt.subplots(figsize=(10, 2.2))
    # compute extent so x maps correctly
    xmin, xmax = float(x.min()), float(x.max())
    extent = [xmin, xmax, -1, 1]

    if symmetric:
        vmax = np.nanmax(np.abs(values))
        vmin = -vmax
    else:
        vmin = np.nanmin(values)
        vmax = np.nanmax(values)

    im = ax.imshow(Z, extent=extent, aspect='auto', cmap=cmap, origin='lower', vmin=vmin, vmax=vmax)

    # overlay beam centerline
    ax.plot([xmin, xmax], [0, 0], color='k', linewidth=2)
    # hide y ticks (not a physical axis)
    ax.set_yticks([])
    ax.set_xlabel('x (m)')
    ax.set_title(title)

    # colorbar on the right
    cbar = fig.colorbar(im, ax=ax, orientation='vertical', pad=0.02)
    cbar.set_label(units)

    # save
    outdir = Path(outpath).parent
    outdir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(outpath, dpi=300)
    # also save PDF
    fig.savefig(str(Path(outpath).with_suffix('.pdf')))
    plt.close(fig)


def main():
    data = load_data('data/forces.xlsx')
    x = data['X'].to_numpy().astype(float).copy()
    shear = data['Shear'].to_numpy().astype(float).copy()
    moment = data['Moment'].to_numpy().astype(float).copy()

    # Ensure bending moment is zero at supports for visualization
    moment[0] = 0.0
    moment[-1] = 0.0

    out_sfd = 'output/sfd.png'
    out_bmd = 'output/bmd.png'

    # Shear: diverging map centered at zero
    make_contour_plot(x, shear, 'Shear Force Diagram (SFD)', 'Shear (N)', out_sfd, cmap='RdBu_r', symmetric=True)

    # Moment: diverging centered at zero
    make_contour_plot(x, moment, 'Bending Moment Diagram (BMD)', 'Moment (N·m)', out_bmd, cmap='RdBu_r', symmetric=True)

    print(f'Wrote {out_sfd} and {out_bmd}')


if __name__ == '__main__':
    main()
