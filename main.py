"""test python file."""

from pathlib import Path

from PIL import Image, ImageOps


def main() -> None:
    """test_function."""
    input_dir = Path("./src/img")
    output_dir = Path("./src/output")

    # Optional: create output folder if needed
    output_dir.mkdir(parents=True, exist_ok=True)

    allowed_exts = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}

    for image_path in input_dir.iterdir():
        if not image_path.is_file():
            continue

        if image_path.suffix.lower() not in allowed_exts:
            continue

        try:
            with Image.open(image_path) as img:
                img2 = ImageOps.exif_transpose(img)

                # AVIF may not support alpha well in some cases; keep alpha if present
                # If your images are photos, RGB is usually better.
                # Use "RGBA" only if you need transparency.
                if img2.mode in ("RGBA", "LA", "P"):
                    img2 = img2.convert("RGBA")
                else:
                    img2 = img2.convert("RGB")

                output_path = output_dir / (image_path.stem + ".avif")
                img2.save(output_path, format="AVIF", quality=40)

                print(f"Converted: {image_path.name} -> {output_path.name}")  # noqa: T201

        except Exception as e:  # noqa: BLE001
            print(f"Failed: {image_path.name} | {e}")  # noqa: T201


if __name__ == "__main__":
    main()
