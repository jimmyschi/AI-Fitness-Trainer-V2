exercise_joint_indices = {  
    "bench press": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
    "barbell biceps curl": [14, 13, 16, 15],  # Elbows, Wrists
    "chest fly machine": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
    "deadlift": [24, 23, 26, 25, 28, 27],  # Hips, Knees, Ankles
    "decline bench press": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
    "hammer curl": [14, 13, 16, 15],  # Elbows, Wrists
    "hip thrust": [24, 23, 26, 25],  # Hips, Knees
    "incline bench press": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
    "lat pulldown": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
    "lateral raise": [12, 11, 16, 15],  # Shoulders, Wrists
    "leg extension": [24, 23, 26, 25, 28, 27],  # Hips, Knees, Ankles
    "leg raises": [24, 23, 26, 25, 28, 27],  # Hips, Knees, Ankles
    "plank": [12, 11, 24, 23, 26, 25, 28, 27],  # Shoulders, Hips, Knees, Ankles
    "pull up": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
    "push-up": [12, 11, 14, 13, 16, 15, 24, 23],  # Shoulders, Elbows, Wrists, Hips
    "romanian deadlift": [24, 23, 26, 25, 28, 27],  # Hips, Knees, Ankles
    "russian twist": [12, 11, 24, 23],  # Shoulders, Hips
    "shoulder press": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
    "squat": [24, 23, 26, 25, 28, 27],  # Hips, Knees, Ankles
    "t bar row": [12, 11, 14, 13, 16, 15, 24, 23],  # Shoulders, Elbows, Wrists, Hips
    "tricep dips": [12, 11, 14, 13, 16, 15],  # Shoulders, Elbows, Wrists
    "tricep pushdown": [12, 11, 14, 13, 16, 15]  # Shoulders, Elbows, Wrists
}

joint_indices = {
    0: "nose",
    1: "right_inner_eye",
    2: "right_eye",
    3: "right_eye_outer",
    4: "left_eye_inner",
    5: "left_eye",
    6: "left_eye_outer",
    7: "right_ear",
    8: "left_ear",
    9: "mouth_right",
    10: "mouth_left",
    11: "right_shoulder",
    12: "left_shoulder",
    13: "right_elbow",
    14: "left_elbow",
    15: "right_wrist",
    16: "left_wrist",
    17: "right_pinky_1",
    18: "left_pinky_1",
    19: "right_index_1",
    20: "left_index_1",
    21: "right_thumb_2",
    22: "left_thumb_2",
    23: "right_hip",
    24: "left_hip"
}

def get_joints_from_exercise(exercise):
    joints = []
    joint_idxs = exercise_joint_indices.get(exercise, [])  # Use .get() to prevent KeyError if exercise not found
    for joint in joint_idxs:
        joints.append(joint_indices.get(joint, f"Unknown joint {joint}"))  # Handle missing indices gracefully
    return joints
