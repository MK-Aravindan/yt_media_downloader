import streamlit as st
import yt_dlp
import os
import tempfile
import time
from datetime import datetime

st.set_page_config(
    page_title="YT Media Downloader",
    page_icon="https://www.youtube.com/favicon.ico",
    layout="centered",
    initial_sidebar_state="auto"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .main {
        background-color: #F5F5F5;
        padding: 2rem;
        border-radius: 10px;
    }
    .block-container {
        margin: 0 0 10px 0;
        padding: 0 0 5rem 0;
    }
    h1 {
        color: #4F4F4F;
    }
    .stButton button {
        padding: 4px 24px;
        border-radius: 4px;
        border-width: 2px;
    }
    .stButton button p {
        font-weight: 700 !important;
        font-size: 14px !important;
    }
    button[kind="secondary"],
    button[kind="secondary"]:active {
        background-color: #1e2833;
        color: #fff !important;
        min-width: 100px;
        border: none;
    }
    button[kind="secondary"]:hover {
        box-shadow: 0 0 8px 4px rgba(0, 0, 0, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

YDL_DEFAULTS = {
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0',
    'skip_download': True,
    'geo_bypass': True,
    'no_mtime': True,
    'socket_timeout': 10
}

def format_upload_date(raw_date):
    if not raw_date or len(raw_date) != 8:
        return raw_date
    try:
        return datetime.strptime(raw_date, "%Y%m%d").strftime("%b %d, %Y")
    except Exception:
        return raw_date

@st.cache_data(show_spinner=False)
def fetch_video_info(url):
    try:
        with yt_dlp.YoutubeDL(YDL_DEFAULTS) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_info = {
                'title': info_dict.get('title'),
                'uploader': info_dict.get('uploader'),
                'upload_date': format_upload_date(info_dict.get('upload_date')),
                'thumbnail': info_dict.get('thumbnail')
            }
            return video_info, True
    except Exception as e:
        return f"Error fetching video info: {e}", False

@st.cache_data(show_spinner=False)
def fetch_audio_formats(url):
    try:
        with yt_dlp.YoutubeDL(YDL_DEFAULTS) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])
            audio_formats = []
            for f in formats:
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    format_id = f.get('format_id')
                    ext = f.get('ext')
                    bitrate = f.get('abr')
                    bitrate_str = f"{bitrate} kbps" if bitrate else "Unknown"
                    audio_formats.append({
                        'format_id': format_id,
                        'extension': ext,
                        'bitrate': bitrate_str,
                        'resolution': 'Audio Only'
                    })
            audio_formats.sort(key=lambda x: int(x['bitrate'].split()[0]) if x['bitrate'] != "Unknown" else 0, reverse=True)
            return audio_formats, True
    except Exception as e:
        return f"Error fetching audio formats: {e}", False

@st.cache_data(show_spinner=False)
def fetch_resolutions(url):
    try:
        with yt_dlp.YoutubeDL(YDL_DEFAULTS) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])
            resolutions = sorted({f.get("height") for f in formats if f.get("height")}, reverse=True)
            return resolutions, True
    except Exception as e:
        return f"Error fetching resolutions: {e}", False

def create_progress_hook(progress_text, progress_bar):
    def progress_hook(d):
        if d.get('status') == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes', 0)

            if total_bytes:
                percent = downloaded_bytes / total_bytes

                progress_bar.progress(percent)

                total_size_str = f"{total_bytes/1024/1024:.2f} MiB"
                speed = d.get('speed')
                speed_str = f"{speed/1024/1024:.2f} MiB/s" if speed else "N/A"
                eta = d.get('eta')
                eta_str = time.strftime("%H:%M:%S", time.gmtime(eta)) if eta is not None else "N/A"
                
                progress_text.text(f"Downloading: {percent:.1%} of {total_size_str} at {speed_str} (ETA: {eta_str})")

            else:
                progress_text.text(f"Downloading: {d.get('downloaded_bytes')/1024/1024:.2f} MiB (Total size unknown)")

        elif d.get('status') == 'finished':
            progress_bar.progress(1.0)
            progress_text.text("Download complete, now post-processing...")
            
    return progress_hook

def download_media_file(url, media_type, selected_format):
    progress_text = st.empty()
    progress_bar = st.progress(0)

    with tempfile.TemporaryDirectory() as tmpdirname:
        ydl_opts_base = {
            'outtmpl': os.path.join(tmpdirname, '%(id)s.%(ext)s'),
            'noplaylist': True,
            'progress_hooks': [create_progress_hook(progress_text, progress_bar)],
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
        }

        if media_type == 'audio':
            ydl_opts = {
                **ydl_opts_base,
                'format': selected_format if selected_format else 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
            }
        elif media_type == 'video':
            ydl_opts = {
                **ydl_opts_base,
                'format': f'bestvideo[height<={selected_format}]+bestaudio/best/best[height<={selected_format}]',
                'merge_output_format': 'mp4',
            }
        else:
            return None, "Unsupported media type.", False

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            downloaded_files = [
                f for f in os.listdir(tmpdirname)
                if os.path.getsize(os.path.join(tmpdirname, f)) > 0
            ]
            if not downloaded_files:
                return None, "The downloaded file is empty or not found after download.", False

            file_name = downloaded_files[0]
            file_path = os.path.join(tmpdirname, file_name)
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            if not file_bytes:
                return None, "The downloaded file content is empty.", False
            return file_bytes, file_name, True
        except Exception as e:
            return None, f"Error during download: {e}", False

def main():
    st.title("Media Downloader")
    st.markdown("Download your favorite YouTube, Instagram, X (Twitter), LinkedIn videos or audio in high quality.")

    video_url = st.text_input("Enter the video URL (YouTube, Instagram, X, LinkedIn etc.):")
    media_type = st.radio("Select media type to download:", ('audio', 'video'))

    selected_format = None

    if video_url:
        with st.spinner("Fetching video information..."):
            video_info, info_success = fetch_video_info(video_url)
            if info_success:
                if video_info.get('thumbnail'):
                    st.image(video_info['thumbnail'], width=320)
                if video_info.get('title'):
                    st.subheader(video_info['title'])
                if video_info.get('uploader') and video_info.get('upload_date'):
                     st.caption(f"Uploaded by {video_info['uploader']} on {video_info['upload_date']}")
                elif video_info.get('uploader'):
                    st.caption(f"Uploaded by {video_info['uploader']}")
            else:
                st.error(video_info)

        # AUDIO SELECTION
        if media_type == 'audio':
            audio_formats, aud_checker = fetch_audio_formats(video_url)
            if aud_checker and audio_formats:
                format_options = [
                    f"{fmt['bitrate']} ({fmt['extension'].upper()})"
                    for fmt in audio_formats
                ]
                if format_options:
                    selected_quality_str = st.selectbox("Choose the audio quality:", format_options)
                    selected_format = audio_formats[format_options.index(selected_quality_str)]['format_id']
                else:
                    st.warning("No audio formats found for this video.")
                    selected_format = None
            else:
                st.info("Couldn't fetch audio formats, defaulting to best audio quality.")
                selected_format = 'bestaudio/best'

        # VIDEO SELECTION
        elif media_type == 'video':
            with st.spinner("Fetching available resolutions..."):
                resolutions, res_checker = fetch_resolutions(video_url)
                if res_checker and resolutions:
                    resolution_options = [f"{r}p" for r in resolutions if r is not None]
                    if resolution_options:
                        selected_resolution_str = st.selectbox("Choose the resolution:", resolution_options)
                        selected_format = selected_resolution_str.replace('p','')
                    else:
                        st.warning("No video resolutions found for this video.")
                        selected_format = None
                else:
                    selected_format = "1080"
                    st.warning(f"Resolution fetching failed or no resolutions found, defaulting to {selected_format}p.")
        else:
            selected_format = None
            st.error("Invalid media type selected.")

        if st.button("Download"):
            if selected_format:
                with st.spinner('Downloading and converting...'):
                    file_bytes, result_filename_or_error, success = download_media_file(video_url, media_type, selected_format)
                if success:
                    st.success("Download completed successfully!")
                    st.download_button(
                        label="Click here to download the file",
                        data=file_bytes,
                        file_name=result_filename_or_error,
                        mime="application/octet-stream"
                    )
                else:
                    st.error(result_filename_or_error)
            else:
                st.warning("Please select a valid quality/resolution before downloading.")

if __name__ == "__main__":
    main()
