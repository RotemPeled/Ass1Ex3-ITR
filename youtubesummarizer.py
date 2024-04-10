import cv2  # Import OpenCV
import os
import ssl
import certifi
import re
from pytube import YouTube, Search
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector
from scenedetect.scene_manager import save_images

ssl._create_default_https_context = ssl._create_unverified_context
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

def find_scenes_and_save_frames(video_path, threshold=30.0):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"The video file {video_path} was not found.")

    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    video_manager.set_downscale_factor()

    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)

    scene_list = scene_manager.get_scene_list()
    base_path = os.path.splitext(video_path)[0]  # Base path for saving images

    # Initialize video capture
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError("Could not open video file.")

    frame_rate = cap.get(cv2.CAP_PROP_FPS)

    for i, scene in enumerate(scene_list):
        start_frame, end_frame = scene

        # For simplicity, let's take the first frame of each scene
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame.get_frames())
        ret, frame = cap.read()
        if ret:
            frame_path = f"{base_path}_scene_{i+1}.jpg"
            cv2.imwrite(frame_path, frame)
            print(f"Saved frame to {frame_path}")

    cap.release()
    return scene_list

subject = input("Enter the subject to search on YouTube: ")
search = Search(subject)
videos = search.results

download_directory = 'downloaded_videos'
os.makedirs(download_directory, exist_ok=True)

for video in videos:
    yt = YouTube(video.watch_url)
    if yt.length < 600:
        safe_title = re.sub(r'[^\w\-_\.]', '_', yt.title)
        print(f"Downloading {yt.title}...")

        downloaded_file = yt.streams.get_highest_resolution().download(output_path=download_directory, filename=safe_title)
        print(f"Downloaded to {downloaded_file}")

        if os.path.exists(downloaded_file):
            print(f"Successfully found the downloaded video at {downloaded_file}")
            scenes = find_scenes_and_save_frames(downloaded_file)
            print(f"Detected scenes: {scenes}")
        else:
            print(f"Failed to find the downloaded video at {downloaded_file}.")
        break
else:
    print("No videos under 10 minutes were found.")
