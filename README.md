## Maps Build123d shapes to the line of code that generated them 
- covers main build123d operations (fillets, sketches, box, etc)
- maps all resulting objects (faces, edges, points)

# Disclaimer: Claude Code was used to help write this code

## Goals: help fill in CAD -> code path in the CAD <-> code pipeline

## Potential integrations: 
- CAD Viewers
  - click face in viewer -> editor jumps to line of code that generated it
  - build a tree of build123d objects -> click tree to show object in viewer and jump to code in editor
- Other
  - let me know ideas you may have!


## How to test:

- clone this repository and run uv sync
- clone https://github.com/fpfcmsr/vscode-ocp-cad-viewer, checkout to the provenance-hooks branch, run "npm install" and "npm run compile"
- run vscode with the compiled extension: code --extensionDevelopmentPath=/someplace/full/path/vscode-ocp-cad-viewer/
- open /someplace/ocp-provenance
- run the examples
