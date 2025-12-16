# MATLAB Testing Guide

## Files in This Directory

### Test Scripts
- **`test_positioning_simple.m`** - Quick verification test with synthetic data
- **`test_positioning_glb.m`** - Template for testing with real GLB models

### Implementation (Parent Directory)
- **`../facenormals.m`** - Computes face normal vectors for triangulated meshes
- **`../positioning.m`** - Main UZY positioning algorithm
- **`../UzyPosCm_for_GUI.m`** - Inertia tensor positioning
- **`../Norm2Posing_for_GUI.m`** - Surface tensor calculation
- **`../Find_Mirror_Sym.m`** - Mirror symmetry alignment

## Quick Start Testing

### Option 1: Simple Synthetic Test (Recommended First)

This verifies that all functions are working correctly:

```matlab
% In MATLAB, navigate to the test directory
cd 'Gadi''s Scripts/test'

% Run the simple test
test_positioning_simple
```

**Expected output:**
- Function execution messages
- Mesh statistics (before/after positioning)
- Two 3D plots showing original and positioned meshes

**If this works:** ✓ All MATLAB functions are working correctly!

### Option 2: Test with Real GLB Model

You'll need to convert a GLB file to a format MATLAB can read:

#### Step 1: Convert GLB to PLY using Python

```bash
# Activate Python environment
source .venv/bin/activate

# Convert one GLB file to PLY
python -c "
import trimesh
mesh = trimesh.load('3DModels/Wansunt_1931_7_11_10.glb')
mesh.export('Gadi''s Scripts/test_model.ply')
print('Converted to test_model.ply')
"
```

#### Step 2: Load and Test in MATLAB

You'll need a PLY reading function. Options:

**Option A: Use built-in (MATLAB R2020a+)**
```matlab
ptCloud = pcread('test_model.ply');
% Note: This reads as point cloud, you may need triangulation
```

**Option B: File Exchange PLY reader**
- Download from: https://www.mathworks.com/matlabcentral/fileexchange/5459-ply-file-reader
- Or search for "ply reader" on MATLAB File Exchange

**Option C: Modify test_positioning_glb.m**
Edit lines 17-25 to use your preferred PLY reading method.

## Troubleshooting

### Error: "Undefined function 'facenormals'" or "Undefined function 'positioning'"
- The test scripts automatically add the parent directory to the path
- If you still see errors, manually add: `addpath('..')`
- Or run from this test directory

### Error: "Index exceeds array dimensions" in facenormals
- Check that face indices in `f` are 1-based (MATLAB convention)
- Check that all face indices are ≤ number of vertices

### Waitbar doesn't close
- The `positioning.m` script opens a waitbar
- Close manually if it gets stuck: `close(findall(0,'Type','figure','Tag','TMWWaitbar'))`

### Memory errors with large meshes
- The Wansunt models have ~1M triangles each
- Test with smaller models first
- Close other MATLAB figures before running

## Expected Results

After running `positioning(v, f)`, the mesh should be:

1. **Centered at origin** - Mean of all vertices ≈ [0, 0, 0]
2. **Aligned to principal axes** - Based on inertia tensor eigenvectors
3. **Face-on orientation** - Maximum projected area in XY plane
4. **Mirror symmetry aligned** - Consistent left/right orientation

The algorithm is deterministic - same input always produces same output.

## Validation

To verify positioning is correct:

```matlab
% After running positioning
v_pos = positioning(v, f);

% Check centering
mean_pos = mean(v_pos);
fprintf('Center: [%.3f, %.3f, %.3f]\n', mean_pos(1), mean_pos(2), mean_pos(3));
% Should be very close to [0, 0, 0]

% Check bounding box is reasonable
fprintf('X range: [%.2f, %.2f]\n', min(v_pos(:,1)), max(v_pos(:,1)));
fprintf('Y range: [%.2f, %.2f]\n', min(v_pos(:,2)), max(v_pos(:,2)));
fprintf('Z range: [%.2f, %.2f]\n', min(v_pos(:,3)), max(v_pos(:,3)));
```

## Next Steps

Once testing is successful:
1. Process multiple models in batch
2. Extract standard measurements (length, width, thickness)
3. Compare with traditional manual measurements
4. Export positioned meshes for visualization

## Questions?

Check the main [README.md](../README.md) for:
- Scientific methodology (Grosman 2008)
- Input data formats
- Known issues and recommendations
