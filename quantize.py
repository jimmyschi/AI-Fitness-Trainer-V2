from pathlib import Path
import os
import onnx
from onnxruntime.quantization import quantize_dynamic, QuantType

# Define paths
base_path = Path(__file__).resolve().parent
onnx_model_path = os.path.join(base_path, "TinyLlama_fitness_chatbot_onnx/model.onnx")
quantized_model_path = os.path.join(base_path, "TinyLlama_fitness_chatbot_onnx/model_quantized.onnx")

print(f"Quantizing ONNX model from: {onnx_model_path}")

model = onnx.load(onnx_model_path)
print("Model Inputs:")
for input in model.graph.input:
    print(f"Name: {input.name}, Type: {input.type}")

# Perform dynamic quantization (int8)
quantized_model = quantize_dynamic(
    model_input=onnx_model_path,  
    model_output=quantized_model_path,
    weight_type=QuantType.QUInt8,  # Quantizes only weights (not activations)
    per_channel=True
)

print(f"Quantized ONNX model saved to: {quantized_model_path}")
