import numpy as np
from typing import List, Dict, Tuple

from ExerciseAssessmentSystem import ExerciseAssessmentSystem
class ExerciseDataGenerator:
    def __init__(self, assessment_system: ExerciseAssessmentSystem):
        self.assessment_system = assessment_system
    def generate_training_prompt(self, exercise_name: str, keypoints: np.ndarray, timestamps: List[float], is_correct: bool):
        """Generate training prompts for the model."""
        # Get assessment results
        assessment_result, feedback = self.assessment_system.assess_movement(
            exercise_name, keypoints
        )
        
        # Create context about the exercise
        joint_info = self.assessment_system.exercise_rules.get(exercise_name, {})
        
        # Format the prompt
        prompt = f"""Exercise Type: {exercise_name} Timestamp: {timestamps[0]:.2f}s Expected Joint Angles:"""
        
        # Add expected ranges
        for joint, rules in joint_info.items():
            prompt += f"- {joint.capitalize()}: {rules['min']}° to {rules['max']}°\n"
        
        # Add actual measurements and feedback
        prompt += "\nObserved Form Issues:\n"
        if feedback:
            for issue in feedback:
                prompt += f"- {issue}\n"
        else:
            prompt += "- No significant form issues detected\n"
            
        return prompt
    
    def label_dataset(self, exercise_type: str, joint_positions: List[np.ndarray], timestamps: List[float]):
        """Generate labeled dataset for training."""
        labeled_data = []
        
        for i, (positions, timestamp) in enumerate(zip(joint_positions, timestamps)):
            # Get assessment results
            is_correct, feedback = self.assessment_system.assess_movement(
                exercise_type, positions
            )
            
            # Generate prompt
            prompt = self.generate_training_prompt(
                exercise_type, positions, [timestamp], is_correct
            )
            
            # Generate target response
            target_response = self.generate_target_response(
                exercise_type, is_correct, feedback
            )
            
            labeled_data.append({
                "prompt": prompt,
                "target": target_response,
                "metadata": {
                    "exercise_type": exercise_type,
                    "timestamp": timestamp,
                    "is_correct": is_correct
                }
            })
            
        return labeled_data

    def generate_target_response(self, exercise_type: str, is_correct: bool, feedback: List[str]):
        """Generate target responses for training."""
        if is_correct:
            response = f"The {exercise_type} form is correct. "
            response += "Key points of good form observed:\n"
            response += self.get_exercise_good_form_points(exercise_type)
        else:
            response = f"The {exercise_type} form needs improvement. "
            response += "Specific issues identified:\n"
            for issue in feedback:
                response += f"- {issue}\n"
            response += "\nRecommended corrections:\n"
            response += self.get_exercise_corrections(exercise_type, feedback)
            
        return response

    def get_exercise_good_form_points(self, exercise_type: str):
        """Return exercise-specific good form points."""
        good_form_points = {
            "squat": """- Proper depth achieved
                        - Knees tracking over toes
                        - Neutral spine maintained
                        - Weight distributed properly""",
            "deadlift": """- Neutral spine maintained
                        - Bar path close to body
                        - Hips and shoulders rising together
                        - Proper hip hinge""",
            "bench press": """- Proper scapular retraction
                        - Elbows tucked appropriately
                        - Stable wrist position
                        - Full range of motion"""
        }
        return good_form_points.get(exercise_type, "- Proper form maintained")

    def get_exercise_corrections(self, exercise_type: str, feedback: List[str]):
        """Generate exercise-specific corrections based on feedback."""
        corrections = {
            "knee valgus": "Focus on pushing knees outward, in line with toes",
            "rounded back": "Maintain neutral spine by engaging core and focusing on hip hinge",
            "insufficient depth": "Work on mobility and gradually increase depth while maintaining form",
            "elbow flare": "Keep elbows tucked closer to body at roughly 45-degree angle"
        }
        
        response = ""
        for issue in feedback:
            for key, correction in corrections.items():
                if key in issue.lower():
                    response += f"- {correction}\n"
        
        return response if response else "- Focus on maintaining proper form throughout the movement\n"
