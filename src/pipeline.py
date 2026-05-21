#!/usr/bin/env python3
"""Main pipeline: video URL -> transcript -> extract picks -> save."""

import json
import os
import sys
from datetime import datetime

from extract_video_id import extract_video_id
from fetch_transcript import fetch_transcript
from extract_picks import extract_picks_llm


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
    
    # Step 4: Extract picks
    result = extract_picks_llm(transcript, video_title=video_id, channel_name=channel_name)
    result["video_id"] = video_id
    result["url"] = video_url
    result["transcript_file"] = transcript_file
    result["processed_at"] = datetime.now().isoformat()
    
    # Step 5: Save result
    os.makedirs("data/picks", exist_ok=True)
    picks_file = f"data/picks/{video_id}.json"
    with open(picks_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"[PIPELINE] Saved picks to: {picks_file}")
    print(f"[PIPELINE] Detected tickers: {result.get('detected_tickers_regex', [])}")
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <youtube_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    result = run_pipeline(url)
    
    print("\n--- RESULT ---")
    print(json.dumps(result, indent=2, default=str))
