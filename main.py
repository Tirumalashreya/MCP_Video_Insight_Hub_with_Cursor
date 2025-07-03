import os
import time
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from ragie import Ragie
from moviepy import VideoFileClip

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# initialize ragie client
ragie = Ragie(
    auth=os.getenv('RAGIE_API_KEY'),
)

# Remove previous docs from index
def clear_index():
    while True:
        try:
            # List all documents
            response = ragie.documents.list()
            documents = response.result.documents

            # Process each document
            for document in documents:
                try:
                    ragie.documents.delete(
                        document_id=document.id
                    )
                    logger.info(f"Deleted document {document.id}")
                except Exception as e:
                    logger.error(f"Failed to delete document {document.id}: {str(e)}")
                    raise

            # Check if there are more documents
            if not response.result.pagination.next_cursor:
                logger.warning("No more documents\n")
                break

        except Exception as e:
            logger.error(f"Failed to retrieve or process documents: {str(e)}")
            raise

# Ingest data from a directory into the Ragie index
def ingest_data(directory):
    # Get list of files in directory
    directory_path = Path(directory)
    files = os.listdir(directory_path)
    
    for file in files:
        try:
            file_path = directory_path / file
            # Read file content
            with open(file_path, mode='rb') as f:
                file_content = f.read()   
            # Create document in Ragie
            response = ragie.documents.create(request={
                "file": {
                    "file_name": file,
                    "content": file_content,
                },
                "mode": {
                    "video": "audio_video",
                    "audio": True
                }
            })
            # Wait for document to be ready
            while True:
                res = ragie.documents.get(document_id=response.id)
                if res.status == "ready":
                    break
        
                time.sleep(2)

            logger.info(f"Successfully uploaded {file}")
            
        except Exception as e:
            logger.error(f"Failed to process file {file}: {str(e)}")
            continue

# Retrieve data from the Ragie index
def retrieve_data(query):
    try:
        logger.info(f"Retrieving data for query: {query}")
        retrieval_response = ragie.retrievals.retrieve(request={
            "query": query
        })

        content = [
            {
                **chunk.document_metadata,
                "text": chunk.text,
                "document_name": chunk.document_name,
                "start_time": chunk.metadata.get("start_time"),
                "end_time": chunk.metadata.get("end_time")
            }
            for chunk in retrieval_response.scored_chunks
        ]

        logger.info(f"Successfully retrieved {len(content)} chunks")
        return content

    except Exception as e:
        logger.error(f"Failed to retrieve data: {str(e)}")
        raise

def chunk_video(document_name, start_time, end_time, directory="videos"):
    output_dir = Path("video_chunks")
    output_dir.mkdir(parents=True, exist_ok=True)
    chunk_filename = f"video_chunk_{start_time:.1f}_{end_time:.1f}.mp4"
    output_path = output_dir / chunk_filename

    with VideoFileClip(directory + "/" + document_name) as video:
        video_duration = video.duration
        if start_time >= video_duration:
            raise ValueError(f"start_time ({start_time}) should be smaller than the clip's duration ({video_duration}).")
        actual_end_time = min(end_time, video_duration) if end_time is not None else video_duration
        video_chunk = video.subclipped(start_time, actual_end_time)
        video_chunk.write_videofile(str(output_path))

    return output_path

def ingest_data_tool(directory: str) -> str:
    try:
        clear_index()
        ingest_data(directory)
        return "Data loaded successfully"
    except Exception as e:
        logger.error(f"Failed to load data: {str(e)}")
        return f"Failed to load data: {str(e)}"

def retrieve_data_tool(query: str) -> Any:
    try:
        logger.info(f"Retrieving data for query: {query}")
        return retrieve_data(query)
    except Exception as e:
        logger.error(f"Failed to retrieve data: {str(e)}")
        return {"error": f"Failed to retrieve data: {str(e)}"}

def show_video_tool(document_name: str, start_time: float, end_time: float) -> str:
    try:
        logger.info(f"Creating video chunk for {document_name} from {start_time} to {end_time}")
        chunk_video(document_name, start_time, end_time)
        return "Video chunk created successfully"
    except ValueError as ve:
        logger.error(f"ValueError: {str(ve)}")
        return f"Error: {str(ve)}"
    except Exception as e:
        logger.error(f"Failed to create video chunk: {str(e)}")
        return f"Failed to create video chunk: {str(e)}"

def get_analytics_tool(document_name: str) -> dict:
    try:
        logger.info(f"Getting analytics for {document_name}")
        return ragie.analytics.get(document_name=document_name)
    except Exception as e:
        logger.error(f"Failed to get analytics: {str(e)}")
        return {"error": f"Failed to get analytics: {str(e)}"}

def image_search_tool(file_path: str) -> dict:
    try:
        logger.info(f"Searching by image: {file_path}")
        return ragie.images.search(file_path=file_path)
    except Exception as e:
        logger.error(f"Failed to search by image: {str(e)}")
        return {"error": f"Failed to search by image: {str(e)}"}

def get_tags_chapters_tool(document_name: str) -> dict:
    try:
        logger.info(f"Getting tags and chapters for {document_name}")
        return ragie.tags_chapters.get(document_name=document_name)
    except Exception as e:
        logger.error(f"Failed to get tags/chapters: {str(e)}")
        return {"error": f"Failed to get tags/chapters: {str(e)}"}

def get_languages_tool() -> dict:
    try:
        logger.info("Getting supported languages")
        return ragie.languages.list()
    except Exception as e:
        logger.error(f"Failed to get languages: {str(e)}")
        return {"error": f"Failed to get languages: {str(e)}"}

if __name__ == "__main__":
    clear_index()
    ingest_data("videos")
    print(retrieve_data("What is the main topic of the video?"))
