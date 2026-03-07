import torch
import os
import sys
import json
import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig, TrainingArguments, Trainer, pipeline
from transformers.trainer_callback import EarlyStoppingCallback
from evaluate import load as load_metric
from datasets import Dataset, load_dataset


from sklearn.model_selection import train_test_split
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from ExerciseAssessmentSystem import ExerciseAssessmentSystem
from ExerciseDataGenerator import ExerciseDataGenerator
from ModelEvaluator import ModelEvaluator

def load_test_data(dataset_path, test_size=0.02):
    try:
        with open(dataset_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Error loading dataset: {e}")
    
    if not data:
        raise ValueError("Dataset is empty")
    
    print(f"Loaded {len(data)} samples from dataset")
    
    all_samples = []
    for sample in data:
        try:
            input_text = (
                        f"Context: {sample['context']}\n"
                        f"Exercise: {sample['exercise_name']}\n"
                        f"Range of Motion: {sample['range_of_motion']}"
                        )
            print(f"input_text: {input_text}")
            output_text = f"Feedback: {sample['feedback']}"

            if input_text and output_text:  # Validate both input and output exist
                all_samples.append((input_text, output_text))
        except KeyError as e:
            print(f"Skipping invalid sample, missing key: {e}")
            continue

    _, test_data = train_test_split(all_samples, test_size=test_size, random_state=42)
    return test_data

base_path = Path(__file__).resolve().parent
if torch.backends.mps.is_available():
    device = torch.device("mps")
elif torch.cuda.is_available():
    device = torch.device("cuda")
model = AutoModelForCausalLM.from_pretrained(
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    trust_remote_code=True,
    device_map=device
).to(device)
tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "left"
tokenizer.chat_template = "{% for message in messages %}<|im_start|>{{ message.role }}\n{{ message.content }}<|im_end|>\n{% endfor %}"
dataset_path = os.path.join(base_path, "llama_labeled_dataset.json")
test_data = load_test_data(dataset_path=dataset_path)
evaluator = ModelEvaluator(model, tokenizer, device)
results = evaluator.evaluate_model(test_data)
print("----Base TinyLlama results----")
for metric, value in results.items():
    print(f"Metric ({metric}): {value}")