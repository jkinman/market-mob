#!/usr/bin/env python3
"""Fetch YouTube video transcript using youtube-transcript-api."""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


def fetch_transcript(video_id: str) -> str | None:
    """Fetch transcript text for a YouTube video.
    
    Args:
        video_id: 11-character YouTube video ID
        
    Returns:
        Full transcript text or None if unavailable
    """
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.fetch(video_id)
        text = " ".join([entry.text for entry in transcript_list])
        return text
    except TranscriptsDisabled:
        print(f"[ERROR] Transcripts disabled for {video_id}")
        return None
    except NoTranscriptFound:
        print(f"[ERROR] No transcript found for {video_id}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to fetch transcript for {video_id}: {e}")
        return None


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fetch_transcript.py <video_id>")
        sys.exit(1)
    
    vid = sys.argv[1]
    transcript = fetch_transcript(vid)
    
    if transcript:
        print(f"--- Transcript for {vid} ---")
        print(transcript[:2000])  # Print first 2000 chars
        print(f"\n... ({len(transcript)} total characters)")
    else:
        print("Failed to fetch transcript.")
