import re
from collections import Counter

from vaderSentiment.vaderSentiment import (
    SentimentIntensityAnalyzer
)

from utils.gemini_client import (
    generate_insights_with_gemini
)


# ============================================================
# TOKENIZATION
# ============================================================

def tokenize(text: str):

    return re.findall(
        r"[A-Za-z0-9_']+",
        text
    )


# ============================================================
# SAFE NUMBER
# ============================================================

def _safe_number(
    value,
    default=0
):

    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return default


# ============================================================
# CLAMP
# ============================================================

def _clamp(
    value,
    minimum=0,
    maximum=100
):

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


# ============================================================
# LOCAL BASELINE SCORE
# ============================================================

def _calculate_local_score(
    word_count,
    avg_word_len,
    hashtag_count,
    mention_count,
    url_count,
    sentiment
):

    score = 70.0

    # Length
    if word_count == 0:

        score -= 30

    elif word_count < 20:

        score -= 8

    elif 20 <= word_count <= 220:

        score += 5

    elif word_count > 350:

        score -= 8


    # Readability
    if avg_word_len <= 5:

        score += 6

    elif avg_word_len <= 7:

        score += 2

    else:

        score -= 7


    # Hashtags
    if hashtag_count == 0:

        score -= 5

    elif 2 <= hashtag_count <= 8:

        score += 4

    elif hashtag_count > 15:

        score -= 5


    # Mentions
    if mention_count > 0:

        score += 2


    # URLs
    if url_count > 3:

        score -= 4


    # Sentiment
    compound = sentiment.get(
        "compound",
        0
    )

    if compound > 0.05:

        score += 3

    elif compound < -0.5:

        score -= 5


    return int(
        _clamp(
            round(score)
        )
    )


# ============================================================
# FALLBACK SCORES
# ============================================================

def _fallback_scores(
    local_score,
    word_count,
    avg_word_len,
    hashtag_count,
    url_count,
    text=""
):

    hook = local_score


    if word_count < 15:

        hook -= 5


    # CTA detection
    action_words = re.findall(
        r"\b("
        r"click|learn|try|join|buy|share|comment|"
        r"follow|visit|discover|download|sign|"
        r"contact|subscribe|start|explore|"
        r"tell|what do you think"
        r")\b",
        text,
        flags=re.IGNORECASE
    )


    cta = 45


    if action_words:

        cta += 25


    clarity = local_score


    if avg_word_len > 7:

        clarity -= 8


    readability = 90


    if avg_word_len > 7:

        readability -= 20

    elif avg_word_len > 5:

        readability -= 8


    if word_count > 350:

        readability -= 10


    shareability = local_score


    if hashtag_count == 0:

        shareability -= 5


    if url_count > 3:

        shareability -= 5


    emotional_impact = local_score


    return {

        "overall":
            int(_clamp(local_score)),

        "hook":
            int(_clamp(hook)),

        "clarity":
            int(_clamp(clarity)),

        "readability":
            int(_clamp(readability)),

        "cta":
            int(_clamp(cta)),

        "shareability":
            int(_clamp(shareability)),

        "emotional_impact":
            int(_clamp(emotional_impact))
    }


# ============================================================
# NORMALIZE AI SCORES
# ============================================================

def _normalize_ai_scores(
    ai_scores,
    fallback_scores
):

    if not isinstance(
        ai_scores,
        dict
    ):

        return fallback_scores


    output = {}


    for key in fallback_scores:

        value = ai_scores.get(
            key
        )


        if value is None:

            value = fallback_scores[key]


        try:

            value = int(
                float(value)
            )

        except (
            TypeError,
            ValueError
        ):

            value = fallback_scores[key]


        output[key] = int(
            _clamp(value)
        )


    return output


# ============================================================
# CONTENT DNA
# ============================================================

def _build_content_dna(
    ai_dna
):

    defaults = {

        "educational": 10,

        "promotional": 10,

        "storytelling": 20,

        "emotional": 20,

        "authority": 15,

        "urgency": 5
    }


    if not isinstance(
        ai_dna,
        dict
    ):

        return defaults


    for key in defaults:

        try:

            defaults[key] = int(
                _clamp(
                    float(
                        ai_dna.get(
                            key,
                            defaults[key]
                        )
                    )
                )
            )

        except (
            TypeError,
            ValueError
        ):

            pass


    return defaults


# ============================================================
# PRIORITY
# ============================================================

def _priority_label(
    priority
):

    priority = str(
        priority or "medium"
    ).lower()


    if priority not in {
        "high",
        "medium",
        "low"
    }:

        return "medium"


    return priority


# ============================================================
# NORMALIZE SUGGESTIONS
# ============================================================

def _normalize_suggestions(
    suggestions
):

    if not isinstance(
        suggestions,
        list
    ):

        return []


    output = []


    for suggestion in suggestions:

        if isinstance(
            suggestion,
            dict
        ):

            output.append({

                "title": str(
                    suggestion.get(
                        "title"
                    )
                    or "Content improvement"
                ),

                "priority":
                    _priority_label(
                        suggestion.get(
                            "priority"
                        )
                    ),

                "reason": str(
                    suggestion.get(
                        "reason"
                    )
                    or "This area could be improved."
                ),

                "action": str(
                    suggestion.get(
                        "action"
                    )
                    or "Make this part more specific."
                )
            })


        elif isinstance(
            suggestion,
            str
        ):

            output.append({

                "title":
                    "Content improvement",

                "priority":
                    "medium",

                "reason":
                    suggestion,

                "action":
                    suggestion
            })


    return output[:6]


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_text(
    text: str,
    platform: str = "LinkedIn",
    goal: str = "Engagement"
):

    text = (
        text or ""
    ).strip()


    if not text:

        return {

            "summary": {},

            "engagement": [],

            "ai_generated": {},

            "scores": {},

            "content_dna": {},

            "top_issue": {},

            "platform_advice": [],

            "ai_available": False
        }


    # ========================================================
    # BASIC TEXT ANALYSIS
    # ========================================================

    analyzer = (
        SentimentIntensityAnalyzer()
    )


    sentiment = (
        analyzer.polarity_scores(
            text
        )
    )


    words = tokenize(
        text
    )


    word_count = len(
        words
    )


    hashtags = re.findall(
        r"#\w+",
        text
    )


    mentions = re.findall(
        r"@\w+",
        text
    )


    urls = re.findall(
        r"https?://\S+",
        text
    )


    # ========================================================
    # KEYWORD ANALYSIS
    # ========================================================

    ignored_words = {

        "the",
        "and",
        "for",
        "that",
        "this",
        "with",
        "from",
        "have",
        "has",
        "her",
        "his",
        "was",
        "are",
        "you",
        "your",
        "been",
        "into",
        "what",
        "they",
        "their"
    }


    top_words = Counter(

        w.lower()

        for w in words

        if (
            len(w) > 2
            and w.lower()
            not in ignored_words
        )

    ).most_common(8)


    # ========================================================
    # LOCAL TONE
    # ========================================================

    compound = sentiment[
        "compound"
    ]


    if compound > 0.05:

        local_tone = "Positive"

    elif compound < -0.05:

        local_tone = "Negative"

    else:

        local_tone = "Neutral"


    # ========================================================
    # WORD LENGTH
    # ========================================================

    avg_len = round(

        sum(
            len(w)
            for w in words
        )
        /
        max(
            1,
            word_count
        ),

        2
    )


    if word_count < 50:

        word_msg = (
            f"{word_count} "
            "(very short - may lack context)"
        )

    elif word_count > 300:

        word_msg = (
            f"{word_count} "
            "(long - consider trimming for attention)"
        )

    else:

        word_msg = (
            f"{word_count} "
            "(medium length - good for social content)"
        )


    if avg_len < 5:

        avg_len_msg = (
            f"{avg_len} - Easy to read"
        )

    elif avg_len < 7:

        avg_len_msg = (
            f"{avg_len} - Moderate complexity"
        )

    else:

        avg_len_msg = (
            f"{avg_len} - Complex, may reduce engagement"
        )


    # ========================================================
    # HASHTAGS
    # ========================================================

    hashtag_msg = str(
        len(hashtags)
    )


    if len(hashtags) == 0:

        hashtag_msg += (
            " - Missing hashtags"
        )

    elif len(hashtags) < 3:

        hashtag_msg += (
            " - Could add more for reach"
        )

    else:

        hashtag_msg += (
            " - Good use"
        )


    # ========================================================
    # MENTIONS
    # ========================================================

    mention_msg = str(
        len(mentions)
    )


    if len(mentions) > 0:

        mention_msg += (
            " - Strong collaboration tagging"
        )


    # ========================================================
    # URLS
    # ========================================================

    url_msg = str(
        len(urls)
    )


    if len(urls) > 2:

        url_msg += (
            " - May appear promotional if all are kept"
        )


    # ========================================================
    # SENTIMENT
    # ========================================================
    #
    # These are VADER baseline values.
    # Gemini tone is kept separate and becomes the final
    # semantic tone when Gemini is available.
    # ========================================================

    sentiment_msg = {

        "compound":
            f"{sentiment['compound']} "
            f"(Baseline tone: {local_tone})",

        "pos":
            f"{sentiment['pos']}",

        "neu":
            f"{sentiment['neu']}",

        "neg":
            f"{sentiment['neg']}"
    }


    # ========================================================
    # LOCAL SCORE
    # ========================================================

    local_score = (
        _calculate_local_score(

            word_count=
                word_count,

            avg_word_len=
                avg_len,

            hashtag_count=
                len(hashtags),

            mention_count=
                len(mentions),

            url_count=
                len(urls),

            sentiment=
                sentiment
        )
    )


    fallback_scores = (
        _fallback_scores(

            local_score=
                local_score,

            word_count=
                word_count,

            avg_word_len=
                avg_len,

            hashtag_count=
                len(hashtags),

            url_count=
                len(urls),

            text=
                text
        )
    )


    # ========================================================
    # GEMINI
    # ========================================================

    ai = (
        generate_insights_with_gemini(

            text=text,

            platform=platform,

            goal=goal
        )
    )


    if not isinstance(
        ai,
        dict
    ):

        ai = {}


    # ========================================================
    # AI CONTENT
    # ========================================================

    ai_caption = str(

        ai.get(
            "caption"
        )

        or text[:500]
    )


    ai_hashtags = (

        ai.get(
            "hashtags"
        )

        or []
    )


    ai_suggestions = (
        _normalize_suggestions(

            ai.get(
                "suggestions"
            )
        )
    )


    # ========================================================
    # FALLBACK RECOMMENDATIONS
    # ========================================================

    if not ai_suggestions:

        ai_suggestions = [

            {
                "title":
                    "Strengthen your opening",

                "priority":
                    "high",

                "reason":
                    "The opening controls initial attention.",

                "action":
                    "Lead with the strongest idea."
            },

            {
                "title":
                    "Add a clearer reader payoff",

                "priority":
                    "high",

                "reason":
                    "Readers need a clear reason to continue.",

                "action":
                    "State the main benefit earlier."
            },

            {
                "title":
                    "Improve scanability",

                "priority":
                    "medium",

                "reason":
                    "Dense text is harder to consume.",

                "action":
                    "Break long paragraphs into smaller sections."
            },

            {
                "title":
                    "Add a conversation trigger",

                "priority":
                    "medium",

                "reason":
                    "A response prompt can encourage interaction.",

                "action":
                    "End with a relevant question."
            },

            {
                "title":
                    "Use focused hashtags",

                "priority":
                    "low",

                "reason":
                    "Relevant tags can improve discovery.",

                "action":
                    "Use a small set of highly relevant tags."
            },

            {
                "title":
                    "Preserve authentic voice",

                "priority":
                    "low",

                "reason":
                    "Authenticity helps content feel natural.",

                "action":
                    "Tighten wording without removing personality."
            }
        ]


    # ========================================================
    # FINAL TONE
    # ========================================================
    #
    # Gemini is the primary semantic classifier.
    # VADER is used only when Gemini doesn't return
    # a valid tone.
    # ========================================================

    ai_tone = str(
        ai.get(
            "tone"
        ) or ""
    ).strip().lower()


    valid_tones = {

        "positive":
            "Positive",

        "negative":
            "Negative",

        "neutral":
            "Neutral",

        "mixed":
            "Mixed"
    }


    if ai_tone in valid_tones:

        display_tone = valid_tones[
            ai_tone
        ]

    else:

        display_tone = local_tone


    # ========================================================
    # AI CONFIDENCE
    # ========================================================

    ai_conf = ai.get(
        "confidence"
    )


    # ========================================================
    # SCORES
    # ========================================================

    scores = (
        _normalize_ai_scores(

            ai.get(
                "scores"
            ),

            fallback_scores
        )
    )


    # ========================================================
    # CONTENT DNA
    # ========================================================

    content_dna = (
        _build_content_dna(

            ai.get(
                "content_dna"
            )
        )
    )


    # ========================================================
    # SCORE EXPLANATIONS
    # ========================================================

    score_explanations = (
        ai.get(
            "score_explanations",
            {}
        )
    )


    if not isinstance(
        score_explanations,
        dict
    ):

        score_explanations = {}


    # ========================================================
    # TOP ISSUE
    # ========================================================

    top_issue = (
        ai.get(
            "top_issue",
            {}
        )
    )


    if not isinstance(
        top_issue,
        dict
    ):

        top_issue = {}


    top_issue = {

        "title": str(

            top_issue.get(
                "title"
            )

            or "Strengthen your opening"
        ),

        "reason": str(

            top_issue.get(
                "reason"
            )

            or "The content can be made more compelling."
        ),

        "fix": str(

            top_issue.get(
                "fix"
            )

            or "Lead with the strongest reader benefit."
        )
    }


    # ========================================================
    # IMPROVED VERSION
    # ========================================================

    improved_version = str(

        ai.get(
            "improved_version"
        )

        or ai_caption
    )


    rewrite_reason = str(

        ai.get(
            "rewrite_reason"
        )

        or (
            "The improved version focuses on "
            "clarity, positioning and engagement."
        )
    )


    # ========================================================
    # PLATFORM ADVICE
    # ========================================================

    platform_advice = (
        ai.get(
            "platform_advice",
            []
        )
    )


    if not isinstance(
        platform_advice,
        list
    ):

        platform_advice = []


    platform_advice = [

        str(item)

        for item
        in platform_advice[:5]

        if str(item).strip()
    ]


    # ========================================================
    # RETURN ANALYSIS
    # ========================================================

    return {

        "summary": {

            "words":
                word_msg,

            "word_count":
                word_count,

            "chars":
                len(text),

            "avg_word_len":
                avg_len_msg,

            "avg_word_length":
                avg_len,

            "hashtags":
                hashtag_msg,

            "hashtag_count":
                len(hashtags),

            "mentions":
                mention_msg,

            "mention_count":
                len(mentions),

            "urls":
                url_msg,

            "url_count":
                len(urls),

            "tone":
                display_tone,

            "sentiment":
                sentiment_msg,

            "sentiment_scores":
                sentiment,

            "top_keywords":
                top_words,

            "gemini_confidence":
                ai_conf
                if ai_conf is not None
                else ""
        },


        "scores":
            scores,


        "score_explanations":
            score_explanations,


        "content_dna":
            content_dna,


        "top_issue":
            top_issue,


        "engagement":
            ai_suggestions,


        "ai_generated": {

            "caption":
                ai_caption,

            "recommended_hashtags":
                ai_hashtags,

            "improved_version":
                improved_version,

            "rewrite_reason":
                rewrite_reason
        },


        "platform_advice":
            platform_advice,


        "platform":
            platform,


        "goal":
            goal,


        "ai_available":
            bool(
                ai.get(
                    "ai_available",
                    False
                )
            )
    }