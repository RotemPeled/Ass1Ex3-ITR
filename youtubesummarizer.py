import cv2
import os
import ssl
import certifi
import re
import easyocr  # Import EasyOCR
from pytube import YouTube, Search
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

ssl._create_default_https_context = ssl._create_unverified_context
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

def find_scenes_and_save_frames(video_path, threshold=40.0):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"The video file {video_path} was not found.")

    reader = easyocr.Reader(['en'])  # Initialize EasyOCR reader for English language
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    video_manager.set_downscale_factor()

    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)

    scene_list = scene_manager.get_scene_list()
    base_path = os.path.splitext(video_path)[0]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError("Could not open video file.")

    for i, scene in enumerate(scene_list):
        start_frame, _ = scene
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame.get_frames())
        ret, frame = cap.read()
        if ret:
            frame_path = f"{base_path}_scene_{i+1}.jpg"
            cv2.imwrite(frame_path, frame)  # Save the original frame without watermark

            # Perform OCR on the saved frame
            results = reader.readtext(frame_path)
            print(f"Text detected in scene {i+1}:")
            for (bbox, text, prob) in results:
                print(f"- {text} (confidence: {prob:.2f})")

            # Read the image again to add the watermark
            img_with_watermark = cv2.imread(frame_path)
            watermark_text = 'Rotem Peled'
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1
            font_color = (255, 255, 255)  # White color
            font_thickness = 2
            text_size = cv2.getTextSize(watermark_text, font, font_scale, font_thickness)[0]
            text_x = img_with_watermark.shape[1] - text_size[0] - 10  # 10 pixels from the right edge
            text_y = img_with_watermark.shape[0] - 10  # 10 pixels from the bottom edge

            cv2.putText(img_with_watermark, watermark_text, (text_x, text_y), font, font_scale, font_color, font_thickness)
            cv2.imwrite(frame_path, img_with_watermark)  # Save the image again with the watermark
            print(f"Watermarked frame saved to {frame_path}")

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
        else:
            print(f"Failed to find the downloaded video at {downloaded_file}.")
        break
else:
    print("No videos under 10 minutes were found.")
