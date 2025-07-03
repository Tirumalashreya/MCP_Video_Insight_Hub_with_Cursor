from fastapi import FastAPI, UploadFile, File, Form, Query, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional
import os
import uuid
import time
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import retrieve_data, clear_index, ingest_data, chunk_video
import inspect
import server
from collections import Counter
import re
import requests

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job status store
job_status = {}

def process_video(file_path, job_id):
    job_status[job_id] = "processing"
    time.sleep(10)  # Simulate processing delay; replace with real logic
    job_status[job_id] = "ready"

def ingest_single_video(file_path):
    from main import ragie
    file_name = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        file_content = f.read()
    response = ragie.documents.create(request={
        "file": {
            "file_name": file_name,
            "content": file_content,
        },
        "mode": {
            "video": "audio_video",
            "audio": True
        }
    })
    import time
    while True:
        res = ragie.documents.get(document_id=response.id)
        if res.status == "ready":
            break
        time.sleep(2)

@app.post("/upload_video/")
def upload_video(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    os.makedirs("videos", exist_ok=True)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")
    file_path = os.path.join("videos", file.filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    
    # Only ingest the newly uploaded video
    ingest_single_video(file_path)

    job_id = str(uuid.uuid4())
    job_status[job_id] = "uploaded"
    if background_tasks is not None:
        background_tasks.add_task(process_video, file_path, job_id)
    return {"message": "Video uploaded successfully", "filename": file.filename, "job_id": job_id}

@app.get("/status/{job_id}")
def get_status(job_id: str):
    status = job_status.get(job_id, "not_found")
    return {"job_id": job_id, "status": status}

@app.post("/query/")
async def query_video(request: Request):
    try:
        data = await request.json()
        query = data.get("query")
        if not query:
            return {"answer": "No query provided.", "chunks": []}
        chunks = retrieve_data(query)
        if chunks and isinstance(chunks, list) and len(chunks) > 0:
            answer = chunks[0].get("text", "No answer found.")
            return {"answer": answer, "chunks": chunks}
        else:
            return {"answer": "No relevant content found.", "chunks": []}
    except Exception as e:
        return {"answer": f"Error: {str(e)}", "chunks": []}

@app.post("/get_video_snippet/")
async def get_video_snippet_post(request: Request):
    data = await request.json()
    document_name = data.get("document_name")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    if not document_name or start_time is None or end_time is None:
        return JSONResponse({"error": "Missing required parameters."}, status_code=400)
    try:
        snippet_path = chunk_video(document_name, float(start_time), float(end_time))
        return FileResponse(str(snippet_path), media_type="video/mp4")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/get_transcript/")
async def get_transcript_post(request: Request):
    data = await request.json()
    document_name = data.get("document_name")
    if not document_name:
        return JSONResponse({"error": "Missing document_name."}, status_code=400)
    try:
        # Get all chunks for this video
        from main import retrieve_data
        chunks = retrieve_data(document_name)
        transcript = " ".join(chunk.get("text", "") for chunk in chunks if chunk.get("document_name") == document_name)
        return {"transcript": transcript}
    except Exception as e:
        return JSONResponse({"error": f"Failed to get transcript: {str(e)}"}, status_code=500)

@app.post("/get_highlights/")
async def get_highlights_post(request: Request):
    data = await request.json()
    document_name = data.get("document_name")
    if not document_name:
        return JSONResponse({"error": "Missing document_name."}, status_code=400)
    try:
        from main import retrieve_data
        chunks = retrieve_data(document_name)
        # Take first 3 non-empty chunks as highlights
        highlights = [chunk.get("text", "") for chunk in chunks if chunk.get("document_name") == document_name and chunk.get("text")] \
            [:3]
        return {"highlights": highlights}
    except Exception as e:
        return JSONResponse({"error": f"Failed to get highlights: {str(e)}"}, status_code=500)

@app.post("/translate_transcript/")
async def translate_transcript_post(request: Request):
    data = await request.json()
    document_name = data.get("document_name")
    target_language = data.get("target_language")
    if not document_name or not target_language:
        return JSONResponse({"error": "Missing document_name or target_language."}, status_code=400)
    try:
        from main import retrieve_data
        chunks = retrieve_data(document_name)
        transcript = " ".join(chunk.get("text", "") for chunk in chunks if chunk.get("document_name") == document_name)
        # Use LibreTranslate public API
        response = requests.post(
            "https://libretranslate.com/translate",
            data={
                "q": transcript,
                "source": "en",
                "target": target_language,
                "format": "text"
            },
            timeout=30
        )
        if response.status_code == 200:
            translated = response.json().get("translatedText", "")
            return {"translated_transcript": translated}
        else:
            return JSONResponse({"error": f"Translation API error: {response.text}"}, status_code=500)
    except Exception as e:
        return JSONResponse({"error": f"Failed to translate transcript: {str(e)}"}, status_code=500)

@app.post("/get_analytics/")
async def get_analytics_post(request: Request):
    data = await request.json()
    document_name = data.get("document_name")
    if not document_name:
        return JSONResponse({"error": "Missing document_name."}, status_code=400)
    try:
        from main import retrieve_data
        chunks = retrieve_data(document_name)
        chunk_texts = [c.get("text", "") for c in chunks if c.get("document_name") == document_name]
        transcript = " ".join(chunk_texts)
        words = re.findall(r"\w+", transcript.lower())
        stopwords = set(["the", "and", "a", "to", "of", "in", "is", "it", "for", "on", "with", "as", "at", "by", "an", "be", "this", "that", "from", "or", "are", "was", "but", "not", "have", "has", "had", "they", "you", "we", "he", "she", "his", "her", "their", "our", "its", "which", "who", "what", "when", "where", "how", "why"])
        non_stopwords = [w for w in words if w not in stopwords]
        most_common_words = [w for w, _ in Counter(non_stopwords).most_common(5)]
        num_highlights = min(3, len([t for t in chunk_texts if t]))
        # Estimate duration: assume 150 words/minute
        duration_min = round(len(words) / 150, 2) if words else 0
        analytics = {
            "num_chunks": len(chunk_texts),
            "total_length": sum(len(t) for t in chunk_texts),
            "duration_minutes": duration_min,
            "most_common_words": most_common_words,
            "num_highlights": num_highlights
        }
        return {"analytics": analytics}
    except Exception as e:
        return JSONResponse({"error": f"Failed to get analytics: {str(e)}"}, status_code=500)

@app.post("/image_search/")
async def image_search_post(request: Request):
    # For demo: expects base64 or similar in JSON, but real use would be multipart/form-data
    data = await request.json()
    # Placeholder: Return matching video segments
    return {"matches": []}

@app.post("/get_tags_chapters/")
async def get_tags_chapters_post(request: Request):
    data = await request.json()
    document_name = data.get("document_name")
    if not document_name:
        return JSONResponse({"error": "Missing document_name."}, status_code=400)
    try:
        from main import retrieve_data
        import collections
        chunks = retrieve_data(document_name)
        # Tags: most common words (excluding stopwords)
        import re
        stopwords = set(["the", "and", "a", "to", "of", "in", "is", "it", "for", "on", "with", "as", "at", "by", "an", "be", "this", "that", "from", "or", "are", "was", "but", "not", "have", "has", "had", "they", "you", "we", "he", "she", "his", "her", "their", "our", "its", "which", "who", "what", "when", "where", "how", "why"])
        all_text = " ".join(chunk.get("text", "") for chunk in chunks if chunk.get("document_name") == document_name)
        words = re.findall(r"\w+", all_text.lower())
        tags = [w for w, _ in collections.Counter([w for w in words if w not in stopwords]).most_common(5)]
        # Chapters: split transcript every 5 chunks
        chapters = []
        chunk_texts = [chunk.get("text", "") for chunk in chunks if chunk.get("document_name") == document_name]
        for i in range(0, len(chunk_texts), 5):
            chapter_text = " ".join(chunk_texts[i:i+5])
            chapters.append(f"Chapter {i//5+1}: {chapter_text[:60]}...")
        return {"tags": tags, "chapters": chapters}
    except Exception as e:
        return JSONResponse({"error": f"Failed to get tags/chapters: {str(e)}"}, status_code=500)

@app.post("/get_languages/")
async def get_languages_post():
    try:
        # Only English supported for now
        return {"languages": ["en"]}
    except Exception as e:
        return JSONResponse({"error": f"Failed to get languages: {str(e)}"}, status_code=500)

# Remove everything below this line that is not a route or utility function!
# If you want to keep test code, use:
# if __name__ == "__main__":
#     # test/demo code here 