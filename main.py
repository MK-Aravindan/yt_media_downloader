import streamlit as st
import yt_dlp
import os
import tempfile
import time

st.set_page_config(
    page_title="Media Downloader",
    page_icon="https://www.media.com/favicon.ico",
    layout="centered",
    initial_sidebar_state="auto"
)

st.markdown("""
    <style>
    .main {
        background-color: #F5F5F5;
        padding: 2rem;
        border-radius: 10px;
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

@st.cache_data(show_spinner=False)
def fetch_video_info(url):
    try:
        with yt_dlp.YoutubeDL() as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_info = {
                'title': info_dict.get('title'),
                'uploader': info_dict.get('uploader'),
                'upload_date': info_dict.get('upload_date'),
                'thumbnail': info_dict.get('thumbnail')
            }
            return video_info, True
    except Exception as e:
        return f"Error fetching video info: {e}", False

@st.cache_data(show_spinner=False)
def fetch_audio_formats(url):
    try:
        with yt_dlp.YoutubeDL() as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])
            
            audio_formats = []
            for f in formats:
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    format_id = f.get('format_id')
                    ext = f.get('ext')
                    bitrate = f.get('abr', 0)
                    audio_formats.append({
                        'format_id': format_id,
                        'extension': ext,
                        'bitrate': bitrate,
                        'resolution': 'Audio Only'
                    })
            
            audio_formats.sort(key=lambda x: x['bitrate'], reverse=True)
            return audio_formats, True
    except Exception as e:
        return f"Error fetching audio formats: {e}", []

@st.cache_data(show_spinner=False)
def fetch_resolutions(url):
    try:
        with yt_dlp.YoutubeDL() as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])
            resolutions = sorted({f.get("height") for f in formats if f.get("height")}, reverse=True)
            return resolutions, True
    except Exception as e:
        return f"Error fetching resolutions: {e}", []

def create_progress_hook(progress_text, progress_bar):
    def progress_hook(d):
        if d.get('status') == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded_bytes = d.get('downloaded_bytes', 0)
            if total_bytes:
                percent = downloaded_bytes / total_bytes * 100
            else:
                percent = 0

            speed = d.get('speed')
            speed_str = f"{speed/1024/1024:.2f}MiB/s" if speed else "N/A"
            eta = d.get('eta')
            eta_str = time.strftime("%H:%M:%S", time.gmtime(eta)) if eta else "N/A"
            total_size_str = f"{total_bytes/1024/1024:.2f}MiB" if total_bytes else "N/A"

            progress_bar.progress(min(int(percent), 100))
            progress_text.text(f"{percent:.1f}% of {total_size_str} at {speed_str} ETA {eta_str}")
        elif d.get('status') == 'finished':
            progress_text.text("Download complete, now post-processing...")
    return progress_hook

def download_media_file(url, media_type, selected_format):
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        ydl_opts_base = {
            'outtmpl': os.path.join(tmpdirname, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'progress_hooks': [create_progress_hook(progress_text, progress_bar)],
        }

        if media_type == 'audio':
            ydl_opts = {
                **ydl_opts_base,
                'format': selected_format,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
            }
        elif media_type == 'video':
            ydl_opts = {
                **ydl_opts_base,
                'format': f'bestvideo[height={selected_format}]+bestaudio/best',
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
                return None, "The downloaded file is empty.", False

            if media_type == 'video':
                mp4_files = [f for f in downloaded_files if f.lower().endswith('.mp4')]
                if mp4_files:
                    file_name = mp4_files[0]
                else:
                    file_name = downloaded_files[0]
            else:
                file_name = downloaded_files[0]

            file_path = os.path.join(tmpdirname, file_name)
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            if not file_bytes:
                return None, "The downloaded file is empty.", False
            return file_bytes, file_name, True
        except Exception as e:
            return None, f"Error during download: {e}", False

def main():
    st.title("Media Downloader")
    st.markdown("Effortlessly download high-quality videos and audio from YouTube, Instagram, LinkedIn, X!")

    video_url = st.text_input("Enter the URL:")
    media_type = st.radio("Select media type to download:", ('audio', 'video'))

    if video_url:
        with st.spinner("Fetching video informations..."):
            video_info, info_success = fetch_video_info(video_url)
            if info_success:
                st.image(video_info['thumbnail'], width=320)
                st.subheader(video_info['title'])
                st.caption(f"Uploaded by {video_info['uploader']} on {video_info['upload_date']}")

        if media_type == 'audio':
            audio_formats, aud_checker = fetch_audio_formats(video_url)
            if aud_checker:
                format_options = [
                    f"{fmt['bitrate']} kbps ({fmt['extension'].upper()})"
                    for fmt in audio_formats
                ]
                selected_quality = st.selectbox("Choose the audio quality:", format_options)
                selected_format = audio_formats[format_options.index(selected_quality)]['format_id']
            else:
                st.warning("Couldn't fetch audio formats, defaulting to best quality.")
                selected_format = 'bestaudio/best'

        elif media_type == 'video':
            with st.spinner("Fetching available resolutions..."):
                resolutions, res_checker = fetch_resolutions(video_url)
                if res_checker:
                    selected_resolution = st.selectbox("Choose the resolution:", resolutions)
                    selected_format = selected_resolution
                else:
                    selected_format = "1080"
                    st.warning(f"Resolution fetching failed, defaulting to {selected_format}p.")

        if st.button("Download"):
            with st.spinner('Downloading and converting...'):
                file_bytes, result, success = download_media_file(video_url, media_type, selected_format)
            if success:
                st.success("Download completed successfully!")
                st.download_button(
                    label="Click here to download the file",
                    data=file_bytes,
                    file_name=result,
                    mime="application/octet-stream"
                )
            else:
                st.error(result)            

if __name__ == "__main__":
    main()
