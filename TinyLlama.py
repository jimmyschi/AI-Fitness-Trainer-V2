import torch
import os
import sys
import json
import logging
import traceback
import numpy as np
import bitsandbytes as bnb
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import onnx
import coremltools as ct
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig, TrainingArguments, Trainer, pipeline
from transformers.trainer_callback import EarlyStoppingCallback
from evaluate import load as load_metric
from datasets import Dataset, load_dataset
from peft import get_peft_model, LoraConfig, TaskType
from trl import SFTTrainer
from torch.fx import symbolic_trace
from torch.nn import functional as F
from functools import lru_cache
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
from sklearn.model_selection import train_test_split
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from read_input_files import process_video
from ExerciseAssessmentSystem import ExerciseAssessmentSystem
from ExerciseDataGenerator import ExerciseDataGenerator
from ModelEvaluator import ModelEvaluator

class TinyLlama():
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing TinyLlama")
        self.base_path = Path(__file__).resolve().parent
        if torch.backends.mps.is_available():
            device_map = torch.device("mps")
            dtype = torch.bfloat16
        elif torch.cuda.is_available():
            device_map = torch.device("cuda")
            dtype = torch.float16
        else:
            device_map = {"": torch.device("cpu")}
            dtype = torch.float32
        device_map = torch.device("cpu")
        dtype = torch.float32
        self.logger.info(f"Using device: {device_map}")
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        self.offload_path = os.path.join(self.base_path, "llama_model_offload")
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                torch_dtype=dtype,
                device_map=device_map,
                offload_folder=self.offload_path,
                use_cache=True,
                offload_state_dict=True,
                low_cpu_mem_usage=True
            )
            self.model.enable_input_require_grads()
            self.model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
            
            self.model.generation_config = GenerationConfig.from_pretrained(model_name)
            self.model.config.pad_token_id = self.model.generation_config.eos_token_id
            
        except Exception as e:
            self.logger.warning(f"Failed to load model: {e}")
            raise
        self.tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "left" #For better batch processing
        self.tokenizer.chat_template = "{% for message in messages %}<|im_start|>{{ message.role }}\n{{ message.content }}<|im_end|>\n{% endfor %}"
        
        #LoRa Configuration
        # lora_config = LoraConfig(
        #     r=8,
        #     lora_alpha=32,
        #     target_modules=["q_proj", "v_proj"],
        #     lora_dropout=0.05,
        #     bias="none",
        #     task_type="CAUSAL_LM"
        # )
        # self.model = get_peft_model(self.model, lora_config)
        # self.model.print_trainable_parameters()
    
    def train_tiny_llama(self):
        # Load or create dataset
        if not os.path.exists(os.path.join(self.base_path, "llama_labeled_dataset.json")):
            print("Creating Dataset...")
            labeled_dataset = self.create_dataset()
        else:
            print("Loading Dataset...")
            labeled_dataset = os.path.join(self.base_path, "llama_labeled_dataset.json")
        print(f"labeled_dataset type: {type(labeled_dataset)}")
        print(f"labeled_dataset: {labeled_dataset}")
        train_data, test_data = self.load_and_split_dataset(labeled_dataset)
        
        
        # Format data for SFTTrainer
        train_dataset = Dataset.from_list([{"text": f"{input_text}{output_text}"} for input_text, output_text in train_data])
        test_dataset = Dataset.from_list([{"text": f"{input_text}{output_text}"} for input_text, output_text in test_data])
        
        
        # Configure training arguments
        training_args = TrainingArguments(
            output_dir="./TinyLlama_finetuned",
            eval_strategy="steps",
            eval_steps=100,
            save_strategy="steps",
            save_steps=100,
            per_device_train_batch_size=16,
            per_device_eval_batch_size=16,
            num_train_epochs=5,
            save_total_limit=5,
            fp16=False, #Primarily for NVIDIA GPUs
            bf16=True, #For MPS, similar benefits to FP16
            load_best_model_at_end=True,
            logging_dir="./logs",
            gradient_accumulation_steps=8,
            learning_rate=1e-5,
            lr_scheduler_type="cosine",
            warmup_steps=200,
            gradient_checkpointing=True,
            optim="adamw_torch",
            max_grad_norm=0.3,
            weight_decay=0.01,
            use_mps_device=True
        )

        print("Initializing trainer...")
        trainer = SFTTrainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=test_dataset,
            processing_class=self.tokenizer
        )
        
        early_stopping_callback = EarlyStoppingCallback(early_stopping_patience=3) # patience is now early_stopping_patience
        trainer.add_callback(early_stopping_callback)

        print("Starting training...")
        trainer.train()
        
        try:
            training_history = trainer.state.log_history
            for log_entry in training_history:
                if "eval_loss" in log_entry:
                    epoch = log_entry["epoch"]
                    train_loss = log_entry["train_loss"]
                    eval_loss = log_entry["eval_loss"]
                    print(f"Epoch {epoch}: Train Loss: {train_loss:.4f}, Eval Loss: {eval_loss:.4f}")
        except Exception as e:
            print(f"Error getting training history: {e}")
        
        return test_data, self.model, self.tokenizer
    
    def convert_to_coreml(self, model, tokenizer, coreml_model_path):
        """Converts the PyTorch model to Core ML format with quantization."""
        print("COREML FUNCTION CALLED")
        try:
            # Ensure model is on CPU and in eval mode
            model = model.to("cpu")
            model.eval()
            
            # Prepare simple dummy inputs
            dummy_messages = [{"role": "user", "content": "test"}]
            dummy_chat_template = tokenizer.apply_chat_template(dummy_messages, tokenize=False)
            dummy_inputs = tokenizer(dummy_chat_template, return_tensors="pt")
            
            # Create a simpler wrapper that only uses input_ids
            class SimpleWrapper(torch.nn.Module):
                def __init__(self, model):
                    super().__init__()
                    self.model = model

                def forward(self, input_ids):
                    # Simplest possible forward pass
                    return self.model(input_ids=input_ids).logits

            wrapped_model = SimpleWrapper(model)
            wrapped_model.eval()
            
            # Create the simplest possible trace
            with torch.no_grad():
                traced_model = torch.jit.trace(
                    wrapped_model.forward,
                    (dummy_inputs["input_ids"],)
                )
            
            # Check CoreML tools version
            import coremltools as ct
            print(f"CoreML Tools version: {ct.__version__}")
            print(f"PyTorch version: {torch.__version__}")
            print(f"CoreML model: {coreml_model}")
            
            # Use the simplest possible conversion parameters
            # coreml_model = ct.convert(
            #     traced_model,
            #     inputs=[ct.TensorType(name="input_ids", shape=dummy_inputs["input_ids"].shape)],
            #     # No convert_to parameter - let it use the default
            #     convert_to="mlprogram",
            #     compute_units=ct.ComputeUnit.CPU_ONLY
            # )
            try:
                coreml_model = ct.convert(
                    traced_model,
                    convert_to="mlprogram"
                )
                print("CoreML conversion successful!")
            except Exception as e:
                print(f"CoreML conversion failed: {e}")
                import traceback
                traceback.print_exc()
                return


            
            # Make sure the path has the correct extension
            if not coreml_model_path.endswith('.mlpackage'):
                coreml_model_path = coreml_model_path.rsplit('.', 1)[0] + '.mlpackage'
            
            # Save without quantization first to see if basic conversion works
            temp_path = coreml_model_path + ".temp.mlmodel"
            coreml_model.save(temp_path)
            print(f"Basic model saved to {temp_path}")
            
            # Now try quantization if basic conversion succeeded
            try:
                quantized_model = ct.models.neural_network.quantization_utils.quantize_weights(
                    coreml_model, 
                    nbits=8
                )
                quantized_model.save(coreml_model_path)
                print(f"Model successfully converted and quantized to Core ML at: {coreml_model_path}")
            except Exception as e:
                print(f"Basic conversion succeeded but quantization failed: {e}")
                print("Keeping the unquantized model as fallback.")

        except Exception as e:
            print(f"Error converting to Core ML: {e}")
            import traceback
            traceback.print_exc()
            
            # Print more debugging information
            print("\nAdditional debugging information:")
            print(f"PyTorch version: {torch.__version__}")
            print(f"Available compute units: {[unit for unit in dir(ct.ComputeUnit) if not unit.startswith('_')]}")
            
    def format_keypoints(self, joint_positions, exercise_name, assessment_system):
        """Convert joint position dictionaries to a NumPy array format expected by ExerciseAssessmentSystem."""
        keypoints_list = []

        for frame in joint_positions:
            keypoints = np.zeros((33, 3))  # Assuming 33 total body landmarks
            # print(f"frame type: {type(frame)}")
            # print(f"frame in format_keypoints: {frame}")
            for joint_name, values in frame.items():
            #    print(f"joint_name: {joint_name} , values: {values}")
                try:
                    joint_index = assessment_system._get_joint_index(joint_name)
                    # print(f"joint_index in format_keypoints: {joint_index}")
                    if joint_index is not None:
                        keypoints[joint_index] = [values['x'], values['y'], values['z']]
                except (ValueError, KeyError) as e:
                    print(f"Error processing joint: {e}")
                    continue
            # print(f"keypoints in format_keypoints: {keypoints}")
            keypoints_list.append(keypoints)
         
        final_keypoints = np.array(keypoints_list)
        return final_keypoints
    
    
    def create_dataset(self):
        """
        Create and save the exercise dataset with proper error handling and validation.
        """
        assessment_system = ExerciseAssessmentSystem()
        dataset = []
        general_context = "Listed below is a workout video data for a particular exercise with its corresponding range of motion calculated in degrees as the maximum minus the minimum joint angle recorded across the entire video. Please provide feedback based on if correct form was used and provide specific explanations to determine if proper technique was used based on biomechanics and exercise science.\n\n"
        input_path = os.path.join(self.base_path, "training_input_videos")
        output_path = os.path.join(self.base_path, "training_output_videos")
        
        print(f"Input path: {input_path}")
        print(f"Output path: {output_path}")
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input path does not exist: {input_path}")
        
        os.makedirs(output_path, exist_ok=True)
        
        # Get list of exercise directories
        exercise_names = [name for name in os.listdir(input_path) 
                        if os.path.isdir(os.path.join(input_path, name))]
        
        if not exercise_names:
            raise ValueError(f"No exercise directories found in {input_path}")
        
        print(f"Found exercise directories: {exercise_names}")
        
        for exercise_type in exercise_names:
            print(f"\nProcessing exercise type: {exercise_type}")
            exercise_input_dir = os.path.join(input_path, exercise_type)
            exercise_output_dir = os.path.join(output_path, exercise_type)
            
            os.makedirs(exercise_output_dir, exist_ok=True)
            
            video_files = [f for f in os.listdir(exercise_input_dir) 
                        if f.endswith(('.mp4'))]
            
            if not video_files:
                print(f"No video files found in {exercise_input_dir}")
                continue
                
            print(f"Found {len(video_files)} video files")
            
            for video_file in video_files:
                print(f"\nProcessing video: {video_file}")
                input_video_path = os.path.join(exercise_input_dir, video_file)
                output_video_path = os.path.join(exercise_output_dir, f"processed_{video_file}")
                
                try:
                    timestamps, joint_positions = process_video(input_video_path, output_video_path, exercise_type)
                    joint_angles_str = ""
                    if not joint_positions:
                        print(f"No joint positions detected in {video_file}")
                        continue
                        
                    print(f"Detected {len(joint_positions)} frames of joint positions")
                    
                    keypoints = self.format_keypoints(joint_positions, exercise_type, assessment_system)
                    
                    if len(keypoints) == 0:
                        print(f"No valid keypoints generated for {video_file}")
                        continue
                    
                    # Calculate joint angles for each frame
                    joint_angles = []
                    for frame in keypoints:
                        try:
                            angles = assessment_system.calculate_joint_angles(
                                frame,  # Pass the NumPy array directly
                                exercise_type
                            )
                            if angles:
                                print(f"angles: {angles}")
                                joint_angles.append(angles)
                                joint_angles_str += ", ".join([f"{key.replace('_', ' ').title()}: {value:.2f}" for key, value in angles.items()]) + "; "
                        except Exception as e:
                            print(f"Error calculating joint angles for frame: {e}")
                            continue
                    print(f"full joint_angles: {joint_angles}")
                    # Get movement assessment
                    is_correct, feedback = assessment_system.assess_movement(exercise_type, keypoints, joint_angles)
                    print(f"is_correct: {is_correct}")
                    print(f"feedback: {feedback}")
                    if not feedback:  # Ensure we have some feedback
                        feedback = ["Exercise form appears correct"] if is_correct else ["Form needs improvement"]
                    rom = assessment_system.calculate_range_of_motion(joint_angles)
                    rom_str = "; ".join(f"{k.replace('_', ' ').title()}: {v:.2f}" for k, v in rom.items())
                    # joint_angles_str = joint_angles_str[:-2] #Remove trailing ;
                    # timestamps_str = ", ".join(map(str, timestamps))
                    
                    # Add to dataset with validation
                    sample = {
                        "context": general_context,
                        "exercise_name": exercise_type,
                        # "timestamps": timestamps_str,
                        "range_of_motion": rom_str,
                        "feedback": " ".join(feedback)
                    }
                    print(f"sample: {sample}")
                    # Validate sample before adding
                    if all(key in sample for key in ["context", "exercise_name", "range_of_motion", "feedback"]):
                        dataset.append(sample)
                        print(f"Successfully added sample for {video_file}")
                    else:
                        print(f"Invalid sample generated for {video_file}")
                    
                except Exception as e:
                    print(f"Error processing {video_file}: {e}")
                    continue
        
        if not dataset:
            raise ValueError("No valid samples were generated for the dataset")
        
        # Save dataset with proper error handling
        labeled_dataset_path = os.path.join(self.base_path, "llama_labeled_dataset.json")
        try:
            with open(labeled_dataset_path, "w") as f:
                json.dump(dataset, f, indent=4, default=str)  # Added default=str to handle non-serializable objects
            print(f"\nDataset successfully saved to {labeled_dataset_path}")
            print(f"Total samples in dataset: {len(dataset)}")
            return labeled_dataset_path
        except Exception as e:
            print(f"Error saving dataset: {e}")
            raise

    def load_and_split_dataset(self, dataset_path, test_size=0.2):
        """
        Load and split the dataset with proper validation and error handling.
        """
        print(f"Loading dataset from: {dataset_path}")
        
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
        
        if not all_samples:
            raise ValueError("No valid samples found in dataset")
        
        print(f"Processing {len(all_samples)} valid samples")
        
        # Split dataset
        train_data, test_data = train_test_split(
            all_samples, 
            test_size=test_size, 
            random_state=42
        )
        
        print(f"Split dataset into {len(train_data)} training and {len(test_data)} testing samples")
        
        return train_data, test_data


tiny_llama = TinyLlama()
# test_data, model, tokenizer = tiny_llama.train_tiny_llama()
# print(f"test_data: {test_data}")

# model.save_pretrained(os.path.join(tiny_llama.base_path, "TinyLlama_fitness_chatbot"))
# tokenizer.save_pretrained(os.path.join(tiny_llama.base_path, "TinyLlama_fitness_chatbot"))

# model_path = os.path.join(tiny_llama.base_path, "TinyLlama_fitness_chatbot")
# tokenizer_path = os.path.join(tiny_llama.base_path, "TinyLlama_fitness_chatbot")
# offload_path = os.path.join(tiny_llama.base_path, "llama_model_offload")
# coreml_path = os.path.join(tiny_llama.base_path, "TinyLlama_quantized.mlpackage")

# if torch.backends.mps.is_available():
#     device = torch.device("mps")
# elif torch.cuda.is_available():
#     device = torch.device("cuda")
# else:
#     device = torch.device("cpu")
# model = AutoModelForCausalLM.from_pretrained(
#     model_path,
#     trust_remote_code=True,
#     offload_folder = offload_path,
#     use_cache=True,
#     offload_state_dict=True,
#     low_cpu_mem_usage=True,
#     device_map=device
# ).to(device)
# tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
# tokenizer.pad_token = tokenizer.eos_token
# tokenizer.padding_side = "left" #For better batch processing
# tokenizer.chat_template ="{% for message in messages %}<|im_start|>{{ message.role }}\n{{ message.content }}<|im_end|>\n{% endfor %}"
# tiny_llama.convert_to_coreml(model, tokenizer, coreml_path)
# evaluator = ModelEvaluator(model, tokenizer, device)
# results = evaluator.evaluate_model(test_data)
# for metric, value in results.items():
#     print(f"Metric ({metric}): {value}")
