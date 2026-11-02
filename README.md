# GTR autonomous — simulator
**Goal:** Make a complete simulator and workspace for autonomous training

### Track guidance ###
1. To create a track, use components/track/data and either change the .txt file or make a new one
2. Then make the track: 
    - . is empty space
    - X tracks drivable area
    - S starting point
    - E ending point
    - [Built in example](components\track\data\shell_2026.txt)
3. update config.json to use the correct file and settings
    - file – Path to the track layout file containing the 2D grid.
    - cell_size_m – Real-world size of each grid cell in meters.
    - width_m – Width of the generated road in meters.
    - mesh_resolution_m – Distance between mesh points in meters. Lower values produce smoother geometry.
    - corner_rounding – Controls how much corners are rounded. Higher values create smoother turns.
    - line_width_m – Width of the white road boundary lines in meters.