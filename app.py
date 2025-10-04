import streamlit as st
import cv2
import os
from pytubefix import YouTube
import shutil

# ---------------------------
# Download YouTube video
# ---------------------------
def download_youtube_video(url, output_path="downloads", filename="video.mp4"):
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    yt = YouTube(url)
    stream = yt.streams.filter(progressive=True, file_extension="mp4").first()
    video_path = stream.download(output_path, filename=filename)
    return video_path

# ---------------------------
# Extract screenshots
# ---------------------------
def extract_screenshots(video_path, frames_path="frames", gap_seconds=15):
    if os.path.exists(frames_path):
        shutil.rmtree(frames_path)  # clean old frames
    os.makedirs(frames_path)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps * gap_seconds)

    frame_count, saved = 0, 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            filename = os.path.join(frames_path, f"screenshot_{saved:04d}.jpg")
            cv2.imwrite(filename, frame)
            saved += 1
        frame_count += 1

    cap.release()
    return frames_path, saved

# ---------------------------
# Streamlit UI
# ---------------------------
st.title("📸 YouTube Video Screenshot Extractor")
st.write("Extract screenshots from a YouTube video every X seconds.")

youtube_url = st.text_input("Enter YouTube URL:")
gap = st.number_input("Screenshot interval (seconds):", min_value=1, max_value=60, value=5, step=1)

if st.button("Extract Screenshots"):
    if youtube_url:
        with st.spinner("Downloading video..."):
            video_file = download_youtube_video(youtube_url)

        with st.spinner("Extracting screenshots..."):
            frames_path, total = extract_screenshots(video_file, gap_seconds=gap)

        st.success(f"✅ Extracted {total} screenshots (every {gap} seconds).")

        # Show a few sample screenshots
        images = sorted(os.listdir(frames_path))[:5]  # show first 5
        st.write("### Sample Screenshots")
        for img in images:
            st.image(os.path.join(frames_path, img), caption=img, use_container_width=True)

        # Option to download screenshots as a zip
        import zipfile
        zip_filename = "screenshots.zip"
        with zipfile.ZipFile(zip_filename, "w") as zipf:
            for img in os.listdir(frames_path):
                zipf.write(os.path.join(frames_path, img), img)

        with open(zip_filename, "rb") as f:
            st.download_button("⬇️ Download All Screenshots (ZIP)", f, file_name=zip_filename)

    else:
        st.error("Please enter a valid YouTube URL.")

