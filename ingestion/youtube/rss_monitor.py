#!/usr/bin/env python3
"""RSS-based YouTube channel monitor.

Polls YouTube channel RSS feeds hourly for new videos.
Tracks seen videos to avoid duplicates.
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Optional

import feedparser
import requests


def get_channel_rss_url(channel_id: str) -> str:
    """Build RSS feed URL for a YouTube channel."""
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def get_channel_id_from_url(channel_url: str) -> Optional[str]:
    """Extract channel ID from various YouTube URL formats.
    
    Handles:
    - youtube.com/channel/UC...
    - youtube.com/@handle
    - youtube.com/c/name
    """
    import re
    
    # Direct channel ID
    match = re.search(r'channel/([A-Za-z0-9_-]+)', channel_url)
    if match:
        return match.group(1)
    
    # @handle format — need to resolve
    match = re.search(r'@([A-Za-z0-9_-]+)', channel_url)
    if match:
        handle = match.group(1)
        return _resolve_handle_to_channel_id(handle)
    
    # /c/ format
    match = re.search(r'/c/([A-Za-z0-9_-]+)', channel_url)
    if match:
        # Would need API or page scrape to resolve
        return None
    
    return None


def _resolve_handle_to_channel_id(handle: str) -> Optional[str]:
    """Resolve @handle to channel ID via YouTube page."""
    try:
        url = f"https://www.youtube.com/@{handle}"
        response = requests.get(url, timeout=10)
        
        # Look for channel ID in page content
        import re
        match = re.search(r'"channelId":"([A-Za-z0-9_-]+)"', response.text)
        if match:
            return match.group(1)
        
        # Alternative pattern
        match = re.search(r'"externalId":"([A-Za-z0-9_-]+)"', response.text)
        if match:
            return match.group(1)
            
    except Exception as e:
        print(f"[ERROR] Failed to resolve handle @{handle}: {e}")
    
    return None


def fetch_channel_videos(channel_id: str, max_results: int = 5) -> List[dict]:
    """Fetch recent videos from channel RSS feed.
    
    Args:
        channel_id: YouTube channel ID
        max_results: Max videos to return
        
    Returns:
        List of video dicts with id, title, published, url
    """
    rss_url = get_channel_rss_url(channel_id)
    
    try:
        feed = feedparser.parse(rss_url)
        
        videos = []
        for entry in feed.entries[:max_results]:
            video = {
                "id": entry.get("yt_videoid", ""),
                "title": entry.get("title", ""),
                "published": entry.get("published", ""),
                "url": entry.get("link", ""),
                "author": entry.get("author", ""),
            }
            videos.append(video)
        
        return videos
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch RSS for {channel_id}: {e}")
        return []


def load_seen_videos(path: str = "data/seen_videos.json") -> dict:
    """Load seen video IDs."""
    if not os.path.exists(path):
        return {}
    
    with open(path, "r") as f:
        return json.load(f)


def save_seen_videos(seen: dict, path: str = "data/seen_videos.json") -> None:
    """Save seen video IDs."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(seen, f, indent=2)


def check_channels_for_new_videos(
    channels: List[dict],
    seen_videos_path: str = "data/seen_videos.json",
) -> List[dict]:
    """Check all channels for new videos.
    
    Args:
        channels: List of channel configs with id and name
        seen_videos_path: Path to seen videos tracking file
        
    Returns:
        List of new video dicts
    """
    seen = load_seen_videos(seen_videos_path)
    new_videos = []
    
    for channel in channels:
        channel_id = channel.get("channel_id")
        if not channel_id:
            print(f"[WARN] No channel ID for {channel.get('name', 'unknown')}")
            continue
        
        videos = fetch_channel_videos(channel_id)
        
        for video in videos:
            video_id = video["id"]
            
            if video_id not in seen:
                print(f"[MONITOR] New video from {channel['name']}: {video['title']}")
                video["channel_name"] = channel["name"]
                video["trust_level"] = channel.get("trust_level", "medium")
                new_videos.append(video)
                seen[video_id] = {
                    "title": video["title"],
                    "detected_at": datetime.now().isoformat(),
                    "channel": channel["name"],
                }
    
    if new_videos:
        save_seen_videos(seen, seen_videos_path)
        print(f"[MONITOR] Found {len(new_videos)} new videos")
    else:
        print("[MONITOR] No new videos")
    
    return new_videos


def run_monitor(config_path: str = "config/sources.json") -> List[dict]:
    """Run full monitor check.
    
    Args:
        config_path: Path to sources config
        
    Returns:
        List of new videos found
    """
    if not os.path.exists(config_path):
        print(f"[ERROR] Config not found: {config_path}")
        return []
    
    with open(config_path, "r") as f:
        config = json.load(f)
    
    channels = config.get("channels", [])
    if not channels:
        print("[WARN] No channels configured")
        return []
    
    print(f"[MONITOR] Checking {len(channels)} channels...")
    return check_channels_for_new_videos(channels)


if __name__ == "__main__":
    new_videos = run_monitor()
    
    if new_videos:
        print("\n=== NEW VIDEOS ===")
        for video in new_videos:
            print(f"  [{video['channel_name']}] {video['title']}")
            print(f"    URL: {video['url']}")
    else:
        print("\nNo new videos found.")
