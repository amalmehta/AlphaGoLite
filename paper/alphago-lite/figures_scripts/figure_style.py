"""Matplotlib styling for paper figures: exact venue sizes, readable fonts, colorblind-safe colors.

Copy next to the figure scripts (paper/<slug>/figures_scripts/figure_style.py) and use:

    import figure_style as fs
    fig, ax = fs.figure("iclr", width="column", aspect=0.6)
    ax.plot(x, y, color=fs.PALETTE[0], label="baseline")
    fs.save(fig, "figures/loss_curves.pdf")

Widths come from each venue's measured \\textwidth and \\columnwidth (see the venue profile). If you
measured different values for a new venue or year, pass them with register_venue().
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PT_PER_INCH = 72.27  # TeX points

# Measured with the \typeout probe in each official template (see references/venues/*.md).
VENUES = {
    "neurips": {"textwidth_pt": 397.48, "columnwidth_pt": 397.48, "fontsize": 9},
    "iclr": {"textwidth_pt": 397.48, "columnwidth_pt": 397.48, "fontsize": 9},
    "icml": {"textwidth_pt": 487.82, "columnwidth_pt": 234.88, "fontsize": 8},
}

# Okabe-Ito: distinguishable with the common forms of color blindness and in grayscale via markers.
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#F0E442", "#000000"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
LINESTYLES = ["-", "--", "-.", ":"]


def register_venue(name, textwidth_pt, columnwidth_pt, fontsize=9):
    """Add or override a venue using widths measured from its template."""
    VENUES[name] = {"textwidth_pt": textwidth_pt, "columnwidth_pt": columnwidth_pt, "fontsize": fontsize}


def setup(venue):
    """Set rcParams for a venue: serif text matching Times-like body fonts, embeddable fonts."""
    size = VENUES[venue]["fontsize"]
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": size,
        "axes.labelsize": size,
        "axes.titlesize": size,
        "legend.fontsize": size - 1,
        "xtick.labelsize": size - 1,
        "ytick.labelsize": size - 1,
        "axes.linewidth": 0.6,
        "lines.linewidth": 1.3,
        "lines.markersize": 3.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "pdf.fonttype": 42,  # TrueType in the PDF, never Type 3 (several venues reject Type 3 fonts)
        "ps.fonttype": 42,
        "savefig.dpi": 300,
        "figure.constrained_layout.use": True,
    })


def size(venue, width="column", aspect=0.62):
    """(width, height) in inches. width: "column", "text", or a fraction of the text width."""
    spec = VENUES[venue]
    if width == "column":
        points = spec["columnwidth_pt"]
    elif width == "text":
        points = spec["textwidth_pt"]
    else:
        points = spec["textwidth_pt"] * float(width)
    inches = points / PT_PER_INCH
    return inches, inches * aspect


def figure(venue, width="column", aspect=0.62, nrows=1, ncols=1, **kwargs):
    """Create a figure sized for the venue. Include it in LaTeX at the same width with no scaling."""
    setup(venue)
    return plt.subplots(nrows, ncols, figsize=size(venue, width, aspect), **kwargs)


def save(fig, path):
    """Save as vector PDF at exactly the requested size (no bbox trimming, which would change the width)."""
    fig.savefig(path)
    plt.close(fig)


# AAAI-27, measured 2026-10-08 with the \typeout probe on AnonymousSubmission2027.tex (see aaai27/venue.md).
register_venue("aaai27", textwidth_pt=505.89, columnwidth_pt=239.39438, fontsize=8)
