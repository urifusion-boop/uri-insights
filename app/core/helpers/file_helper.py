import requests
import tempfile
import os
import gc
from moviepy import VideoFileClip


class FileHelper:
    @staticmethod
    async def download_file_as_binary(url):
        try:
            # Send a GET request to the URL
            response = requests.get(url)

            # Check if the request was successful
            response.raise_for_status()

            # Get the binary content
            binary_content = response.content
            return binary_content
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None

    @staticmethod
    async def get_file_size(url):
        try:
            # Send a GET request to the URL
            response = requests.get(url)

            # Check if the request was successful
            response.raise_for_status()

            # Get the size of the content in bytes
            file_size = len(response.content)
            return file_size
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None

    @staticmethod
    def enforce_facebook_reel_requirements(
        input_bytes,
        target_aspect_ratio=9 / 16,
        min_resolution=(540, 960),
        min_fps=24,
        max_fps=90,
    ):
        print("\nInput type: ", type(input_bytes))
        try:
            temp_file = None
            output_file = None
            temp_file_path = None
            output_path = None
            # Save input bytes to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
                temp_file.write(input_bytes)
                temp_file_path = temp_file.name

            # Load the video from the temporary file
            clip = VideoFileClip(temp_file_path)

            # Check aspect ratio
            aspect_ratio = clip.size[0] / clip.size[1]
            target_aspect_ratio = 9 / 16
            if abs(aspect_ratio - target_aspect_ratio) >= 0.01:
                # Resize to meet aspect ratio
                new_width = int(clip.size[1] * target_aspect_ratio)
                clip = clip.resized(width=new_width)

            # Check resolution
            min_resolution = (540, 960)
            if clip.size[0] < min_resolution[0] or clip.size[1] < min_resolution[1]:
                # Resize to meet minimum resolution
                clip = clip.resized(height=min_resolution[1])

            # Check length
            if clip.duration < 3 or clip.duration > 90:
                raise Exception(
                    "Video length is outside the allowed range (3-90 seconds)."
                )

            # Save the edited video to bytes
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".mp4"
            ) as output_file:
                output_path = output_file.name
                target_fps = max(24, min(clip.fps, 90))
                clip.write_videofile(
                    output_path,
                    codec="libx264",
                    fps=target_fps,
                    threads=4,
                    preset="fast",
                    audio_codec="aac",
                )

            # Read the output file into bytes
            with open(output_path, "rb") as output_file:
                output_bytes = output_file.read()

            # Close the clip
            clip.close()
            print("Output type: ", type(output_bytes))
            return output_bytes

        except Exception as e:
            print(f"Error in enforcing reel video requirements: {e}")
            if "clip" in locals():
                clip.close()
            raise e

        finally:
            # Cleanup temp files
            if temp_file and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            if output_file and os.path.exists(output_path):
                os.remove(output_path)
            if "clip" in locals():
                clip.close()
            # Force garbage collection
            gc.collect()
