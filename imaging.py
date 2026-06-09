"""
MedLens — Medical Imaging Pipeline
Handles DICOM loading, NIfTI mask processing, PI-RADS scoring,
lesion visualization, and MRI volume operations.
"""

import os
import numpy as np
import pydicom
import nibabel as nib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.ndimage import zoom


# ─────────────────────────────────────────────────────
# DICOM I/O
# ─────────────────────────────────────────────────────

def load_dicom_volume(series_dir: str) -> np.ndarray | None:
    """
    Load all DICOM slices in a directory into a sorted 3-D volume.
    Returns array of shape (slices, H, W) or None on failure.
    """
    slices = []
    for fname in os.listdir(series_dir):
        if not fname.endswith(".dcm"):
            continue
        fpath = os.path.join(series_dir, fname)
        try:
            dcm = pydicom.dcmread(fpath)
            z = float(dcm.ImagePositionPatient[2])
            slices.append((z, dcm.pixel_array))
        except Exception:
            continue

    if not slices:
        return None

    slices.sort(key=lambda x: x[0])
    return np.stack([s[1] for s in slices], axis=0)


def load_nifti_mask(mask_path: str) -> np.ndarray | None:
    """Load a NIfTI mask, flip to DICOM axial orientation."""
    try:
        nii = nib.load(mask_path)
        data = nii.get_fdata()
        return np.flip(data, axis=0)
    except Exception:
        return None


# ─────────────────────────────────────────────────────
# Mask overlay
# ─────────────────────────────────────────────────────

def overlay_mask_on_slice(
    ax: plt.Axes,
    dicom_slice: np.ndarray,
    mask_vol: np.ndarray | None,
    color_rgba: list,
) -> bool:
    """
    Project the most-populated mask slice onto a DICOM panel.
    Returns True if an overlay was drawn.
    """
    if mask_vol is None or mask_vol.max() == 0:
        return False

    slice_sums = [mask_vol[:, :, z].sum() for z in range(mask_vol.shape[2])]
    best_z = int(np.argmax(slice_sums))
    mask_slice = mask_vol[:, :, best_z]

    if mask_slice.shape != dicom_slice.shape:
        zf = [
            dicom_slice.shape[0] / mask_slice.shape[0],
            dicom_slice.shape[1] / mask_slice.shape[1],
        ]
        mask_slice = zoom(mask_slice, zf, order=0)

    mask_slice = mask_slice.T
    if mask_slice.max() == 0:
        return False

    overlay = np.zeros((*mask_slice.shape, 4))
    overlay[mask_slice > 0] = color_rgba
    ax.imshow(overlay, aspect="equal")
    return True


# ─────────────────────────────────────────────────────
# Visualization
# ─────────────────────────────────────────────────────

def visualize_patient(
    patient_id: str,
    patient_index: dict,
    lesion_index: dict,
    patient_pirads: dict,
    output_path: str | None = None,
) -> plt.Figure | None:
    """
    Render a two-panel figure: T2W (with lesion overlays) + ADC map.
    Returns the matplotlib Figure.
    """
    if patient_id not in patient_index:
        print(f"Patient {patient_id} not found.")
        return None

    info = patient_index[patient_id]
    findings = lesion_index.get(patient_id, [])
    pirads = patient_pirads.get(patient_id, "N/A")
    sig_count = sum(1 for f in findings if f["significant"])

    # Load volumes
    t2_vol = adc_vol = None
    if info.get("t2"):
        t2_vol = load_dicom_volume(info["t2"][0])
    if info.get("adc"):
        adc_vol = load_dicom_volume(info["adc"][0])

    if t2_vol is None:
        print(f"Could not load T2W volume for {patient_id}.")
        return None

    mid = t2_vol.shape[0] // 2
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor("#0a0a0a")

    # T2W panel
    axes[0].imshow(t2_vol[mid], cmap="gray", aspect="equal")
    axes[0].set_title(f"T2-Weighted — {patient_id}", color="white",
                      fontsize=12, pad=10)
    axes[0].axis("off")

    legend_patches = []
    for finding in findings:
        if finding.get("t2_mask"):
            mask_vol = load_nifti_mask(finding["t2_mask"])
            color = "red" if finding["significant"] else "yellow"
            rgba = [1, 0, 0, 0.5] if finding["significant"] else [1, 1, 0, 0.5]
            drawn = overlay_mask_on_slice(axes[0], t2_vol[mid], mask_vol, rgba)
            if drawn:
                label = (
                    f"Finding {finding['finding']}: "
                    f"{'⚠ ClinSig' if finding['significant'] else 'Benign'} "
                    f"(GG{finding.get('gleason', 'N/A')})"
                )
                legend_patches.append(
                    mpatches.Patch(color=color, alpha=0.7, label=label)
                )

    if legend_patches:
        axes[0].legend(handles=legend_patches, loc="lower left",
                       fontsize=8, facecolor="#1a1a1a", labelcolor="white")

    # ADC panel
    if adc_vol is not None:
        adc_mid = adc_vol.shape[0] // 2
        axes[1].imshow(adc_vol[adc_mid], cmap="hot", aspect="equal")
        for finding in findings:
            if finding.get("adc_mask"):
                mask_vol = load_nifti_mask(finding["adc_mask"])
                rgba = [1, 0, 0, 0.5] if finding["significant"] else [1, 1, 0, 0.5]
                overlay_mask_on_slice(axes[1], adc_vol[adc_mid], mask_vol, rgba)
    else:
        axes[1].set_facecolor("black")
        axes[1].text(0.5, 0.5, "ADC not available", ha="center", va="center",
                     color="gray", transform=axes[1].transAxes)

    axes[1].set_title("ADC Map", color="white", fontsize=12, pad=10)
    axes[1].axis("off")

    status_text = f"{'🔴' if sig_count else '🟢'} {sig_count} Clinically Significant" \
                  if sig_count else "🟢 No Significant Findings"
    fig.suptitle(
        f"{patient_id}  |  PI-RADS: {pirads}  |  {status_text}",
        color="red" if sig_count else "lime",
        fontsize=14, y=0.02,
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight",
                    facecolor="#0a0a0a")

    return fig
