import numpy as np
from typing import List, Dict, Tuple
class ExerciseAssessmentSystem:
    def __init__(self):
        # Joint indices mapping
        self.exercise_joint_indices = {
            "bench press": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
            "barbell biceps curl": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
            "chest fly machine": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
            "deadlift": [24, 23, 26, 25, 28, 27],  # Hips, Knees, Ankles
            "hammer curl": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
            "hip thrust": [24, 23, 26, 25, 28, 27],  # Hips, Knees, Ankles
            "incline bench press": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
            "lat pulldown": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
            "lateral raise": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
            "leg extension": [24, 23, 26, 25, 28, 27],  # Hips, Knees, Ankles
            "leg raises": [24, 23, 26, 25, 28, 27],  # Hips, Knees, Ankles
            "plank": [12, 11, 24, 23, 26, 25],  # Shoulders, Hips, Knees
            "pull up": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
            "push-up": [12, 11, 14, 13, 16, 15, 24, 23],  # Shoulders, Elbows, Wrists
            "shoulder press": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
            "squat": [24, 23, 26, 25, 28, 27],  # Hips, Knees, Ankles
            "t bar row": [12, 11, 14, 13, 24, 23],  # Shoulders, Elbows, Hips
            "tricep dips": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
            "tricep pushdown": [12, 11, 14, 13, 16, 15]  # Shoulders, Elbows, Wrists
        }

        self.exercise_joint_configs = {
            "bench press": {
                "elbow_angle": (11, 13, 15),  # Left Elbow, Left Wrist, Right Wrist
                "opposite_elbow_angle": (12, 14, 16), # Right Elbow, Right Wrist, Left Wrist
                "shoulder_angle": (23, 11, 13), # Left Hip, Left Shoulder, Left Elbow
                "opposite_shoulder_angle": (24, 12, 14) # Right Hip, Right Shoulder, Right Elbow
            },
            "barbell biceps curl": {
                "elbow_angle": (11, 13, 15),
                "opposite_elbow_angle": (12, 14, 16),
            },
            "chest fly machine": {
                "shoulder_angle": (11, 13, 15), # Left Shoulder, Left Elbow, Left Wrist
                "opposite_shoulder_angle": (12, 14, 16), # Right Shoulder, Right Elbow, Right Wrist
            },
            "deadlift": {
                "knee_angle": (23, 25, 27),
                "opposite_knee_angle": (24, 26, 28),
                "hip_angle": (25, 23, 11), # Left Knee, Left Hip, Left Shoulder
                "opposite_hip_angle": (26, 24, 12), # Right Knee, Right Hip, Right Shoulder
            },
            "hammer curl": {
                "elbow_angle": (11, 13, 15),
                "opposite_elbow_angle": (12, 14, 16),
            },
            "hip thrust": {
                "knee_angle": (23, 25, 27),
                "opposite_knee_angle": (24, 26, 28),
                "hip_angle": (11, 23, 25), # Left Shoulder, Left Hip, Left Knee
                "opposite_hip_angle": (12, 24, 26), # Right Shoulder, Right Hip, Right Knee
            },
            "incline bench press": {
                "elbow_angle": (11, 13, 15),
                "opposite_elbow_angle": (12, 14, 16),
                "shoulder_angle": (23, 11, 13), # Left Hip, Left Shoulder, Left Elbow
                "opposite_shoulder_angle": (24, 12, 14) # Right Hip, Right Shoulder, Right Elbow
            },
            "lat pulldown": {
                "elbow_angle": (11, 13, 15),
                "opposite_elbow_angle": (12, 14, 16),
            },
            "lateral raise": {
                "shoulder_angle": (11, 13, 15), # Left Shoulder, Left Elbow, Left Wrist
                "opposite_shoulder_angle": (12, 14, 16), # Right Shoulder, Right Elbow, Right Wrist
            },
            "leg extension": {
                "knee_angle": (23, 25, 27),
                "opposite_knee_angle": (24, 26, 28),
            },
            "leg raises": {
                "hip_angle": (23, 25, 27), # Left Hip, Left Knee, Left Ankle
                "opposite_hip_angle": (24, 26, 28), # Right Hip, Right Knee, Right Ankle
            },
            "plank": {
                "shoulder_angle": (11, 13, 23), # Left Shoulder, Left Elbow, Left Hip
                "opposite_shoulder_angle": (12, 14, 24), # Right Shoulder, Right Elbow, Right Hip
                "hip_angle": (13, 23, 25), # Left Elbow, Left Hip, Left Knee
                "opposite_hip_angle": (14, 24, 26), # Right Elbow, Right Hip, Right Knee
            },
            "pull up": {
                "elbow_angle": (11, 13, 15),
                "opposite_elbow_angle": (12, 14, 16),
            },
            "push-up": {
                "elbow_angle": (11, 13, 15),
                "opposite_elbow_angle": (12, 14, 16),
                "shoulder_angle": (23, 11, 13), # Left Hip, Left Shoulder, Left Elbow
                "opposite_shoulder_angle": (24, 12, 14) # Right Hip, Right Shoulder, Right Elbow
            },
            "shoulder press": {
                "shoulder_angle": (11, 13, 15), # Left Shoulder, Left Elbow, Left Wrist
                "opposite_shoulder_angle": (12, 14, 16), # Right Shoulder, Right Elbow, Right Wrist
            },
            "squat": {
                "knee_angle": (23, 25, 27),
                "opposite_knee_angle": (24, 26, 28),
                "hip_angle": (11, 23, 25), # Left Shoulder, Left Hip, Left Knee
                "opposite_hip_angle": (12, 24, 26), # Right Shoulder, Right Hip, Right Knee
            },
            "t bar row": {
                "elbow_angle": (11, 13, 15),
                "opposite_elbow_angle": (12, 14, 16),
                "hip_angle": (13, 23, 25), # Left Elbow, Left Hip, Left Knee
                "opposite_hip_angle": (14, 24, 26), # Right Elbow, Right Hip, Right Knee
            }
        }
        # Define joint angle ranges for each exercise
        self.exercise_rules = {
            "bench press": {
                "elbow_angle": {"min": 90, "max": 160, "critical": True},  # Example values, adjust as needed
                "opposite_elbow_angle": {"min": 90, "max": 160, "critical": True},
                "shoulder_angle": {"min": 45, "max": 75, "critical": True},
                "opposite_shoulder_angle": {"min": 45, "max": 75, "critical": True}
            },
            "barbell biceps curl": {
                "elbow_angle": {"min": 30, "max": 150, "critical": True},
                "opposite_elbow_angle": {"min": 30, "max": 150, "critical": True}
            },
            "chest fly machine": {
                "shoulder_angle": {"min": 30, "max": 120, "critical": True},
                "opposite_shoulder_angle": {"min": 30, "max": 120, "critical": True}
            },
            "deadlift": {
                "knee_angle": {"min": 20, "max": 90, "critical": True},
                "opposite_knee_angle": {"min": 20, "max": 90, "critical": True},
                "hip_angle": {"min": 70, "max": 120, "critical": True},
                "opposite_hip_angle": {"min": 70, "max": 120, "critical": True}
            },
            "hammer curl": {
                "elbow_angle": {"min": 30, "max": 50, "critical": True},
                "opposite_elbow_angle": {"min": 30, "max": 50, "critical": True}
            },
            "hip thrust": {
                "knee_angle": {"min": 70, "max": 120, "critical": True},
                "opposite_knee_angle": {"min": 70, "max": 120, "critical": True},
                "hip_angle": {"min": 90, "max": 180, "critical": True},
                "opposite_hip_angle": {"min": 90, "max": 180, "critical": True}
            },
            "incline bench press": {
                "elbow_angle": {"min": 90, "max": 160, "critical": True},
                "opposite_elbow_angle": {"min": 90, "max": 160, "critical": True},
                "shoulder_angle": {"min": 45, "max": 75, "critical": True},
                "opposite_shoulder_angle": {"min": 45, "max": 75, "critical": True}
            },
            "lat pulldown": {
                "elbow_angle": {"min": 30, "max": 160, "critical": True},
                "opposite_elbow_angle": {"min": 30, "max": 160, "critical": True}
            },
            "lateral raise": {
                "shoulder_angle": {"min": 10, "max": 90, "critical": True},
                "opposite_shoulder_angle": {"min": 10, "max": 90, "critical": True}
            },
            "leg extension": {
                "knee_angle": {"min": 0, "max": 90, "critical": True},
                "opposite_knee_angle": {"min": 0, "max": 90, "critical": True}
            },
            "leg raises": {
                "hip_angle": {"min": 30, "max": 90, "critical": True},
                "opposite_hip_angle": {"min": 30, "max": 90, "critical": True}
            },
            "plank": {
                "shoulder_angle": {"min": 70, "max": 110, "critical": True},
                "opposite_shoulder_angle": {"min": 70, "max": 110, "critical": True},
                "hip_angle": {"min": 160, "max": 180, "critical": True},
                "opposite_hip_angle": {"min": 160, "max": 180, "critical": True}
            },
            "pull up": {
                "elbow_angle": {"min": 0, "max": 90, "critical": True},
                "opposite_elbow_angle": {"min": 0, "max": 90, "critical": True}
            },
            "push-up": {
                "elbow_angle": {"min": 30, "max": 160, "critical": True},
                "opposite_elbow_angle": {"min": 30, "max": 160, "critical": True},
                "shoulder_angle": {"min": 45, "max": 90, "critical": True},
                "opposite_shoulder_angle": {"min": 45, "max": 90, "critical": True}
            },
            "shoulder press": {
                "shoulder_angle": {"min": 45, "max": 90, "critical": True},
                "opposite_shoulder_angle": {"min": 45, "max": 90, "critical": True}
            },
            "squat": {
                "knee_angle": {"min": 80, "max": 140, "critical": True},
                "opposite_knee_angle": {"min": 80, "max": 140, "critical": True},
                "hip_angle": {"min": 60, "max": 120, "critical": True},
                "opposite_hip_angle": {"min": 60, "max": 120, "critical": True}
            },
            "t bar row": {
                "elbow_angle": {"min": 0, "max": 90, "critical": True},
                "opposite_elbow_angle": {"min": 0, "max": 90, "critical": True},
                "hip_angle": {"min": 0, "max": 0, "critical": True},  # Or adjust as needed
                "opposite_hip_angle": {"min": 0, "max": 0, "critical": True} # Or adjust as needed

            },
            "tricep dips": {
                "elbow_angle": {"min": 30, "max": 160, "critical": True},
                "opposite_elbow_angle": {"min": 30, "max": 160, "critical": True}
            },
            "tricep pushdown": {
                "elbow_angle": {"min": 30, "max": 160, "critical": True},
                "opposite_elbow_angle": {"min": 30, "max": 160, "critical": True}
            }
        }

    def calculate_joint_angles(self, keypoints: np.ndarray, exercise_type: str):
        """
        Calculate joint angles from keypoints. For each exercise, we need three points to calculate
        an angle.
        - Point 1: anchor point 
        - Point 2: joint being measured
        - Point 3: end point
        
        Args:
            keypoints: Numpy array of shape (N, 3) containing joint coordinates
            exercise_type: name of exercise to evaluate
            
        Returns:
            Dictionary of joint angles
        """
        if exercise_type not in self.exercise_joint_configs:
            raise ValueError(f"Unknown exercise type: {exercise_type}")
        
        joint_config = self.exercise_joint_configs[exercise_type]
        # print(f"joint_config in calaculate_joint_angles: {joint_config}")
        angles = {}
        
        for angle_name, (point1_index, point2_index, point3_idx) in joint_config.items():
            try:
                point1 = keypoints[point1_index] #Anchor point
                point2 = keypoints[point2_index] #Joint being measured
                point3 = keypoints[point3_idx] #End point
                
                #Calculate vectors
                vector1 = point2 - point1
                vector2 = point3 - point2
                
                #Skip if any vector has zero length
                if np.all(vector1 == 0) or np.all(vector2 == 0):
                    print(f"Warning: Zero vector detected for {angle_name}")
                    continue
                
                #Calculate angle using dot product
                dot_product = np.dot(vector1, vector2)
                norms = np.linalg.norm(vector1) * np.linalg.norm(vector2)
                
                if norms != 0:
                    cos_angle = dot_product / norms
                    cos_angle = np.clip(cos_angle, -1.0, 1.0) #Handle numerical errors
                    angle_rad = np.arccos(cos_angle)
                    angle_deg = np.degrees(angle_rad)
                    angles[angle_name] = angle_deg
                else:
                    print(f"Warning: very small vector detected for {angle_name}")
            except Exception as e:
                print(f"Error calculating angle {angle_name}: {e}")
                continue
        return angles
    
    def calculate_range_of_motion(self, joint_angles):
        """Range of motioon = max(joint_angle) - min(joint_angle)

        Args:
            joint_angles (List[Dict]): dictionary for relevant joint angles for a particular exercise 
            as the key and value is the angle in degrees. List of dicts for each timestamp.
        """
        range_of_motion = {}
        if not joint_angles:
            return range_of_motion
        
        for joint_name in joint_angles[0].keys():
            angles = [frame[joint_name] for frame in joint_angles if frame and joint_name in frame]
            if angles:
                max_angle = np.max(angles)
                min_angle = np.min(angles)
                range_of_motion[joint_name] = max_angle - min_angle
            else:
                range_of_motion[joint_name] = 0
        return range_of_motion
    
    def _get_joint_name(self, joint_index: int):
        """Map joint index to joint name."""
        joint_mapping = {
            11: "right_shoulder",
            12: "left_shoulder",
            13: "right_elbow",
            14: "left_elbow",
            15: "right_wrist",
            16: "left_wrist",
            23: "right_hip",
            24: "left_hip",
            25: "right_knee",
            26: "left_knee",
            27: "right_ankle",
            28: "left_ankle"
        }
        try: 
            joint_name = joint_mapping[joint_index]
            print(f"Joint name: {joint_name}")
            return joint_name
        except KeyError:
            print(f"Joint index: {joint_index} not found.")
            raise ValueError(f"Joint index {joint_index} not found.")
    def _get_joint_index(self, joint_name: str):
        """Map joint name to joint index."""
        joint_mapping = {
            "right_shoulder": 11,
            "left_shoulder": 12,
            "right_elbow": 13,
            "left_elbow": 14,
            "right_wrist": 15,
            "left_wrist": 16,
            "right_hip": 23,
            "left_hip": 24,
            "right_knee": 25,
            "left_knee": 26,
            "right_ankle": 27,
            "left_ankle": 28
        }
        try:
            return joint_mapping.get(joint_name)
        except KeyError:
                raise ValueError(f"Joint name '{joint_name}' not found.")

    def assess_movement(self, 
                       exercise_name: str, 
                       keypoints: np.ndarray, 
                       joint_angles):
        """
        Assess if an exercise movement is being performed correctly.
        
        Args:
            exercise_name: Name of the exercise
            keypoints: Numpy array of shape (N, 3) containing joint coordinates
            frame_idx: Current frame index for temporal analysis
            
        Returns:
            Tuple of (is_correct, list of feedback messages)
        """
        print("ASSESS MOVEMENT CALLED...")
        print(f"joint_angles: {joint_angles}")
        if exercise_name not in self.exercise_joint_indices:
            return False, ["Unknown exercise"]

        joint_indices = self.exercise_joint_indices[exercise_name]
        print(f"joint_indices in access_movement: {joint_indices}")
        # angles = self.calculate_joint_angles(keypoints, joint_indices)
        
        feedback = []
        is_correct = True

        # Get exercise-specific rules
        rules = self.exercise_rules.get(exercise_name)
        print(f"exercise rules for ({exercise_name}): {rules}")
        if not rules:
            return False, [f"No assessment rules defined for {exercise_name}"]

        # Check each joint against its rules
        for joint_name, angle_rules in rules.items():
            print(f"joint_name in assess_movement: {joint_name}")
            if joint_name in joint_angles:
                print("CONDITION TRUE")
                angle = joint_angles[joint_name]
                
                # Check if angle is within acceptable range
                if angle < angle_rules["min"] or angle > angle_rules["max"]:
                    is_correct = False if angle_rules["critical"] else is_correct
                    feedback.append(
                        f"{joint_name.capitalize()} angle ({angle:.1f}°) outside "
                        f"acceptable range ({angle_rules['min']}° - {angle_rules['max']}°)"
                    )
                else:
                    feedback.append(
                        f"{joint_name.capitalize()} angle ({angle:.1f}°) inside "
                        f"acceptable range ({angle_rules['min']}° - {angle_rules['max']}°)"
                    )
        print(f"feedback before checking specific rules: {feedback}")
        # Add exercise-specific checks
        specific_feedback = self._check_exercise_specific_rules(
            exercise_name, joint_angles, keypoints
        )
        if specific_feedback:
            print(f"specific feedback: {specific_feedback}")
            feedback.extend(specific_feedback)
            is_correct = False

        return is_correct, feedback

    def _check_exercise_specific_rules(self, 
                                     exercise_name: str, 
                                     angles: Dict[str, float], 
                                     keypoints: np.ndarray):
        """
        Apply exercise-specific rules and checks.
        
        Args:
            exercise_name: Name of the exercise
            angles: Dictionary of calculated joint angles
            keypoints: Numpy array of joint coordinates
            
        Returns:
            List of feedback messages
        """
        feedback = []
        
        if exercise_name == "squat": 
            if self._detect_knee_valgus(keypoints):
                feedback.append("Knee valgus detected - knees caving inward")   
            if "hip" in angles and angles["hip"] < 70:
                feedback.append("Insufficient squat depth")        
        elif exercise_name == "deadlift":
            if self._detect_rounded_back(keypoints):
                feedback.append("Rounded back detected - maintain neutral spine")
            if self._check_bar_path(keypoints):
                feedback.append("Bar path not vertical - keep bar close to legs")   
        elif exercise_name == "bench press":
            if self._check_scapular_retraction(keypoints):
                feedback.append("Improve scapular retraction - pull shoulders back")
            print(f"{exercise_name} feedback after scapular retraction: {feedback}")
            # if self._check_elbow_flare(keypoints):
            #     feedback.append("Excessive elbow flare - keep elbows tucked")
        elif exercise_name == "incline bench press":
            if self._check_scapular_retraction(keypoints):
                feedback.append("Improve scapular retraction - pull shoulders back")
            # if self._check_elbow_flare(keypoints):
            #     feedback.append("Excessive elbow flare - keep elbows tucked")
        elif exercise_name == "barbell biceps curl":
            if self._check_scapular_retraction(keypoints):
                feedback.append("Improve scapular retraction - pull shoulders back")
            # if self._check_elbow_flare(keypoints):
            #     feedback.append("Excessive elbow flare - keep elbows tucked")
        elif exercise_name == "hammer curl":
            if self._check_scapular_retraction(keypoints):
                feedback.append("Improve scapular retraction - pull shoulders back")
            # if self._check_elbow_flare(keypoints):
            #     feedback.append("Excessive elbow flare - keep elbows tucked")
        elif exercise_name == "chest fly machine":
            if self._detect_rounded_shoulders(keypoints):
                feedback.append("Excessive rounded shoulder - keep shoulders back to keep tension on the chest")
            # if self._check_elbow_flare(keypoints):
            #     feedback.append("Excessive elbow flare - keep elbows tucked")
        elif exercise_name == "hip thrust":
            if self._check_hip_extension(keypoints):
                feedback.append("Ensure full hip extension at the top")
        elif exercise_name == "lat pulldown":
            if self._check_scapular_retraction(keypoints):
                feedback.append("Improve scapular retraction - pull shoulders back")
        elif exercise_name == "lat raises":
            feedback.append("Form appears correct.")
            # if self._check_elbow_flare(keypoints):
            #     feedback.append("Excessive elbow flare - keep elbows tucked")
        elif exercise_name == "pull up":
            if self._check_scapular_retraction(keypoints):
                feedback.append("Improve scapular retraction - pull shoulders back")
        elif exercise_name == "push-up":
            if self._check_core_engagement(keypoints):
                feedback.append("Keep core tight and avoid sagging hips")
        elif exercise_name == "shoulder press":
            feedback.append("Form appears correct.")
            # if self._check_elbow_flare(keypoints):
            #     feedback.append("Excessive elbow flare - keep elbows tucked")
        elif exercise_name == "leg raises":
            if self._check_pelvic_stability(keypoints):
                feedback.append("Keep pelvis stable to avoid excessive lower back strain")
        elif exercise_name == "leg extension":
            if self._check_pelvic_stability(keypoints):
                feedback.append("Keep pelvis stable to avoid excessive lower back strain")
        elif exercise_name == "tricp dips":
            if self._check_scapular_retraction(keypoints):
                feedback.append("Improve scapular retraction - pull shoulders back")
            # if self._check_elbow_flare(keypoints):
            #     feedback.append("Excessive elbow flare - keep elbows tucked")
        elif exercise_name == "tricep pushdown":
            if self._check_scapular_retraction(keypoints):
                feedback.append("Improve scapular retraction - pull shoulders back")
            # if self._check_elbow_flare(keypoints):
            #     feedback.append("Excessive elbow flare - keep elbows tucked")
        return feedback

    def _detect_knee_valgus(self, keypoints: np.ndarray):
        """
        Detect knee valgus (knees caving inward) using MediaPipe landmarks.
        
        Args:
            keypoints: numpy array containing MediaPipe pose landmarks
            
        Returns:
            bool: True if knee valgus is detected, False otherwise
        """
        # MediaPipe indices for relevant joints
        LEFT_HIP = 23
        RIGHT_HIP = 24
        LEFT_KNEE = 25
        RIGHT_KNEE = 26
        LEFT_ANKLE = 27
        RIGHT_ANKLE = 28
        
        # Get joint coordinates
        left_hip = keypoints[LEFT_HIP]
        right_hip = keypoints[RIGHT_HIP]
        left_knee = keypoints[LEFT_KNEE]
        right_knee = keypoints[RIGHT_KNEE]
        left_ankle = keypoints[LEFT_ANKLE]
        right_ankle = keypoints[RIGHT_ANKLE]
        
        # Calculate vectors for knee alignment
        left_hip_knee = left_knee - left_hip
        right_hip_knee = right_knee - right_hip
        left_knee_ankle = left_ankle - left_knee
        right_knee_ankle = right_ankle - right_knee
        
        # Calculate angles between upper and lower leg
        left_angle = np.arccos(np.dot(left_hip_knee, left_knee_ankle) / 
                            (np.linalg.norm(left_hip_knee) * np.linalg.norm(left_knee_ankle)))
        right_angle = np.arccos(np.dot(right_hip_knee, right_knee_ankle) /
                            (np.linalg.norm(right_hip_knee) * np.linalg.norm(right_knee_ankle)))
        
        # Convert to degrees
        left_angle = np.degrees(left_angle)
        right_angle = np.degrees(right_angle)
        
        # Check for knee valgus (angle threshold is typically around 165 degrees)
        return left_angle < 165 or right_angle < 165

    def _detect_rounded_back(self, keypoints: np.ndarray):
        """
        Detect rounded back during deadlift using MediaPipe landmarks.
        
        Args:
            keypoints: numpy array containing MediaPipe pose landmarks
            
        Returns:
            bool: True if rounded back is detected, False otherwise
        """
        # MediaPipe indices for spine alignment
        NOSE = 0
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        LEFT_HIP = 23
        RIGHT_HIP = 24
        
        # Get midpoints for shoulders and hips
        shoulder_mid = (keypoints[LEFT_SHOULDER] + keypoints[RIGHT_SHOULDER]) / 2
        hip_mid = (keypoints[LEFT_HIP] + keypoints[RIGHT_HIP]) / 2
        
        # Calculate spine vectors
        upper_spine = shoulder_mid - keypoints[NOSE]
        lower_spine = hip_mid - shoulder_mid
        
        # Calculate angle between spine segments
        angle = np.arccos(np.dot(upper_spine, lower_spine) /
                        (np.linalg.norm(upper_spine) * np.linalg.norm(lower_spine)))
        angle = np.degrees(angle)
        
        # Return True if spine is rounded (angle less than 170 degrees)
        return angle < 170

    def _check_bar_path(self, keypoints: np.ndarray):
        """
        Check if bar path is vertical during deadlift using MediaPipe landmarks.
        
        Args:
            keypoints: numpy array containing MediaPipe pose landmarks
            
        Returns:
            bool: True if bar path deviates significantly from vertical, False otherwise
        """
        # MediaPipe indices for wrists (to track bar position)
        LEFT_WRIST = 15
        RIGHT_WRIST = 16
        
        # Use wrist positions as proxy for bar position
        wrist_mid = (keypoints[LEFT_WRIST] + keypoints[RIGHT_WRIST]) / 2
        
        # Store wrist positions if not already tracking
        if not hasattr(self, 'bar_positions'):
            self.bar_positions = []
        self.bar_positions.append(wrist_mid)
        
        # Only check if we have enough positions
        if len(self.bar_positions) < 3:
            return False
        
        # Calculate maximum horizontal deviation
        start_x = self.bar_positions[0][0]
        max_deviation = max(abs(pos[0] - start_x) for pos in self.bar_positions)
        
        # Clear positions if list gets too long
        if len(self.bar_positions) > 30:  # About 1 second at 30fps
            self.bar_positions = []
        
        # Return True if deviation is more than threshold (adjusted for MediaPipe coordinates)
        return max_deviation > 0.1  # Threshold in MediaPipe coordinate space

    def _check_scapular_retraction(self, keypoints: np.ndarray):
        """
        Check proper scapular retraction using MediaPipe landmarks.
        
        Args:
            keypoints: numpy array containing MediaPipe pose landmarks
            
        Returns:
            bool: True if insufficient scapular retraction, False otherwise
        """
        # MediaPipe indices for shoulders
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        
        # Calculate current shoulder width
        shoulder_width = np.linalg.norm(keypoints[RIGHT_SHOULDER] - keypoints[LEFT_SHOULDER])
        print(f"shoulder_width: {shoulder_width}")
        # Initialize reference width if not set
        if not hasattr(self, 'reference_shoulder_width'):
            self.reference_shoulder_width = shoulder_width
        
        # Return True if shoulders are too wide apart (indicates lack of retraction)
        return shoulder_width > self.reference_shoulder_width * 1.1


    def _check_elbow_flare(self, keypoints: np.ndarray):
        """
        Check for excessive elbow flare using MediaPipe landmarks.
        
        Args:
            keypoints: numpy array containing MediaPipe pose landmarks
            
        Returns:
            bool: True if excessive elbow flare detected, False otherwise
        """
        # MediaPipe indices for relevant joints
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        LEFT_ELBOW = 13
        RIGHT_ELBOW = 14
        
        # Calculate vectors
        shoulder_vector = keypoints[RIGHT_SHOULDER] - keypoints[LEFT_SHOULDER]
        left_upper_arm = keypoints[LEFT_ELBOW] - keypoints[LEFT_SHOULDER]
        right_upper_arm = keypoints[RIGHT_ELBOW] - keypoints[RIGHT_SHOULDER]
        
        # Calculate angles between upper arms and torso
        left_angle = np.arccos(np.dot(shoulder_vector, left_upper_arm) /
                            (np.linalg.norm(shoulder_vector) * np.linalg.norm(left_upper_arm)))
        print(f"left_angle in elbow_flare: {left_angle}")
        right_angle = np.arccos(np.dot(shoulder_vector, right_upper_arm) /
                            (np.linalg.norm(shoulder_vector) * np.linalg.norm(right_upper_arm)))
        print(f"right_angle in elbow_flare: {right_angle}")
        
        # Convert to degrees
        left_angle = np.degrees(left_angle)
        right_angle = np.degrees(right_angle)
        
        # Return True if either elbow flares more than 45 degrees
        return left_angle > 45 or right_angle > 45
    
    #TODO: Finish this function
    def _detect_rounded_shoulders(self, keypoints: np.ndarray):
        """Detect if shoulders are rolled forward for movements like chest fly.

        Args:
            keypoints (np.ndarray): numpy array containing MediaPipe pose landmarks

        Returns:
            bool: true if shoulders are too far forward, false otherwise.
        """
        shoulder_protraction_threshold = 0.1  # Example threshold for detecting excessive rounding
        left_shoulder = keypoints[11]
        right_shoulder = keypoints[12]
        left_hip = keypoints[23]
        right_hip = keypoints[24]
        
        shoulder_midpoint = (left_shoulder + right_shoulder) / 2
        hip_midpoint = (left_hip + right_hip) / 2
        
        spine_vector = shoulder_midpoint - hip_midpoint
        shoulder_protraction = abs(spine_vector[0])  # Example way to measure forward rounding
        
        return shoulder_protraction > shoulder_protraction_threshold
    
    def _check_core_engagement(self, keypoints: np.ndarray):
        """Check to make sure core is engaged and no sagging hips.

        Args:
            keypionts (np.ndarray): np array containing MediaPipe pose landmarks
            
        Returns:
            bool: true if core is not engaged and the hips are sagging, false otherwise. 
        """
        hip_sag_threshold = 10  # Example threshold in degrees
        shoulder_mid = (keypoints[11] + keypoints[12]) / 2
        hip_mid = (keypoints[23] + keypoints[24]) / 2
        knee_mid = (keypoints[25] + keypoints[26]) / 2
        
        upper_body_vector = shoulder_mid - hip_mid
        lower_body_vector = hip_mid - knee_mid
        
        upper_angle = np.degrees(np.arctan2(upper_body_vector[1], upper_body_vector[0]))
        lower_angle = np.degrees(np.arctan2(lower_body_vector[1], lower_body_vector[0]))
        
        core_engagement = abs(upper_angle - lower_angle)
        return core_engagement > hip_sag_threshold
    
    def _check_pelvic_stability(self, keypoints: np.ndarray):
        """Check pelvic stability to make sure no rounded back

        Args:
            keypoints (np.ndarray): np array containing MediaPipe pose landmarks
            
        Returns:
            bool: true if pelvus is not stable and needs to be more stable, false otherwise.
        """
        pelvic_tilt_threshold = 5  # Example threshold in degrees
        left_hip = keypoints[23]
        right_hip = keypoints[24]
        left_knee = keypoints[25]
        right_knee = keypoints[26]
        
        hip_vector = right_hip - left_hip
        knee_vector = right_knee - left_knee
        
        hip_angle = np.degrees(np.arctan2(hip_vector[1], hip_vector[0]))
        knee_angle = np.degrees(np.arctan2(knee_vector[1], knee_vector[0]))
        
        pelvic_stability = abs(hip_angle - knee_angle)
        return pelvic_stability > pelvic_tilt_threshold