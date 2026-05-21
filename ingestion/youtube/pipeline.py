#!/usr/bin/env python3
"""Main pipeline: video URL -> transcript -> extract picks -> save."""

import json
import os
import sys
from datetime import datetime

from .extract_video_id import extract_video_id
from .fetch_transcript import fetch_transcript

# Note: extract_picks module was removed in favor of agents/pick_extractor/llm_extractor.py
# Keeping pipeline focused on transcript fetch only


def run_pipeline(video_url: str, channel_name: str = "manual") -> dict:
    """Run full pipeline on a single video URL.
    
    Args:
        video_url: YouTube URL
        channel_name: Source channel name for tracking
        
    Returns:
        Result dict with picks, transcript preview, and file paths
    """
    print(f"[PIPELINE] Processing: {video_url}")
    
    # Step 1: Extract video ID
    video_id = extract_video_id(video_url)
    if not video_id:
        return {"error": "Could not extract video ID", "url": video_url}
    
    print(f"[PIPELINE] Video ID: {video_id}")
    
    # Step 2: Fetch transcript
    transcript = fetch_transcript(video_id)
    if not transcript:
        return {"error": "No transcript available", "video_id": video_id}
    
    print(f"[PIPELINE] Transcript: {len(transcript)} chars")
    
    # Step 3: Save raw transcript
    os.makedirs("data/transcripts", exist_ok=True)
    transcript_file = f"data/transcripts/{video_id}.txt"
    with open(transcript_file, 'w') as f:
        f.write(transcript)
    
    # Return transcript data — pick extraction is handled by agents/pick_extractor
    result = {
        "video_id": video_id,
        "url": video_url,
        "transcript": transcript,
        "transcript_file": transcript_file,
        "processed_at": datetime.now().isoformat(),
    }
    
    print(f"[PIPELINE] Saved transcript to: {transcript_file}")
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <youtube_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    result = run_pipeline(url)
    
    print("\n--- RESULT ---")
    print(json.dumps(result, indent=2, default=str))
