% test_positioning_simple.m
% Simple test of the UZY positioning algorithm with synthetic data
%
% This script tests the positioning algorithm on a simple tetrahedron
% to verify that facenormals.m and the positioning workflow are working.

clear all;
close all;
clc;

% Add parent directory to path (where the actual scripts are)
addpath('..');

fprintf('=== Testing UZY Positioning Algorithm ===\n\n');

%% Create a simple test mesh - irregular tetrahedron
fprintf('Creating test mesh (irregular tetrahedron)...\n');

% Define vertices (deliberately not centered or aligned)
v = [
    1.0,  0.5,  0.2;   % vertex 1
    3.0,  0.3,  0.1;   % vertex 2
    1.5,  2.5,  0.3;   % vertex 3
    1.8,  1.2,  2.0    % vertex 4
];

% Define faces (1-based indexing)
f = [
    1, 2, 3;   % bottom face
    1, 2, 4;   % side face 1
    2, 3, 4;   % side face 2
    1, 3, 4    % side face 3
];

fprintf('  Vertices: %d\n', size(v, 1));
fprintf('  Faces: %d\n', size(f, 1));

%% Test facenormals function
fprintf('\nTesting facenormals function...\n');
try
    fn = facenormals(f, v);
    fprintf('  ✓ facenormals() executed successfully\n');
    fprintf('  Face normals computed: %d\n', size(fn, 1));
    fprintf('  Sample normal: [%.3f, %.3f, %.3f]\n', fn(1,1), fn(1,2), fn(1,3));
catch ME
    fprintf('  ✗ Error in facenormals(): %s\n', ME.message);
    return;
end

%% Display original mesh properties
fprintf('\nOriginal mesh:\n');
fprintf('  Center: [%.3f, %.3f, %.3f]\n', mean(v(:,1)), mean(v(:,2)), mean(v(:,3)));
fprintf('  X range: [%.3f, %.3f]\n', min(v(:,1)), max(v(:,1)));
fprintf('  Y range: [%.3f, %.3f]\n', min(v(:,2)), max(v(:,2)));
fprintf('  Z range: [%.3f, %.3f]\n', min(v(:,3)), max(v(:,3)));

%% Run positioning algorithm
fprintf('\nRunning positioning algorithm...\n');
try
    v_positioned = positioning(v, f);
    fprintf('  ✓ Positioning completed successfully\n');
catch ME
    fprintf('  ✗ Error in positioning(): %s\n', ME.message);
    fprintf('  Stack trace:\n');
    for i = 1:length(ME.stack)
        fprintf('    %s (line %d)\n', ME.stack(i).name, ME.stack(i).line);
    end
    return;
end

%% Display positioned mesh properties
fprintf('\nPositioned mesh:\n');
fprintf('  Center: [%.3f, %.3f, %.3f]\n', mean(v_positioned(:,1)), mean(v_positioned(:,2)), mean(v_positioned(:,3)));
fprintf('  X range: [%.3f, %.3f]\n', min(v_positioned(:,1)), max(v_positioned(:,1)));
fprintf('  Y range: [%.3f, %.3f]\n', min(v_positioned(:,2)), max(v_positioned(:,2)));
fprintf('  Z range: [%.3f, %.3f]\n', min(v_positioned(:,3)), max(v_positioned(:,3)));

%% Visualize results
fprintf('\nGenerating visualization...\n');

figure('Name', 'UZY Positioning Test', 'Position', [100, 100, 1200, 500]);

% Original mesh
subplot(1, 2, 1);
trimesh(f, v(:,1), v(:,2), v(:,3), 'FaceAlpha', 0.8, 'EdgeColor', 'k');
axis equal;
grid on;
xlabel('X'); ylabel('Y'); zlabel('Z');
title('Original Mesh');
view(3);

% Positioned mesh
subplot(1, 2, 2);
trimesh(f, v_positioned(:,1), v_positioned(:,2), v_positioned(:,3), ...
    'FaceAlpha', 0.8, 'EdgeColor', 'k');
axis equal;
grid on;
xlabel('X'); ylabel('Y'); zlabel('Z');
title('After UZY Positioning');
view(3);

fprintf('\n=== Test Complete ===\n');
fprintf('If you see two plots, the positioning algorithm is working!\n');
