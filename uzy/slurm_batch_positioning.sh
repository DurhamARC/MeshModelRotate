#!/bin/bash
#
# SLURM Batch Processing Script for UZY Positioning
#
# This script processes GLB files in parallel using SLURM array jobs.
# Each array task processes one file.
#
# Usage:
#   1. Place GLB files in input directory
#   2. Create file list: ls input/*.glb > file_list.txt
#   3. Count files: NUM_FILES=$(wc -l < file_list.txt)
#   4. Edit --array parameter below to match: --array=1-${NUM_FILES}
#   5. Submit: sbatch uzy/slurm_batch_positioning.sh
#
# Monitor:
#   squeue -u $USER           # Check job status
#   tail -f logs/pos_*.out    # Monitor output
#
# Cancel:
#   scancel <JOB_ID>          # Cancel specific job
#   scancel -u $USER          # Cancel all your jobs
#

# =============================================================================
# SLURM Configuration
# =============================================================================

# Generic options
#SBATCH --account=bddur53
#SBATCH --time=0:10:00              # 10 minutes per file (adjust as needed)

# Job array: process files 1 through N
# Update N to match number of files in file_list.txt
# %40 means max 40 jobs running concurrently
#SBATCH --array=1-100%40

# Node resources
#SBATCH --partition=gpu              # Use GPU partition for PowerPC V100 nodes
#SBATCH --nodes=1                    # Resources from a single node
#SBATCH --gres=gpu:1                 # One GPU per node (4x V100s per node)

# Output files: %A = job ID, %a = array task ID
#SBATCH --output=logs/pos_%A_%a.out
#SBATCH --error=logs/pos_%A_%a.err

# Job name
#SBATCH --job-name=uzy_positioning

# =============================================================================
# Environment Setup
# =============================================================================

# Print job info
echo "=================================================="
echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "Array Task ID: ${SLURM_ARRAY_TASK_ID}"
echo "Running on host: $(hostname)"
echo "Started at: $(date)"
echo "Working directory: $(pwd)"
echo "=================================================="
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Load required modules (adjust for your HPC environment)
# module load python/3.11
# module load cuda/11.8  # If using GPU-accelerated libraries

# Activate Python virtual environment
# Adjust path to your environment
source .venv/bin/activate

# Verify Python and dependencies
echo "Python: $(which python)"
echo "Python version: $(python --version)"
python -c "import trimesh, scipy, numpy; print('✓ Dependencies loaded')" || {
    echo "Error: Failed to load Python dependencies"
    exit 1
}

# =============================================================================
# File Processing
# =============================================================================

# Get input file for this array task
FILE_LIST="file_list.txt"
INPUT_FILE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "${FILE_LIST}")

if [ -z "$INPUT_FILE" ]; then
    echo "Error: No file found for array task ${SLURM_ARRAY_TASK_ID}"
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: File does not exist: $INPUT_FILE"
    exit 1
fi

echo "Processing file ${SLURM_ARRAY_TASK_ID}: ${INPUT_FILE}"
echo ""

# Determine output file
BASENAME=$(basename "$INPUT_FILE" .glb)
DIRNAME=$(dirname "$INPUT_FILE")
OUTPUT_FILE="${DIRNAME}/${BASENAME}_positioned.glb"
METADATA_FILE="${DIRNAME}/${BASENAME}_metadata.json"

# Run positioning
echo "Running UZY positioning..."
python uzy/positioning.py "$INPUT_FILE" \
    -o "$OUTPUT_FILE" \
    --save-metadata "$METADATA_FILE" \
    --quiet

EXIT_CODE=$?

# =============================================================================
# Results
# =============================================================================

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ Success!"
    echo "  Output: $OUTPUT_FILE"
    echo "  Metadata: $METADATA_FILE"

    # Verify output file was created
    if [ -f "$OUTPUT_FILE" ]; then
        SIZE=$(stat -f%z "$OUTPUT_FILE" 2>/dev/null || stat -c%s "$OUTPUT_FILE" 2>/dev/null)
        echo "  Output size: $SIZE bytes"
    else
        echo "  Warning: Output file not created"
        EXIT_CODE=1
    fi
else
    echo ""
    echo "✗ Failed with exit code $EXIT_CODE"
fi

echo ""
echo "=================================================="
echo "Finished at: $(date)"
echo "Exit code: $EXIT_CODE"
echo "=================================================="

exit $EXIT_CODE
