import os
from pathlib import Path
import onnx
from onnxruntime_extensions.quantization import quantize_qat, QuantFormat, CalibrationDataReader, QuantizationMode
from onnxruntime.quantization import quantize_dynamic, QuantType
import numpy as np
from transformers import AutoTokenizer

# Define paths
base_path = Path(__file__).resolve().parent
onnx_model_path = os.path.join(base_path, "TinyLlama_fitness_chatbot_onnx/model.onnx")
quantized_model_path = os.path.join(base_path, "TinyLlama_fitness_chatbot_onnx/model_quantized.onnx")

print(f"Quantizing ONNX model from: {onnx_model_path}")

model = onnx.load(onnx_model_path)
print("Model Inputs:")
for input in model.graph.input:
    print(f"Name: {input.name}, Type: {input.type}")

# Load tokenizer for calibration data
tokenizer_name = os.path.join(base_path.parent, "TinyLlama_fitness_chatbot")
tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "left"
tokenizer.chat_template = "{% for message in messages %}<|im_start|>{{ message.role }}\n{{ message.content }}<|im_end|>\n{% endfor %}"

# Calibration Data Reader
class TinyLlamaCalibrationDataReader(CalibrationDataReader):
    def __init__(self, tokenizer, num_samples=10):
        self.tokenizer = tokenizer
        self.num_samples = num_samples
        self.sample_index = 0

    def get_next(self):
        if self.sample_index < self.num_samples:
            messages = [{"role": "user", "content": f"Test message {self.sample_index}"}]
            input_text = self.tokenizer.apply_chat_template(messages, tokenize=False)
            inputs = self.tokenizer(input_text, return_tensors="np", padding=True)
            self.sample_index += 1
            return {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"]
            }
        else:
            return None

calibration_data_reader = TinyLlamaCalibrationDataReader(tokenizer)

# Perform static quantization (int8)
quantize_qat(
    model_input=onnx_model_path,
    model_output=quantized_model_path,
    quant_format=QuantFormat.QDQ, #Quantize DeQuantize
    calibrate_method=QuantizationMode.IntegerOps, #Integer operations
    calibrate_additional_options={'reduce_range': True}, #reduce range
    calibration_data_reader=calibration_data_reader,
    use_external_data_format=False,
    per_channel=True,
    weight_type=QuantType.QInt8,
    activation_type=QuantType.QUInt8
)

print(f"Quantized ONNX model saved to: {quantized_model_path}")