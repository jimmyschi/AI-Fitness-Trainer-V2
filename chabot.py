#Use a pipelione as high-level helper
import torch
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
import numpy as np
import random
import os
import sys
import json
import nltk
import logging
import traceback
from typing import List, Tuple
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig, TrainingArguments, Trainer, pipeline
from evaluate import load as load_metric
from datasets import Dataset
from peft import get_peft_model, LoraConfig, TaskType
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm 
import matplotlib.pyplot as plt


from read_input_files import process_video

print(torch.__version__)

base_path = Path(__file__).resolve().parent

def label_dataset(exercise_type, joint_positions, timestamps):
    # print(f"Debug: Type of joint_positions: {type(joint_positions)}")
    # if isinstance(joint_positions, list) and joint_positions:
    #     print(f"Debug: First element type: {type(joint_positions[0])}")
        
    if not isinstance(joint_positions, list) or not joint_positions:
        print(f"Skipping {exercise_type}: No valid joint positions")
        return []
    try:
        # Convert joint positions into a proper 2D NumPy array
        joint_positions_flattened = np.array([
            [joint.x, joint.y, joint.z, joint.visibility] for frame in joint_positions for joint in frame
        ])
        print(f"joint_positions_flattened.shape: {joint_positions_flattened.shape}")
        # print(f"joint_positions_flattened: {joint_positions_flattened}")
        
    except Exception as e:
        print(f"Error processing joint_positions: {e}")
        return []

    # print(f"Joint Positions Shape: {joint_positions_flattened.shape}")  # Debugging

    
    #Normalize the data
    scaler = StandardScaler()
    joint_positions_normalized = scaler.fit_transform(joint_positions_flattened)
    
    
    #k=Start with 2 clusters representing good/bad form
    k=2
    kmeans = KMeans(n_clusters=k,random_state=42, n_init="auto")
    labels = kmeans.fit_predict(joint_positions_normalized)
    
    if isinstance(timestamps, np.ndarray):
        timestamps = timestamps.tolist()
        
    print(f"Types - joint_positions_flattened: {type(joint_positions_flattened)}, timestamps: {type(timestamps)}")
   
    labeled_data = []
    for i in range(len(joint_positions_flattened)):
        try:
            joint_pos = joint_positions_flattened[i]
            if isinstance(joint_pos, np.ndarray):
                joint_pos = joint_pos.tolist()
            
            timestamp = timestamps[i] if i < len(timestamps) else None
            if isinstance(timestamp, np.generic):
                timestamp = timestamp.item()
                
            data_point = {
                "exercise" : str(exercise_type),
                "joint_positions": joint_pos,
                "timestamps": timestamp,
                "label": "Good form" if labels[i] == 0 else "Bad form"
            }
            
            json.dumps(data_point)
            labeled_data.append(data_point)
        except Exception as e:
            print(f"Error processing data point {i}: {e}")
            print(f"Types - joint_pos: {type(joint_pos)}, timestamp: {type(timestamp)}")
            continue
    
    
    return labeled_data
def create_dataset():
    exercises = {}
    print(f"base_path: {base_path}")
    # input_path = os.path.join(base_path, "training_input_videos")
    input_path = os.path.join(base_path, "workout_videos")
    output_path = os.path.join(base_path, "training_output_videos")
    
    if not os.path.exists(input_path):
        print(f"Input path does not exist: {input_path}")
        return None

    os.makedirs(output_path, exist_ok=True)
    
    exercise_names = os.listdir(input_path)
    exercise_directory = [exercise_name for exercise_name in exercise_names if os.path.isdir(os.path.join(input_path, exercise_name))]
    print(f"exercise_directory: {exercise_directory}")

    for exercise_type in exercise_directory:
        exercise_input_dir = os.path.join(input_path, exercise_type)
        exercise_output_dir = os.path.join(output_path, exercise_type)
        # print(f"EXERCISE_OUTPUT_DIR: {exercise_output_dir}")
        os.makedirs(exercise_output_dir, exist_ok=True)
        
        video_files = [f for f in os.listdir(exercise_input_dir) if f.endswith(('.mp4', '.MOV'))]
        for video_file in video_files:
            input_video_path = os.path.join(exercise_input_dir, video_file)
            output_video_path = os.path.join(exercise_output_dir, video_file)
            # print(f"OUTPUT_VIDEO_PATH: {output_video_path}")
            timestamps, joint_positions = process_video(input_video_path, output_video_path, exercise_type=exercise_type)
            try:
                labeled_data = label_dataset(exercise_type, joint_positions, timestamps)
                # print(f"labeled_data: {labeled_data}")
                if exercise_type not in exercises:
                    exercises[exercise_type] = []
                exercises[exercise_type].extend(labeled_data)
            except Exception as e:
                print(f"Error processing video {video_file}: {e}")
                continue
    try:
        json_str = json.dumps(exercises, indent=4)
        labeled_dataset = os.path.join(base_path, "labeled_dataset.txt")
        with open(labeled_dataset, "w") as f:
            f.write(json_str)
        print(f"Dataset saved to {labeled_dataset}")
        return labeled_dataset
    except TypeError as e:
        print(f"Error serializing data: {e}")
        for ex_type, data in exercises.items():
            print(f"Exercise type: {ex_type}")
            print(f"Data type: {type(data)}")
            if isinstance(data, list):
                for i, item in enumerate(data):
                    print(f"Item {i} types:")
                    for k, v in item.items():
                        print(f"    {k}: {type(v)}")
        return None

def load_and_split_dataset(dataset_path, test_size=.2):
    with open(dataset_path, "r") as f:
        data = json.load(f)     
    
    all_samples = []
    
    for exercise, samples in data.items():
        for sample in samples:
            input_text = f"Exercise: {sample['exercise']}\nJoint Positions: {sample['joint_positions']}\nTimestamps: {sample['timestamps']}"
            output_text = sample['label']
            all_samples.append((input_text, output_text))
    
    #Split into training and testing sets
    train_data, test_data = train_test_split(all_samples,test_size=test_size, random_state=42)
    
    return train_data, test_data


def load_model():
    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    print(f"Loading tokenizer from {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Create offload directory
    offload_folder = os.path.join(base_path, "model_offload")
    os.makedirs(offload_folder, exist_ok=True)
    
    print("Loading base model...")
    # Check for CUDA first, then fall back to CPU
    if torch.cuda.is_available():
        print("Using CUDA...")
        device_map = "auto"
        dtype = torch.float16
    elif torch.backends.mps.is_available:
        device_map = torch.device("mps")
        dtype = torch.float16
    else:
        print("Using CPU...")
        device_map = {"": torch.device("cpu")}
        dtype = torch.float32

    # Load the model with device mapping
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=dtype,
        device_map=device_map,
        offload_folder=offload_folder,
        offload_state_dict=True,
        low_cpu_mem_usage=True
    )
    
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})

    print("Configuring model...")
    model.generation_config = GenerationConfig.from_pretrained(model_name)
    model.generation_config.pad_token_id = model.generation_config.eos_token_id
    
    # Configure LoRA
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=4,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        bias="none"
    )
    
    print("Applying LoRA adapters...")
    model = get_peft_model(model, peft_config)
    
    # Load or create dataset
    if not os.path.exists(os.path.join(base_path, "labeled_dataset.txt")):
        labeled_dataset = create_dataset()
    else:
        labeled_dataset = os.path.join(base_path, "labeled_dataset.txt")
    
    print("Loading dataset...")
    train_data, test_data = load_and_split_dataset(labeled_dataset)
    
    print("Preparing encodings...")
    train_encodings = tokenizer(
        [x[0] for x in train_data], 
        text_target=[x[1] for x in train_data], 
        padding="max_length", 
        truncation=True, 
        max_length=256
    )
    test_encodings = tokenizer(
        [x[0] for x in test_data], 
        text_target=[x[1] for x in test_data], 
        padding="max_length", 
        truncation=True, 
        max_length=256
    )

    train_dataset = Dataset.from_dict({
        "input_ids": train_encodings["input_ids"], 
        "labels": train_encodings["labels"]
    })
    test_dataset = Dataset.from_dict({
        "input_ids": test_encodings["input_ids"], 
        "labels": test_encodings["labels"]
    })

    # Configure training arguments
    training_args = TrainingArguments(
        output_dir="./TinyLlama_finetuned",
        evaluation_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=100,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        num_train_epochs=2,
        save_total_limit=2,
        fp16=False,  # Disable fp16
        logging_dir="./logs",
        gradient_accumulation_steps=8,
        learning_rate=1e-5,
        warmup_steps=100,
        gradient_checkpointing=True,
        optim="adamw_torch",
        max_grad_norm=0.3,
        weight_decay=0.01,
        # Disable both CUDA and MPS to force CPU usage
        no_cuda=True,
        use_mps_device=True
    )

    print("Initializing trainer...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        tokenizer=tokenizer
    )

    print("Starting training...")
    trainer.train()
    return test_data, model, tokenizer
    

def evaluate_model(test_samples: List[Tuple[str, str]], model, tokenizer, max_length: int = 200, batch_size: int = 8, num_workers: int = 4):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Create pipeline without specifying device
        pipe = pipeline(
            "text-generation", 
            model=model, 
            tokenizer=tokenizer, 
            batch_size=batch_size
        )
        
        def create_batches(samples, batch_size):
            return [samples[i:i + batch_size] for i in range(0, len(samples), batch_size)]
        
        def process_batch(batch):
            inputs = [text for text, _ in batch]
            references = [truth for _, truth in batch]
            
            try:
                outputs = pipe(
                    inputs, 
                    max_length=max_length, 
                    truncation=True, 
                    num_return_sequences=1,
                    pad_token_id=tokenizer.eos_token_id,
                    do_sample=False
                )
                
                # Extract generated text and clean it
                predictions = []
                for out in outputs:
                    if isinstance(out, list):
                        text = out[0]['generated_text']
                    else:
                        text = out['generated_text']
                    # Clean and extract the form prediction
                    if "Good form" in text:
                        predictions.append("Good form")
                    elif "Bad form" in text:
                        predictions.append("Bad form")
                    else:
                        predictions.append("Unknown")
                
                return list(zip(predictions, references))
            except Exception as e:
                logger.error(f"Batch processing error: {str(e)}")
                return []
        
        all_results = []
        batches = create_batches(test_samples, batch_size)
        
        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_batch = {
                executor.submit(process_batch, batch): batch for batch in batches 
            }
            
            with tqdm(total=len(batches), desc="Processing batches") as pbar:
                for future in as_completed(future_to_batch):
                    try:
                        results = future.result()
                        all_results.extend(results)
                        pbar.update(1)
                    except Exception as e:
                        logger.error(f"Batch processing error: {e}")
                        continue
        
        if not all_results:
            raise ValueError("No valid predictions or references generated")
        
        predictions, references = zip(*all_results)
        
        #Calculate comprehensive metrics
        precision, recall, f1, _ = precision_recall_fscore_support(
            references, predictions, average='weighted'
        )
        
        #Calculate confusion matrix
        cm = confusion_matrix(references, predictions, labels=["Good form", "Bad form"])
        
        class_metrics = {}
        for i, class_name in enumerate(["Good form", "Bad form"]):
            tp = cm[i,i]
            fp = cm[:, i].sum() - tp
            fn = cm[i,:].sum() - tp
            tn = cm.sum() - (tp + fp + fn)
            
            class_metrics[class_name] = {
                'precision': tp / (tp + fp) if (tp + fp) > 0 else 0,
                'recall': tp / (tp + fn) if (tp + fn) > 0 else 0,
                'specificity': tn / (tn + fp) if (tn + fp) > 0 else 0
            }        
            
        accuracy = sum(1 for p, r in zip(predictions, references) if p == r) / len(predictions)
        
        error_cases = []
        for pred, ref, input_text in zip(predictions, references, [text for text, _ in test_samples]):
            if pred != ref:
                error_cases.append({
                    'input': input_text[:100] + "...",
                    'predicted': pred,
                    'actual': ref
                })
        results = {
            'overall_metrics': {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1
            },
            'class_metrics': class_metrics,
            'confusion_matrix': cm.tolist(),
            'sample_size': len(predictions),
            'error_analysis': {
                'total_errors': len(error_cases),
                'error_rate': 1 - accuracy,
                'sample_errors': error_cases[:5]
            }
        }
        
        logger.info("\nEvaluation Results:")
        logger.info(f"Total Samples: {results['sample_size']}")
        logger.info("\nOverall Metrics:")
        for metric, value in results['overall_metrics'].items():
            logger.info(f"  {metric}: {value:.4f}")
        
        logger.info("\nClass-wise Metrics:")
        for class_name, metrics in results['class_metrics'].items():
            logger.info(f"\n{class_name}:")
            for metric, value in metrics.items():
                logger.info(f"  {metric}: {value:.4f}")
        
        return results
    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None
    
    


def load_test_data(dataset_path, test_size=0.02):
    with open(dataset_path, "r") as f:
        data = json.load(f)
    
    all_samples = [(f"Exercise: {sample['exercise']}\nJoint Positions: {sample['joint_positions']}\nTimestamps: {sample['timestamps']}", 
                    sample['label']) 
                   for exercise in data.values() 
                   for sample in exercise]
    
    _, test_data = train_test_split(all_samples, test_size=test_size, random_state=42)
    return test_data


test_data, model, tokenizer = load_model()
model.save_pretrained(os.path.join(base_path, "TinyLlama_fitness_chatbot"))
tokenizer.save_pretrained(os.path.join(base_path, "TinyLlama_fitness_chatbot"))
#TODO: EDIT MODEL PATH TO base_path
# backend_path = os.path.join(base_path, "fitness_backend")
# model_path = os.path.join(backend_path, "deepseek_fitness_chatbot")
# offload_folder = os.path.join(backend_path, "model_offload")
# print("---------LOADING MODEL---------")
# model = AutoModelForCausalLM.from_pretrained(
#     model_path,
#     trust_remote_code=True, 
#     device_map={"": torch.device("cpu")}, 
#     torch_dtype=torch.float32,
#     offload_folder=offload_folder,
#     offload_state_dict=True,
#     low_cpu_mem_usage=True
#     )
# print("-------LOADING TOKENIZER---------")
# tokenizer = AutoTokenizer.from_pretrained("deepseek-ai/deepseek-llm-7b-chat")
# test_data = load_test_data(os.path.join(base_path, "labeled_dataset.txt"))
print(f"test data: {test_data}")
results = evaluate_model(test_data, model, tokenizer)