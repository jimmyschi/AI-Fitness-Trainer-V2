import cv2
import numpy as np
import tensorflow as tf
import os
from time_under_tension import calculate_force_vector
from time_under_tension import draw_force_vectors
from time_under_tension import plot_reps

from django.conf import settings

def video_feed(mp_pose, mp_drawing, mp_drawing_styles, video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Cannot open video file.")
        exit()
        
    pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5, model_complexity=2)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        mp_drawing.draw_landmarks(
            frame,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
        )
        
        # Encode the frame as JPEG
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            break
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

    cap.release()

def analyze_video(mp_pose, video_path, joint_idx=14):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("Error: Cannot open video file.")
    
    timestamps = []
    joint_positions = []
    pose = mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5, model_complexity=2)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        if results.pose_landmarks:
            joint_positions.append(results.pose_landmarks.landmark[joint_idx])
            timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            timestamps.append(timestamp)
    
    cap.release()
    return timestamps, joint_positions
