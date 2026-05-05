#!/bin/bash
# skills.sh - Project Rain Skill Manager
# Managed by Parent Agent

set -e

SKILLS_DIR="./skills_registry"
SCHEMA_FILE="./backend/src/rain_backend/schemas/skill_manifest.schema.json"

mkdir -p "$SKILLS_DIR"

usage() {
    echo "Usage: $0 [command] [args]"
    echo ""
    echo "Commands:"
    echo "  install <git-url>  Install a skill from a GitHub repository"
    echo "  list               List all installed skills"
    echo "  remove <name>      Remove an installed skill"
    echo "  enable <name>      Enable a skill"
    echo "  disable <name>     Disable a skill"
}

install_skill() {
    local url=$1
    if [ -z "$url" ]; then
        echo "Error: Git URL is required"
        exit 1
    fi

    echo "Cloning skill from $url..."
    local tmp_dir=$(mktemp -d)
    git clone "$url" "$tmp_dir" --depth 1

    if [ ! -f "$tmp_dir/manifest.yaml" ]; then
        echo "Error: Skill missing manifest.yaml"
        rm -rf "$tmp_dir"
        exit 1
    fi

    # Extract name from manifest (simple grep for now, should use yq in production)
    local skill_name=$(grep "^name:" "$tmp_dir/manifest.yaml" | cut -d':' -f2 | xargs)
    
    if [ -z "$skill_name" ]; then
        echo "Error: Could not extract skill name from manifest"
        rm -rf "$tmp_dir"
        exit 1
    fi

    echo "Installing skill: $skill_name..."
    local target_dir="$SKILLS_DIR/$skill_name"
    
    if [ -d "$target_dir" ]; then
        echo "Warning: Skill $skill_name is already installed. Overwriting..."
        rm -rf "$target_dir"
    fi

    mv "$tmp_dir" "$target_dir"

    echo "Building Docker image for $skill_name..."
    # Placeholder for docker build command
    # docker build -t "rain-skill-$skill_name" "$target_dir"

    echo "Registering skill in database..."
    # Placeholder for database registration script
    # python -m backend.scripts.register_skill "$skill_name"

    echo "Successfully installed $skill_name!"
}

case "$1" in
    install)
        install_skill "$2"
        ;;
    list)
        echo "Installed skills in $SKILLS_DIR:"
        ls "$SKILLS_DIR"
        ;;
    remove)
        name=$2
        if [ -d "$SKILLS_DIR/$name" ]; then
            rm -rf "$SKILLS_DIR/$name"
            echo "Removed skill: $name"
        else
            echo "Error: Skill $name not found"
        fi
        ;;
    enable|disable)
        echo "Command $1 not yet implemented"
        ;;
    *)
        usage
        ;;
esac
