import os
import time
import torch
import numpy as np
import onnx
import onnxruntime as ort
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch.nn as nn

def export_to_onnx(model, tokenizer, onnx_model_path):
    """
    Exports a PyTorch model to ONNX format with type-safe conversions.
    
    Args:
        model (PreTrainedModel): Hugging Face model to export
        tokenizer (PreTrainedTokenizer): Corresponding tokenizer
        onnx_model_path (str): Path to save the ONNX model
    """
    # Ensure model is in evaluation mode
    model.eval()

    # Prepare dummy input that mimics real-world scenario
    dummy_messages = [{"role": "user", "content": "Provide detailed exercise form feedback."}]
    dummy_chat_template = tokenizer.apply_chat_template(dummy_messages, tokenize=False)
    
    # Explicitly convert to Long tensor for input_ids
    dummy_inputs = tokenizer(dummy_chat_template, return_tensors="pt", padding=True)
    dummy_inputs = {
        'input_ids': dummy_inputs['input_ids'].long(),  # Convert to Long
        'attention_mask': dummy_inputs['attention_mask'].long()  # Convert to Long
    }

    # Input and output names
    input_names = ["input_ids", "attention_mask"]
    output_names = ["logits"]

    try:
        torch.onnx.export(
            model,
            (dummy_inputs["input_ids"], dummy_inputs["attention_mask"]),
            onnx_model_path,
            input_names=input_names,
            output_names=output_names,
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "sequence_length"},
                "attention_mask": {0: "batch_size", 1: "sequence_length"},
            },
            do_constant_folding=True,
            opset_version=17,
            export_params=True,
        )
        print(f"ONNX model exported successfully to: {onnx_model_path}")
    except Exception as e:
        print(f"ONNX export error: {e}")
        import traceback
        traceback.print_exc()
        raise
    
def quantize_onnx_model(input_path, output_path):
    """
    Quantize ONNX model with advanced configuration.
    
    Args:
        input_path (str): Path to original ONNX model
        output_path (str): Path to save quantized model
    """
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantizationMode
        
        quantize_dynamic(
            model_input=input_path,
            model_output=output_path,
            quantization_mode=QuantizationMode.IntegerOps,
            weight_type=torch.qint8,
            per_channel=True,  # Per-channel quantization for better accuracy
            reduce_seed=42  # Seed for reproducibility
        )
        print(f"Quantized model saved to: {output_path}")
    except Exception as e:
        print(f"Quantization error: {e}")
        raise

def benchmark_onnx_inference(onnx_path, tokenizer, num_runs=10):
    """
    Benchmark ONNX model inference with detailed performance metrics.
    
    Args:
        onnx_path (str): Path to ONNX model
        tokenizer (PreTrainedTokenizer): Tokenizer for input preparation
        num_runs (int): Number of inference runs
    
    Returns:
        Tuple of (average inference time, standard deviation)
    """
    # Prepare test prompt
    test_messages = [{"role": "user", "content": """
        Provide detailed feedback on form improvement for this bench press exercise, 
        analyzing biomechanical principles and exercise science techniques.
    """}]
    
    input_text = tokenizer.apply_chat_template(test_messages, tokenize=False)
    inputs = tokenizer(input_text, return_tensors="pt", padding=True)

    # Determine providers (prioritize MPS)
    providers = ['CoreMLExecutionProvider', 'CPUExecutionProvider']
    
    try:
        # Create inference session
        session = ort.InferenceSession(
            onnx_path, 
            providers=providers
        )

        # Prepare inputs
        ort_inputs = {
            'input_ids': inputs['input_ids'].numpy(),
            'attention_mask': inputs['attention_mask'].numpy()
        }

        # Warm-up run
        session.run(None, ort_inputs)

        # Performance tracking
        inference_times = []
        for _ in range(num_runs):
            start_time = time.time()
            outputs = session.run(None, ort_inputs)
            inference_times.append(time.time() - start_time)

        # Calculate statistics
        avg_time = np.mean(inference_times)
        std_time = np.std(inference_times)

        print("\nInference Benchmark Results:")
        print(f"Average Inference Time: {avg_time:.4f} seconds")
        print(f"Standard Deviation: {std_time:.4f} seconds")
        print(f"Min Inference Time: {min(inference_times):.4f} seconds")
        print(f"Max Inference Time: {max(inference_times):.4f} seconds")

        return avg_time, std_time

    except Exception as e:
        print(f"Benchmarking error: {e}")
        return None, None

def main():
    # Setup paths
    base_path = Path(__file__).resolve().parent
    model_name = os.path.join(base_path, "TinyLlama_fitness_chatbot")
    onnx_dir = os.path.join(base_path, "TinyLlama_fitness_chatbot_onnx")
    os.makedirs(onnx_dir, exist_ok=True)

    # Load model and tokenizer
    model = AutoModelForCausalLM.from_pretrained(
        model_name, 
        use_cache=False,
        torch_dtype=torch.float32  # Ensure float32 for ONNX export
    )
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    tokenizer.chat_template = "{% for message in messages %}<|im_start|>{{ message.role }}\n{{ message.content }}<|im_end|>\n{% endfor %}"

    # Paths for ONNX models
    original_onnx_path = os.path.join(onnx_dir, "model.onnx")
    quantized_onnx_path = os.path.join(onnx_dir, "model_quantized.onnx")

    # Export to ONNX
    export_to_onnx(model, tokenizer, original_onnx_path)

    # Quantize the model
    quantize_onnx_model(original_onnx_path, quantized_onnx_path)

    # Benchmark models
    print("\nBenchmarking Original ONNX Model:")
    orig_avg_time, orig_std_time = benchmark_onnx_inference(original_onnx_path, tokenizer)

    print("\nBenchmarking Quantized ONNX Model:")
    quant_avg_time, quant_std_time = benchmark_onnx_inference(quantized_onnx_path, tokenizer)

    # Performance comparison
    if orig_avg_time and quant_avg_time:
        speedup = (orig_avg_time - quant_avg_time) / orig_avg_time * 100
        print(f"\nPerformance Improvement: {speedup:.2f}%")

if __name__ == "__main__":
    main()