#!/bin/bash
#
# Helper script to prepare for SLURM batch processing
#
# This script:
#   1. Creates file list from input directory
#   2. Counts files
#   3. Shows SLURM command to submit
#

set -e

# Configuration
INPUT_DIR="${1:-.}"
FILE_PATTERN="${2:-*.glb}"
OUTPUT_LIST="file_list.txt"

echo "UZY Positioning - Batch Preparation"
echo "===================================="
echo ""

# Check input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Directory not found: $INPUT_DIR"
    echo ""
    echo "Usage: $0 [INPUT_DIR] [FILE_PATTERN]"
    echo ""
    echo "Examples:"
    echo "  $0                          # Use current directory, *.glb"
    echo "  $0 3DModels                 # Use 3DModels/, *.glb"
    echo "  $0 data '*.ply'             # Use data/, *.ply"
    exit 1
fi

# Generate file list
echo "Searching for files matching: $FILE_PATTERN"
echo "In directory: $INPUT_DIR"
echo ""

# Use find to get absolute paths
find "$INPUT_DIR" -name "$FILE_PATTERN" -type f | sort > "$OUTPUT_LIST"

NUM_FILES=$(wc -l < "$OUTPUT_LIST")

if [ "$NUM_FILES" -eq 0 ]; then
    echo "Error: No files found matching pattern: $FILE_PATTERN"
    echo "In directory: $INPUT_DIR"
    rm -f "$OUTPUT_LIST"
    exit 1
fi

echo "✓ Found $NUM_FILES files"
echo "✓ Saved to: $OUTPUT_LIST"
echo ""

# Show first few files
echo "First 5 files:"
head -5 "$OUTPUT_LIST" | nl
echo ""

# Show SLURM command
echo "=================================================="
echo "Next steps:"
echo "=================================================="
echo ""
echo "1. Review file list:"
echo "   less $OUTPUT_LIST"
echo ""
echo "2. Edit uzy/slurm_batch_positioning.sh:"
echo "   Update line: #SBATCH --array=1-${NUM_FILES}%40"
echo ""
echo "3. Submit job:"
echo "   sbatch uzy/slurm_batch_positioning.sh"
echo ""
echo "4. Monitor progress:"
echo "   squeue -u \$USER"
echo "   tail -f logs/pos_*.out"
echo ""
echo "=================================================="

# Suggest sed command to update array parameter
echo ""
echo "Quick edit command:"
echo "  sed -i.bak 's/^#SBATCH --array=.*/#SBATCH --array=1-${NUM_FILES}%40/' uzy/slurm_batch_positioning.sh"
echo ""
