
# STEP/IGES Importer for Blender

[![Blender](https://img.shields.io/badge/Blender-4.0+-orange.svg)](https://www.blender.org)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A Blender addon that enables import of CAD files (STEP/IGES formats) through conversion to mesh formats using Mayo conversion toolkit.

![Plugin Demo](demo-screenshot.jpg) <!-- Add actual screenshot later -->

## Features

- 🚀 **CAD Format Support**
  - Import `.step`, `.stp`, `.iges`, `.igs` files
  - Supports both drag-and-drop and traditional file import
  
- ⚙️ **Conversion Options**
  - Choose between GLTF (hierarchy preservation) or OBJ (fast import)
  - Adjustable mesh quality levels (Very Coarse → Very Precise)
  - Custom scaling factors (0.0001x to 100x)

- 🧹 **Automatic Cleanup**
  - Optional deletion of intermediate files
  - Duplicate material cleanup system

- 🖥️ **Workflow Optimization**
  - Real-time conversion progress monitoring
  - Preset system for frequent configurations
  - 3D viewport integration

## System Requirements

❗ **Windows Only**  
This addon requires  Windows 

1. **Mayo Conversion Tool**  
   Download Windows binaries from:  
   [https://github.com/fougue/mayo/releases](https://github.com/fougue/mayo/releases)

2. **Blender**  
	- **Blender**:4.0 and newer

## Installation

1. **Install Addon**
-1. Download the latest `.zip` file from [Releases](https://github.com/yourusername/auto-maximize-nodes/releases).
-2. In Blender, go to **Edit > Preferences > Add-ons**.
-3. Click **Install...** and select the downloaded `.zip` file.
-4. Enable the checkbox next to "Stp/IGES Import".

2. **Configure Mayo Path**  
   ```python
   # In Blender Preferences:
   Add-ons > Import-Export > STEP/IGES Importer
   Set path to mayo-conv.exe in addon preferences
   ```

## Usage

### Basic Import
1. **File Import**
   ```
   File > Import > STEP/IGES (.step/.stp/.iges/.igs)
   ```

2. **Drag-and-Drop**
   - Drag files directly into 3D Viewport

### Conversion Settings
| Parameter          | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| **Output Format**  | `.gltf` (slow, hierarchy) / `.obj` (fast, collections)                      |
| **Mesh Quality**   | Controls BRep conversion precision (trade-off between speed and accuracy)  |
| **Global Scale**   | Adjust model scaling factor (0.0001-100)                                   |
| **Post-Process**   | Auto-delete temp files, clean duplicate materials                          |


### Troubleshooting
**Common Issues**  
❌ "mayo-conv.exe not found"  
✅ Verify executable path in addon preferences  



## Support

| Resource                  | Link                                                                 |
|---------------------------|---------------------------------------------------------------------|
| Documentation             | [Plugin Wiki](https://github.com/yourusername/blender-step-import/wiki) |
| Issue Tracking            | [GitHub Issues](https://github.com/yourusername/blender-step-import/issues) |
| Commercial Support        | contact@yourdomain.com                                              |

---

**Disclaimer**  
This addon is not affiliated with the Mayo project. CAD conversion quality depends on Mayo's core functionality.
````
