from mcp.server.fastmcp import FastMCP
from main import clear_index, ingest_data, retrieve_data, chunk_video
from typing import Any
import requests
from collections import Counter
import re
import cv2
import numpy as np
import json

mcp = FastMCP("ragie")

@mcp.tool()
def ingest_data_tool(directory: str) -> str:
    """
    Loads data from a directory into the Ragie index. Wait until the data is fully ingested before continuing.

    Args:
        directory (str): The directory to load data from.

    Returns:
        str: A message indicating that the data was loaded successfully.
    """
    try:
        clear_index()
        ingest_data(directory)
        return "Data loaded successfully"
    except Exception as e:
        return f"Failed to load data: {str(e)}"

@mcp.tool()
def retrieve_data_tool(query: str) -> Any:
    """
    Retrieves data from the Ragie index based on the query. The data is returned as a list of dictionaries, each containing the following keys:
    - text: The text of the retrieved chunk
    - document_name: The name of the document the chunk belongs to
    - start_time: The start time of the chunk
    - end_time: The end time of the chunk

    Args:
        query (str): The query to retrieve data from the Ragie index.

    Returns:
        list[dict]: The retrieved data or error message.
    """
    try:
        return retrieve_data(query)
    except Exception as e:
        return {"error": f"Failed to retrieve data: {str(e)}"}

@mcp.tool()
def show_video_tool(document_name: str, start_time: float, end_time: float) -> str:
    """
    Creates and saves a video chunk based on the document name, start time, and end time of the chunk.
    Returns a message indicating that the video chunk was created successfully.

    Args:
        document_name (str): The name of the document the chunk belongs to
        start_time (float): The start time of the chunk
        end_time (float): The end time of the chunk

    Returns:
        str: A message indicating that the video chunk was created successfully
    """
    try:
        chunk_video(document_name, start_time, end_time)
        return "Video chunk created successfully"
    except Exception as e:
        return f"Failed to create video chunk: {str(e)}"

def format_transcript(transcript):
    # Split on } { to handle multiple JSON objects in a single string
    transcript = transcript.replace('} {', '}|||{')
    chunks = transcript.split('|||')
    formatted_chunks = []
    for chunk in chunks:
        try:
            parsed = json.loads(chunk)
            if isinstance(parsed, dict) and "video_description" in parsed:
                formatted_chunks.append(parsed["video_description"])
            else:
                formatted_chunks.append(json.dumps(parsed, indent=2))
        except Exception:
            formatted_chunks.append(chunk)
    return ('\n' + '='*60 + '\n').join(formatted_chunks)

@mcp.tool()
def get_transcript_tool(document_name: str) -> dict:
    """
    Returns the transcript for the given video document, formatted for readability.
    Args:
        document_name (str): The name of the document.
    Returns:
        dict: The formatted transcript.
    """
    try:
        chunks = retrieve_data(document_name)
        transcript = " ".join(chunk.get("text", "") for chunk in chunks if chunk.get("document_name") == document_name)
        formatted = format_transcript(transcript)
        return {"transcript": formatted}
    except Exception as e:
        return {"error": f"Failed to get transcript: {str(e)}"}

@mcp.tool()
def get_highlights_tool(document_name: str) -> dict:
    """
    Returns highlights for the given video document.
    Args:
        document_name (str): The name of the document.
    Returns:
        dict: The highlights.
    """
    try:
        chunks = retrieve_data(document_name)
        highlights = [chunk.get("text", "") for chunk in chunks if chunk.get("document_name") == document_name and chunk.get("text")] [:3]
        return {"highlights": highlights}
    except Exception as e:
        return {"error": f"Failed to get highlights: {str(e)}"}

@mcp.tool()
def get_analytics_tool(document_name: str) -> dict:
    """
    Returns analytics for the given video document.
    Args:
        document_name (str): The name of the document.
    Returns:
        dict: The analytics.
    """
    try:
        chunks = retrieve_data(document_name)
        chunk_texts = [c.get("text", "") for c in chunks if c.get("document_name") == document_name]
        transcript = " ".join(chunk_texts)
        words = re.findall(r"\w+", transcript.lower())
        stopwords = set(["the", "and", "a", "to", "of", "in", "is", "it", "for", "on", "with", "as", "at", "by", "an", "be", "this", "that", "from", "or", "are", "was", "but", "not", "have", "has", "had", "they", "you", "we", "he", "she", "his", "her", "their", "our", "its", "which", "who", "what", "when", "where", "how", "why"])
        non_stopwords = [w for w in words if w not in stopwords]
        most_common_words = [w for w, _ in Counter(non_stopwords).most_common(5)]
        num_highlights = min(3, len([t for t in chunk_texts if t]))
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
        return {"error": f"Failed to get analytics: {str(e)}"}

@mcp.tool()
def image_search_tool(image_path: str, video_path: str, threshold: float = 0.8, frame_interval: float = 0.5) -> dict:
    """
    Searches for the given image in the specified video file using template matching.
    Args:
        image_path (str): Path to the image file to search for.
        video_path (str): Path to the video file to search in.
        threshold (float): Similarity threshold (default 0.8).
        frame_interval (float): Time interval (in seconds) between frames to check (default 0.5).
    Returns:
        dict: {"matches": [timestamps_in_seconds]}
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": f"Could not read image: {image_path}"}
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {"error": f"Could not open video: {video_path}"}
        img_h, img_w = img.shape[:2]
        fps = cap.get(cv2.CAP_PROP_FPS)
        matches = []
        frame_count = 0
        while True:
            pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % int(frame_interval * fps) == 0:
                res = cv2.matchTemplate(frame, img, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                if max_val >= threshold:
                    matches.append(pos_msec / 1000.0)  # seconds
            frame_count += 1
        cap.release()
        return {"matches": matches}
    except Exception as e:
        return {"error": f"Failed to search by image: {str(e)}"}

@mcp.tool()
def get_tags_chapters_tool(document_name: str) -> dict:
    """
    Returns tags and chapters for the given video document.
    Args:
        document_name (str): The name of the document.
    Returns:
        dict: The tags and chapters.
    """
    try:
        chunks = retrieve_data(document_name)
        stopwords = set(["the", "and", "a", "to", "of", "in", "is", "it", "for", "on", "with", "as", "at", "by", "an", "be", "this", "that", "from", "or", "are", "was", "but", "not", "have", "has", "had", "they", "you", "we", "he", "she", "his", "her", "their", "our", "its", "which", "who", "what", "when", "where", "how", "why"])
        all_text = " ".join(chunk.get("text", "") for chunk in chunks if chunk.get("document_name") == document_name)
        words = re.findall(r"\w+", all_text.lower())
        tags = [w for w, _ in Counter([w for w in words if w not in stopwords]).most_common(5)]
        chapters = []
        chunk_texts = [chunk.get("text", "") for chunk in chunks if chunk.get("document_name") == document_name]
        for i in range(0, len(chunk_texts), 5):
            chapter_text = " ".join(chunk_texts[i:i+5])
            chapters.append(f"Chapter {i//5+1}: {chapter_text[:60]}...")
        return {"tags": tags, "chapters": chapters}
    except Exception as e:
        return {"error": f"Failed to get tags/chapters: {str(e)}"}

@mcp.tool()
def get_languages_tool() -> dict:
    """
    Returns supported languages.
    Returns:
        dict: The supported languages.
    """
    try:
        # Placeholder: Replace with actual language support logic
        return {"languages": ["en"]}
    except Exception as e:
        return {"error": f"Failed to get languages: {str(e)}"}

@mcp.tool()
def translate_transcript_tool(document_name: str, target_language: str) -> dict:
    try:
        chunks = retrieve_data(document_name)
        transcript = " ".join(chunk.get("text", "") for chunk in chunks if chunk.get("document_name") == document_name)
        response = requests.post(
            "http://localhost:5000/translate",
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
            # Fallback to Hugging Face Transformers for Hindi
            if target_language == "hi":
                try:
                    from transformers import pipeline
                    translator = pipeline("translation_en_to_hi", model="Helsinki-NLP/opus-mt-en-hi")
                    result = translator(transcript)
                    return {"translated_transcript": result[0]['translation_text']}
                except Exception as hf_e:
                    return {"error": f"Hugging Face translation failed: {str(hf_e)}"}
            return {"error": f"Translation API error: {response.text}"}
    except Exception as e:
        return {"error": f"Failed to translate transcript: {str(e)}"}

# Run the server locally
if __name__ == "__main__":
    mcp.run(transport='stdio')