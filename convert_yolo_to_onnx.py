#!/usr/bin/env python3
"""
YOLOv8 to ONNX Converter with Dynamic Batching

This script converts a YOLOv8 model to ONNX format with dynamic batching
enabled for inference optimization, particularly suited for GPUs with
limited VRAM like the RTX 2050 (4GB).

Features:
- Dynamic batching: Allows variable batch sizes during inference
- FP16 precision: Reduces memory usage and improves performance on modern GPUs
- Optimized for low-VRAM GPUs

Usage:
    python convert_yolo_to_onnx.py path/to/model.pt [--output output.onnx]
"""

import argparse
import os
from ultralytics import YOLO


def convert_to_onnx(model_path: str, output_path: str = None) -> str:
    """
    Convert YOLOv8 model to ONNX format with dynamic batching and FP16 optimization.

    Args:
        model_path: Path to the YOLOv8 model file (.pt)
        output_path: Optional output path for the ONNX file

    Returns:
        Path to the converted ONNX file
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Load the YOLOv8 model
    print(f"Loading model from {model_path}...")
    model = YOLO(model_path)

    # Export to ONNX with optimizations
    print("Converting to ONNX with dynamic batching and FP16 precision...")
    export_kwargs = {
        'format': 'onnx',
        'dynamic': True,  # Enable dynamic batching
        'half': True,     # Use FP16 precision for memory optimization
        'opset': 11       # ONNX opset version for compatibility
    }

    if output_path:
        export_kwargs['save_dir'] = os.path.dirname(output_path)
        export_kwargs['name'] = os.path.splitext(os.path.basename(output_path))[0]

    # Perform the export
    model.export(**export_kwargs)

    # Determine the output file path
    if output_path:
        onnx_path = output_path
    else:
        # Default output path follows Ultralytics convention
        model_name = os.path.splitext(os.path.basename(model_path))[0]
        onnx_path = f"{model_name}.onnx"

    print(f"Model successfully converted to: {onnx_path}")
    print("Features enabled:")
    print("- Dynamic batching: Batch size can vary during inference")
    print("- FP16 precision: Optimized for RTX 2050 GPU memory and performance")

    return onnx_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert YOLOv8 model to ONNX format with dynamic batching for inference optimization"
    )
    parser.add_argument(
        'model_path',
        help='Path to the YOLOv8 model file (.pt)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output path for the ONNX file (optional)'
    )

    args = parser.parse_args()

    try:
        convert_to_onnx(args.model_path, args.output)
        print("\nConversion completed successfully!")
        print("You can now use the ONNX model for inference with:")
        print("- ONNX Runtime")
        print("- TensorRT (for NVIDIA GPU acceleration)")
        print("- OpenVINO")
        print("- Any ONNX-compatible inference engine")

    except Exception as e:
        print(f"Error during conversion: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())