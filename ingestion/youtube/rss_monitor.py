#!/usr/bin/env python3
"""YouTube channel monitor — scrapes channel pages for new videos.

Replaces broken RSS feed approach with direct page scraping.
Tracks seen videos to avoid duplicates.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import List, Optional

import requests


def get_channel_id_from_url(channel_url: str) -> Optional[str]:
    """Extract or resolve channel ID from various YouTube URL formats.
    
    Handles:
    - youtube.com/channel/UC...
    - youtube.com/@handle
    - youtube.com/c/name
    """
    # Direct channel ID
    match = re.search(r'channel/([A-Za-z0-9_-]+)', channel_url)
    if match:
        return match.group(1)
    
    # @handle format — resolve via page scrape
    match = re.search(r'@([A-Za-z0-9_-]+)', channel_url)
    if match:
        handle = match.group(1)
        return _resolve_handle_to_channel_id(handle)
    
    # /c/ format
    match = re.search(r'/c/([A-Za-z0-9_-]+)', channel_url)
    if match:
        return _resolve_handle_to_channel_id(match.group(1))
    
    return None


def _resolve_handle_to_channel_id(handle: str) -> Optional[str]:
    """Resolve @handle to channel ID via YouTube page scrape."""
    try:
        url = f"https://www.youtube.com/@{handle}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        # Look for channel ID in page content
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
    """Fetch recent videos from channel page scrape.
    
    Args:
        channel_id: YouTube channel ID
        max_results: Max videos to return
        
    Returns:
        List of video dicts with id, title, published, url
    """
    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Extract ytInitialData JSON
        match = re.search(r'var ytInitialData = ({.+?});', response.text)
        if not match:
            print(f"[WARN] Could not find ytInitialData for channel {channel_id}")
            return []
        
        data = json.loads(match.group(1))
        
        # Navigate to video contents
        videos = []
        contents = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
        
        for tab in contents:
            if tab.get('tabRenderer', {}).get('selected'):
                items = tab.get('tabRenderer', {}).get('content', {}).get('richGridRenderer', {}).get('contents', [])
                
                for item in items[:max_results]:
                    lockup = item.get('richItemRenderer', {}).get('content', {}).get('lockupViewModel', {})
                    if not lockup:
                        continue
                    
                    content_id = lockup.get('contentId', '')
                    metadata = lockup.get('metadata', {}).get('lockupMetadataViewModel', {})
                    title = metadata.get('title', {}).get('content', '')
                    
                    if content_id and title:
                        videos.append({
                            "id": content_id,
                            "title": title,
                            "published": "",  # Not easily available in new layout
                            "url": f"https://youtube.com/watch?v={content_id}",
                            "author": "",
                        })
                
                break  # Found the videos tab
        
        return videos
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch videos for {channel_id}: {e}")
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
            # Try to resolve from URL
            channel_id = get_channel_id_from_url(channel.get("url", ""))
            if channel_id:
                channel["channel_id"] = channel_id
            else:
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
