#!/bin/bash
# Example usage of AI-powered scientific schematic generation
# 
# Prerequisites:
# 1. Set OPENROUTER_API_KEY environment variable
# 2. Ensure Python 3.10+ is installed
# 3. Install requests: uv pip install requests

set -e

echo "=========================================="
echo "Scientific Schematics - AI Generation"
echo "Example Usage Demonstrations"
echo "=========================================="
echo ""
echo "This runs three real generations against OpenRouter and will be billed"
echo "to your account: 2 API calls per iteration, up to 4 per example."
echo ""

# Check for API key
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "[FAIL] Error: OPENROUTER_API_KEY environment variable not set"
    echo ""
    echo "Get an API key at: https://openrouter.ai/keys"
    echo "Then set it with: export OPENROUTER_API_KEY='your_key'"
    exit 1
fi

echo "[OK] OPENROUTER_API_KEY is set"
echo ""

# Create output directory
mkdir -p figures
echo "[OK] Created figures/ directory"
echo ""

# Example 1: Simple flowchart
echo "Example 1: CONSORT Flowchart"
echo "----------------------------"
python scripts/generate_schematic.py \
  "CONSORT participant flow diagram. Assessed for eligibility (n=500). Excluded (n=150) with reasons: age<18 (n=80), declined (n=50), other (n=20). Randomized (n=350) into Treatment (n=175) and Control (n=175). Received allocated intervention: 175 and 175; did not receive: 0 and 0. Discontinued intervention: 0 and 0. Lost to follow-up for primary outcome: 15 and 10 (outcome visit not attended). Analyzed for primary outcome: 160 and 165; excluded due to missing primary outcome: 15 and 10. This is an illustrative complete-case analysis, not an intention-to-treat analysis." \
  -o figures/consort_example.png \
  --iterations 2

echo ""
echo "[OK] Generated: figures/consort_example.png"
echo "  - Also created: consort_example_v1.png (and v2.png if it needed a second pass)"
echo "  - Review log: consort_example_review_log.json"
echo ""

# Example 2: Neural network (shorter for demo)
echo "Example 2: Simple Neural Network"
echo "--------------------------------"
python scripts/generate_schematic.py \
  "Simple feedforward neural network diagram. Input layer with 4 nodes, hidden layer with 6 nodes, output layer with 2 nodes. Show all connections. Label layers clearly." \
  -o figures/neural_net_example.png \
  --iterations 2

echo ""
echo "[OK] Generated: figures/neural_net_example.png"
echo ""

# Example 3: Biological pathway (minimal)
echo "Example 3: Signaling Pathway"
echo "---------------------------"
python scripts/generate_schematic.py \
  "Simple signaling pathway: Receptor -> Kinase A -> Kinase B -> Transcription Factor -> Gene. Show arrows with 'activation' labels. Use different colors for each component." \
  -o figures/pathway_example.png \
  --iterations 2

echo ""
echo "[OK] Generated: figures/pathway_example.png"
echo ""

echo "=========================================="
echo "All examples completed successfully!"
echo "=========================================="
echo ""
echo "Generated files in figures/:"
ls -lh figures/*example*.png 2>/dev/null || echo "  (Files will appear after running with valid API key)"
echo ""
echo "Review the review_log.json files to see:"
echo "  - Quality scores for each iteration"
echo "  - Detailed critiques and suggestions"
echo "  - Improvement progression"
echo ""
echo "Next steps:"
echo "  1. View the generated images"
echo "  2. Review the quality scores in *_review_log.json"
echo "  3. Try your own prompts!"
echo ""

