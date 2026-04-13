"""JSON utilities."""

import json


def save_json(data, filepath, indent=2):
    """Save data to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    return filepath


def load_json(filepath):
    """Load JSON from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)