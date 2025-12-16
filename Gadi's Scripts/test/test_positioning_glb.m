% test_positioning_glb.m
% Test the UZY positioning algorithm on a GLB file from the 3DModels directory
%
% This script loads a GLB file, extracts vertices and faces, and runs
% the positioning algorithm. You'll need a way to read GLB files in MATLAB.
%
% Options for reading GLB files:
%   1. Use the Python bridge to read with trimesh, then import to MATLAB
%   2. Convert GLB to PLY first using the Python script, then read PLY
%   3. Use MATLAB File Exchange tools for GLB import (if available)
%
% For now, this template assumes you've converted to PLY format.

clear all;
close all;
clc;

% Add parent directory to path (where the actual scripts are)
addpath('..');

fprintf('=== Testing UZY Positioning on Real GLB Model ===\n\n');

%% Method 1: Load pre-exported MAT
% Use: save_mat_for_matlab.py to export
mat_file = fullfile('..','ToConvert','converted','Wansunt_1931_7_11_10.mat');

fprintf('Loading MAT file: %s\n', mat_file);
data = load(mat_file);
v = data.v;
f = data.f;
fprintf('  Vertices: %d\n', size(v,1));
fprintf('  Faces: %d\n', size(f,1));


%% Method 2: Read PLY file (if converted from GLB)
% Requires: PLY reading function (e.g., from File Exchange)
%
% Uncomment and modify the path:
% ply_file = '../3DModels/Wansunt_1931_7_11_10.ply';
% fprintf('Loading PLY file: %s\n', ply_file);
%
% % You'll need a PLY reading function, e.g.:
% % [v, f] = read_ply(ply_file);
% % or use:
% % pcread() for point clouds, then extract triangulation
%
% fprintf('  Vertices: %d\n', size(v, 1));
% fprintf('  Faces: %d\n', size(f, 1));

%% Method 3: Use MATLAB's stlread (if you convert GLB to STL)
%
% stl_file = '../3DModels/Wansunt_1931_7_11_10.stl';
% fprintf('Loading STL file: %s\n', stl_file);
% TR = stlread(stl_file);
% v = TR.Points;
% f = TR.ConnectivityList;
% fprintf('  Vertices: %d\n', size(v, 1));
% fprintf('  Faces: %d\n', size(f, 1));

%% Temporary: Load test data (replace with actual file loading)
fprintf('NOTE: This template needs actual file loading code.\n');
fprintf('For now, please:\n');
fprintf('  1. Convert a GLB file to PLY using the Python script\n');
fprintf('  2. Load the PLY file using a MATLAB PLY reader\n');
fprintf('  3. Uncomment one of the loading methods above\n\n');

% Placeholder - remove this when you have real data
fprintf('Using placeholder tetrahedron for testing...\n');
v = [1, 0.5, 0.2; 3, 0.3, 0.1; 1.5, 2.5, 0.3; 1.8, 1.2, 2.0];
f = [1, 2, 3; 1, 2, 4; 2, 3, 4; 1, 3, 4];

%% Display mesh info
fprintf('\nMesh Information:\n');
fprintf('  Vertices: %d\n', size(v, 1));
fprintf('  Faces: %d\n', size(f, 1));
fprintf('  Bounding box:\n');
fprintf('    X: [%.2f, %.2f]\n', min(v(:,1)), max(v(:,1)));
fprintf('    Y: [%.2f, %.2f]\n', min(v(:,2)), max(v(:,2)));
fprintf('    Z: [%.2f, %.2f]\n', min(v(:,3)), max(v(:,3)));

%% Run positioning algorithm
fprintf('\nRunning UZY positioning algorithm...\n');
tic;
try
    v_positioned = positioning(v, f);
    elapsed = toc;
    fprintf('  ✓ Positioning completed in %.2f seconds\n', elapsed);
catch ME
    fprintf('  ✗ Error: %s\n', ME.message);
    fprintf('  In function: %s (line %d)\n', ME.stack(1).name, ME.stack(1).line);
    return;
end

%% Display results
fprintf('\nPositioned Mesh:\n');
fprintf('  Center: [%.3f, %.3f, %.3f]\n', ...
    mean(v_positioned(:,1)), mean(v_positioned(:,2)), mean(v_positioned(:,3)));
fprintf('  Bounding box:\n');
fprintf('    X: [%.2f, %.2f]\n', min(v_positioned(:,1)), max(v_positioned(:,1)));
fprintf('    Y: [%.2f, %.2f]\n', min(v_positioned(:,2)), max(v_positioned(:,2)));
fprintf('    Z: [%.2f, %.2f]\n', min(v_positioned(:,3)), max(v_positioned(:,3)));

%% Visualize
fprintf('\nGenerating visualization...\n');

figure('Name', 'GLB Model - UZY Positioning', 'Position', [50, 50, 1400, 600]);

% Original orientation
subplot(1, 2, 1);
trimesh(f, v(:,1), v(:,2), v(:,3), ...
    'FaceColor', [0.8 0.8 1.0], 'FaceAlpha', 0.9, 'EdgeColor', [0.3 0.3 0.3]);
axis equal;
grid on;
xlabel('X (mm)'); ylabel('Y (mm)'); zlabel('Z (mm)');
title('Original Orientation');
view(45, 30);
camlight;
lighting gouraud;

% UZY positioned
subplot(1, 2, 2);
trimesh(f, v_positioned(:,1), v_positioned(:,2), v_positioned(:,3), ...
    'FaceColor', [1.0 0.8 0.8], 'FaceAlpha', 0.9, 'EdgeColor', [0.3 0.3 0.3]);
axis equal;
grid on;
xlabel('X (mm)'); ylabel('Y (mm)'); zlabel('Z (mm)');
title('UZY Positioned (Face-on View)');
view(45, 30);
camlight;
lighting gouraud;

fprintf('\n=== Test Complete ===\n');

%% Save positioned mesh (optional)
% Uncomment to save the positioned vertices
% save('positioned_vertices.mat', 'v_positioned', 'f');
% fprintf('Positioned mesh saved to positioned_vertices.mat\n');
