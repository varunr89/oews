"""Fuzzy string matching utilities for query understanding."""

from typing import List, Dict, Any, Optional
from rapidfuzz import fuzz, process
from src.database.connection import OEWSDatabase


def get_best_matches(
    query: str,
    candidates: List[str],
    limit: int = 5,
    score_threshold: int = 60
) -> List[Dict[str, Any]]:
    """
    Find best fuzzy matches from a list of candidates.

    Args:
        query: Search query string
        candidates: List of candidate strings to match against
        limit: Maximum number of matches to return
        score_threshold: Minimum similarity score (0-100)

    Returns:
        List of matches with name and score, sorted by score descending
    """
    if not query or not candidates:
        return []

    # Use RapidFuzz to find best matches
    # Use token_sort_ratio for better word order independence
    matches = process.extract(
        query,
        candidates,
        scorer=fuzz.token_sort_ratio,
        limit=limit,
        score_cutoff=score_threshold
    )

    return [
        {"name": match[0], "score": match[1]}
        for match in matches
    ]


def fuzzy_match_area(
    query: str,
    limit: int = 5,
    score_threshold: int = 60
) -> List[Dict[str, Any]]:
    """
    Find best matching area names from OEWS database using fuzzy matching.

    Handles:
    - Typos (Seatle → Seattle)
    - Abbreviations (WA → Washington)
    - Partial names (Seattle → Seattle-Tacoma-Bellevue, WA)

    Args:
        query: Area search query
        limit: Maximum number of matches
        score_threshold: Minimum similarity score

    Returns:
        List of area matches with name and score
    """
    try:
        db = OEWSDatabase()

        # Get all distinct area names
        df = db.execute_query(
            "SELECT DISTINCT AREA_TITLE FROM oews_data LIMIT 1000"
        )
        db.close()

        candidates = df['AREA_TITLE'].tolist()

        # Find best matches
        matches = get_best_matches(query, candidates, limit, score_threshold)

        return matches

    except Exception as e:
        print(f"Error in fuzzy_match_area: {e}")
        return []


def fuzzy_match_occupation(
    query: str,
    limit: int = 5,
    score_threshold: int = 60
) -> List[Dict[str, Any]]:
    """
    Find best matching occupation names from OEWS database using fuzzy matching.

    Handles:
    - Alternative names (programmer → software developer)
    - Typos
    - Partial matches

    Args:
        query: Occupation search query
        limit: Maximum number of matches
        score_threshold: Minimum similarity score

    Returns:
        List of occupation matches with name and score
    """
    try:
        db = OEWSDatabase()

        # Get all distinct occupation names
        df = db.execute_query(
            "SELECT DISTINCT OCC_TITLE FROM oews_data WHERE O_GROUP = 'detailed' LIMIT 1000"
        )
        db.close()

        candidates = df['OCC_TITLE'].tolist()

        # Find best matches
        matches = get_best_matches(query, candidates, limit, score_threshold)

        return matches

    except Exception as e:
        print(f"Error in fuzzy_match_occupation: {e}")
        return []


def extract_location_from_query(query: str) -> Optional[str]:
    """
    Extract location name from natural language query.

    Examples:
    - "salaries in Seattle" → "Seattle"
    - "What are jobs in San Francisco, CA?" → "San Francisco, CA"
    - "Compare Bellingham and Portland" → "Bellingham"

    Args:
        query: Natural language query

    Returns:
        Extracted location or None
    """
    # Simple extraction patterns
    patterns = [
        " in ",
        " for ",
        " at ",
    ]

    query_lower = query.lower()

    for pattern in patterns:
        if pattern in query_lower:
            # Extract text after pattern
            parts = query_lower.split(pattern)
            if len(parts) > 1:
                # Clean up extracted location
                location = parts[1].strip(" ?.!,")
                # Take first part before other prepositions
                location = location.split(" and")[0].split(" or")[0]
                return location.title()

    return None


def extract_occupation_from_query(query: str) -> Optional[str]:
    """
    Extract occupation name from natural language query.

    Examples:
    - "software developer salaries" → "software developer"
    - "How much do nurses make?" → "nurses"

    Args:
        query: Natural language query

    Returns:
        Extracted occupation or None
    """
    # Common occupation keywords
    keywords = [
        "developer", "engineer", "nurse", "teacher", "analyst",
        "manager", "technician", "specialist", "administrator",
        "designer", "programmer", "scientist", "consultant"
    ]

    query_lower = query.lower()

    for keyword in keywords:
        if keyword in query_lower:
            # Extract surrounding words
            words = query_lower.split()
            idx = next(i for i, w in enumerate(words) if keyword in w)

            # Get 1-2 words before and the keyword
            start = max(0, idx - 2)
            end = idx + 1
            occupation = " ".join(words[start:end])

            return occupation.strip()

    return None
