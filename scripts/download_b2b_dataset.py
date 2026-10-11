"""Download and verify the complete Global B2B Invoice & Payments dataset."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


DATASET = "tharishreddy22/global-b2b-invoice-and-payments-dataset"
EXPECTED_FILES = ("train_invoices.csv", "test_invoices.csv")


def download(destination: Path, dataset: str = DATASET, force: bool = False) -> None:
    """Download and verify both complete Kaggle CSV splits.

    Args:
        destination: Directory receiving extracted source files and manifest.
        dataset: Kaggle dataset identifier in ``owner/name`` form.
        force: Redownload even when the existing manifest matches.

    Raises:
        RuntimeError: If Kaggle is unavailable, authentication fails, or files
            are missing after extraction.
    """
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "manifest.json"
    if not force and manifest_path.is_file() and all(
        (destination / name).is_file() for name in EXPECTED_FILES
    ):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("dataset") == dataset and all(
            manifest["files"].get(name) == (destination / name).stat().st_size
            for name in EXPECTED_FILES
        ):
            return
    command = [
        "kaggle", "datasets", "download", "-d", dataset,
        "-p", str(destination), "--unzip",
    ]
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Kaggle CLI is missing. Install it and configure ~/.kaggle/kaggle.json."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Kaggle download failed. Configure credentials and accept the dataset terms."
        ) from exc
    missing = [name for name in EXPECTED_FILES if not (destination / name).is_file()]
    if missing:
        raise RuntimeError(f"Dataset download is incomplete; missing {missing}")
    manifest = {
        "dataset": dataset,
        "files": {name: (destination / name).stat().st_size for name in EXPECTED_FILES},
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Parse download options and fetch the complete external dataset."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path("data/external/b2b_invoices"))
    parser.add_argument("--dataset", default=DATASET)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    download(args.destination, args.dataset, args.force)
    print(f"Downloaded complete dataset to {args.destination}")


if __name__ == "__main__":
    main()
