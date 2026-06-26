"""Google Colab training script for YOLO11 garbage classification.
Set DRIVE_DATASET_PATH and TRAINING_PRESET, then run all cells."""


# --- Cell 1: Install packages ---
import subprocess, sys

def run(cmd):
    subprocess.run(cmd, shell=True, check=False)

print("Installing packages...")
run("pip install ultralytics -q")
run("pip install scikit-learn matplotlib seaborn -q")
print("Done.\n")

# --- Cell 2: Mount Google Drive ---
from google.colab import drive
drive.mount("/content/drive")

# --- Cell 3: Imports & GPU check ---
import os, shutil, time
import numpy as np
import matplotlib.pyplot as plt
import torch
from pathlib import Path
from ultralytics import YOLO
from sklearn.metrics import (classification_report,
                              confusion_matrix,
                              roc_auc_score)
from PIL import Image
import torchvision.transforms as T

print("=" * 60)
print("GC-CAR  —  YOLO11m Garbage Classifier Training")
print("=" * 60)
print(f"Python     : {sys.version.split()[0]}")
print(f"PyTorch    : {torch.__version__}")
print(f"CUDA       : {torch.version.cuda}")
if torch.cuda.is_available():
    props = torch.cuda.get_device_properties(0)
    print(f"GPU        : {props.name}")
    print(f"VRAM       : {props.total_memory / 1e9:.1f} GB")
else:
    print("GPU        : NOT AVAILABLE (training will be slow)")
    raise RuntimeError(
        "Colab is currently using CPU. In Colab, go to Runtime -> Change runtime type "
        "-> Hardware accelerator -> GPU, save, then Runtime -> Restart session and Run all."
    )

DEVICE = 0 if torch.cuda.is_available() else "cpu"
print("=" * 60)

# --- Cell 4: Configuration (edit paths here) ---

# Path to your uploaded 'prepared_dataset' folder on Google Drive
DRIVE_DATASET_PATH = "/content/drive/MyDrive/prepared_dataset"   # <── CHANGE if needed

COLAB_DATASET_PATH = "/content/gc_car_dataset"     # Temp fast local copy
DRIVE_OUTPUT_DIR   = "/content/drive/MyDrive/gc_car_trained_model"
PROJECT_DIR        = "/content/runs/classify"

# Choose one:
#   "fast"         -> quickest T4-friendly run
#   "balanced"     -> good accuracy/speed tradeoff
#   "max_accuracy" -> slowest, best chance of squeezing extra accuracy
TRAINING_PRESET    = "fast"

COMMON_CFG = dict(
    lr0             = 0.001,
    lrf             = 0.01,
    momentum        = 0.9,
    weight_decay    = 0.0005,
    warmup_epochs   = 2,
    optimizer       = "AdamW",
    amp             = True,
    augment         = True,
    label_smoothing = 0.1,
    dropout         = 0.0,
    pretrained      = True,
    seed            = 42,
    workers         = min(2, os.cpu_count() or 2),
)

PRESETS = {
    "fast": dict(
        model         = "yolo11s-cls.pt",
        run_name      = "gc_car_yolo11s_fast",
        epochs        = 35,
        imgsz         = 192,
        batch         = 96,
        patience      = 10,
        deterministic = False,
        save_period   = -1,
        plots         = False,
        verbose       = False,
    ),
    "balanced": dict(
        model         = "yolo11m-cls.pt",
        run_name      = "gc_car_yolo11m_balanced",
        epochs        = 50,
        imgsz         = 224,
        batch         = 64,
        patience      = 15,
        deterministic = False,
        save_period   = -1,
        plots         = True,
        verbose       = True,
    ),
    "max_accuracy": dict(
        model         = "yolo11m-cls.pt",
        run_name      = "gc_car_yolo11m_max",
        epochs        = 100,
        imgsz         = 224,
        batch         = 64,
        patience      = 25,
        deterministic = True,
        save_period   = 10,
        plots         = True,
        verbose       = True,
    ),
}

if TRAINING_PRESET not in PRESETS:
    raise ValueError(f"Unknown TRAINING_PRESET: {TRAINING_PRESET}")

CFG = {**COMMON_CFG, **PRESETS[TRAINING_PRESET]}
RUN_NAME = CFG["run_name"]

# --- Cell 5: Copy dataset from Drive to /content (faster I/O) ---
print("\n[STEP 1] Copying dataset from Google Drive to Colab /content ...")
print("(Training directly from Drive is 3–5× slower)")

if os.path.exists(COLAB_DATASET_PATH):
    shutil.rmtree(COLAB_DATASET_PATH)

shutil.copytree(DRIVE_DATASET_PATH, COLAB_DATASET_PATH)
print("Copy done.\n")

# Verify
print("Dataset contents:")
for split in ["train", "val", "test"]:
    for cls in ["hazardous", "non_hazardous"]:
        p = Path(COLAB_DATASET_PATH) / split / cls
        if p.exists():
            n = len(list(p.glob("*.jpg")))
            bar = "█" * (n // 200)
            print(f"  {split:5s}/{cls:15s}: {n:6d}  {bar}")

# --- Cell 6: Load model & train ---
print(f"\n[STEP 2] Loading YOLO11m-cls (pretrained on ImageNet)...")
model = YOLO(CFG["model"])
total_params = sum(p.numel() for p in model.model.parameters())
print(f"Parameters : {total_params:,}")

print(f"\n[STEP 3] Starting training  ({CFG['epochs']} epochs max)")
print("=" * 60)
t0 = time.time()

results = model.train(
    data           = COLAB_DATASET_PATH,
    epochs         = CFG["epochs"],
    imgsz          = CFG["imgsz"],
    batch          = CFG["batch"],
    device         = DEVICE,
    workers        = CFG["workers"],
    lr0            = CFG["lr0"],
    lrf            = CFG["lrf"],
    momentum       = CFG["momentum"],
    weight_decay   = CFG["weight_decay"],
    warmup_epochs  = CFG["warmup_epochs"],
    optimizer      = CFG["optimizer"],
    patience       = CFG["patience"],
    amp            = CFG["amp"],
    augment        = CFG["augment"],
    label_smoothing= CFG["label_smoothing"],
    dropout        = CFG["dropout"],
    pretrained     = CFG["pretrained"],
    seed           = CFG["seed"],
    deterministic  = CFG["deterministic"],
    save_period    = CFG["save_period"],
    plots          = CFG["plots"],
    verbose        = CFG["verbose"],
    project        = PROJECT_DIR,
    name           = RUN_NAME,
    exist_ok       = True,
    val            = True,
    save           = True,
)

elapsed = time.time() - t0
print(f"\nTraining complete in {elapsed/60:.1f} minutes")

# --- Cell 7: Validate on test split ---
WEIGHTS_DIR = f"{PROJECT_DIR}/{RUN_NAME}/weights"
best_pt     = f"{WEIGHTS_DIR}/best.pt"

print("\n[STEP 4] Validating best model on test split...")
best_model  = YOLO(best_pt)
val_result  = best_model.val(
    data   = COLAB_DATASET_PATH,
    imgsz  = CFG["imgsz"],
    batch  = 32,
    device = DEVICE,
    split  = "test",
    augment= False,
    plots  = True,
)
print(f"\nTop-1 Accuracy : {val_result.top1 * 100:.2f}%")
print(f"Top-5 Accuracy : {val_result.top5 * 100:.2f}%")

# --- Cell 8: Detailed sklearn metrics ---
print("\n[STEP 5] Computing detailed classification metrics...")

test_dir    = Path(COLAB_DATASET_PATH) / "test"
class_names = sorted([d.name for d in test_dir.iterdir() if d.is_dir()])
cls_to_idx  = {c: i for i, c in enumerate(class_names)}
print(f"Classes: {class_names}")

test_items = []
for cls_name in class_names:
    img_paths = sorted((test_dir / cls_name).glob("*.*"))
    for img_path in img_paths:
        if img_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            test_items.append((img_path, cls_to_idx[cls_name]))

if not test_items:
    raise RuntimeError(f"No test images found in: {test_dir}")

test_paths  = [str(p) for p, _ in test_items]
all_labels  = np.array([label for _, label in test_items], dtype=int)
all_preds   = []
all_probs   = []

results = best_model.predict(
    source  = test_paths,
    imgsz   = CFG["imgsz"],
    batch   = 32,
    device  = DEVICE,
    verbose = False,
)

for res in results:
    probs = res.probs
    if probs is None:
        raise RuntimeError("Prediction returned no class probabilities for one or more test images.")
    all_preds.append(int(probs.top1))
    all_probs.append(probs.data.cpu().numpy())

all_preds = np.array(all_preds, dtype=int)
all_probs = np.vstack(all_probs)

if len(all_preds) != len(all_labels):
    raise RuntimeError(
        f"Prediction count mismatch: got {len(all_preds)} predictions for {len(all_labels)} test images."
    )

print("\nClassification Report:")
print(classification_report(
    all_labels,
    all_preds,
    labels=list(range(len(class_names))),
    target_names=class_names,
    digits=4,
    zero_division=0,
))

cm = confusion_matrix(all_labels, all_preds, labels=list(range(len(class_names))))
print(f"Confusion Matrix:\n{cm}")

if len(class_names) == 2:
    pos_idx = class_names.index("hazardous") if "hazardous" in class_names else 1
    auc = roc_auc_score((all_labels == pos_idx).astype(int), all_probs[:, pos_idx])
    print(f"ROC-AUC Score : {auc:.4f}")

# Confusion matrix plot
fig, ax = plt.subplots(figsize=(6, 5))
import seaborn as sns
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
            xticklabels=class_names, yticklabels=class_names)
ax.set_title("Confusion Matrix — GC-Car Garbage Classifier")
ax.set_xlabel("Predicted"); ax.set_ylabel("True")
plt.tight_layout()
plt.savefig(f"{PROJECT_DIR}/{RUN_NAME}/confusion_matrix_detailed.png", dpi=150)
plt.show()

# --- Cell 9: Save model + plots to Google Drive ---
print(f"\n[STEP 6] Saving to Google Drive: {DRIVE_OUTPUT_DIR}")
os.makedirs(DRIVE_OUTPUT_DIR, exist_ok=True)

shutil.copy(best_pt, f"{DRIVE_OUTPUT_DIR}/{RUN_NAME}_best.pt")
shutil.copy(f"{WEIGHTS_DIR}/last.pt", f"{DRIVE_OUTPUT_DIR}/{RUN_NAME}_last.pt")

for fname in ["results.png", "confusion_matrix.png",
              "confusion_matrix_detailed.png"]:
    src = Path(f"{PROJECT_DIR}/{RUN_NAME}/{fname}")
    if src.exists():
        shutil.copy(src, f"{DRIVE_OUTPUT_DIR}/{fname}")

print(f"\nModel saved to Google Drive successfully!")
print(f"\n{'='*60}")
print("TRAINING COMPLETE!")
print(f"{'='*60}")
print("Next steps:")
print(f"  1. Download  {RUN_NAME}_best.pt  from Drive")
print(f"  2. Place it in  GC_Car_Project/models/")
print(f"  3. Run  src/inference/esp32_live_inference.py  on laptop")
print(f"{'='*60}")
