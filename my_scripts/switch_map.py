#!/usr/bin/env python3
"""
Map Switcher Tool

This script helps you easily switch between different maps by updating the env.sh file.

Usage:
    python switch_map.py list                    # List all available maps
    python switch_map.py set <map_key>          # Switch to a specific map
    python switch_map.py current                # Show current map configuration
    python switch_map.py add <key> <path> <lat> <lon>  # Add a new map configuration
"""

import json
import sys
import os
from pathlib import Path


CONFIG_FILE = Path(__file__).parent / "maps_config.json"
ENV_FILE = Path(__file__).parent.parent / "env.sh"


def load_config():
    """Load the maps configuration file."""
    if not CONFIG_FILE.exists():
        print(f"Error: Configuration file not found at {CONFIG_FILE}")
        sys.exit(1)
    
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def save_config(config):
    """Save the maps configuration file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Configuration saved to {CONFIG_FILE}")




def list_maps():
    """List all available maps."""
    config = load_config()
    current_map = config.get('current_map', 'unknown')
    
    print("\n=== Available Maps ===\n")
    
    for key, map_info in config['maps'].items():
        current_marker = " (CURRENT)" if key == current_map else ""
        print(f"  {key}{current_marker}")
        print(f"    Name: {map_info['name']}")
        print(f"    Path: {map_info['path']}")
        print(f"    Origin: ({map_info['origin_lat']}, {map_info['origin_lon']})")
        print(f"    Description: {map_info['description']}")
        print()


def set_map(map_key):
    """Switch to the specified map."""
    config = load_config()
    
    if map_key not in config['maps']:
        print(f"Error: Map '{map_key}' not found in configuration.")
        print(f"\nAvailable maps: {', '.join(config['maps'].keys())}")
        sys.exit(1)
    
    map_info = config['maps'][map_key]
    
    # Update current map in config
    config['current_map'] = map_key
    save_config(config)
    
    print(f"\n✓ Switched to map: {map_info['name']}")
    print(f"  Path: {map_info['path']}")
    print(f"  Origin: ({map_info['origin_lat']}, {map_info['origin_lon']})")


def show_current():
    """Show the current map configuration."""
    config = load_config()
    current_map = config.get('current_map', 'unknown')
    
    if current_map == 'unknown' or current_map not in config['maps']:
        print("No current map set or map not found in configuration.")
        return
    
    map_info = config['maps'][current_map]
    
    print("\n=== Current Map Configuration ===\n")
    print(f"  Key: {current_map}")
    print(f"  Name: {map_info['name']}")
    print(f"  Path: {map_info['path']}")
    print(f"  Origin: ({map_info['origin_lat']}, {map_info['origin_lon']})")
    print(f"  Description: {map_info['description']}")
    print()


def add_map(key, path, lat, lon, name=None, description=None):
    """Add a new map to the configuration."""
    config = load_config()
    
    if key in config['maps']:
        print(f"Warning: Map '{key}' already exists. Overwriting...")
    
    config['maps'][key] = {
        'name': name or key,
        'path': path,
        'origin_lat': float(lat),
        'origin_lon': float(lon),
        'description': description or f"Map {key}"
    }
    
    save_config(config)
    print(f"\n✓ Added map: {key}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_maps()
    
    elif command == 'set':
        if len(sys.argv) < 3:
            print("Error: Please specify a map key")
            print("Usage: python switch_map.py set <map_key>")
            sys.exit(1)
        set_map(sys.argv[2])
    
    elif command == 'current':
        show_current()
    
    elif command == 'add':
        if len(sys.argv) < 6:
            print("Error: Insufficient arguments")
            print("Usage: python switch_map.py add <key> <path> <lat> <lon> [name] [description]")
            sys.exit(1)
        key = sys.argv[2]
        path = sys.argv[3]
        lat = sys.argv[4]
        lon = sys.argv[5]
        name = sys.argv[6] if len(sys.argv) > 6 else None
        description = sys.argv[7] if len(sys.argv) > 7 else None
        add_map(key, path, lat, lon, name, description)
    
    else:
        print(f"Error: Unknown command '{command}'")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
