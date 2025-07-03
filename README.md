# MCP Video RAG: Video Retrieval-Augmented Generation with Streamlit & Cursor

## Overview
This project enables semantic search, Q&A, and analytics over video content using Retrieval-Augmented Generation (RAG) and the Model Context Protocol (MCP). It supports two main interfaces:
- **Streamlit Web UI**: For uploading, ingesting, and analyzing videos in your browser.
- **Cursor MCP Client**: For interacting with the same backend tools via natural language or code in the Cursor IDE.

---

## Architecture Diagram

![videorag](https://github.com/user-attachments/assets/ff212d93-cf43-426e-b99b-3e71e6db0ef3)



## Features
- **Video Upload & Ingestion**: Upload videos via the web UI or add them to the `videos/` directory.
- **Semantic Search & Q&A**: Query video content using natural language.
- **Transcripts, Highlights, Analytics**: Extract and analyze video content.
- **Image-to-Video Search**: Find where a screenshot appears in a video.
- **Translation**: Translate video transcripts to supported languages.

---

## Setup & Installation

### 1. Clone the Repository
```sh
git clone <your-repo-url>
cd mcp-video-rag
```

### 2. Set Up Python Environment
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # or use pyproject.toml with uv/poetry
```

### 3. Install Additional Dependencies
```sh
pip install opencv-python streamlit
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and set your `RAGIE_API_KEY` if required.

---

## Usage

### Option 1: Streamlit Web UI
1. **Start the Streamlit app:**
   ```sh
   source .venv/bin/activate
   streamlit run streamlit_app.py
   ```
2. **Open your browser:**
   Go to `http://localhost:8501` (or the port shown in your terminal).
3. **Upload videos:**
   - Use the sidebar to upload `.mp4` or `.mov` files.
   - Click "Ingest All Videos" to process them.
4. **Analyze videos:**
   - Select a video from the dropdown.
   - Use the tool panel to get transcripts, highlights, analytics, run queries, search by image, or translate transcripts.

### Option 2: Cursor MCP Client
1. **Start the MCP server:**
   ```sh
   source .venv/bin/activate
   python server.py
   ```
2. **Configure Cursor IDE:**
   - Go to Cursor settings > MCP Tools.
   - Add a new MCP server pointing to your project and `server.py`.
   - Use the Cursor agent to issue queries like:
     - "Ingest videos"
     - "Get transcript for cricket.mov"
     - "Search this image in messi-goals.mp4"
     - "Translate transcript to Hindi"
3. **Results** will appear in the Cursor chat or output panel.

---

## Project Structure
```
mcp-video-rag/
├── server.py           # MCP tools backend
├── streamlit_app.py    # Streamlit web UI
├── videos/             # Video files directory
├── video_chunks/       # Output video chunks
├── pyproject.toml      # Python dependencies
├── README.md           # This file
└── ...
```

---

## Extending the Project
- Add new MCP tools in `server.py` for more analytics or video processing.
- Customize the Streamlit UI for your workflow.
- Integrate with other RAG or LLM APIs as needed.

---

## Credits
- Built with [Ragie](https://www.ragie.ai/), [Streamlit](https://streamlit.io/), [Cursor](https://www.cursor.so/), and [OpenCV](https://opencv.org/).
