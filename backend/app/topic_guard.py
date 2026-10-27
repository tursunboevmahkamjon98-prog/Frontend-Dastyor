"""Reject a topic before it costs anything.

The generator will happily write a full konspekt for "asdkjh" or for a subject
that does not exist, because nothing ever asked whether the topic was real. A
teacher then pays a limit for a document made of invented facts.

Two layers, both of which run *before* `limits.reserve`, so a rejected topic
never touches the balance:

  1. `shape_verdict` - deterministic, free, instant. Catches keyboard mashing:
     random letter runs, repeated characters, keyboard rows, strings with no
     vowels. No model involved, so it is fully testable (see
     tests/test_topic_guard.py).

  2. `check_topic` - one small model call for the cases layer 1 cannot judge:
     strings made of real words that still do not name a teachable topic.

Layer 2 fails OPEN. If the validator times out, errors, or returns something
unparseable, the topic is allowed through. Blocking a real lesson because a
side-channel check broke is far worse than letting an odd topic reach the
generator, which is where we were before this file existed anyway.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from app.config import get_settings
from app.logger import logger

settings = get_settings()

# Cyrillic, Tajik and Latin vowels. 'ъ' and 'ь' are not vowels and must not be
# listed here - "объект" would otherwise pass on a sign rather than a vowel.
VOWELS = set("аеёиоуыэюяӣӯəaeiouy")

CONSONANT_RUN = re.compile(r"[бвгджзйклмнпрстфхцчшщқғҳҷbcdfghjklmnpqrstvwxz]{5,}", re.I)
REPEATED_CHAR = re.compile(r"(.)\1{3,}")
TOKEN_SPLIT = re.compile(r"[^\wЀ-ӿ]+", re.U)

KEYBOARD_ROWS = (
    "йцукенгшщзхъ",
    "фывапролджэ",
    "ячсмитьбю",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
    "1234567890",
)

MIN_LENGTH = 3

# Tokens this short carry too little signal to judge, and plenty of real ones
# exist (pH, ДНК, 3D).
SHORT_TOKEN = 3


@dataclass
class TopicVerdict:
    ok: bool
    reason: str = ""
    detail: str = ""


def _is_acronym(token: str) -> bool:
    """ДНК, HTML, CSS - all consonants on purpose, and legitimately topics."""
    return len(token) <= 6 and token.isupper()


def _looks_like_keyboard_run(token: str) -> bool:
    low = token.lower()
    return any(low in row or low in row[::-1] for row in KEYBOARD_ROWS)


def shape_verdict(topic: str) -> TopicVerdict:
    """Deterministic checks. No network, no model, no cost."""
    text = (topic or "").strip()

    if len(text) < MIN_LENGTH:
        return TopicVerdict(False, "too_short", f"length {len(text)}")

    letters = [c for c in text if c.isalpha()]
    if not letters:
        return TopicVerdict(False, "gibberish", "no letters at all")

    if len(letters) / len(text) < 0.4:
        return TopicVerdict(False, "gibberish", "mostly non-letters")

    if REPEATED_CHAR.search(text):
        return TopicVerdict(False, "gibberish", "a character repeats 4+ times")

    tokens = [t for t in TOKEN_SPLIT.split(text) if t]
    judgeable = [t for t in tokens if len(t) > SHORT_TOKEN and not _is_acronym(t)]

    for token in judgeable:
        if _looks_like_keyboard_run(token):
            return TopicVerdict(False, "gibberish", f"keyboard run: {token}")
        if CONSONANT_RUN.search(token):
            return TopicVerdict(False, "gibberish", f"consonant run: {token}")

    # A topic made only of vowelless long words is mashing. One real word is
    # enough to clear this: mixed input like "ДНК ва синтези сафеда" passes on
    # its second word.
    if judgeable and not any(set(t.lower()) & VOWELS for t in judgeable):
        return TopicVerdict(False, "gibberish", "no vowels in any word")

    return TopicVerdict(True)


_SYSTEM = (
    "You decide whether a string names something real that a school lesson "
    "could be about. You never write lessons, only judge. Reply with JSON only."
)

# The subject is context, never the test. An earlier version asked "could a
# teacher teach this IN THAT SUBJECT", and whenever the subject did not match
# the topic's field - a history topic filed under Biology - the model stopped
# judging whether the topic was real at all and answered ok. "Таърихи ҷанги
# Тоҷикистон бо Миррих" (a war with Mars) passed under Биология and was
# rejected under История. Reality has to be the question; fit must not be.
_USER = """Topic: "{topic}"
(Context only, not the test — subject: {subject}, grade: {grade})

Does this topic name something that actually exists: a real phenomenon,
event, person, work, technology or body of knowledge?

{{"ok": true}} — it is real and teachable, even if narrow, unusual, loosely
phrased, in Tajik/Russian/English, or filed under a subject it does not
obviously belong to.

{{"ok": false, "why": "<at most 8 words>"}} — it is random characters, a
meaningless phrase, or it describes something that does not exist: an
invented event, an impossible object, a fictional claim stated as fact.

Do not reject a topic for being a poor fit for the subject or the grade.
Reject it only when it is not real."""


async def check_topic(topic: str, subject: str, grade: str) -> TopicVerdict:
    """Layer 1, then one small model call. Fails open on any problem."""
    shape = shape_verdict(topic)
    if not shape.ok:
        logger.info("topic_guard rejected on shape: %r (%s)", topic, shape.detail)
        return shape

    keys = [
        k
        for k in (
            settings.AI_API_KEY,
            settings.AI_API_KEY_2,
            settings.AI_API_KEY_3,
            settings.AI_API_KEY_4,
            settings.AI_API_KEY_5,
        )
        if k
    ]
    if not keys:
        return TopicVerdict(True)

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                f"{settings.AI_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {keys[0]}", "Content-Type": "application/json"},
                json={
                    "model": settings.AI_MODEL,
                    "messages": [
                        {"role": "system", "content": _SYSTEM},
                        {
                            "role": "user",
                            "content": _USER.format(
                                subject=subject or "-", grade=grade or "-", topic=topic.strip()
                            ),
                        },
                    ],
                    "temperature": 0,
                    # gpt-oss is a reasoning model: it emits a `reasoning`
                    # field first and `content` only after it finishes. An
                    # 80-token budget ran out mid-reasoning, so every call
                    # came back with finish_reason="length" and no content at
                    # all - the check silently failed open on every topic.
                    # "low" effort answers in 27-89 completion tokens and
                    # ~0.3s; 400 leaves room without inviting a long think.
                    "reasoning_effort": "low",
                    "max_tokens": 400,
                },
            )
        if response.status_code != 200:
            logger.warning("topic_guard check unavailable: HTTP %s", response.status_code)
            return TopicVerdict(True)

        message = response.json()["choices"][0].get("message", {})
        raw = (message.get("content") or "").strip()
        if not raw:
            logger.warning("topic_guard got no content (reasoning model ran long)")
            return TopicVerdict(True)
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return TopicVerdict(True)
        parsed = json.loads(match.group(0))
    except Exception as exc:
        logger.warning("topic_guard check failed open: %s: %s", type(exc).__name__, exc)
        return TopicVerdict(True)

    if parsed.get("ok") is False:
        why = str(parsed.get("why", ""))[:120]
        logger.info("topic_guard rejected on meaning: %r (%s)", topic, why)
        return TopicVerdict(False, "not_a_topic", why)

    return TopicVerdict(True)
