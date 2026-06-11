"""
Extract structured message data from terminal.log for use in unit tests.

Usage:
    cd POC/test1
    python test/fixtures/extract_messages.py
"""

import json
import os
import re
import sys


def extract_messages_from_log(log_file: str, start_line: int = 907, end_line: int = 1435) -> list:
    """Extract Discord message data from terminal.log using section-based extraction."""
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    lines = content.split('\n')
    joined = ''.join(lines[start_line - 1:end_line])

    # Find all 'has received [' positions to split message batches
    hr_positions = [m.start() for m in re.finditer(r'has received \[', joined)]

    messages = []

    for hr_pos in hr_positions:
        # Get the data section between this has_received and the next
        next_hr_idx = hr_positions.index(hr_pos) + 1
        if next_hr_idx < len(hr_positions):
            section_end = hr_positions[next_hr_idx]
        else:
            section_end = len(joined)

        data_start = hr_pos + len('has received ')
        section = joined[data_start:section_end]

        # Find all message dict starts in this section
        msg_starts = [m.start() for m in re.finditer(r"\{'type':", section)]

        for mi, ms in enumerate(msg_starts):
            # Get the dict block - from this start to the next start
            if mi + 1 < len(msg_starts):
                block = section[ms:msg_starts[mi + 1]]
            else:
                # Last message - find the end marker
                # Look for the pattern that ends a message dict in the list
                end_patterns = [
                    block.find("}, 'type'"),
                    block.find("}, 'pinned'"),
                    block.find("},\n"),
                ]
                end_pos = min(e for e in end_patterns if e >= 0) if any(e >= 0 for e in end_patterns) else len(block)
                block = block[:end_pos]

            # Extract fields from the block
            msg = extract_message_fields(block)
            if msg and msg.get("author"):
                messages.append(msg)

    return messages


def extract_message_fields(block: str) -> dict:
    """Extract message fields from a Python dict string block."""
    result = {}

    # Extract content - handle content that may span multiple lines
    # Pattern: 'content': '...' where ... may contain newlines
    content_match = re.search(r"'content':\s*'(.+?)',\s*'mentions':", block, re.DOTALL)
    if content_match:
        result["content"] = content_match.group(1).strip()
        # Clean up newlines - replace \n sequences with spaces
        result["content"] = re.sub(r'\s*\n\s*', ' ', result["content"])
    else:
        result["content"] = ""

    # Extract timestamp
    ts_match = re.search(r"'timestamp':\s*'([^']+)'", block)
    if ts_match:
        result["timestamp"] = ts_match.group(1)

    # Extract message id (first 'id' that's not inside author)
    # Find 'id' at the top level (not inside 'author': {...})
    author_end = block.find("'author':")
    if author_end > 0:
        before_author = block[:author_end]
    else:
        before_author = block

    id_match = re.search(r"'id':\s*'([^']+)'", before_author)
    if id_match:
        result["message_id"] = id_match.group(1)

    # Extract channel_id
    ch_match = re.search(r"'channel_id':\s*'([^']+)'", before_author)
    if ch_match:
        result["channel_id"] = ch_match.group(1)

    # Extract author info
    author_match = re.search(
        r"'author':\s*\{\s*'id':\s*'([^']*?)',\s*'username':\s*'([^']*?)'",
        block
    )
    if author_match:
        result["author_id"] = author_match.group(1)
        result["author"] = author_match.group(2)

    # Extract global_name (display name)
    gname_match = re.search(r"'global_name':\s*'([^']*?)'", block)
    if gname_match and gname_match.group(1):
        result["display_name"] = gname_match.group(1)
    else:
        result["display_name"] = result.get("author", "Unknown")

    # Extract attachments (image URLs) - look for url patterns outside author block
    # Find all 'url' patterns and filter for HTTP URLs
    url_matches = re.findall(r"'url':\s*'([^']+)'", block)
    result["image_urls"] = [u for u in url_matches if u.startswith("http")]
    result["has_image"] = len(result["image_urls"]) > 0

    # Detect replies
    content = result.get("content", "")
    if "Reply to" in content or "re: " in content.lower() or "In reply to" in content:
        result["is_reply"] = True
    else:
        result["is_reply"] = False

    return result


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    log_file = os.path.join(project_root, "terminal.log")

    if not os.path.exists(log_file):
        print(f"Error: {log_file} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Parsing {log_file} lines 907-1435...")
    messages = extract_messages_from_log(log_file, 907, 1435)
    print(f"Extracted {len(messages)} messages")

    # Write to fixture file
    output_file = os.path.join(script_dir, "channel_messages.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)

    print(f"Written to {output_file}")

    # Print summary
    for i, msg in enumerate(messages):
        content_preview = msg.get("content", "")[:80].replace("\n", " ")
        print(f"  Msg {i+1}: [{msg.get('author','?')}] {content_preview}...")


if __name__ == "__main__":
    main()