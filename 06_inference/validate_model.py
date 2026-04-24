"""
================================================================
 GC-CAR — MODEL VALIDATION & METRICS
 File   : validate_model.py
 Folder : 06_inference/

 Run after downloading best.pt from Colab to check:
   • Accuracy, Precision, Recall, F1
   • Confusion matrix plot
   • ROC-AUC curve
   • Sample prediction printout

 Usage:
   python validate_model.py

 Or with custom paths:
   python validate_model.py --model ../05_model/gc_car_yolo11m_best.pt
                            --data  ../03_dataset/prepared_dataset
                            --split test

 Requirements:
   pip install ultralytics torch opencv-python scikit-learn
               matplotlib seaborn Pillow
================================================================
"""

import argparse
import sys
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import torch
from pathlib import Path
from ultralytics import YOLO
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_curve, auc,
    precision_recall_curve,
    average_precision_score,
)
from PIL import Image
import torchvision.transforms as T

# ── Default paths (relative to this script's folder) ─────────
DEFAULT_MODEL = "../05_model/gc_car_trained_model/gc_car_yolo11m_best.pt"
DEFAULT_DATA  = "../03_dataset/prepared_dataset"
DEFAULT_SPLIT = "test"
DEFAULT_IMGSZ = 224
DEFAULT_BATCH = 32

# ─────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="GC-Car Model Validation")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--data",  default=DEFAULT_DATA)
    p.add_argument("--split", default=DEFAULT_SPLIT)
    p.add_argument("--imgsz", type=int, default=DEFAULT_IMGSZ)
    p.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    return p.parse_args()


def resolve_path(p: str, base: Path) -> Path:
    """Return absolute path, resolving relative to base."""
    path = Path(p)
    if not path.is_absolute():
        path = base / p
    return path.resolve()


def load_test_images(split_dir: Path, imgsz: int):
    """Load all images from split_dir/<class>/ and return tensors + labels."""
    class_names = sorted([d.name for d in split_dir.iterdir() if d.is_dir()])
    cls_to_idx  = {c: i for i, c in enumerate(class_names)}

    transform = T.Compose([
        T.Resize((imgsz, imgsz)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406],
                    std =[0.229, 0.224, 0.225]),
    ])

    tensors, labels, paths = [], [], []
    for cls_name in class_names:
        cls_dir = split_dir / cls_name
        imgs    = sorted(cls_dir.glob("*.jpg"))
        print(f"  {cls_name:15s}: {len(imgs)} images")
        for img_path in imgs:
            try:
                img = Image.open(img_path).convert("RGB")
                tensors.append(transform(img))
                labels.append(cls_to_idx[cls_name])
                paths.append(img_path)
            except Exception:
                pass

    return torch.stack(tensors), np.array(labels), class_names, paths


def run_inference(model_torch, images, device, batch_size):
    """Batch inference. Returns probs array (N, num_classes)."""
    all_probs = []
    model_torch.eval()
    with torch.no_grad():
        for i in range(0, len(images), batch_size):
            batch  = images[i:i + batch_size].to(device)
            logits = model_torch(batch)
            probs  = torch.softmax(logits, dim=1).cpu().numpy()
            all_probs.append(probs)
    return np.vstack(all_probs)


def plot_confusion_matrix(cm, class_names, save_path):
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax,
                xticklabels=class_names, yticklabels=class_names,
                linewidths=0.5)
    ax.set_title("Confusion Matrix — GC-Car Garbage Classifier", pad=12)
    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"[SAVED] {save_path}")
    plt.show()


def plot_roc_and_pr(labels, probs, class_names, save_path):
    if len(class_names) != 2:
        return   # ROC only implemented for binary

    pos_idx = class_names.index("hazardous") if "hazardous" in class_names else 1
    pos_probs = probs[:, pos_idx]
    binary_labels = (labels == pos_idx).astype(int)

    fig, axes   = plt.subplots(1, 2, figsize=(12, 5))

    # ROC curve
    fpr, tpr, _ = roc_curve(binary_labels, pos_probs)
    roc_auc     = auc(fpr, tpr)
    axes[0].plot(fpr, tpr, color="#185FA5", lw=2,
                 label=f"ROC (AUC = {roc_auc:.3f})")
    axes[0].plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4)
    axes[0].fill_between(fpr, tpr, alpha=0.08, color="#185FA5")
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate")
    axes[0].set_title("ROC Curve")
    axes[0].legend(loc="lower right")
    axes[0].grid(True, alpha=0.25)

    # Precision-Recall curve
    prec, rec, _ = precision_recall_curve(binary_labels, pos_probs)
    ap           = average_precision_score(binary_labels, pos_probs)
    axes[1].plot(rec, prec, color="#0F6E56", lw=2,
                 label=f"PR (AP = {ap:.3f})")
    axes[1].fill_between(rec, prec, alpha=0.08, color="#0F6E56")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_title("Precision-Recall Curve")
    axes[1].legend(loc="lower left")
    axes[1].grid(True, alpha=0.25)

    plt.suptitle("GC-Car  Garbage Classifier — Evaluation Curves", y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"[SAVED] {save_path}")
    plt.show()
    return roc_auc, ap


def print_sample_preds(paths, labels, preds, probs, class_names, n=10):
    print(f"\nSample predictions (first {n}):")
    print(f"  {'Status':6} {'Filename':35} {'True':15} {'Predicted':15} {'Conf':6}")
    print("  " + "-" * 80)
    for i in range(min(n, len(paths))):
        status = "  OK " if labels[i] == preds[i] else " WRONG"
        true_l = class_names[labels[i]]
        pred_l = class_names[preds[i]]
        conf   = probs[i][preds[i]]
        print(f"  {status}  {paths[i].name[:34]:34s} "
              f"{true_l:15s} {pred_l:15s} {conf:.3f}")


# ─────────────────────────────────────────────────────────────
def main():
    args    = parse_args()
    base    = Path(__file__).parent
    mp      = resolve_path(args.model, base)
    dp      = resolve_path(args.data,  base)
    device  = "cuda" if torch.cuda.is_available() else "cpu"

    print("=" * 60)
    print("GC-CAR  —  Model Validation")
    print("=" * 60)
    print(f"Model  : {mp}")
    print(f"Data   : {dp}")
    print(f"Split  : {args.split}")
    print(f"ImgSz  : {args.imgsz}")
    print(f"Device : {device.upper()}")
    print("=" * 60)

    if not mp.exists():
        print(f"\n[ERROR] Model not found: {mp}")
        print("Download gc_car_yolo11m_best.pt from Colab and place it in 05_model/")
        sys.exit(1)

    split_dir = dp / args.split
    if not split_dir.exists():
        print(f"\n[ERROR] Split folder not found: {split_dir}")
        sys.exit(1)

    # Load model
    model       = YOLO(str(mp))
    torch_model = model.model.eval().to(device)

    # Load images
    print(f"\nLoading {args.split} images...")
    images, labels, class_names, paths = load_test_images(split_dir, args.imgsz)
    print(f"Total: {len(images)} images  |  Classes: {class_names}")

    # Inference
    print(f"\nRunning inference (batch={args.batch})...")
    probs = run_inference(torch_model, images, device, args.batch)
    preds = np.argmax(probs, axis=1)

    # Accuracy
    acc = (preds == labels).mean()
    print(f"\nAccuracy : {acc * 100:.2f}%")

    # Detailed report
    print("\nClassification Report:")
    print(classification_report(labels, preds, target_names=class_names, digits=4))

    # Confusion matrix
    cm       = confusion_matrix(labels, preds)
    cm_path  = base / "validation_confusion_matrix.png"
    plot_confusion_matrix(cm, class_names, cm_path)

    # ROC / PR curves
    curves_path = base / "validation_roc_pr_curves.png"
    ret = plot_roc_and_pr(labels, probs, class_names, curves_path)
    if ret:
        roc_auc, ap = ret
        print(f"\nROC-AUC          : {roc_auc:.4f}")
        print(f"Average Precision: {ap:.4f}")

    # Sample predictions
    print_sample_preds(paths, labels, preds, probs, class_names, n=10)

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"  Test images  : {len(images)}")
    print(f"  Accuracy     : {acc * 100:.2f}%")
    if cm.shape == (2, 2):
        haz_idx = class_names.index("hazardous") if "hazardous" in class_names else 0
        non_idx = 1 - haz_idx
        tp = int(cm[haz_idx, haz_idx])
        fn = int(cm[haz_idx, non_idx])
        fp = int(cm[non_idx, haz_idx])
        tn = int(cm[non_idx, non_idx])
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        print(f"  Sensitivity  : {sensitivity * 100:.2f}%  "
              f"(hazardous correctly caught)")
        print(f"  Specificity  : {specificity * 100:.2f}%  "
              f"(safe correctly passed)")
    print("=" * 60)


if __name__ == "__main__":
    main()
