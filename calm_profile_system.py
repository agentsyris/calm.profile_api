"""
Calm Profile Scoring System
Binary A/B responses mapped to behavioral axes and archetypes
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import math


# Question to axis mapping (0–19 by quintiles)
AXIS_QUESTIONS = {
    "structure": [0, 1, 2, 3, 4],
    "collaboration": [5, 6, 7, 8, 9],
    "scope": [10, 11, 12, 13, 14],
    "tempo": [15, 16, 17, 18, 19]
}

# Archetype definitions with axis target values (0-100 scale)
ARCHETYPES = {
    "architect": {
        "name": "Architect",
        "axes": {
            "structure": 85,
            "collaboration": 35,
            "scope": 70,
            "tempo": 40
        },
        "tagline": "systematic builders of scalable foundations",
        "strengths": [
            "Framework design",
            "Process optimization",
            "Long-term planning",
            "System integration"
        ],
        "quick_wins": [
            "Implement project templates",
            "Create workflow documentation",
            "Set up automation tools"
        ]
    },
    "conductor": {
        "name": "Conductor",
        "axes": {
            "structure": 70,
            "collaboration": 85,
            "scope": 75,
            "tempo": 60
        },
        "tagline": "orchestrators of collaborative excellence",
        "strengths": [
            "Team coordination",
            "Meeting facilitation",
            "Stakeholder alignment",
            "Resource orchestration"
        ],
        "quick_wins": [
            "Reduce status meetings with async updates",
            "Define decision owners",
            "Weekly cadence dashboard"
        ]
    },
    "curator": {
        "name": "Curator",
        "axes": {
            "structure": 40,
            "collaboration": 75,
            "scope": 30,
            "tempo": 45
        },
        "tagline": "quality guardians and creative refiners",
        "strengths": [
            "Quality assurance",
            "Detail orientation",
            "Creative curation",
            "Standard maintenance"
        ],
        "quick_wins": [
            "Develop review checklists",
            "Create style guides",
            "Set up quality gates"
        ]
    },
    "craftsperson": {
        "name": "Craftsperson",
        "axes": {
            "structure": 80,
            "collaboration": 30,
            "scope": 80,
            "tempo": 40
        },
        "tagline": "deep work and quality at the edges",
        "strengths": [
            "Detail execution",
            "Technical craft",
            "Quality control",
            "Repeatable delivery"
        ],
        "quick_wins": [
            "Protect maker time",
            "Limit WIP",
            "Definition of ready"
        ]
    }
}


def clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def calculate_axis_scores(responses: Dict[str, int]) -> Dict[str, float]:
    """
    Calculate axis scores from binary responses.
    1 = A (high on axis), 0 = B (low on axis)
    """
    axis_scores = {}
    for axis_name, idxs in AXIS_QUESTIONS.items():
        total = sum(responses.get(str(i), 0) for i in idxs)
        axis_scores[axis_name] = (total / len(idxs)) * 100.0
    return axis_scores


def distance(a: float, b: float) -> float:
    return abs(a - b)


def calculate_archetype_match(axis_scores: Dict[str, float]) -> Dict[str, float]:
    matches = {}
    for name, arche in ARCHETYPES.items():
        d = sum(distance(axis_scores[k], arche["axes"][k]) for k in ["structure", "collaboration", "scope", "tempo"])
        matches[name] = clamp(100 - d / 4)
    return matches


def determine_archetype_mix(matches: Dict[str, float]) -> Dict[str, float]:
    total = sum(matches.values()) or 1.0
    return {k: round(100.0 * v / total, 1) for k, v in matches.items()}


def score_assessment(responses: Dict[str, int]) -> Dict[str, Any]:
    axis_scores = calculate_axis_scores(responses)
    matches = calculate_archetype_match(axis_scores)
    primary = max(matches, key=lambda k: matches[k])
    return {
        "archetype": {
            "primary": primary,
            "mix": determine_archetype_mix(matches),
            "tagline": ARCHETYPES[primary].get("tagline", "")
        },
        "scores": {
            "axes": {k: round(v) for k, v in axis_scores.items()},
            "match": {k: round(v, 1) for k, v in matches.items()}
        },
        "recommendations": {
            "strengths": ARCHETYPES[primary]["strengths"],
            "quick_wins": ARCHETYPES[primary]["quick_wins"],
        }
    }


def format_response(result: Dict[str, Any], platform: str = "google") -> Dict[str, Any]:
    # placeholder for platform-specific tool stack mapping if needed
    return result


if __name__ == "__main__":
    test_responses = {str(i): 1 for i in range(20)}
    print(score_assessment(test_responses))
