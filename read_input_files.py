import cv2
import numpy as np
import tensorflow as tf
import os
import mediapipe as mp
import logging
from time_under_tension import calculate_force_vector
from time_under_tension import draw_force_vectors
from time_under_tension import plot_reps

from helper import exercise_joint_indices, joint_indices, get_joints_from_exercise



def process_video(input_path, output_path, exercise_type):
    logger = logging.getLogger(__name__)
    logger.info("INSIDE PROCESS_VIDEO!")
    print("INSDIE PROCESS_VIDEO PRINT STATEMENT!")
    cap = cv2.VideoCapture(input_path)
    # Check if the file is opened successfully
    if not cap.isOpened():
        print("Error: Cannot open video file in process_video.")
        logger.info("Error: Cannot open video file in process_video.")
        exit()
    
    # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    logger.info("Using avc1")
    print("Using avc1")
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    
    
    if exercise_type not in exercise_joint_indices:
        print(f"Error: '{exercise_type}' is not a recognized exercise.")
        logger.info(f"Error: '{exercise_type}' is not a recognized exercise.")
        return None, None

    timestamps = []
    joint_positions = []
    frames = 0
    
    pose = mp_pose.Pose(static_image_mode = True, min_detection_confidence=.5, model_complexity=2)
        
    # Read and display frames
    while True:
        ret, frame = cap.read()
        frames += 1
        
        if not ret:  # Break the loop if no more frames
            break
        
        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)) 
        
        if results.pose_landmarks:
            # Store joint positions as a dictionary instead of a list
            joint_position = {
                joint_indices[joint_idx]: {
                    "x": results.pose_landmarks.landmark[joint_idx].x,
                    "y": results.pose_landmarks.landmark[joint_idx].y,
                    "z": results.pose_landmarks.landmark[joint_idx].z,
                    "visibility": results.pose_landmarks.landmark[joint_idx].visibility
                }
                for joint_idx in exercise_joint_indices[exercise_type]
            }
            joint_positions.append(joint_position)
            timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 #convert to seconds
            timestamps.append(timestamp)
            
        mp_drawing.draw_landmarks(
            frame,
            results.pose_landmarks, 
            mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
        )
        
        out.write(frame)

        # Break on 'q' key
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

    # Release the capture and close windows
    cap.release()
    out.release()
    pose.close()
    
    logger.info(f"FRAMES: {frames}")
    print(f"FRAMES: {frames}")
    # timestamps = np.array(timestamps)
    # joint_positions = np.array([[lm.x, lm.y, lm.z] for lm in joint_position])
    # forces, angles = calculate_force_vector(joint_position, 100, timestamps)
    
    # print(f"JOINT POSITIONS: {joint_positions}")
 
    # plot_reps(forces=forces, angles=angles, timestamps=timestamps, exercise="bench_press")
    return timestamps, joint_positions

        
        




