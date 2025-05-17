# Multi-Part Boolean for Blender
# [日本語版 README はこちら (Japanese README)](README_ja.md)
## Overview

Multi-Part Boolean is a Blender addon designed to execute complex boolean operations in a single step by processing objects composed of multiple, overlapping, yet disconnected mesh parts. The result is generated in a new collection for each execution, leaving the original objects unaffected.
For example, it can perform a boolean operation on an object like a figure's hair part, which consists of a collection of independent strands, while maintaining the separation of each strand in the final result.

## Features

*   **Supported Boolean Operations:**
    *   **Difference:** Cuts cutter parts from base parts.
    *   **Intersect:** Keeps the common volume between base parts and cutter parts.
*   **One-Click Batch Process:** The entire workflow, from splitting objects to applying modifiers and joining results, is handled by a single operator.
*   **Organized Output:** A new collection is created for the result objects with each execution, preventing scene clutter and making iteration management easier.
*   **Internationalization:** The UI supports English and Japanese.

## Installation

1.  Download the `.zip` file.
2.  Open Blender.
3.  Go to `Edit > Preferences > Add-ons`.
4.  Click `Install...`, navigate to the downloaded `.zip` file, select it, and click `Install Add-on`.
5.  Search for "Multi-Part Boolean" in the Add-ons list and enable it by checking the box next to its name.

## Tool Location
 *   3D View > Sidebar > Multi-Part Boolean
    
## How to Use

1.  **Select Objects:**
    *   Select two objects.
    *   The **active object** (last selected, highlighted in a lighter orange) will be treated as the **Base** object.
2.  **Configure Settings:**
    *   **Operation:** Choose the boolean operation you want to perform:
        *   `Difference`
        *   `Intersect`
3.  **Execute:**
    *   Click the **"Execute Batch Boolean Process"** button.
4.  **Result:**
    *   A new collection (e.g., `MultiPartBoolean_Result_001`) will be created with each execution, containing the generated result.

## Known Issues / Limitations

*   **Performance:** For meshes with a very large number of loose parts, the process can be computationally intensive and may take a significant amount of time. This is because it generates `(number of base parts) * (number of cutter parts)` boolean modifiers.
*   **Complex Geometry:** As with other boolean operations in Blender, highly complex or non-manifold geometry may lead to unexpected results or errors from the boolean solver. It is recommended to keep the base and cutter meshes relatively clean.

## License
Multi-Part Boolean is released under the **GNU General Public License v3 (GPLv3)**. This addon can be freely used, modified, and distributed, but any derivative works must also be released under the same license. For details, please refer to the [LICENSE](LICENSE) file.
