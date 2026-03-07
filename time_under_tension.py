import time
import os
import sys
import numpy as np
import math
import cv2
import io
import base64
from PIL import Image
import matplotlib
from matplotlib import pyplot as plt

from scipy.signal import find_peaks, savgol_filter
from scipy.ndimage import gaussian_filter1d

from skimage.filters import median
from skimage.morphology import disk

from helper import exercise_joint_indices, joint_indices, get_joints_from_exercise


import numpy as np

def calculate_force_vector(joint_positions, timestamps, body_weight, lift_weight, exercise_name):
    body_mass = float(body_weight) / 2.2  # Convert lbs to kg
    lift_mass = float(lift_weight) / 2.2  # Convert lbs to kg
    
    relevant_joints = list(joint_positions[0].keys())  # Extract joint names from first frame
    # print(f"relevant joints: {relevant_joints}")
    # Convert joint_positions into a NumPy array (frames, joints, 3)
    positions_array = np.array([
        [[frame[joint]["x"], frame[joint]["y"], frame[joint]["z"]] for joint in relevant_joints]
        for frame in joint_positions
    ])
    # print(f"positions_array {positions_array}")
    timestamps = np.array(timestamps)  # Convert timestamps to NumPy array
    
    if len(positions_array) < 2 or len(timestamps) < 2:
        raise ValueError("Not enough data points to calculate velocity or acceleration.")
    
    # Calculate velocity (m/s)
    position_differences = np.diff(positions_array, axis=0)  
    time_differences = np.diff(timestamps)[:, None, None]  # Shape: (frames-1, 1, 1)
    
    velocities = position_differences / time_differences  # Shape: (frames-1, joints, 3)
    # print(f"velocities: {velocities}")
    
    # Calculate acceleration (m/s²)
    acceleration_differences = np.diff(velocities, axis=0)
    acceleration_time_diffs = np.diff(timestamps[:-1])[:, None, None]
    
    accelerations = acceleration_differences / acceleration_time_diffs  # Shape: (frames-2, joints, 3)
    # print(f"accelerations: {accelerations}")
    # Assume each segment has 3% of body + lift mass
    segment_mass = (body_mass + lift_mass) * 0.03
    
    # Calculate force (F = m * a)
    forces = segment_mass * accelerations  # Shape: (frames-2, joints, 3)
    
    # Compute force magnitudes
    magnitudes = np.linalg.norm(forces, axis=2)  # Shape: (frames-2, joints)
    # print(f"magnitudes: {magnitudes}")
    # Compute force angles
    angles = {
        "theta_x": np.arccos(forces[:, :, 0] / (magnitudes + 1e-8)),  # Avoid division by zero
        "theta_y": np.arccos(forces[:, :, 1] / (magnitudes + 1e-8)),
        "theta_z": np.arccos(forces[:, :, 2] / (magnitudes + 1e-8)),
    }
    # print(f"angles: {angles}")
    return magnitudes, angles

def draw_force_vectors(frame, forces, joint_positions, scale_factor=1):
    #TODO: make sure width and height are correct
    #TODO: look into scale factor
    image_height, image_width, _ = frame.shape
    for force, position in zip(forces, joint_positions):
        start_point = (int(position[0] * image_width), int(position[1] * image_height))
        end_point = (
            int(start_point[0] + force[0] * scale_factor),
            int(start_point[1] - force[1] * scale_factor)
        )
        cv2.arrowedLine(frame, start_point, end_point, (0, 255, 0), 2) #green arrow for force vector
    
def old_plot_reps(forces, angles, timestamps, exercise):
    if 'theta_y' not in angles:
        raise ValueError("Key 'theta_y' not found in angles dictionary")

    images = []
    theta_y = angles['theta_y']
    joints = get_joints_from_exercise(exercise=exercise)

    for i in range(len(theta_y[0])):  # Iterate over joints
        joint = joints[i]
        theta_y_joint = theta_y[:, i]  # Get data for the current joint

        # 1. Signal Preprocessing (Combined Filters):
        theta_y_filtered = median(theta_y_joint, disk(3))  # Median filter
        smoothed_theta_y = savgol_filter(theta_y_filtered, window_length=7, polyorder=2) # Savgol filter

        # 2. Peak Detection (Adjust parameters as needed):
        peaks, _ = find_peaks(smoothed_theta_y, prominence=0.3, distance=10)  # Adjust prominence and distance
        troughs, _ = find_peaks(-smoothed_theta_y, prominence=0.3, distance=10)  # Adjust prominence and distance

        # 3. Robust Rep Counting Logic (Handle edge cases):
        valid_reps = []
        eccentric_times = []
        concentric_times = []

        if len(troughs) > 0 and len(peaks) > 0:  # Ensure there are peaks and troughs
            if troughs[0] > peaks[0]:  # Remove leading trough
                troughs = troughs[1:]
            if len(troughs) > 0 and troughs[-1] > peaks[-1]: #Remove trailing trough only if there are troughs left
                troughs = troughs[:-1]
            if len(peaks) > 0 and peaks[0] > troughs[0]: #Remove leading peak only if there are peaks left
                peaks = peaks[1:]
            if len(peaks) > 0 and peaks[-1] > troughs[-1]: #Remove trailing peak only if there are peaks left
                peaks = peaks[:-1]
            for i in range(min(len(troughs),len(peaks)) - 1): #Iterate up to the minimum length of troughs and peaks to avoid index errors
                peak_candidates = peaks[(peaks > troughs[i]) & (peaks < troughs[i + 1])]
                if len(peak_candidates) > 0:
                    peak = peak_candidates[0]
                    valid_reps.append((troughs[i], peak, troughs[i + 1]))
                    eccentric_times.append(timestamps[peak] - timestamps[troughs[i]])
                    concentric_times.append(timestamps[troughs[i + 1]] - timestamps[peak])

        # 4. Plotting:
        matplotlib.use('Agg')
        plt.figure(figsize=(10, 6))

        x = np.arange(1, len(eccentric_times) + 1)
        plt.bar(x - 0.2, eccentric_times, width=0.4, color='r', label='Eccentric time')
        plt.bar(x + 0.2, concentric_times, width=0.4, color='b', label='Concentric time')
        plt.xticks(x)
        plt.ylabel('Time (s)')
        plt.xlabel('Reps')
        plt.title(f'{exercise} - Eccentric vs Concentric Portions ({joint})')
        plt.legend()

        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        buffer.seek(0)

        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        image_data = base64.b64decode(image_base64)
        image_file = Image.open(io.BytesIO(image_data))
        reps = len(eccentric_times)

        image = {
            "image_file": image_file,
            "concentric_times": concentric_times,
            "eccentric_times": eccentric_times,
            "reps": reps
        }
        images.append(image)

    return images
#TODO: get exercise as a string from UI
def plot_reps(forces, angles, timestamps, exercise):
    # print("Forces: ", type(forces), "Shape:", getattr(forces, 'shape', 'Unknown'))
    # print("Angles: ", type(angles), angles)
    
    if 'theta_y' not in angles:
        raise ValueError("Key 'theta_y not oofund in angles dictionary")
    
    images = []

    # Detect peaks (highest points in eccentric phase) and troughs (lowest points in concentric phase)
    theta_y = angles['theta_y']
    joints = get_joints_from_exercise(exercise=exercise)
    for i in range(len(theta_y[0])):
        joint = joints[i]
        #Applpy Guassian filtering to reduce noise
        smoothed_theta_y = gaussian_filter1d(theta_y[:,i], sigma=2)
    
        peaks, _ = find_peaks(smoothed_theta_y, prominence=0.2, distance=5)  # Peaks correspond to eccentric-to-concentric transitions
        troughs, _ = find_peaks(-smoothed_theta_y, prominence=0.2, distance=5)  # Troughs correspond to concentric-to-eccentric transitions
        print("Peaks (eccentric to concentric):", peaks)
        print("Troughs (concentric to eccentric):", troughs)
        # Ensure we alternate peaks and troughs correctly to count valid repetitions
        valid_reps = []
        eccentric_times = []
        concentric_times = []

        for i in range(len(troughs) - 1):
            peak_candidates = peaks[(peaks > troughs[i]) & (peaks < troughs[i + 1])]
            if len(peak_candidates) > 0:
                peak = peak_candidates[0]
                valid_reps.append((troughs[i], peak, troughs[i + 1]))
                eccentric_times.append(timestamps[peak] - timestamps[troughs[i]])
                concentric_times.append(timestamps[troughs[i + 1]] - timestamps[peak])

        print("Valid reps (trough -> peak -> trough):", valid_reps)
        print("Eccentric Times: ", eccentric_times)
        print("Concentric Times: ", concentric_times)
        
        matplotlib.use('Agg') #non-GUI backend

        # Plotting the reps with time (eccentric vs concentric)
        plt.figure(figsize=(10, 6))
        x = np.arange(1, len(eccentric_times) + 1)
        plt.bar(x - 0.2, eccentric_times, width=0.4, color='r', label='Eccentric time')
        plt.bar(x + 0.2, concentric_times, width=0.4, color='b', label='Concentric time')
        plt.xticks(x)
        plt.ylabel('Time (s)')
        plt.xlabel('Reps')
        plt.title(f'{exercise} - Eccentric vs Concentric Portions ({joint})')
        plt.legend()
        #Convert plot to a PNG image in memory
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        plt.close()
        buffer.seek(0)
    
        #Convert image to Base64
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        image_data = base64.b64decode(image_base64)
        image_file = Image.open(io.BytesIO(image_data))
        reps = len(eccentric_times)
        
        image = {
            "image_file": image_file,
            "concentric_times": concentric_times,
            "eccentric_times": eccentric_times,
            "reps": reps
        }
        images.append(image)
    
    return images

        
             
             