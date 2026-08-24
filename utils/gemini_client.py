import os
import json
import re

from google import genai
from google.genai import types


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.7-flash"
)


# ============================================================
# GEMINI CLIENT
# ============================================================

def _get_client():
    """
    Create the Gemini client using GEMINI_API_KEY.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("WARNING: GEMINI_API_KEY is not set.")
        return None

    try:
        return genai.Client(
            api_key=api_key
        )

    except Exception as e:
        print(
            f"Gemini client initialization failed: {e}"
        )
        return None


# ============================================================
# JSON CLEANING
# ============================================================

def _clean_json_response(raw):
    """
    Clean Gemini's response before JSON parsing.
    """

    if not raw:
        return ""

    raw = str(raw).strip()

    raw = re.sub(
        r"^```(?:json)?\s*",
        "",
        raw,
        flags=re.IGNORECASE
    )

    raw = re.sub(
        r"\s*```$",
        "",
        raw
    )

    raw = raw.strip()

    start = raw.find("{")
    end = raw.rfind("}")

    if start >= 0 and end > start:
        raw = raw[start:end + 1]

    return raw.strip()


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_list(value):
    if isinstance(value, list):
        return value
    return []


def _safe_score(value, default=50):
    try:
        return max(
            0,
            min(
                100,
                int(float(value))
            )
        )
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.75):
    try:
        return max(
            0,
            min(
                1,
                float(value)
            )
        )
    except (TypeError, ValueError):
        return default


# ============================================================
# FALLBACK HASHTAGS
# ============================================================

def _fallback_hashtags(text, platform):

    text_lower = text.lower()

    tags = []

    keyword_map = {
        "music": [
            "#music",
            "#newmusic",
            "#popmusic",
            "#musicdiscovery"
        ],

        "artist": [
            "#artist",
            "#musician",
            "#musicartist"
        ],

        "linkedin": [
            "#linkedin",
            "#contentstrategy",
            "#socialmedia"
        ],

        "instagram": [
            "#instagram",
            "#contentcreator",
            "#reels"
        ],

        "marketing": [
            "#marketing",
            "#digitalmarketing",
            "#contentmarketing"
        ],

        "technology": [
            "#technology",
            "#innovation",
            "#tech"
        ],

        "business": [
            "#business",
            "#businessstrategy",
            "#entrepreneurship"
        ]
    }


    for keyword, keyword_tags in keyword_map.items():

        if keyword in text_lower:

            for tag in keyword_tags:

                if tag not in tags:
                    tags.append(tag)


    if platform.lower() == "linkedin":

        tags.extend([
            "#linkedin",
            "#contentstrategy"
        ])

    elif platform.lower() == "instagram":

        tags.extend([
            "#instagram",
            "#contentcreator"
        ])


    tags.extend([
        "#content",
        "#socialmedia",
        "#engagement"
    ])


    unique = []

    for tag in tags:

        if tag not in unique:
            unique.append(tag)


    return unique[:10]


# ============================================================
# FALLBACK SUGGESTIONS
# ============================================================

def _fallback_suggestions(text, platform, goal):

    return [

        {
            "title": "Strengthen the opening",
            "priority": "high",
            "reason": (
                "The first line determines whether "
                "someone continues reading."
            ),
            "action": (
                "Lead with the most interesting "
                "idea, benefit, question, or observation."
            )
        },

        {
            "title": "Create a clearer reader payoff",
            "priority": "high",
            "reason": (
                "The reader should quickly understand "
                "why the post is worth their attention."
            ),
            "action": (
                "State the key takeaway or value "
                "earlier in the post."
            )
        },

        {
            "title": "Improve scanability",
            "priority": "medium",
            "reason": (
                "Long paragraphs are harder to consume "
                "on social platforms."
            ),
            "action": (
                "Break dense paragraphs into shorter "
                "2–3 line sections."
            )
        },

        {
            "title": "Add a conversation trigger",
            "priority": "medium",
            "reason": (
                "Engagement improves when readers have "
                "a specific reason to respond."
            ),
            "action": (
                "End with a relevant question or "
                "opinion prompt."
            )
        },

        {
            "title": "Use focused hashtags",
            "priority": "low",
            "reason": (
                "Relevant hashtags can improve discovery "
                "without making the post look spammy."
            ),
            "action": (
                "Use 5–10 highly relevant hashtags."
            )
        },

        {
            "title": "Keep the voice authentic",
            "priority": "low",
            "reason": (
                "Over-optimized social copy can lose "
                "the personality of the original."
            ),
            "action": (
                "Preserve the original voice while "
                "tightening unnecessary wording."
            )
        }
    ]


# ============================================================
# FALLBACK CONTENT DNA
# ============================================================

def _fallback_dna(text):

    text_lower = text.lower()

    educational = 10
    promotional = 10
    storytelling = 20
    emotional = 20
    authority = 15
    urgency = 5


    if any(
        word in text_lower
        for word in [
            "learn",
            "guide",
            "explains",
            "how to",
            "tips",
            "lesson"
        ]
    ):
        educational += 45


    if any(
        word in text_lower
        for word in [
            "buy",
            "sale",
            "offer",
            "available",
            "shop",
            "product"
        ]
    ):
        promotional += 50


    if any(
        word in text_lower
        for word in [
            "story",
            "journey",
            "remember",
            "years",
            "grew",
            "started"
        ]
    ):
        storytelling += 45


    if any(
        word in text_lower
        for word in [
            "love",
            "beautiful",
            "amazing",
            "excited",
            "inspiring",
            "powerful"
        ]
    ):
        emotional += 45


    if any(
        word in text_lower
        for word in [
            "expert",
            "research",
            "experience",
            "award",
            "leader",
            "professional"
        ]
    ):
        authority += 45


    if any(
        word in text_lower
        for word in [
            "now",
            "today",
            "limited",
            "urgent",
            "deadline",
            "soon"
        ]
    ):
        urgency += 50


    return {
        "educational": _safe_score(
            educational,
            10
        ),

        "promotional": _safe_score(
            promotional,
            10
        ),

        "storytelling": _safe_score(
            storytelling,
            20
        ),

        "emotional": _safe_score(
            emotional,
            20
        ),

        "authority": _safe_score(
            authority,
            15
        ),

        "urgency": _safe_score(
            urgency,
            5
        )
    }


# ============================================================
# FALLBACK ANALYSIS
# ============================================================

def _fallback_analysis(
    text,
    platform,
    goal
):

    words = re.findall(
        r"[A-Za-z0-9']+",
        text
    )

    word_count = len(words)


    sentences = re.split(
        r"[.!?]+",
        text
    )

    sentences = [
        s.strip()
        for s in sentences
        if s.strip()
    ]


    first_sentence = (
        sentences[0]
        if sentences
        else text[:150]
    )


    hook = 65

    if len(first_sentence) < 20:
        hook -= 10

    if "?" in first_sentence:
        hook += 10


    clarity = 75

    if word_count > 300:
        clarity -= 10


    readability = 80


    avg_word_len = (
        sum(len(w) for w in words)
        / max(
            1,
            word_count
        )
    )


    if avg_word_len > 7:
        readability -= 15


    cta = 45

    if re.search(
        r"\b(comment|share|follow|learn|visit|"
        r"discover|try|join|tell|what do you think)\b",
        text,
        flags=re.IGNORECASE
    ):
        cta = 70


    shareability = 65
    emotional = 65


    overall = round(
        (
            hook
            + clarity
            + readability
            + cta
            + shareability
            + emotional
        ) / 6
    )


    positive_words = [
        "love",
        "great",
        "amazing",
        "beautiful",
        "exciting",
        "powerful",
        "successful"
    ]


    negative_words = [
        "bad",
        "hate",
        "terrible",
        "worst",
        "problem",
        "failed"
    ]


    positive_count = sum(
        text.lower().count(word)
        for word in positive_words
    )


    negative_count = sum(
        text.lower().count(word)
        for word in negative_words
    )


    if positive_count > negative_count:
        tone = "positive"

    elif negative_count > positive_count:
        tone = "negative"

    else:
        tone = "neutral"


    hashtags = _fallback_hashtags(
        text,
        platform
    )


    suggestions = _fallback_suggestions(
        text,
        platform,
        goal
    )


    dna = _fallback_dna(
        text
    )


    improved = (
        f"{first_sentence}\n\n"
        "Here's the key idea: "
        "make the main takeaway clearer, "
        "more concise, and easier for the "
        "reader to act on.\n\n"
        "What do you think?"
    )


    return {

        "caption":
            improved,

        "hashtags":
            hashtags,

        "suggestions":
            suggestions,

        "tone":
            tone,

        "confidence":
            0.55,

        "scores": {

            "overall":
                overall,

            "hook":
                hook,

            "clarity":
                clarity,

            "readability":
                readability,

            "cta":
                cta,

            "shareability":
                shareability,

            "emotional_impact":
                emotional
        },

        "score_explanations": {

            "hook":
                "The opening was evaluated for curiosity and immediate relevance.",

            "clarity":
                "The content was evaluated for structure and ease of understanding.",

            "readability":
                "Sentence and word complexity were considered.",

            "cta":
                "The analysis looked for a clear reader action.",

            "shareability":
                "The content was evaluated for usefulness, relatability and share value.",

            "emotional_impact":
                "The analysis evaluated the emotional response likely created by the content."
        },

        "content_dna":
            dna,

        "top_issue": {

            "title":
                "Strengthen your opening",

            "reason":
                "The opening can communicate the main value more quickly.",

            "fix":
                "Lead with the strongest idea, benefit, question, or observation."
        },

        "improved_version":
            improved,

        "rewrite_reason":
            "The improved version makes the message easier to scan while preserving its central meaning.",

        "platform_advice": [

            f"For {platform}, keep the opening highly relevant to the audience.",

            "Use short paragraphs to improve mobile readability.",

            f"End with a clear action aligned with the goal of {goal.lower()}."
        ],

        "ai_available":
            False
    }


# ============================================================
# MAIN GEMINI ANALYSIS
# ============================================================

def generate_insights_with_gemini(
    text: str,
    platform: str = "LinkedIn",
    goal: str = "Engagement"
) -> dict:

    text = (
        text or ""
    ).strip()


    if not text:
        return {}


    client = _get_client()


    if client is None:

        return _fallback_analysis(
            text,
            platform,
            goal
        )


    source_text = text[:8000]


    # ========================================================
    # GEMINI PROMPT
    # ========================================================

    prompt = f"""
You are a senior social-media strategist,
content analyst and professional copywriter.

Analyze the supplied social-media content deeply.

TARGET PLATFORM:
{platform}

PRIMARY GOAL:
{goal}

IMPORTANT:

The source may have been extracted from a screenshot
using OCR.

Ignore obvious OCR garbage such as:

- phone status bars
- battery indicators
- LTE/Wi-Fi text
- random numbers
- UI icons represented as characters
- Instagram navigation labels
- timestamps
- duplicated OCR fragments

Focus on the actual social-media post.

Do NOT invent facts.

Do NOT invent statistics.

Do NOT invent products, people, events or claims.

Preserve the meaning of the source.

Return ONLY valid JSON.

The JSON must contain:

{{
  "caption": "A strong rewritten caption",

  "hashtags": [
    "#relevanttag1",
    "#relevanttag2",
    "#relevanttag3",
    "#relevanttag4",
    "#relevanttag5",
    "#relevanttag6",
    "#relevanttag7"
  ],

  "suggestions": [
    {{
      "title": "specific improvement",
      "priority": "high",
      "reason": "specific reason",
      "action": "specific action"
    }}
  ],

  "tone": "neutral",

  "confidence": 0.9,

  "scores": {{
    "overall": 80,
    "hook": 75,
    "clarity": 80,
    "readability": 85,
    "cta": 60,
    "shareability": 78,
    "emotional_impact": 72
  }},

  "score_explanations": {{
    "hook": "why",
    "clarity": "why",
    "readability": "why",
    "cta": "why",
    "shareability": "why",
    "emotional_impact": "why"
  }},

  "content_dna": {{
    "educational": 20,
    "promotional": 10,
    "storytelling": 40,
    "emotional": 60,
    "authority": 30,
    "urgency": 5
  }},

  "top_issue": {{
    "title": "Most important problem",
    "reason": "Specific explanation",
    "fix": "Specific solution"
  }},

  "improved_version":
    "Complete improved version of the post",

  "rewrite_reason":
    "Why the rewritten version is stronger",

  "platform_advice": [
    "Specific platform recommendation",
    "Specific platform recommendation",
    "Specific platform recommendation",
    "Specific platform recommendation"
  ]
}}

RULES:

1. hashtags must contain 7-10 relevant lowercase hashtags.

2. suggestions MUST contain exactly 6 items:
   - 2 high priority
   - 2 medium priority
   - 2 low priority

3. Suggestions must refer to the actual content.

4. Do not use generic advice such as:
   "make it engaging"
   "improve your content"
   "make it better"

5. Scores must be integers from 0 to 100.

6. Content DNA must be integers from 0 to 100.

7. Confidence must be between 0 and 1.

8. The improved version must preserve the original meaning.

9. Do not fabricate information.

10. Make the rewrite genuinely useful.

11. Do not simply say:
    "add a concise caption".

12. The CTA score must reflect the actual presence
    and quality of a call to action.

13. Hook score must evaluate the actual opening.

14. Readability must consider sentence length,
    paragraph structure and word complexity.

15. Shareability must consider usefulness,
    emotional value and relatability.

16. Emotional impact must consider curiosity,
    inspiration, excitement, concern or other emotion.

17. Platform advice must specifically consider
    {platform}.

18. Recommendations must specifically support
    the goal of {goal}.

19. Ignore obvious OCR artifacts.

20. For tone, choose:
    positive only when positive language clearly dominates.
    negative only when negative language clearly dominates.
    neutral when the content is mainly factual/descriptive.
    mixed when meaningful positive and negative signals coexist.

SOURCE CONTENT:

{source_text}
"""


    # ========================================================
    # GEMINI REQUEST
    # ========================================================

    try:

        response = client.models.generate_content(

            model=MODEL_NAME,

            contents=prompt,

            config=types.GenerateContentConfig(

                max_output_tokens=3000,

                response_mime_type="application/json"
            )
        )


        raw = getattr(
            response,
            "text",
            ""
        ) or ""


        raw = _clean_json_response(
            raw
        )


        if not raw:

            print(
                "Gemini returned an empty response."
            )

            return _fallback_analysis(
                text,
                platform,
                goal
            )


        data = json.loads(
            raw
        )


        if not isinstance(
            data,
            dict
        ):

            raise ValueError(
                "Gemini returned non-object JSON."
            )


        # ====================================================
        # NORMALIZE CAPTION
        # ====================================================

        data["caption"] = str(

            data.get("caption")

            or data.get("improved_version")

            or text[:500]
        )


        # ====================================================
        # NORMALIZE HASHTAGS
        # ====================================================

        hashtags = _safe_list(
            data.get("hashtags")
        )


        hashtags = [

            str(tag)

            for tag in hashtags

            if str(tag).startswith("#")
        ]


        if not hashtags:

            hashtags = _fallback_hashtags(
                text,
                platform
            )


        data["hashtags"] = hashtags[:10]


        # ====================================================
        # NORMALIZE SUGGESTIONS
        # ====================================================

        suggestions = []


        for item in _safe_list(
            data.get("suggestions")
        ):

            if not isinstance(
                item,
                dict
            ):
                continue


            priority = str(
                item.get("priority")
                or "medium"
            ).lower()


            if priority not in {
                "high",
                "medium",
                "low"
            }:

                priority = "medium"


            suggestions.append({

                "title":
                    str(
                        item.get("title")
                        or "Content improvement"
                    ),

                "priority":
                    priority,

                "reason":
                    str(
                        item.get("reason")
                        or "This area can be improved."
                    ),

                "action":
                    str(
                        item.get("action")
                        or "Make this section more specific."
                    )
            })


        fallback_suggestions = _fallback_suggestions(
            text,
            platform,
            goal
        )


        while len(suggestions) < 6:

            suggestions.append(
                fallback_suggestions[
                    len(suggestions)
                ]
            )


        data["suggestions"] = suggestions[:6]


        # ====================================================
        # NORMALIZE TONE
        # ====================================================

        tone = str(
            data.get("tone")
            or "neutral"
        ).lower()


        if tone not in {
            "positive",
            "negative",
            "neutral",
            "mixed"
        }:

            tone = "neutral"


        data["tone"] = tone


        # ====================================================
        # CONFIDENCE
        # ====================================================

        data["confidence"] = _safe_float(
            data.get("confidence"),
            0.8
        )


        # ====================================================
        # SCORES
        # ====================================================

        default_scores = {

            "overall": 70,

            "hook": 65,

            "clarity": 70,

            "readability": 75,

            "cta": 50,

            "shareability": 65,

            "emotional_impact": 60
        }


        scores = data.get(
            "scores"
        )


        if not isinstance(
            scores,
            dict
        ):

            scores = {}


        data["scores"] = {

            key:
                _safe_score(
                    scores.get(key),
                    default
                )

            for key, default
            in default_scores.items()
        }


        # ====================================================
        # SCORE EXPLANATIONS
        # ====================================================

        explanation_defaults = {

            "hook":
                "Evaluated based on the strength of the opening.",

            "clarity":
                "Evaluated based on structure and message clarity.",

            "readability":
                "Evaluated based on sentence length and scanning ease.",

            "cta":
                "Evaluated based on the strength of the reader action.",

            "shareability":
                "Evaluated based on usefulness, relatability and share value.",

            "emotional_impact":
                "Evaluated based on emotional response and curiosity."
        }


        explanations = data.get(
            "score_explanations"
        )


        if not isinstance(
            explanations,
            dict
        ):

            explanations = {}


        data["score_explanations"] = {

            key:
                str(
                    explanations.get(
                        key,
                        default
                    )
                )

            for key, default
            in explanation_defaults.items()
        }


        # ====================================================
        # CONTENT DNA
        # ====================================================

        dna_defaults = _fallback_dna(
            text
        )


        dna = data.get(
            "content_dna"
        )


        if not isinstance(
            dna,
            dict
        ):

            dna = {}


        data["content_dna"] = {

            key:
                _safe_score(
                    dna.get(key),
                    dna_defaults[key]
                )

            for key in dna_defaults
        }


        # ====================================================
        # TOP ISSUE
        # ====================================================

        top_issue = data.get(
            "top_issue"
        )


        if not isinstance(
            top_issue,
            dict
        ):

            top_issue = {}


        data["top_issue"] = {

            "title":
                str(
                    top_issue.get("title")
                    or "Strengthen your opening"
                ),

            "reason":
                str(
                    top_issue.get("reason")
                    or "The opening can be more compelling."
                ),

            "fix":
                str(
                    top_issue.get("fix")
                    or "Lead with the strongest reader benefit."
                )
        }


        # ====================================================
        # IMPROVED VERSION
        # ====================================================

        improved = str(

            data.get("improved_version")

            or data.get("caption")

            or text
        )


        data["improved_version"] = improved


        data["rewrite_reason"] = str(

            data.get("rewrite_reason")

            or (
                "The rewrite improves clarity, "
                "structure and platform fit while "
                "preserving the original meaning."
            )
        )


        # ====================================================
        # PLATFORM ADVICE
        # ====================================================

        advice = _safe_list(
            data.get("platform_advice")
        )


        advice = [

            str(item)

            for item in advice

            if str(item).strip()
        ]


        if not advice:

            advice = [

                (
                    f"Optimize the opening specifically "
                    f"for {platform}."
                ),

                (
                    "Use short, scannable paragraphs "
                    "for mobile readers."
                ),

                (
                    f"End with a clear action aligned "
                    f"with {goal.lower()}."
                )
            ]


        data["platform_advice"] = advice[:5]


        # ====================================================
        # SUCCESS
        # ====================================================

        data["ai_available"] = True


        return data


    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as e:

        print(
            "\n========================================"
        )

        print(
            "GEMINI ANALYSIS ERROR:"
        )

        print(
            repr(e)
        )

        print(
            "========================================\n"
        )


        return _fallback_analysis(
            text,
            platform,
            goal
        )