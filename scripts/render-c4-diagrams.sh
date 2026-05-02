#!/usr/bin/env bash
# Render all C4-PlantUML diagrams to SVG.
# Usage: ./scripts/render-c4-diagrams.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JAR="$REPO_ROOT/tools/plantuml.jar"
SRC_DIR="$REPO_ROOT/docs/architecture/c4-plantuml"
PLANTUML_VERSION="1.2025.2"

if [[ ! -f "$JAR" ]]; then
    echo "Downloading plantuml.jar v$PLANTUML_VERSION..."
    mkdir -p "$REPO_ROOT/tools"
    curl -fsSL -o "$JAR" \
        "https://github.com/plantuml/plantuml/releases/download/v${PLANTUML_VERSION}/plantuml-${PLANTUML_VERSION}.jar"
fi

mkdir -p "$SRC_DIR/rendered"
java -jar "$JAR" -tsvg -Playout=smetana -o rendered "$SRC_DIR"/*.puml
echo "Rendered to: $SRC_DIR/rendered/"
ls "$SRC_DIR/rendered/"
