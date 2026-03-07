# llama_model.py
import os
import random
import re
import time
import traceback
# import psutil
import logging 
import numpy as np
import sys
print(f"sys.path: {sys.path}")
from flask import Flask, request, jsonify

from llama_cpp import Llama

from ExerciseAssessmentSystem  import ExerciseAssessmentSystem

class BlokeLlamaChatbot:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        self.logger.info("Initializing BlokeLlamaChatbot")
        
        self.logger.info("Loading base model...")
        self.model = self._load_base_model()

    def _load_base_model(self):
        """Load the base TinyLlama model without optimizations."""
        try:
            # model_path = os.path.join(
            #     "/app", # changed from os.path.expanduser("~/Downloads")
            #     "tinyllama-1.1b-chat-v0.3.Q8_0.gguf"
            # )
            model_path = "/app/tinyllama-1.1b-chat-v0.3.Q8_0.gguf"
            
            # Ensure the model file exists
            if not os.path.exists(model_path):
                self.logger.info(f"file not found at {model_path}")
                raise FileNotFoundError(f"Model file not found at {model_path}")
            
            stop = ["Q", "\n"]

            # Initialize the model with appropriate parameters
            model = Llama(
                model_path=model_path,
                n_ctx=4096,  # Context window size
                n_batch=512,  # Batch size
            )
            
            return model
        except Exception as e:
            self.logger.error(f"Failed to load base model: {e}")
            raise
    
    def generate_response(self, prompt_text: str):
        """Generate response with caching for repeated prompts"""
        self.logger.info("Generate Response")
        self.logger.info(f"prompt_text: {prompt_text}")
        start_time = time.time()
        try:
            start_time = time.time()
            
            output = self.model(
                prompt=prompt_text,
                max_tokens=500,
                temperature=random.uniform(0.7,1.0),
                top_p=0.9,
                top_k=random.randint(40,60),
                repeat_penalty=random.uniform(1.1,1.3),
                # stop=["###", "\n\n"],
            )
            generated_text = output['choices'][0]['text']
            # Find the starting index after "<|im_start|>assistant"
            start_index = generated_text.find("<|im_start|>assistant") + len("<|im_start|>assistant")
            # Extract the desired output
            response = generated_text[start_index:].strip()
            # Clean up the response
            response = re.sub(r'<[^>]+>', '', response)
            response = re.sub(r'\s+', ' ', response)
            
            end_time = time.time() - start_time
            self.logger.info(f"Inference Time: {end_time}")
            self.logger.info(f"Response: {response}")
            return response
        except Exception as e:
            self.logger.info(f"An error occurred in generate_test_response: {e}")
            traceback.print_exc()
            return None

    def generate_test_response(self):
        try:
            start_time = time.time()
            prompt = """<|im_start|>user
            Biomechanical Analysis of Bench Press Form

            Given the following precise joint angle measurements:
            - Right Elbow Angle: 135.28°
            - Left Elbow Angle: 56.13°
            - Right Shoulder Angle: 91.77°
            - Left Shoulder Angle: 112.97°

            Provide a comprehensive, unique technical assessment focusing on:
            1. Detailed analysis of each angle's implications for bench press technique
            2. Specific biomechanical recommendations for form improvement
            3. Potential compensation patterns or injury risks
            4. Precise adjustments to optimize movement efficiency

            Your response should be original, technical, and provide actionable insights.<|im_end|>
            <|im_start|>assistant
            """
            print(f"Base Model Input Text: {prompt}")
            self._measure_resources("Before Inference")
            
            output = self.model(
                prompt=prompt,
                max_tokens=500,
                temperature=random.uniform(0.7,1.0),
                top_p=0.9,
                top_k=random.randint(40,60),
                repeat_penalty=random.uniform(1.1,1.3),
            )
            generated_text = output['choices'][0]['text']
            response = re.sub(r'<[^>]+>', '', generated_text) #remove any html tags
            end_time = time.time() - start_time
            print(f"Inference Time: {end_time}")
            return response
        except Exception as e:
            print(f"An error occurred in generate_test_response: {e}")
            traceback.print_exc()
            return None
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
                    self.logger.info(f"Error processing joint: {e}")
                    continue
            # print(f"keypoints in format_keypoints: {keypoints}")
            keypoints_list.append(keypoints)
         
        final_keypoints = np.array(keypoints_list)
        return final_keypoints
    
    def video_feedback(self, joint_positions, timestamps, exercise_type):
        """_summary_

        Args:
            exercise_type (str): _description_
            joint_positions (List[Dict]): _description_
            timestamps (List[float]): _description_
            max_joint (str): _description_
            num_frames (int, optional): _description_. Defaults to 5.

        Returns:
            _type_: _description_
        """
        print("LlamaChatbot Video Feedback")
        assessment_system = ExerciseAssessmentSystem()
        keypoints = self.format_keypoints(joint_positions=joint_positions, exercise_name=exercise_type,assessment_system=assessment_system)
        self.logger.info(f"keypoints: {keypoints}")
        joint_angles = []
        for frame in keypoints:
            angles = assessment_system.calculate_joint_angles(keypoints=frame, exercise_type=exercise_type)
            if angles:
                print(f"angles: {angles}")
                joint_angles.append(angles)
        self.logger.info(f"joint_angles: {joint_angles}")
        
        rom = assessment_system.calculate_range_of_motion(joint_angles)

        rom_str = self.create_llama_prompt(rom)
        prompt_text = """<|im_start|>user
            Biomechanical Analysis of Bench Press Form

            Given the following precise joint angle measurements:
            {rom_str}

            Provide a comprehensive, unique technical assessment focusing on:
            1. Detailed analysis of each angle's implications for bench press technique
            2. Specific biomechanical recommendations for form improvement
            3. Potential compensation patterns or injury risks
            4. Precise adjustments to optimize movement efficiency

            Your response should be original, technical, and provide actionable insights.<|im_end|>
            <|im_start|>assistant
            """
        # self.logger.info(f"prompt_text: {prompt_text}")
        
        return self.generate_response(prompt_text)
    
    def create_llama_prompt(self, rom):
        rom_str = "; ".join(f"{k.replace('_', ' ').title()}: {v:.2f}" for k, v in rom.items())
        self.logger.info(f"rom_string: {rom_str}")
        return rom_str

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route('/generate_text', methods=['POST'])
def generate_text_endpoint():
    data = request.get_json()
    logger.info(f"Request data: {data}")
    joint_positions = data.get('joint_positions')
    timestamps = data.get('timestamps')
    exercise_type = data.get('exercise_type')
    
    logger.info(f"Extracted joint_positions (first 5): {joint_positions[:5] if joint_positions else None}")
    logger.info(f"Extracted timestamps (first 5): {timestamps[:5] if timestamps else None}")
    logger.info(f"Extracted exercise_type: {exercise_type}")
        
        
    model = BlokeLlamaChatbot()
    logger.info("BlokeLlamaChatbot initialized")
    try:
        feedback = model.video_feedback(joint_positions, timestamps, exercise_type)
        logger.info(f"Generated feedback: {feedback}")
        return jsonify({
            'chatbot_response' : feedback
        })
    except Exception as e:
        logger.error(f"Error during video_feedback: {e}", exc_info=True)
        return jsonify({'error' : str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Flask app...")
    app.run(host='0.0.0.0', port=8001)
    