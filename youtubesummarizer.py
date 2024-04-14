import cv2
import os
import ssl
import certifi
import re
import easyocr
import imageio 
from pytube import YouTube, Search
from scenedetect import VideoManager, SceneManager
from scenedetect.video_splitter import split_video_ffmpeg
from scenedetect.detectors import ContentDetector

# SSL configuration 
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

DOWNLOAD_DIRECTORY = 'downloaded_videos'

def find_scenes_and_save_frames(video_path, desired_frames=30, minimum_frames=20):
    reader = easyocr.Reader(['en'])  
    base_path = os.path.splitext(video_path)[0]
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise IOError("Could not open video file.")

    threshold = 30
    max_attempts = 5
    attempt = 0

    while attempt < max_attempts:
        video_manager = VideoManager([video_path])
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold))
        video_manager.set_downscale_factor()

        video_manager.start()
        scene_manager.detect_scenes(frame_source=video_manager)

        scene_list = scene_manager.get_scene_list(base_timecode=video_manager.get_base_timecode())
        scenes_per_frame = max(1, len(scene_list) // desired_frames)

        all_text = []  
        if len(scene_list) >= minimum_frames:
            for i, scene in enumerate(scene_list[::scenes_per_frame][:desired_frames]):
                frame_num = scene[0].get_frames()
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if ret and not is_frame_black(frame):
                    frame_path = f"{base_path}_scene_{i+1}.jpg"
                    cv2.imwrite(frame_path, frame)

                    # OCR
                    results = reader.readtext(frame)
                    for (bbox, text, prob) in results:
                        print(f"- {text} (confidence: {prob:.2f})")
                        all_text.append(text)

                    # Watermark
                    img_with_watermark = cv2.imread(frame_path)
                    watermark_text = 'Rotem Peled'
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 1
                    font_color = (255, 255, 255)
                    font_thickness = 2
                    text_size = cv2.getTextSize(watermark_text, font, font_scale, font_thickness)[0]
                    text_x = img_with_watermark.shape[1] - text_size[0] - 10
                    text_y = img_with_watermark.shape[0] - 10

                    cv2.putText(img_with_watermark, watermark_text, (text_x, text_y), font, font_scale, font_color, font_thickness)
                    cv2.imwrite(frame_path, img_with_watermark)

            video_manager.release()
            cap.release()
            return all_text
        else:
            video_manager.release()
            threshold -= 5  # Decrease threshold to increase sensitivity
            attempt += 1
            print(f"Adjusting threshold to {threshold} and retrying...")

    cap.release()
    raise Exception("Failed to detect sufficient scenes even after adjusting threshold.")


def is_frame_black(frame, threshold=30):
    """Check if the frame is mostly black."""
    return cv2.mean(frame)[0] < threshold

def capture_frames_at_intervals(video_path, desired_frames=25):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    interval = total_frames // desired_frames
    frames_captured = 0
    all_text = []

    while frames_captured < desired_frames:
        frame_num = frames_captured * interval
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()
        if ret and not is_frame_black(frame):
            frame_path = f"{os.path.splitext(video_path)[0]}_frame_{frames_captured + 1}.jpg"
            cv2.imwrite(frame_path, frame)
            # OCR and other processing...
        frames_captured += 1

    cap.release()
    return all_text

# GIF creation function
def generate_gif(image_folder, output_file='output.gif', duration=10):
    images = []
    for filename in sorted(os.listdir(image_folder), key=lambda x: os.path.getmtime(os.path.join(image_folder, x))):
        if filename.endswith('.jpg'):
            image_path = os.path.join(image_folder, filename)
            images.append(imageio.imread(image_path))
    imageio.mimsave(output_file, images, duration=duration / len(images))


def main():
    subject = input("Enter the subject to search on YouTube: ")
    search = Search(subject)
    videos = search.results
    
    download_directory = DOWNLOAD_DIRECTORY
    os.makedirs(download_directory, exist_ok=True)
    
    for video in videos:
        yt = YouTube(video.watch_url)
        try:
            if yt.age_restricted:
                continue  # Skip age-restricted videos
            if yt.length < 600:
                safe_title = re.sub(r'[^\w\-_\.]', '_', yt.title)
        
                downloaded_file = yt.streams.get_highest_resolution().download(output_path=download_directory, filename=safe_title)
        
                if os.path.exists(downloaded_file):
                    all_text = find_scenes_and_save_frames(downloaded_file)
                    gif_path = os.path.join(download_directory, 'output.gif')
                    generate_gif(download_directory, gif_path) 
                    print("All detected text:")
                    print(" ".join(all_text))
                    
                    os.system(f'open {gif_path}')
                else:
                    print(f"Failed to find the downloaded video at {downloaded_file}.")
                break
        except Exception as e:
            print(f"Error processing video {video.watch_url}: {str(e)}")
    else:
        print("No videos under 10 minutes were found.")

if __name__ == "__main__":
    main()