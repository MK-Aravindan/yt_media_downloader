import os
import time
import tempfile
import streamlit as st
import yt_dlp


def configure_page():
    st.set_page_config(
        page_title="YT Media Downloader",
        page_icon="https://www.youtube.com/favicon.ico",
        layout="centered",
        initial_sidebar_state="auto"
    )
    st.markdown(
        """
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
        """,
        unsafe_allow_html=True
    )


@st.cache_data(show_spinner=False)
def fetch_video_info(url: str):
    try:
        with yt_dlp.YoutubeDL({}) as ydl:
            info = ydl.extract_info(url, download=False)
        return ({
            'title': info.get('title'),
            'uploader': info.get('uploader'),
            'upload_date': info.get('upload_date'),
            'thumbnail': info.get('thumbnail')
        }, True)
    except Exception as e:
        return (f"Error fetching video info: {e}", False)


@st.cache_data(show_spinner=False)
def list_formats(url: str, media: str):
    with yt_dlp.YoutubeDL({}) as ydl:
        info = ydl.extract_info(url, download=False)
    formats = info.get('formats', [])
    if media == 'MP3':
        audio = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        sorted_audio = sorted(audio, key=lambda x: x.get('abr') or 0, reverse=True)
        return [f"{f['format_id']} - {(f.get('abr') or 0)}kbps" for f in sorted_audio]
    heights = sorted({f.get('height') for f in formats if f.get('height')}, reverse=True)
    return [str(h) for h in heights]


def create_progress_hook(progress_text, progress_bar):
    def hook(d):
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            downloaded = d.get('downloaded_bytes', 0)
            pct = int(downloaded / total * 100)
            speed = d.get('speed') or 0
            speed_str = f"{speed/1024/1024:.2f}MiB/s" if speed else "N/A"
            eta = d.get('eta')
            eta_str = time.strftime("%H:%M:%S", time.gmtime(eta)) if eta else "N/A"
            total_size = f"{total/1024/1024:.2f}MiB"
            progress_bar.progress(min(pct, 100))
            progress_text.text(f"{pct:.1f}% of {total_size} at {speed_str} ETA {eta_str}")
        elif status == 'finished':
            progress_text.text("Download complete, now post-processing...")
    return hook


def download_media_file(url: str, media_kind: str, selected: str):
    progress_text = st.empty()
    progress_bar = st.progress(0)
    ydl_opts = {'noplaylist': True, 'progress_hooks': [create_progress_hook(progress_text, progress_bar)]}
    if media_kind == 'MP3':
        ydl_opts.update({'format': selected, 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]})
    else:
        ydl_opts.update({'format': f"bestvideo[height={selected}]+bestaudio/best", 'merge_output_format': 'mp4'})
    try:
        with tempfile.TemporaryDirectory() as tmp:
            ydl_opts['outtmpl'] = os.path.join(tmp, '%(title)s.%(ext)s')
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            files = [f for f in os.listdir(tmp) if os.path.getsize(os.path.join(tmp, f))]
            if not files:
                return None, "Downloaded file empty.", False
            path = os.path.join(tmp, files[0])
            with open(path, 'rb') as f:
                data = f.read()
            return data, files[0], True
    except Exception as e:
        return None, f"Error during download: {e}", False


def main():
    configure_page()
    st.title("YouTube Media Downloader")
    st.markdown("Download your favorite YouTube videos or audio in high quality.")

    if 'formats' not in st.session_state:
        st.session_state.formats = []
        st.session_state.url = ''
        st.session_state.media = 'MP4'

    with st.form('fetch_form'):
        url = st.text_input("Enter the YouTube URL:", value=st.session_state.url)
        media = st.selectbox("Convert to:", ['MP4', 'MP3'], index=0 if st.session_state.media=='MP4' else 1)
        fetch = st.form_submit_button("Fetch formats")
    if fetch and url:
        st.session_state.url = url
        st.session_state.media = media
        st.session_state.formats = list_formats(url, media)

    if st.session_state.formats:
        info, ok = fetch_video_info(st.session_state.url)
        if ok:
            st.image(info['thumbnail'], width=320)
            st.subheader(info['title'])
            st.caption(f"Uploaded by {info['uploader']} on {info['upload_date']}")
            st.video(st.session_state.url)
        choice = st.selectbox("Choose format:", st.session_state.formats)
        if st.button("Download"):
            data, name, success = download_media_file(st.session_state.url, st.session_state.media, choice.split(' ')[0])
            if success:
                st.success("Download completed successfully!")
                st.download_button("Click here to download the file", data=data, file_name=name, mime="application/octet-stream")
            else:
                st.error(name)

if __name__ == '__main__':
    main()
