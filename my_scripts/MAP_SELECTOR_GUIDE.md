# Map Selector Guide - Complete Documentation

## 🎯 Quick Start

### Using the Web Interface
1. Open the FMS web application
2. Go to **Map Viewer** page
3. Click the **Select Map** dropdown in the right panel
4. Choose a map from the list
5. Page automatically reloads with the new map ✓

---

## 📋 Available Maps

| Key | Name | Location |
|-----|------|----------|
| `town01` | Town01 | (0, 0) |
| `tc_frontyard` | TC Autonomous Frontyard | (35.238, 139.901) |
| `tc_frontyard_1lane` | TC Frontyard - 1 Lane | (35.238, 139.901) |
| `tc_frontyard_parking` | TC Frontyard - Parking | (35.238, 139.901) |
| `tc_complete` | TC Complete | (35.238, 139.901) |
| `tc_complete_loop` | TC Complete - Loop | (35.238, 139.901) |
| `tc_complete_parking` | TC Complete - Parking | (35.238, 139.901) |
| `tcav_office` | TCAV Office | (35.238, 139.901) |
| `tcav_office_straight` | TCAV Office - Straight | (35.238, 139.901) |

---

## 🌐 Web Interface Guide

### Location in UI
The map selector is in the **Map Viewer** page, right panel:

```
┌─────────────────────────────────────────────────────────────────┐
│ Map Viewer                                                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────┐  ┌─────────────────────────────┐ │
│  │                          │  │  Select Map                 │ │
│  │                          │  │  [Dropdown ▼]              │ │
│  │     Map Viewer           │  │                             │ │
│  │  (OSM Lanelet2 Map)      │  │  Select a vehicle           │ │
│  │                          │  │  [Dropdown ▼]              │ │
│  │  [Map Display Area]      │  │                             │ │
│  │                          │  │  Goal Pose                  │ │
│  │                          │  │  [Select] [Set]             │ │
│  │                          │  │  [Engage]                   │ │
│  │                          │  │                             │ │
│  └──────────────────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### How It Works
1. **Click dropdown** → List of available maps appears
2. **Select map** → Button shows loading state with spinner
3. **Switch completes** → Page automatically reloads
4. **New map displays** → Map view updated with new map

### Visual States

**Loading/Switching**
- Spinner animation
- Button disabled
- Text: "Switching..."

**Success**
- Page reloads automatically
- New map displays
- Dropdown closes

---

## 💻 Command Line Tool

### Basic Commands
```bash
# List all available maps
python3 my_scripts/switch_map.py list

# Switch to a map
python3 my_scripts/switch_map.py set tc_frontyard

# Check current map
python3 my_scripts/switch_map.py current

# Add a new map
python3 my_scripts/switch_map.py add new_map /carla_map/path/map.osm 35.0 139.0 "Display Name" "Description"
```

---

## 🔌 API Endpoints

### Get Available Maps
```bash
curl http://localhost:8000/map/list-available
```

**Response:**
```json
{
  "maps": {
    "town01": {
      "name": "Town01",
      "description": "CARLA Town01 Map",
      "origin_lat": 0,
      "origin_lon": 0
    },
    "tc_frontyard": {
      "name": "TC Autonomous Frontyard",
      "description": "...",
      "origin_lat": 35.238,
      "origin_lon": 139.901
    }
  },
  "current_map": "town01"
}
```

### Switch to a Map
```bash
curl "http://localhost:8000/map/switch?map_key=tc_frontyard"
```

**Response:**
```json
{
  "success": true,
  "message": "Switched to tc_frontyard"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Map 'invalid_key' not found"
}
```

---

## 📝 Configuration

### File Location
```
my_scripts/maps_config.json
```

### Configuration Format
```json
{
  "current_map": "town01",
  "maps": {
    "town01": {
      "name": "Town01",
      "path": "/carla_map/Town01/lanelet2_map.osm",
      "origin_lat": 0,
      "origin_lon": 0,
      "description": "CARLA Town01 Map"
    },
    "tc_frontyard": {
      "name": "TC Autonomous Frontyard",
      "path": "/carla_map/TC_autonomous_frontyard/lanelet2_map.osm",
      "origin_lat": 35.238,
      "origin_lon": 139.901,
      "description": "TC Autonomous Frontyard Map"
    }
  }
}
```

### Adding a New Map Manually
Edit `maps_config.json` and add a new entry:

```json
{
  "maps": {
    "my_custom_map": {
      "name": "My Custom Map",
      "path": "/carla_map/custom/map.osm",
      "origin_lat": 35.5,
      "origin_lon": 140.0,
      "description": "My custom map description"
    }
  }
}
```

The new map will appear automatically in the web UI!

---

## 🏗️ Architecture

### How Map Switching Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│                                                                 │
│  User clicks map in dropdown → MapSelector component calls API  │
└────────────────────────┬────────────────────────────────────────┘
                         │ Calls: /map/switch?map_key=...
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                            │
│                                                                │
│  api_server.py receives request:                              │
│  1. Validates map key in config                               │
│  2. Calls switch_map.py CLI script                            │
│  3. Reloads maps_config.json                                  │
│  4. Updates backend state (env vars, projector)               │
│  5. Returns success response                                  │
└────────────────────────┬───────────────────────────────────────┘
                         │ Returns: {"success": true}
                         ↓
┌────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│                                                                 │
│  1. Detects success response                                  │
│  2. Shows loading spinner                                     │
│  3. Waits 1 second for backend to settle                      │
│  4. Automatically reloads page                                │
│  5. New map loads with updated configuration                  │
└────────────────────────────────────────────────────────────────┘
```

### Key Components

**Frontend:**
- `frontend/src/features/fms/mapview/MapSelector.js` - Dropdown component
- `frontend/src/features/fms/mapview/index.js` - Main map view
- `frontend/src/features/fms/mapview/mapViewer.js` - Leaflet map display

**Backend:**
- `api_server.py` - FastAPI server with `/map/list-available` and `/map/switch` endpoints
- `my_scripts/switch_map.py` - CLI tool to update configuration
- `my_scripts/maps_config.json` - Map configuration storage
- `zenoh_app/pose_service.py` - Vehicle pose tracking (updated on map switch)

---

## 🛠️ Implementation Details

### Coordinate Systems
The system handles two coordinate systems:

1. **Global Coordinates (lat/lon)** - Used by Town01
   - Standard GPS coordinates
   - Displayed directly in map

2. **Local Coordinates (local_x/local_y)** - Used by TC maps
   - Local coordinates from lanelet2 map
   - Converted using origin point (lat/lon)
   - Formula: lat = origin_lat + (local_y / 111320), lon = origin_lon + (local_x / 111320 * cos(lat))

### Map Loading
When a map is selected:

1. Frontend requests `/map/list-available`
2. Backend returns current map and all available maps
3. Frontend loads XML file from path
4. MapViewer component parses coordinates
5. Leaflet displays polylines on map
6. Zoom adjusted to fit map bounds

### Vehicle Integration
- Vehicle position updates every cycle
- Goal routing uses current map coordinates
- Projector and orientation parser updated on map switch

---

## ❌ Troubleshooting

### Maps not showing in web UI
**Symptoms:** Dropdown empty or maps not listed
1. Check if API server is running: `curl http://localhost:8000/map/list-available`
2. Check browser console for JavaScript errors
3. Verify `maps_config.json` exists and is valid JSON
4. **Fix:** Restart API server

### Map switch fails
**Symptoms:** Error message or page doesn't reload
1. Verify map key exists: `python3 my_scripts/switch_map.py list`
2. Check map file path is valid: `ls -la /carla_map/...`
3. Check API server logs: `tail -f logs/api_server.log`
4. Verify write permissions on `maps_config.json`
5. **Fix:** Use CLI to verify, then retry web UI

### New map not appearing
**Symptoms:** Map added to config but doesn't show in UI
1. Verify JSON syntax in `maps_config.json`
2. Check map file path is correct
3. **Fix:** Refresh browser page or restart application

### Old map still displays
**Symptoms:** Map doesn't update after switching
1. Check browser cache: Hard refresh (Ctrl+Shift+R)
2. Verify backend actually switched: Check `maps_config.json` current_map value
3. Check browser console for errors
4. **Fix:** Hard refresh or clear browser cache

### Map display is blank or wrong
**Symptoms:** Map loads but shows no polylines
1. Check map file exists: `ls -la <map_path>`
2. Verify map file is valid OSM/Lanelet2 format
3. Check coordinate system matches: local_x/local_y vs lat/lon
4. **Fix:** Validate map file, check origin coordinates in config

---

## 📚 Files Reference

```
zenoh_autoware_fms/
├── api_server.py                      # Backend API with /map/* endpoints
├── my_scripts/
│   ├── switch_map.py                 # CLI tool to switch maps
│   ├── maps_config.json              # Map configuration
│   └── MAP_SELECTOR_GUIDE.md         # This file
├── frontend/
│   └── src/features/fms/mapview/
│       ├── index.js                  # Main map view container
│       ├── MapSelector.js            # Map dropdown selector
│       ├── mapViewer.js              # Leaflet map display
│       └── mapViewSlice.js           # Redux state
└── zenoh_app/
    └── pose_service.py               # Vehicle pose & goal routing
```

---

## 💡 Tips & Tricks

### View Current Map
```bash
cat my_scripts/maps_config.json | grep -A 1 '"current_map"'
```

### Check Map File Exists
```bash
ls -la /carla_map/TC_autonomous_frontyard/lanelet2_map.osm
```

### View API Logs
```bash
tail -f logs/api_server.log
```

### Combine CLI and Web
- Use CLI in scripts for automation
- Use Web UI for manual selection
- Both update the same config

### Development
To modify the map selector:
1. Edit `frontend/src/features/fms/mapview/MapSelector.js`
2. Modify styling in component's className
3. Update state handling in index.js

---

## 🚀 Getting Started

### I want to switch maps
**Option 1: Web UI (Recommended)**
1. Go to Map Viewer page
2. Click "Select Map" dropdown
3. Choose a map
4. Wait for automatic reload

**Option 2: Command Line**
```bash
python3 my_scripts/switch_map.py set tc_frontyard
```

### I want to add a new map
**Option 1: Edit configuration**
```bash
nano my_scripts/maps_config.json
# Add new map entry (see Configuration section)
```

**Option 2: Use CLI**
```bash
python3 my_scripts/switch_map.py add my_map /carla_map/custom/map.osm 35.0 139.0 "Map Name" "Description"
```

### I want to understand the code
1. Start with this guide's Architecture section
2. Read `api_server.py` for backend implementation
3. Read `frontend/src/features/fms/mapview/MapSelector.js` for frontend
4. Read `my_scripts/switch_map.py` for CLI tool

---

## 📞 Support

If you encounter issues:

1. **Check logs:**
   ```bash
   tail -f logs/api_server.log
   ```

2. **Verify configuration:**
   ```bash
   cat my_scripts/maps_config.json
   ```

3. **Test API directly:**
   ```bash
   curl http://localhost:8000/map/list-available
   ```

4. **Review this guide:** Check the Troubleshooting section

5. **Check file permissions:**
   ```bash
   ls -la my_scripts/maps_config.json
   ```

---

## 📄 Summary

The Map Selector feature provides an easy way to switch between different Lanelet2 OSM maps:

- **Web UI (Recommended)**: Click dropdown in Map Viewer page - automatic reload
- **CLI**: Use Python script for automation or scripting
- **API**: Use `/map/list-available` and `/map/switch` endpoints
- **Configuration**: Edit `my_scripts/maps_config.json`

All methods update the same configuration file and work seamlessly together.

**Happy map switching! 🗺️**
