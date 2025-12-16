function fn = facenormals(f, v)
% FACENORMALS Compute face normal vectors for a triangulated mesh
%
% fn = facenormals(f, v)
%
% Computes the normal vector for each triangular face in a mesh.
% The magnitude of each normal vector is twice the area of the triangle,
% which is used for area-weighted calculations in the UZY positioning algorithm.
%
% Inputs:
%   f - Mx3 matrix of face indices (1-based MATLAB indexing)
%       Each row contains indices of the 3 vertices forming a triangle
%   v - Nx3 matrix of vertex coordinates [x, y, z]
%       Each row is a 3D point
%
% Output:
%   fn - Mx3 matrix of face normal vectors
%        Each row is the normal vector for the corresponding face
%        Magnitude of fn(i,:) = 2 * area of triangle i
%
% The normal vectors are NOT normalized to unit length. Their magnitude
% equals twice the triangle area, which is used in area-weighted tensor
% calculations.
%
% Example:
%   % Simple tetrahedron
%   v = [0 0 0; 1 0 0; 0 1 0; 0 0 1];
%   f = [1 2 3; 1 2 4; 2 3 4; 1 3 4];
%   fn = facenormals(f, v);
%
% See also: cross, triangulation, faceNormal

% Get vertices for each face
v1 = v(f(:,1), :);  % First vertex of each triangle
v2 = v(f(:,2), :);  % Second vertex of each triangle
v3 = v(f(:,3), :);  % Third vertex of each triangle

% Compute edge vectors
e1 = v2 - v1;  % Edge from v1 to v2
e2 = v3 - v1;  % Edge from v1 to v3

% Cross product gives the normal vector
% Magnitude = 2 * triangle area (by definition of cross product)
fn = cross(e1, e2, 2);

% Note: We do NOT normalize these vectors!
% The UZY algorithm uses the magnitude for area-weighted calculations.
% From the cross product formula: ||e1 × e2|| = ||e1|| * ||e2|| * sin(θ)
% which equals twice the area of the triangle formed by e1 and e2.

end
