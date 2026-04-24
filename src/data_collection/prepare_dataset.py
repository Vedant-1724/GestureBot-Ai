"""
================================================================
 GC-CAR — DATASET PREPARATION
 File   : prepare_dataset.py
 Folder : 03_dataset/

 What it does:
   Reads the raw Kaggle Garbage Classification dataset from
   Dataset/, remaps the source classes → 2 project labels
   (hazardous / non_hazardous), pads each image to 640×640 while
   preserving aspect ratio, and splits into train/val/test folders
   ready for YOLO11.

 Important:
   These are project-specific operational safety labels, not legal
   hazardous-waste determinations. For this rover, items such as
   broken glass and sharp metal are treated as "hazardous" because
   they are dangerous on dump-yard roads.

 Run this LOCALLY before uploading dataset to Google Colab.

 Steps:
   1. Extract Kaggle ZIP into  data/raw/
   2. cd GC_Car_Project/03_dataset
   3. python prepare_dataset.py

 Requirements:
   pip install Pillow tqdm

 Output structure created:
   prepared_dataset/
     train/hazardous/
     train/non_hazardous/
     val/hazardous/
     val/non_hazardous/
     test/hazardous/
     test/non_hazardous/
================================================================
"""

import os
import shutil
import random
from pathlib import Path
from tqdm import tqdm
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True   # Skip corrupt images gracefully
random.seed(42)

# ── Config ────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
DATASET_DIR  = SCRIPT_DIR / "Dataset"
OUTPUT_DIR   = SCRIPT_DIR / "prepared_dataset"
TRAIN_RATIO  = 0.80
VAL_RATIO    = 0.10
TEST_RATIO   = 0.10
IMG_SIZE     = 640       # Final square canvas size
MIN_IMG_DIM  = 32        # Skip images smaller than this in either dimension

# ── Hazardous / Non-hazardous class map ───────────────────────
#    Key = folder name inside Dataset/  (case-insensitive)
#    Val = target binary label
CLASS_MAPPING = {
    # ── HAZARDOUS ─────────────────────────────────────────────
    "battery":     "hazardous",   # Lead/acid/lithium — toxic + fire
    "biological":  "hazardous",   # Pathogens, disease vectors
    "glass":       "hazardous",   # Broken glass — laceration
    "metal":       "hazardous",   # Sharp edges — cuts / punctures
    "trash":       "hazardous",   # Mixed unidentified — unknown risk
    # ── NON-HAZARDOUS ─────────────────────────────────────────
    "cardboard":   "non_hazardous",
    "paper":       "non_hazardous",
    "plastic":     "non_hazardous",
    "clothes":     "non_hazardous",
    "shoes":       "non_hazardous",
}

VALID_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"}

# ─────────────────────────────────────────────────────────────
def is_valid_image(path: Path) -> bool:
    if path.suffix.lower() not in VALID_EXT:
        return False
    try:
        with Image.open(path) as img:
            w, h = img.size
            return w >= MIN_IMG_DIM and h >= MIN_IMG_DIM
    except Exception:
        return False


def resize_and_save(src: Path, dst: Path, size: int = IMG_SIZE):
    try:
        with Image.open(src) as img:
            img = img.convert("RGB")
            w, h = img.size
            scale = min(size / w, size / h)
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))

            resized = img.resize((new_w, new_h), Image.LANCZOS)
            canvas = Image.new("RGB", (size, size), color=(0, 0, 0))
            off_x = (size - new_w) // 2
            off_y = (size - new_h) // 2
            canvas.paste(resized, (off_x, off_y))
            dst.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(dst, "JPEG", quality=95, optimize=True)
    except Exception as e:
        print(f"  [SKIP] {src.name}: {e}")


def collect_images():
    """Walk Dataset/ and bucket images by binary class."""
    buckets = {"hazardous": [], "non_hazardous": []}
    found_folders = []

    for folder in sorted(DATASET_DIR.rglob("*")):
        if not folder.is_dir():
            continue
        key = folder.name.lower().strip()
        if key not in CLASS_MAPPING:
            continue
        target = CLASS_MAPPING[key]
        imgs   = [f for f in folder.rglob("*") if f.is_file() and is_valid_image(f)]
        buckets[target].extend(imgs)
        found_folders.append((key, target, len(imgs)))
        print(f"  {key:15s} → {target:15s}  |  {len(imgs):5d} valid images")

    return buckets, found_folders


def split_and_copy(buckets):
    for cls_name, img_list in buckets.items():
        random.shuffle(img_list)
        n     = len(img_list)
        n_trn = int(n * TRAIN_RATIO)
        n_val = int(n * VAL_RATIO)

        splits = {
            "train": img_list[:n_trn],
            "val":   img_list[n_trn:n_trn + n_val],
            "test":  img_list[n_trn + n_val:],
        }

        for split_name, split_imgs in splits.items():
            out_dir = OUTPUT_DIR / split_name / cls_name
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n  Copying {len(split_imgs):5d}  →  {split_name}/{cls_name}")

            for idx, src in enumerate(tqdm(split_imgs,
                                            desc=f"  {split_name}/{cls_name}",
                                            unit="img",
                                            leave=False)):
                dst_name = f"{cls_name}_{split_name}_{idx:06d}.jpg"
                resize_and_save(src, out_dir / dst_name)


def print_final_stats():
    print("\n" + "=" * 60)
    print("FINAL DATASET STATISTICS")
    print("=" * 60)
    grand_total = 0
    for split in ["train", "val", "test"]:
        for cls in ["hazardous", "non_hazardous"]:
            folder = OUTPUT_DIR / split / cls
            if folder.exists():
                n = len(list(folder.glob("*.jpg")))
                grand_total += n
                print(f"  {split:5s} / {cls:15s} :  {n:6d} images")
    print(f"\n  TOTAL                    :  {grand_total:6d} images")
    print("=" * 60)
    print(f"\nDataset saved to: {OUTPUT_DIR.absolute()}")
    print("Next step → upload the 'prepared_dataset' folder to Google Drive,")
    print("then run src/training/train_colab.py in Google Colab.")


# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("GC-CAR  — Dataset Preparation")
    print("=" * 60)
    print(f"Source  : {DATASET_DIR.absolute()}")
    print(f"Output  : {OUTPUT_DIR.absolute()}")
    print(f"Split   : {int(TRAIN_RATIO*100)}% train / "
          f"{int(VAL_RATIO*100)}% val / {int(TEST_RATIO*100)}% test")
    print(f"Img size: {IMG_SIZE}×{IMG_SIZE}")
    print()

    if not DATASET_DIR.exists():
        print(f"[ERROR] Dataset/ not found at {DATASET_DIR}")
        print("Please extract the Kaggle ZIP into:")
        print(f"  {DATASET_DIR}")
        return

    # Clean previous output
    if OUTPUT_DIR.exists():
        print("[INFO] Removing previous prepared_dataset/ output...")
        shutil.rmtree(OUTPUT_DIR)

    print("Scanning Dataset/ folders...\n")
    buckets, found = collect_images()

    total = sum(len(v) for v in buckets.values())
    if total == 0:
        print("\n[ERROR] No images found. Check that CLASS_MAPPING folder")
        print("names match the subfolders inside Dataset/")
        print("Subfolders found:")
        for d in sorted(DATASET_DIR.rglob("*")):
            if d.is_dir():
                print(f"  {d.relative_to(DATASET_DIR)}")
        return

    print(f"\nTotal valid images found : {total}")
    print(f"  hazardous              : {len(buckets['hazardous'])}")
    print(f"  non_hazardous          : {len(buckets['non_hazardous'])}")

    print("\nResizing and splitting...")
    split_and_copy(buckets)
    print_final_stats()


if __name__ == "__main__":
    main()
