#!/bin/bash
# Skill Evaluator Shortcut
# Usage: ./eval-skill.sh <path-to-skill> [--format json|md|html] [--batch]

EVALUATOR_PATH="../skills-evaluator/skills/ontos-skill-evaluator/scripts/quick_eval.js"

if [ ! -f "$EVALUATOR_PATH" ]; then
    echo "Error: skills-evaluator not found at ../skills-evaluator/"
    echo "Please ensure skills-evaluator is in the same parent directory as anything-skills"
    exit 1
fi

node "$EVALUATOR_PATH" "$@"
