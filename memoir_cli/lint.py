"""The truth-contract linter (ROADMAP Phase 5).

The memoir truth contract (memoir-ethics-and-care.md Part 3) says the writer may
shape and compress, but must not invent. This module makes that checkable: it
reads the prose in `chapters/`, extracts the *concrete* claims — years, dates,
ages, quantities, proper names, quoted dialogue — and reports the ones with no
trace in the source material under `memories/`.

What it is: a reviewer's checklist generator. A finding means "this detail is
not in your notes — confirm it before you publish", not "this is a lie".

What it is not: a truth oracle. It cannot know what the writer remembers but
never wrote down, so an allowlist (`.memoir/lint-allow.txt`) exists for details
that are legitimately from the writer's own head. False positives are the
intended failure mode; silently missing an invented detail is the one to avoid.

Known limits, stated plainly: proper-noun detection is Latin-script only
(CJK personal names are not reliably separable without a tokenizer, so for CJK
text the linter leans on dates, numbers and dialogue). Dialogue is reported at
its own severity because reconstructed speech is normal in memoir — it needs a
disclosure in the author's note, not deletion.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

ALLOW_FILE = ".memoir/lint-allow.txt"

KIND_UNSUPPORTED = "unsupported-detail"
KIND_DIALOGUE = "reconstructed-dialogue"

# Titles and honorifics that carry no identifying force on their own.
TITLES = {
    "aunt", "uncle", "grandma", "grandpa", "grandmother", "grandfather",
    "mother", "father", "mom", "dad", "mr", "mrs", "ms", "miss", "dr",
    "doctor", "professor", "sister", "brother", "cousin", "nurse", "captain",
}
# Capitalized words that are ordinary English, not names.
COMMON_CAPS = {
    "i", "a", "an", "the", "and", "but", "or", "if", "when", "while", "after",
    "before", "she", "he", "they", "we", "it", "there", "then", "that", "this",
    "my", "his", "her", "their", "our", "one", "two", "three", "later", "even",
    "every", "everything", "nothing", "someone", "somebody", "yes", "no", "so",
    "at", "in", "on", "of", "for", "to", "from", "by", "with", "was", "were",
    "is", "are", "had", "has", "have", "did", "do", "does", "not", "never",
    "always", "still", "just", "only", "what", "who", "how", "why", "where",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
}

YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
CJK_YEAR_RE = re.compile(r"(1[89]\d{2}|20\d{2})\s*年")
# A number carrying a unit is a factual claim; a bare "two" usually is not.
UNIT_NUMBER_RE = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*"
    r"(years?\s+old|months?|weeks?|days?|hours?|minutes?|miles?|km|kilometres?|"
    r"kilometers?|metres?|meters?|feet|foot|inches|dollars?|yuan|pounds?|"
    r"o'clock|percent|%)",
    re.I,
)
CJK_UNIT_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(岁|元|块|公里|米|分钟|小时|天|个月|年级|层|号)")
BIG_NUMBER_RE = re.compile(r"\b(\d{3,})\b")
# Spelled-out numbers are claims too ("sixty-four", "three weeks"). Bare small
# words are skipped — "the quiet one" is not a quantity.
_UNITS = (r"years?\s+old|months?|weeks?|days?|hours?|minutes?|miles?|"
          r"kilometres?|kilometers?|metres?|meters?|dollars?|yuan|pounds?|"
          r"children|siblings|brothers?|sisters?|times?")
_ONES = ("one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
         "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen")
_TENS = "twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"
COMPOUND_WORD_NUM_RE = re.compile(rf"\b(({_TENS})[-\s]({_ONES}))\b", re.I)
UNIT_WORD_NUM_RE = re.compile(rf"\b(({_ONES}|{_TENS})\s+({_UNITS}))\b", re.I)
WORD_TO_DIGIT = {
    w: i for i, w in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
    )
}
WORD_TO_DIGIT.update({
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
})


def _number_word_value(phrase: str) -> str:
    """Digit form of a spelled number phrase, for cross-checking the corpus."""
    parts = re.split(r"[-\s]+", phrase.casefold())
    total = sum(WORD_TO_DIGIT[p] for p in parts if p in WORD_TO_DIGIT)
    return str(total) if total else ""
# Latin proper nouns: runs of capitalized words, captured with any leading title.
PROPER_RE = re.compile(r"\b([A-Z][a-z]{1,}(?:\s+[A-Z][a-z]{1,}){0,3})\b")
DIALOGUE_RES = [
    re.compile(r"[“]([^”]{4,})[”]"),   # “ ... ”
    re.compile(r"\"([^\"]{4,})\""),                     # " ... "
    re.compile(r"[「]([^」]{2,})[」]"),   # 「 ... 」
    re.compile(r"[『]([^』]{2,})[』]"),   # 『 ... 』
]
# Lines that are structure, not prose.
SKIP_LINE_RE = re.compile(r"^\s*(#{1,6}\s|<!--|\[.*\]:\s*http|\|)")


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    kind: str
    claim: str
    detail: str

    def render(self) -> str:
        return f"  {self.file}:{self.line}  [{self.kind}] {self.claim} — {self.detail}"


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def load_allowlist(workspace: Path) -> set[str]:
    path = workspace / ALLOW_FILE
    if not path.is_file():
        return set()
    out = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.add(normalize(line))
    return out


def build_corpus(sources: list[Path]) -> str:
    """All source material, normalized, as one searchable blob."""
    parts = []
    for root in sources:
        if root.is_file():
            parts.append(root.read_text(encoding="utf-8", errors="replace"))
        elif root.is_dir():
            for p in sorted(root.rglob("*")):
                if p.is_file() and p.suffix.lower() in {".md", ".txt"}:
                    parts.append(p.read_text(encoding="utf-8", errors="replace"))
    return normalize("\n".join(parts))


def _supported_token(token: str, corpus: str, allow: set[str]) -> bool:
    t = normalize(token).strip()
    return not t or t in allow or t in corpus


def _proper_noun_tokens(phrase: str) -> list[str]:
    """The identifying words of a name phrase (titles and ordinary words out)."""
    tokens = []
    for word in phrase.split():
        low = word.casefold().strip(".,;:!?")
        if low in TITLES or low in COMMON_CAPS or len(low) < 2:
            continue
        tokens.append(word.strip(".,;:!?"))
    return tokens


def extract_findings(
    text: str, filename: str, corpus: str, allow: set[str]
) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple] = set()

    def add(line_no: int, kind: str, claim: str, detail: str) -> None:
        key = (kind, normalize(claim))
        if key in seen:
            return          # report each distinct claim once per chapter
        seen.add(key)
        findings.append(Finding(filename, line_no, kind, claim, detail))

    in_fence = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or SKIP_LINE_RE.match(line):
            continue

        # Dialogue first, and remove it so its interior is not double-reported.
        remainder = line
        for pattern in DIALOGUE_RES:
            for match in pattern.finditer(line):
                said = match.group(1).strip()
                if normalize(said) in corpus or normalize(said) in allow:
                    continue
                add(line_no, KIND_DIALOGUE, f'"{said[:60]}"',
                    "quoted speech not recorded in memories — reconstructed; "
                    "disclose in the author's note")
            remainder = pattern.sub(" ", remainder)

        for match in YEAR_RE.finditer(remainder):
            year = match.group(1)
            if not _supported_token(year, corpus, allow):
                add(line_no, KIND_UNSUPPORTED, year, "year not found in memories")
        for match in CJK_YEAR_RE.finditer(remainder):
            year = match.group(1)
            if not _supported_token(year, corpus, allow):
                add(line_no, KIND_UNSUPPORTED, f"{year}年", "year not found in memories")

        for regex in (UNIT_NUMBER_RE, CJK_UNIT_NUMBER_RE):
            for match in regex.finditer(remainder):
                claim = match.group(0).strip()
                if not _supported_token(match.group(1), corpus, allow) and \
                        normalize(claim) not in corpus:
                    add(line_no, KIND_UNSUPPORTED, claim,
                        "quantity not found in memories")

        for match in BIG_NUMBER_RE.finditer(remainder):
            number = match.group(1)
            if YEAR_RE.fullmatch(number):
                continue
            if not _supported_token(number, corpus, allow):
                add(line_no, KIND_UNSUPPORTED, number,
                    "number not found in memories")

        for regex in (COMPOUND_WORD_NUM_RE, UNIT_WORD_NUM_RE):
            for match in regex.finditer(remainder):
                claim = match.group(1).strip()
                words = match.group(2)
                digits = _number_word_value(words if regex is UNIT_WORD_NUM_RE
                                            else claim)
                if normalize(claim) in corpus or normalize(claim) in allow:
                    continue
                if _supported_token(words, corpus, allow):
                    continue
                if digits and _supported_token(digits, corpus, allow):
                    continue
                add(line_no, KIND_UNSUPPORTED, claim,
                    "quantity not found in memories")

        for match in PROPER_RE.finditer(remainder):
            phrase = match.group(1)
            if match.start() == 0 and len(phrase.split()) == 1:
                continue                      # sentence-initial single word
            for token in _proper_noun_tokens(phrase):
                if not _supported_token(token, corpus, allow):
                    add(line_no, KIND_UNSUPPORTED, token,
                        "name not found in memories")
    return findings


def lint_workspace(
    workspace: Path,
    chapters_dir: Path | None = None,
    memories_dir: Path | None = None,
) -> list[Finding]:
    chapters = chapters_dir or workspace / "chapters"
    memories = memories_dir or workspace / "memories"
    if not chapters.is_dir():
        raise SystemExit(f"no chapters directory to check: {chapters}")
    corpus = build_corpus([memories])
    allow = load_allowlist(workspace)

    findings: list[Finding] = []
    for path in sorted(chapters.rglob("*.md")):
        if path.name == "authors_note_flags.md":
            continue
        rel = path.relative_to(chapters).as_posix()
        findings += extract_findings(
            path.read_text(encoding="utf-8", errors="replace"), rel, corpus, allow
        )
    return findings


def render(findings: list[Finding], as_json: bool = False) -> str:
    if as_json:
        return json.dumps([asdict(f) for f in findings], indent=2, ensure_ascii=False)
    if not findings:
        return ("truth-contract lint: no unsupported details found.\n"
                "(Heuristic check — it confirms nothing, it only finds things to confirm.)")
    unsupported = [f for f in findings if f.kind == KIND_UNSUPPORTED]
    dialogue = [f for f in findings if f.kind == KIND_DIALOGUE]
    lines = ["truth-contract lint — details to confirm before publishing:", ""]
    current = None
    for f in findings:
        if f.file != current:
            current = f.file
            lines.append(f"{current}:")
        lines.append(f.render())
    lines += [
        "",
        f"{len(unsupported)} unsupported detail(s), "
        f"{len(dialogue)} reconstructed line(s) of dialogue.",
        "These are prompts for the writer, not verdicts: confirm each one, or add "
        "it to .memoir/lint-allow.txt if it is yours and simply unwritten.",
    ]
    return "\n".join(lines)
