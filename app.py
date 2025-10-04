import os
import shutil
import zipfile
import glob

import streamlit as st
import cv2
import yt_dlp


# ---------------------------
# Download YouTube video (no ffmpeg needed)
# ---------------------------
def download_youtube_video(url: str, output_dir: str = "downloads", base_name: str = "video"):
    """
    Uses yt-dlp to fetch a single-file download (prefer MP4) so ffmpeg is not required.
    Returns the absolute path to the downloaded file.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Prefer a single-file MP4. If not available, fall back to best single-file (any container).
    # We avoid "bv+ba" merges to keep this ffmpeg-free on Render Free instances.
    ydl_opts = {
        "format": "b[ext=mp4]/b",     # best single-file mp4, else best single-file
        "outtmpl": os.path.join(output_dir, f"{base_name}.%(ext)s"),
        "noprogress": True,
        "quiet": True,
        "restrictfilenames": True,
    }

    # Clean any old matching files for a predictable result name
    for old in glob.glob(os.path.join(output_dir, f"{base_name}.*")):
        try:
            os.remove(old)
        except OSError:
            pass

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Find the file we just downloaded (could be .mp4 or other single-file format)
    matches = glob.glob(os.path.join(output_dir, f"{base_name}.*"))
    if not matches:
        raise RuntimeError("Download failed — no output file found.")
    return os.path.abspath(matches[0])


# ---------------------------
# Extract screenshots
# ---------------------------
def extract_screenshots(video_path: str, frames_dir: str = "frames", gap_seconds: int = 15):
    """
    Extracts frames every `gap_seconds` from the given video.
    Returns (frames_dir, saved_count).
    """
    if os.path.exists(frames_dir):
        shutil.rmtree(frames_dir)  # clean old frames
    os.makedirs(frames_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)

    # Guard against videos that fail to open
    if not cap.isOpened():
        raise RuntimeError("Unable to open the downloaded video. Try another URL.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    # Fallback if FPS can't be read
    if fps <= 0:
        fps = 25.0

    frame_interval = max(1, int(fps * gap_seconds))

    frame_count, saved = 0, 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            filename = os.path.join(frames_dir, f"screenshot_{saved:04d}.jpg")
            cv2.imwrite(filename, frame)
            saved += 1
        frame_count += 1

    cap.release()
    return frames_dir, saved


# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="YouTube Screenshot Extractor", page_icon="📸", layout="centered")

st.title("📸 YouTube Video Screenshot Extractor")
st.write("Extract screenshots from a YouTube video every X seconds (server-friendly, no ffmpeg required).")

youtube_url = st.text_input("Enter YouTube URL:")
gap = st.number_input("Screenshot interval (seconds):", min_value=1, max_value=60, value=5, step=1)

if st.button("Extract Screenshots"):
    if youtube_url.strip():
        try:
            with st.spinner("Downloading video..."):
                video_file = download_youtube_video(youtube_url.strip(), base_name="video")

            with st.spinner("Extracting screenshots..."):
                frames_path, total = extract_screenshots(video_file, gap_seconds=int(gap))

            st.success(f"✅ Extracted {total} screenshots (every {int(gap)} seconds).")

            # Show a few sample screenshots
            images = sorted(os.listdir(frames_path))[:5]  # show first 5
            if images:
                st.write("### Sample Screenshots")
                for img in images:
                    st.image(os.path.join(frames_path, img), caption=img, use_container_width=True)

            # Option to download screenshots as a zip
            zip_filename = "screenshots.zip"
            with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
                for img in sorted(os.listdir(frames_path)):
                    zipf.write(os.path.join(frames_path, img), arcname=img)

            with open(zip_filename, "rb") as f:
                st.download_button("⬇️ Download All Screenshots (ZIP)", f, file_name=zip_filename)
        except Exception as e:
            st.error(f"❌ Error: {e}")
    else:
        st.error("Please enter a valid YouTube URL.")
