#!/usr/bin/env python3
"""Extract YouTube video ID from various URL formats."""

import re
from urllib.parse import urlparse, parse_qs


def extract_video_id(url: str) -> str | None:
    """Extract video ID from YouTube URL.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    # youtu.be short links
    if "youtu.be/" in url:
        match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)
    
    # Standard watch links
    parsed = urlparse(url)
    if parsed.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        query = parse_qs(parsed.query)
        if 'v' in query:
            return query['v'][0]
        
        # /embed/VIDEO_ID or /shorts/VIDEO_ID
        match = re.search(r'/(?:embed|shorts)/([a-zA-Z0-9_-]{11})', parsed.path)
        if match:
            return match.group(1)
    
    return None


if __name__ == "__main__":
    test_urls = [
        "https://youtu.be/KgzthZdu8Rk?si=cFIpuExrgf_a6F4B",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/abc123def45",
    ]
    
    for url in test_urls:
        vid = extract_video_id(url)
        print(f"{url} -> {vid}")
