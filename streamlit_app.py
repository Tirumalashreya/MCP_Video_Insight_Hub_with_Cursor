import streamlit as st
import os
from server import (
    ingest_data_tool, retrieve_data_tool, get_transcript_tool, get_highlights_tool,
    get_analytics_tool, get_tags_chapters_tool, translate_transcript_tool, image_search_tool
)

st.set_page_config(page_title="MCP Video RAG", layout="wide")
st.title("🎬 MCP Video RAG Tools")

# Sidebar: Video ingestion, upload, and selection
st.sidebar.header("Video Management")
video_dir = "videos"
os.makedirs(video_dir, exist_ok=True)

# Video upload widget in sidebar
uploaded_file = st.sidebar.file_uploader("Upload a video file", type=["mp4", "mov"])
if uploaded_file is not None:
    uploaded_filename = uploaded_file.name
    save_path = os.path.join(video_dir, uploaded_filename)
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Uploaded {uploaded_filename}")

# Ingest videos
ingest = st.sidebar.button("Ingest All Videos in 'videos/'")
ingest_status = ""
if ingest:
    ingest_status = ingest_data_tool(video_dir)
    st.sidebar.success(ingest_status)

# List available videos
videos = [f for f in os.listdir(video_dir) if f.endswith((".mp4", ".mov"))]
selected_video = st.sidebar.selectbox("Select a video", videos if videos else ["No videos found"])

st.sidebar.markdown("---")

# Main area: Tool selection and results
if selected_video and selected_video != "No videos found":
    st.header(f"Tools for: {selected_video}")
    tool = st.selectbox("Choose a tool", [
        "Transcript", "Highlights", "Analytics", "Tags/Chapters", "Translate Transcript", "Image Search", "Query"
    ])

    if tool == "Transcript":
        result = get_transcript_tool(selected_video)
        st.subheader("Transcript")
        st.write(result.get("transcript", result))

    elif tool == "Highlights":
        result = get_highlights_tool(selected_video)
        st.subheader("Highlights")
        st.write(result.get("highlights", result))

    elif tool == "Analytics":
        result = get_analytics_tool(selected_video)
        st.subheader("Analytics")
        st.write(result.get("analytics", result))

    elif tool == "Tags/Chapters":
        result = get_tags_chapters_tool(selected_video)
        st.subheader("Tags and Chapters")
        st.write(result)

    elif tool == "Translate Transcript":
        lang = st.selectbox("Target Language", ["hi", "te", "en"])
        if st.button("Translate"):
            result = translate_transcript_tool(selected_video, lang)
            st.subheader(f"Translated Transcript ({lang})")
            st.write(result.get("translated_transcript", result))

    elif tool == "Image Search":
        image_path = st.text_input("Path to image file (absolute or relative)")
        threshold = st.slider("Match threshold", 0.0, 1.0, 0.8, 0.05)
        if st.button("Search Image in Video") and image_path:
            result = image_search_tool(image_path, os.path.join(video_dir, selected_video), threshold)
            st.subheader("Image Search Matches (seconds)")
            st.write(result.get("matches", result))

    elif tool == "Query":
        query = st.text_input("Enter your query about the video")
        if st.button("Run Query") and query:
            result = retrieve_data_tool(query)
            st.subheader("Query Results")
            st.write(result)
else:
    st.info("No video selected or available. Please add videos to the 'videos/' directory.") 