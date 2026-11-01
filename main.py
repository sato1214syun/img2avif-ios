"""Convert images from files, folders, and ZIP/RAR archives into AVIF."""

from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageOps
try:
    import rarfile
    except ImportError:  # pragma: no cover - optional dependency for RAR support
    rarfile = None
finally:
    pass

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
ARCHIVE_EXTS = {".zip", ".rar"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert images in folders, files, and ZIP/RAR archives to AVIF."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="One or more file or directory paths. ZIP/RAR archives are extracted automatically.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("./src/output"),
        help="Directory where converted AVIF files will be saved.",
    )
    return parser.parse_args()


def is_archive(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in ARCHIVE_EXTS


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_EXTS


def extract_archive(archive_path: Path, destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)

    if archive_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(destination_dir)
        return

    if archive_path.suffix.lower() == ".rar":
        if rarfile is None:
            raise RuntimeError(
                "rarfile is not installed. Install it with: pip install rarfile"
            )
        with rarfile.RarFile(archive_path) as archive:
            archive.extractall(destination_dir)
        return

    raise ValueError(f"Unsupported archive type: {archive_path}")


def convert_image(image_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as img:
        img2 = ImageOps.exif_transpose(img)

        if img2.mode in ("RGBA", "LA", "P"):
            img2 = img2.convert("RGBA")
        else:
            img2 = img2.convert("RGB")

        img2.save(output_path, format="AVIF", quality=40)

    print(f"Converted: {image_path} -> {output_path}")


def process_directory(directory: Path, output_root: Path) -> None:
    for child in sorted(directory.rglob("*")):
        if child.is_dir():
            continue

        if is_image(child):
            relative_path = child.relative_to(directory)
            target_path = output_root / relative_path.with_suffix(".avif")
            convert_image(child, target_path)
            continue

        if is_archive(child):
            with tempfile.TemporaryDirectory(prefix="avif_archive_") as tmp_dir:
                extracted_dir = Path(tmp_dir)
                try:
                    extract_archive(child, extracted_dir)
                    process_directory(extracted_dir, output_root / child.stem)
                except Exception as exc:  # noqa: BLE001
                    print(f"Failed archive: {child} | {exc}")


def process_path(input_path: Path, output_root: Path) -> None:
    if not input_path.exists():
        print(f"Not found: {input_path}")
        return

    if input_path.is_dir():
        process_directory(input_path, output_root / input_path.name)
        return

    if is_image(input_path):
        output_path = output_root / (input_path.stem + ".avif")
        convert_image(input_path, output_path)
        return

    if is_archive(input_path):
        with tempfile.TemporaryDirectory(prefix="avif_archive_") as tmp_dir:
            extracted_root = Path(tmp_dir)
            try:
                extract_archive(input_path, extracted_root)
                process_directory(extracted_root, output_root / input_path.stem)
            except Exception as exc:  # noqa: BLE001
                print(f"Failed archive: {input_path} | {exc}")
        return

    print(f"Unsupported file type ignored: {input_path}")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    for raw_path in args.paths:
        input_path = Path(raw_path).expanduser()
        process_path(input_path, output_dir)


if __name__ == "__main__":
    main()
