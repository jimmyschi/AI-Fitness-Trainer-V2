# mediapipe_model.py
import os
import tempfile
import logging
import requests
import numpy as np
from flask import Flask, request, jsonify

from urllib.parse import urlparse
from google.cloud import storage

from read_input_files import process_video
from time_under_tension import calculate_force_vector, plot_reps

print("mediapipe_model.py started!")

class MediapipeModel:
    def __init__(self, name, exercise_weight, input_video_url, intput_video_name):
        print("Exercise mediapipe_model.py called!!!")
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.name = name
        self.logger.info(f"MediapipeModel name: {self.name}")
        self.exercise_weight = exercise_weight
        self.logger.info(f"MediapipeModel exercise_weight: {self.exercise_weight}")
        self.input_video_url = input_video_url
        self.logger.info(f"MediapipeModel input_video (url): {self.input_video_url}")
        self.input_video_name = intput_video_name
        self.logger.info(f"MediapipeModel input_video (name): {self.input_video_name}")
        self.chatbot_response = None

    def download_video_from_gcs(self, gcs_url):
        """Download video file from Google Cloud Storage to a temporary file.

        Args:
            gcs_url (str): url to video file on gcs bucket
        """
        self.logger.info("----------DOWNLOAD_VIDEO_FROM_GCS CALLED------------")
        response = requests.get(gcs_url, stream=True)
        self.logger.info(f"gcs_url: {gcs_url}")
        self.logger.info(f"response in gcs: {response}")
        if response.status_code == 200:
            temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            for chunk in response.iter_content(chunk_size=1024):
                temp_video.write(chunk)
            temp_video.close()
            self.logger.info(f"temp_video.name: {temp_video.name}")
            return temp_video.name
        else:
            self.logger.info("Status was never 200")
            raise RuntimeError(f"Failed to download video from {gcs_url}, Status: {response.status_code}")

    def read_video(self, user): 
        self.logger.info("ANALYZE VIDEO")
        self.logger.info(f"self.input_video_url: {self.input_video_url}")
        input_path = self.download_video_from_gcs(self.input_video_url)
        self.logger.info(f"Input path in read_video: {input_path}")
        
        # Parse the URL to get the path part
        parsed_url = urlparse(self.input_video_url)
        video_filename_with_path = parsed_url.path
        # Extract the base filename from the path
        base_video_name = os.path.basename(video_filename_with_path)
        # Create the output filename without the URL parameters
        output_file_name = f"pose_{os.path.splitext(base_video_name)[0]}.mp4"

        # output_file_name = f"pose_{os.path.basename(self.input_video_url)}"
        output_dir = "/app/media/pose_videos"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_file_name) # Changed to container path
        self.logger.info(f"Output Path (Shared Volume): {output_path}")
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            self.logger.info("Before reading video")
            self.logger.info(f"Input Path: {input_path}")
            timestamps, joint_positions = process_video(input_path, output_path, self.name)
            processed_output_path = output_path
            self.logger.info(f"processed_output_path: {processed_output_path}")
            self.logger.info("Joint positions (in Mediapipe): {joint_positions}")
            self.logger.info("Timestamps (in Mediapipe): {timestamps}")

            if not user:
                raise ValueError("No user found in the database.")
            else:
                self.logger.info(f"User found in read_video: ${user}")

            forces, angles = calculate_force_vector(joint_positions, timestamps, user, self.exercise_weight, self.name)
            reps_list = plot_reps(forces, angles, timestamps, self.name)
            progress_images = []
            concentric_times = []
            eccentric_times = []
            reps = []
            for reps_dict in reps_list:
                progress_images.append(reps_dict["image_file"])
                concentric_times.append(reps_dict["concentric_times"])
                eccentric_times.append(reps_dict["eccentric_times"])
                reps.append(reps_dict["reps"])

            self.logger.info("---------PLOT REPS RETURNED VALUES----------")
            self.logger.info(f"progress_images type: {type(progress_images)}")
            self.logger.info(f"concentric_times type: {type(concentric_times)}")
            self.logger.info(f"eccentric_times type: {type(eccentric_times)}")
            self.logger.info(f"reps: {reps}")

            idx = np.argmax(reps)
            display_image = progress_images[idx]
            display_image_dir = "/app/media/progress_images"
            os.makedirs(display_image_dir, exist_ok=True)
            display_image_path = os.path.join(display_image_dir, "best_rep.png") # Changed to container path

            self.logger.info(f"Attempting to save best rep image. display_image type: {type(display_image)}, save path: {display_image_path}")
            
            # Save the PIL Image object to the specified path
            try:
                display_image.save(display_image_path, "PNG")
                self.logger.info(f"Successfully saved best rep image to: {display_image_path}")
            except Exception as e:
                self.logger.error(f"Error saving best rep image: {e}")
                raise
            
            return output_file_name, processed_output_path, display_image_path, joint_positions, timestamps

        except Exception as e:
            self.logger.error(f"Error analyzing video: {e}")
            raise RuntimeError(f"Error analyzing video: {e}")


app = Flask(__name__)

# Configure logging for the Flask app
app_logger = logging.getLogger(__name__)
app_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app_logger.addHandler(handler)

@app.route('/process_video', methods=['POST'])
async def process_video_endpoint():
    data = request.get_json()
    app_logger.info(f"Request data: {data}")
    user = data.get('user')
    exercise_name = data.get("exercise_name")
    exercise_weight = data.get("exercise_weight")
    input_video_url = data.get("input_video_url")
    input_video_name = data.get("input_video_name")
    
    app_logger.info(f"user: {user}")
    app_logger.info(f"exercise_name: {exercise_name}")
    app_logger.info(f"exercise_weight: {exercise_weight}")
    app_logger.info(f"input_video_url: {input_video_url}")
    
    model = MediapipeModel(exercise_name, exercise_weight, input_video_url, input_video_name)
    try:
        output_file_name, output_path, display_image_path, joint_positions, timestamps = model.read_video(user)
        return jsonify({
            'output_file_name' : output_file_name,
            'output_path' : output_path,
            'display_image_path' : display_image_path,
            'joint_positions' : joint_positions,
            'timestamps' : timestamps,
        })
    except Exception as e:
        app_logger.error(f"Error processing /process_video request: {e}", exc_info=True)
        return jsonify({'error' : str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002)