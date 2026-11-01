"""Convert images from files, folders, and ZIP/RAR archives into AVIF."""

from __future__ import annotations

import argparse
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
    """Parse args."""
    parser = argparse.ArgumentParser(
        description="Convert images in folders, files, and ZIP/RAR archives to AVIF.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        metavar="FILES_OR_DIR",
        help="a file, files or directory paths. ZIP/RAR are extracted automatically.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        metavar="DIR",
        type=Path,
        help="Directory where converted AVIF files will be saved.",
    )
    return parser.parse_args()


def is_archive(path: Path) -> bool:
    """Check the input is an archived file or not."""
    return path.is_file() and path.suffix.lower() in ARCHIVE_EXTS


def is_image(path: Path) -> bool:
    """Check the input is an image file or not."""
    return path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_EXTS


def extract_archive(archive_path: Path, destination_dir: Path) -> None:
    """Extract the archived file depends on its suffix."""
    destination_dir.mkdir(parents=True, exist_ok=True)

    if archive_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(destination_dir)
        return

    if archive_path.suffix.lower() == ".rar":
        if rarfile is None:
            err_msg = "rarfile is not installed. Install it with: pip install rarfile"
            raise RuntimeError(err_msg)
        with rarfile.RarFile(archive_path) as archive:
            archive.extractall(destination_dir)
        return

    err_msg = f"Unsupported archive type: {archive_path}"
    raise ValueError(err_msg)


def convert_image(image_path: Path, output_path: Path) -> None:
    """Convert image to avif by pillow."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as img:
        img2 = ImageOps.exif_transpose(img)

        if img2.mode in ("RGBA", "LA", "P"):
            img2 = img2.convert("RGBA")
        else:
            img2 = img2.convert("RGB")

        img2.save(output_path, format="AVIF", quality=40)
    org_size = int(image_path.stat().st_size / 1024)
    cnv_size = int(output_path.stat().st_size / 1024)
    ratio = int(cnv_size / org_size * 100)
    print(  # noqa: T201
        f"Converted: ({ratio}%) : {image_path.name}({org_size}KB) -> {output_path.name}({cnv_size}KB)",  # noqa: E501
    )


def process_directory(directory: Path, output_root: Path) -> None:
    """Convert files inside a directory."""
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
                    print(f"Failed archive: {child} | {exc}")  # noqa: T201


def process_path(input_path: Path, output_root: Path) -> None:
    """Check path type and process."""
    if not input_path.exists():
        print(f"Not found: {input_path}")  # noqa: T201
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
                print(f"Failed archive: {input_path} | {exc}")  # noqa: T201
        return

    print(f"Unsupported file type ignored: {input_path}")  # noqa: T201


def main() -> None:
    """Implement main."""
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    for raw_path in args.paths:
        input_path = Path(raw_path).expanduser()
        process_path(input_path, output_dir)


if __name__ == "__main__":
    main()
