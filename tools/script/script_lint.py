"""Script lint: the script gate. Flags the lines that sound like AI narration, a reporter or a vague writer before they're voiced.
Every check is a mistake that kept coming back in real script reviews, and each flag names the reason. It flags; a human-sounding
exception can stay, but each flag is read. Tests: tools/script/tests/test_script_lint.py.

  PIPE tools/script/script_lint.py <script.md | text file> [--all] [--strict] [--json <out.json>]
      [--ignore 12,15] [--against earlier|all] [--no-copies] [--format long|short]

Reads the [Sxx] VOICE: lines of a script.md's newest Beats block (older versions below it are history; or every line of a text file) and
prints, per flagged line, the beat, the rule and the words; then the whole-script numbers (sentence lengths and the rest: a
measure to read, not a target band).

The checks, by the mistake they catch:
  wording   announcer lines, "X? Y." beats, "And honestly", stock AI lines, writerly irony, boasts, hedges ("reportedly", "who knows"),
            "literally" twice, long sentences (over 45 words), nerd and finance words (a fan talking, not a reporter)
  vague     a count without its noun ("makes it two", "they put out one"), "this time" / "the other one", "the product" / "the story"
            with no name in the line, a role where a name belongs, a change with no subject, a bare pronoun opening a section, a
            number with no owner, a money word with no figure ("plus its debts"), a descriptor said as of today inside a dated line
            ("Acme, the company behind the best-selling phone" in a line set in 2008)
  point     a big number stated without its point: no comparison, rate or consequence in its line or the next ("$38 billion" without
            "19 times the first offer, so it was the right call")
  opinion   an opinion line whose words share nothing with the three lines before it (the take lands after an unrelated line; a take
            that continues a take is fine); a long video with no take of the creator's at all
  copies    a line also in an earlier video's script: the same sentence, a shared run of six words, four or more shared content words
            that make up most of the shorter line, or nearly the same words; the channel's own recurring lines (channel_lines) pass;
            --ignore <ids> for a prototype that became the film; --against all to include later videos too
  time      "just" as recency, yesterday/today/this week, "right now", "currently", "recently", "latest", "breaking" (a video is
            watched for years: timeless wording)
  shape     the sub ask before 35% of the words; chapter cards in a topic video; a stretch of 20 lines where 40%+ open on a date, the
            timeline of a report, and no line announcing the rundown ("before we talk about what's next, let me quickly ..."); a
            reporter's share of said/told/says lines (over 25%); no I/you in a long video (nobody in the room); a long video not
            ending on the sign-off word (sign_off_words); a Short's hook with no name; one opener on over 15% of lines
  search    the word search of standard/SCRIPTS_AND_PACKAGING.md ("a <thing>", "the <thing>", "someone", "a company", just, now,
            today, this week, recently, latest, breaking, literally, honestly, favorite line, wild, crazy, the funny part, "?", kill):
            the counts and their beats, printed every run

--strict exits 1 when anything is flagged (the gate in tools/pipeline/pipe.py). --json writes every flag and number for the gate's
report. --format defaults from the folder name ("short" in it = a Short); a Short skips the long-form shape checks.

The niche's own words live in tools/script/niche.json (empty lists when the repo ships; the creator's chat fills them as the niche's
scripts get reviewed). Every key is optional:
  niche           a few words naming the niche, for the blind judges' brief ("home cooking"): a string
  names           the niche's big names (brands, people, titles) as written: they count as names anywhere in a line
  subject_names   the one name most scripts are about: its rate per 1,000 words is checked (real creators say it about 1.35 times)
  things          the niche's own nouns for its subject ("recipe", "phone"): "a certain <thing>", "the <thing>" with no name, the search
  audience_roles  the niche's audience words ("one <role> said ..." credits a stranger)
  site_kinds      "the <kind> site": an outlet credited by its kind
  nerd_words      the niche's jargon a casual viewer never says
  flagged_lines   regular expressions of stock lines the creator flagged (each one fails the gate)
  channel_lines   regular expressions of the channel's own recurring lines (intro, sub ask, sign-off): never a copy, never vague
  universal       words every script of the niche shares (no evidence of a copied line)
  sign_off_words  the word a long video ends on ("Cheers"): the last line must end on one of them
  source_names    outlets and people the niche quotes (tools/script/voice_metrics.py counts "<source> says")
  gloss_nouns     nouns the niche glosses in an add-on (tools/script/tell_lint.py)"""
import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import VIDEOS_REPO  # noqa: E402

HERE = Path(__file__).resolve().parent
VIDEOS = VIDEOS_REPO
NICHE_FILE = HERE / "niche.json"


def _load_niche():
    try:
        d = json.loads(NICHE_FILE.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


NICHE = _load_niche()


def niche_words(key):
    v = NICHE.get(key) or []
    return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []


def alt(words):
    """An alternation of the words, longest first, each escaped (empty string for none)."""
    return "|".join(re.escape(w) for w in sorted(set(words), key=len, reverse=True))


def regexes(key):
    """The key's entries as regular expressions; one that does not compile is skipped with a warning."""
    out = []
    for rx in niche_words(key):
        try:
            re.compile(rx)
            out.append(rx)
        except re.error as e:
            print(f"niche.json {key}: skipped {rx!r} ({e})", file=sys.stderr)
    return out


THINGS = niche_words("things")
T_ALT = alt(THINGS)
TH = "product" + ("|" + T_ALT if T_ALT else "")          # the subject nouns: a generic one, then the niche's own
SIGN = niche_words("sign_off_words")
SIGN_ALT = alt(SIGN)
SUBJECT = niche_words("subject_names")

ANNOUNCER = (r"\b(here'?s the (crazy|wild|weird|funny|best|interesting|scary|insane|kicker|catch|thing|twist)|this is where it gets|"
             r"and that'?s not even|it gets (even )?(crazier|wilder|better|worse)|let that sink in|buckle up|"
             r"(the )?(craziest|wildest|funniest|best|scariest) part( is| was)?\s*[.?!:]|(the )?(craziest|wildest|funniest|scariest) part$|"
             r"you won'?t believe|think about (that|what that means)|and what happened (next|there)|"
             r"was wild|got wild|is wild|that'?s insane|that'?s crazy|my favou?rite (part|detail|shot))")
ROLES = "writer|journalist|reporter|critic|reviewer|redditor|streamer|youtuber|fan|guy|person|user|blogger|analyst" + \
    ("|" + alt(niche_words("audience_roles")) if niche_words("audience_roles") else "")
SITES = "tech|news" + ("|" + alt(niche_words("site_kinds")) if niche_words("site_kinds") else "")
FLAGGED = regexes("flagged_lines")
NERD = niche_words("nerd_words")
RULES = [
    # (name, regex, reason). Every regex runs case-insensitively on one VOICE line.
    ("an unimportant source credited: 'one writer / a journalist / one user / a site said'. Say the fact itself, and a common "
     "experience as the viewer's own ('you'd wait about forty minutes'), never one stranger's story",
     rf"\b(one|a|another|some|this)\s+(?:{ROLES})s?\b[^.?!]{{0,60}}\b(said|says|wrote|writes|found|worked out|posted|reported|told|tweeted|"
     r"made|lost|earned|got|spent|counted|tested|asked)\b|\b(according to|as reported by|per)\s+(a|one|the)?\s*(site|outlet|report|"
     rf"writer|journalist|user|post)\b|\bthe (?:{SITES}) site\b",
     "one stranger's word makes the viewers feel left out, as if millions had not seen it for themselves"),
    ("announcer: a line that announces the next line", ANNOUNCER,
     "the textbook AI-narration tell; the same words can stay when they carry the point, not when they only announce"),
    ("'not just X, it's Y' / restating for emphasis", r"\bnot just [^.?!]{1,40}[,.]\s*(it'?s|but|it is)\b|\bnot just [a-z ]+\. [A-Z][a-z]+ [a-z]+\.",
     "restating for emphasis reads as AI narration"),
    ("topic fragment + '?' then the answer ('X? Y.')", r"(^|[.!?]\s)(\w+(\s\w+){0,3})\?\s+[A-Z]", "the AI beat: a fragment asked, then answered"),
    ("a spoken question with a comma inside (the voice builds up, then the last word hangs)", r"(^|[.!?]\s+)[^.!?]*,[^.!?]*\?",
     "a cloned voice lifts toward the question mark, so the words after the comma come out strangled"),
    ("'And honestly' / 'honestly' as a filler", r"\b(and )?honestly,|^honestly\?", "a filler that reads as AI narration"),
    ("writerly irony clause", r"\blike that was the (good|best|bad) news\b|\bif that makes sense\b|\bin a way\b|\bwhich is kind of hilarious\b",
     "written irony, not how people talk"),
    ("time words: not timeless", r"\b(just (dropped|released|came out|announced|revealed|got (delayed|pushed|cancelled|canceled|confirmed|leaked))|"
     r"yesterday|tomorrow|tonight|this (week|month|year|fall|summer|winter|spring|weekend|morning)|right now|currently|recently|latest|breaking|"
     r"as of (now|today)|(?<!still )(?<!till )(?<!until )today)\b", "a video is watched for years; time words date it"),
    ("words that hurt ad suitability", r"\b(kill(s|ed|ing)?|porn|sex|naked|nude|suicide|jew\w*)\b", "these words limit ads on the video"),
    ("announcing self-insert ('like I did', 'definitely gonna be one of')", r"\blike I did\b|\bI'?m definitely gonna be one of\b",
     "a self-insert that announces itself rings false"),
    ("vague future: predictions are said boldly", r"\bremains to be seen\b|\bonly time will tell\b|\bwho knows( what| if| how|\.|,|$)|\bwe'?ll (have to )?(see|find out)\b",
     "real creators say what they think will happen"),
    ("boomer/coy phrasing", r"\byou know exactly what I mean\b|\bquestionable\b|\bthe whole internet\b|\beveryone'?s losing (their|it)",
     "coy or dated phrasing"),
    ("stock AI line", r"\bthat'?s the energy\b|\byou can already see it happening\b|\bmy favou?rite line (was|is)\b|"
     r"\bthey just got it wrong\b|\blazy writing\b|\bactually holds up\b|\bbroke the internet\b|\bthe internet (is|went) (crazy|wild|nuts)\b|"
     r"\bI understand where (that|this) comes from\b|\bnot saying (that|this) to rage.?bait\b|\battention buzz ?saw\b|\beither way\b\.?$|"
     r"\bso for once\b|\bwhat a time to be alive\b|\bgame.?changer\b" + "".join("|" + rx for rx in FLAGGED),
     "stock lines flagged in reviews"),
    ("vague where a name belongs", rf"\ba (?:{TH}) that isn'?t (even )?out yet\b|\ba real (city|place|company)\b|\bone (?:{TH}|company|studio)\b(?! (of|at a time))|"
     rf"\ba certain (?:{TH}|company|studio|city|song)\b|\bsome (?:{TH}|company|studio|song)\b|\ban? (?:{TH}) called\b|"
     r"\ba (company|studio|publisher) (in|from) the (US|UK|states)\b|\b(an|one) (?:NBA|NFL|NHL|MLB) team\b|\bone song\b|\bsome people\b|"
     r"\ba (big|major) (studio|company|publisher)\b",
     "vagueness where the name is known loses the viewer: say the name"),
    ("nerd wording for a normie", r"\bin terms of\b|\butili[sz]e\b|\bnumerous\b|\bapproximately\b|\bneurodivergent\b|\bmarket cap\b" +
     "".join(r"|\b" + re.escape(w) + r"\b" for w in NERD), "a casual viewer never says these"),
    ("a finance word: say it the way the viewer would", r"\b(revenue|bookings|fiscal( year)?|shareholders?|valuation|quarterly|portfolio|monetiz\w+|"
     r"intellectual property|headcount|workforce|restructur\w+|consolidat\w+|stakeholders?|operating (income|margin|profit)|guidance|year-over-year"
     + (rf"|the (?:{T_ALT})s? (?:sector|market)" if T_ALT else "") + r")\b",
     "a fan in the room, not an analyst on a finance channel"),
    ("a change with no subject: say what grew, with the numbers", r"\b(doubled|tripled|quadrupled|halved|shrank|grew)( in size)?\b(?! (its|the|their|his|her) "
     r"(staff|employees|team|workforce|budget|price|sales|users|viewers|revenue))(?! up)|\bin size\b",
     "'doubled in size' says nothing: 'twice as many employees' does"),
    ("a count without its noun: say what it counts ('their second album, Low Tide')", r"\bmakes? it (one|two|three|four|five|six|\d+)\b(?! (clear|easy|hard|look|seem|so))|"
     r"\bthat makes (one|two|three|four|five|\d+)\b|\b(put out|released|made|got|shipped) (one|two|three|four|five)\s*[.,;!?]|\bthe (first|second|third) one\s*[.,;!?]",
     "'they put out one ... it finally makes it two' leaves the listener counting: 'their second album in nine years'"),
    ("'this time' / 'the other one': say which, by its name", r"\bthis time\b(?! (around|last year|in \d))|\bthe (next|other|last) one\b",
     "'I think this time, the show gets a second season' -> say which one, by its name"),
    ("a definition tacked onto a term: explain few terms, from the picture or the problem",
     r"(?:,|\band) (?:which|that)(?:'s| is| are) (?:called|basically)\b|\bthat'?s called\b|\b(?:it'?s|is|are) called\b|"
     r"\bthe (?:fancy |long |official |technical )?(?:name|word|term) for (?:that|this|it)\b|\ba (?:trick|technique|thing|system) called\b",
     "blind judges flag term-then-gloss as AI writing"),
    ("an 'isn't X, it's Y' reveal: say the thing itself", r"\b(?:isn'?t|wasn'?t|aren'?t|doesn'?t|not) (?:even |really |just )?[a-z]+(?: [a-z]+){0,4}[.,;]\s+(?:it'?s|that'?s|they'?re|the [a-z]+ (?:is|are))\b"
     r"|\bnot [a-z]+(?: [a-z]+)?, not [a-z]+(?: [a-z]+)?, (?:just|only|but)\b",
     "negative parallelism runs at many times the human rate in AI text"),
    ("a hedge: the news is the story, told straight", r"\breportedly\b|\ballegedly\b|\bsupposedly\b|\bunconfirmed\b|\bif (this is|it'?s|that'?s) (even )?true\b|\bgrain of salt\b|"
     r"\bnobody (has )?confirmed\b|\bnothing is official\b|\bapparently\b",
     "hedges make a story weaker; check the fact, then say it straight"),
    ("a fact check's doubt in the voice: say the fact straight or leave it out", r"\bat least (?:that'?s|for now)\b|"
     r"\b(?:called|named|known as|labell?ed)\b[^.?!]{0,40}\bfor now\b|\bfor now,? at least\b|\bas far as (?:we|anyone) know\b|"
     r"\b(?:it|this|that) (?:could|might|may) (?:still )?change(?=\s*(?:before|by) (?:launch|release)\b|\s*[.;!?]|\s*$)",
     "'at least that's what they're called for now' leaves the viewer asking what 'for now' means"),
    ("a definition wedged inside a clause: finish the clause, then explain in its own sentence",
     r",\s+(?:that'?s|which is|which are|aka|meaning)\s+(?:the|a|an|basically|some)\b[^.?!,]{3,60},\s+(?!and\b|but\b|so\b|or\b|then\b)[a-z]+",
     "'until the broker, that's the person who sells the house, signs the papers': the listener loses the clause"),
]
NAME_ROLE = re.compile(r"\bthe (boss|head|ceo|chief|owner|founder|president|chairman) of the (company|studio|publisher|firm|business)\b|"
                       r"\bthe (company|studio|firm|publisher) (that|which|who) (owns|makes|made|runs|publishes)\b|"
                       r"\bthe (studio|company|publisher|developer) behind\b|\bthe parent company\b|\bthe (man|guy|woman|people) (behind|in charge)\b", re.I)
COUNTED = (r"(?-i:(?<![A-Z]\w )(?<![A-Z]\w\w )(?<![A-Z]\w\w\w )(?<![A-Z]\w\w\w\w )(?<![A-Z]\w\w\w\w\w )(?<![A-Z]\w\w\w\w\w\w )(?<![A-Z]\w\w\w\w\w\w\w ))"   # "Apollo 11", "Chapter 2": a name's number
           r"\b(?!(?:19|20)\d\d\b)(\d[\d,.]*|one|two|three|four|five|six|seven|eight|nine|ten|twelve|thirteen|fifteen|twenty|thirty|forty|fifty|"
           r"hundred|thousand|million|billion)\b(?![- ]?(years?|months?|weeks?|days?|hours?|minutes?|seconds?|times)\b)")   # years and durations aren't counts
_NAMES = alt(niche_words("names") + SUBJECT)
NAMED = r"\b(" + (_NAMES + "|" if _NAMES else "") + r"[A-Z][a-z]+[A-Z]\w*|[A-Z]{2,}\w*)\b"
BIG_NUMBER = re.compile(r"\b(million|billion|thousand|hundred thousand|\d{1,3}(,\d{3}){1,}|\d+(\.\d+)?\s*%|percent|per cent|\$\s?\d)", re.I)
POINT = re.compile(r"\b(than|times|twice|double|triple|half|as (many|much|big|fast|long)|more|less|fewer|almost|nearly|over|under|only|just|"
                   r"that'?s|which (is|means|was)|so|because|enough|every|per|out of|compared|same|record|first|fastest|biggest|most|never|ever|"
                   r"still|already|while|but|even|in (one|two|three|four|five|six|seven|eight|nine|ten|\d+) (days?|hours?|weeks?|months?|minutes?)|"
                   r"a (day|year|week|month)|each|alone|up|down|instead|worth it|right|wrong)\b", re.I)
MONEY_NOUN = re.compile(r"\b(debts?|loans?|fines?|bonus(es)?|salar(y|ies)|budget|a fortune|losses|profits?|damages)\b", re.I)
NUMBER_WORD = re.compile(r"\b(\d[\d,.]*|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fifteen|twenty|thirty|forty|fifty|sixty|"
                         r"seventy|eighty|ninety|hundred|thousand|million|billion|half|dozen)\b|[$€£]", re.I)
OPINION = re.compile(r"\b(I think|I believe|I don'?t think|I'?d (be|say|bet|rather|love|want)|I'?m (down|glad|curious|sure|not sure|pretty sure|hoping)|my bet|"
                     r"to me,|in my opinion|I hope|I can('t| not)? see|I don'?t see|I (just )?(wouldn'?t|would) (bet|trust|be surprised)|I feel like|"
                     r"I'?m calling it|if you ask me|personally)\b", re.I)
DESCRIPTOR_TODAY = re.compile(r"\bthe (company|studio|people|publisher|maker|makers|team|guys|label) behind\b|\b(known|famous) for\b|\bthe (makers?|creators?) of\b", re.I)
PAST_YEAR = re.compile(r"\b(19\d\d|20[01]\d|202[0-3])\b")
BARE_PRONOUN = re.compile(r"^(It|This|That|They|These|Those)('s|'re|'ve|'ll|'d)?\b(?=\s*(,|is|was|were|are|has|had|have|got|went|did|does|do|made|took|can|could|"
                          r"will|would|also|still|never|even|all|both|starts?|started|explained|made|became|came|kept|put|say|said|told))(?!'s it for me)", re.I)
DATE_OPENER = re.compile(r"^(in|by|back in|around|since|until|that same|the same|a year|two years|three years|five years|a (few )?(months?|weeks?|years?) (later|after|before)|"
                         r"then,? in|and (in|by) (19|20)\d\d|on (january|february|march|april|may|june|july|august|september|october|november|december|"
                         r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)|(19|20)\d\d)\b", re.I)
ATTRIBUTION = re.compile(r"\b(said|says|saying|told|tells|according to|reports?|reported|expects?|expected|estimated|announced|called it|compared|"
                         r"confirmed|revealed|claims?|claimed|pointed (to|out)|wrote|writes|asked)\b", re.I)
SUB_ASK = re.compile(r"\b(subscrib\w+|a sub (would|helps)|hit (the )?subscribe|sub would help)\b", re.I)
SIGN_OFF = re.compile(r"that'?s it for me|if you enjoyed|a like helps|see you in the next|tell me in the comments|let me know in the comments|"
                      r"subscrib|a sub would|comment (down )?below" + (rf"|(?:{SIGN_ALT})\.?$" if SIGN_ALT else ""), re.I)
RUNDOWN_ANNOUNCED = re.compile(r"\b(before we (talk|get|go|dive|start)|let me (quickly|real quick|first)|real quick,? here'?s|in a nutshell|quick (rundown|recap|summary)|"
                               r"a quick (rundown|recap|look|history)|to catch (you|everyone) up|so (you|everyone)'?s on the same page|here'?s the short version)\b", re.I)
WORD_SEARCH = [  # the word search of standard/SCRIPTS_AND_PACKAGING.md: searched on every script, counts printed, the strong ones are rules above
    ("a <thing>", rf"\ba (?:{TH})\b(?! (called|about|like|where|you|that|of))"),
    ("the <thing>", rf"\bthe (unfinished |new |whole |full |same |actual |real )?(?:{TH})\b"),
    ("someone", r"\bsomeone\b"), ("a company", r"\ba (company|studio)\b(?! (called|that|in|from|named))"), ("just", r"\bjust\b"), ("now", r"\bnow\b"),
    ("today", r"\btoday\b"), ("this week", r"\bthis (week|month|year)\b"), ("recently", r"\brecently\b"), ("latest", r"\blatest\b"), ("breaking", r"\bbreaking\b"),
    ("literally", r"\bliterally\b"), ("honestly", r"\bhonestly\b"), ("favorite line", r"\bfavou?rite (line|part)\b"), ("wild", r"\bwild\b"), ("crazy", r"\bcrazy\b"),
    ("the funny part", r"\bthe (funny|crazy|best) part\b"), ("?", r"\?"), ("kill", r"\bkill\w*\b"),
]
STOP = set("""a an the and or but so to of in on at for from by with as is are was were be been being it its it's this that these those they them their there
here he she his her him we our you your i i'm i'd i'll me my not no yes do does did done have has had having will would can could should may might must
if then than too very just also even still more most less own same other another one all any each every some such what which who whom whose when where
why how up down out over under again further off about into through during before after above below between because while until against get got gets
gonna going go went come came like way thing things lot bit really actually basically kind sort pretty much many well okay ok right now let let's us
almost nearly only ever never already yet back first second last next new old big long time year years day days week weeks month months
zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty
fifty sixty seventy eighty ninety hundred thousand million billion dozen half something anything nothing everything someone anyone everyone
don't doesn't didn't isn't wasn't won't can't couldn't wouldn't shouldn't aren't weren't haven't hasn't ain't it's that's there's they're we're you're
i'm i'd i'll he's she's let's gonna wanna gotta""".split())
LOOK = ("an opinion with no lead-in", "a big number stated without its point", "long sentence for the voice", "a line also in")   # read, not fail
UNIVERSAL = {"video", "think", "believe", "see", "want", "feel", "glad", "curious", "down", "sure", "hope", "bet", "say", "mean", "know", "guess"}
for _w in niche_words("universal") + niche_words("names") + SUBJECT + THINGS:   # the niche's shared words are no evidence of a copy
    UNIVERSAL |= {t.strip("'") for t in re.sub(r"[^a-z0-9' -]+", " ", _w.lower()).replace("-", " ").split()} | {_w.lower()}
RELATIVE_TIME = re.compile(r"^(that same year|the same year|a year (later|earlier|after|before)|(two|three|four|five|six|seven|eight|nine|ten) years (later|after|before)|"
                           r"back then|at the time|a (few )?(months?|weeks?) later|then,? in)\b", re.I)
STOCK_LINE = re.compile(r"that'?s it for me|if you'?re enjoying|if you enjoyed|a (like|sub) (helps|would)|see you in the next|tell me in the comments|"
                        r"let me know in the comments|comment your favou?rite|subscrib" + (rf"|^(?:{SIGN_ALT})\.?$" if SIGN_ALT else "") +
                        "".join("|" + rx for rx in regexes("channel_lines")), re.I)


def norm_tokens(s):
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return [t.strip("'") for t in s.split() if t.strip("'")]


def stem(t):
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    for suf in ("sses", "shes", "ches", "xes"):
        if t.endswith(suf):
            return t[:-2]
    if t.endswith("ing") and len(t) > 5:
        return t[:-3]
    if t.endswith("ed") and len(t) > 4:
        return t[:-2]
    if t.endswith("s") and not t.endswith("ss") and len(t) > 3:
        return t[:-1]
    return t


def content_words(s):
    return {stem(t) for t in norm_tokens(s) if t not in STOP and t not in UNIVERSAL and not t.isdigit() and len(t) > 1}


def unowned_number(sentence):
    """A count with no named owner in its own sentence ('forty million units' of what?). A capital on the first word is only the
    sentence's start ('Analysts'), so plain capitalised words count from the second word on; known names (niche.json) anywhere."""
    if not re.search(COUNTED, sentence, re.I) or re.search(NAMED, sentence):
        return False
    rest = sentence.split(" ", 1)[1] if " " in sentence else ""
    return not re.search(r"\b[A-Z][a-z]+\b", rest)


def has_name(text):
    """A proper name anywhere but the first word (a known name, an all-caps or camel-case name, a capitalised word)."""
    rest = text.split(" ", 1)[1] if " " in text else ""
    return bool(re.search(NAMED, text) or re.search(r"\b[A-Z][a-z]+\b", rest))


def name_before(text, pos):
    """A name in the three tokens before a role phrase ('Acme, the company that owns Brightline' names it: the name is there)."""
    toks = text[:pos].split()
    before = [(k, w.strip(",.;:()")) for k, w in enumerate(toks)][-3:]
    # the text's first word is capitalised anyway ("He is the boss ..."): it counts only as a known name
    return any(re.match(r"[A-Z][\w'-]+$|[A-Z]{2,}$", w) and (k > 0 or re.match(NAMED, w)) for k, w in before if w)


def parse_block(text):
    """The newest Beats block of a script.md (older versions below it are history): [(beat, text, starts_a_section)], from the lines
    before the second '## Beats' or '## v<N>' heading when the file has one. A '# =====' line between two VOICE lines marks a section."""
    m = list(re.finditer(r"^## (Beats|v\d+ )", text, re.M))
    if len(m) >= 2:
        text = text[: m[1].start()]
    out, pending = [], True
    for ln in text.splitlines():
        if re.match(r"^# =====", ln) or re.search(r"\bchapter=", ln):
            pending = True
            continue
        mm = re.match(r"^\[(S\w+)\] VOICE: (.*)$", ln)
        if mm:
            out.append((mm.group(1), re.sub(r"\*([^*]+)\*", r"\1", mm.group(2)).strip(), pending))
            pending = False
    return out


def load_lines(path):
    raw = Path(path).read_text(encoding="utf-8")
    block = parse_block(raw)
    if block:
        return block, raw
    return [(f"L{i + 1}", ln.strip(), i == 0) for i, ln in enumerate(raw.splitlines()) if ln.strip()], raw


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


# ----------------------------------------------------------------------------------------------------------------------------------- copies
def other_scripts(this_path, ignore, against):
    """Other videos' VOICE lines (all versions in each file): [(video id, beat, text)]; by default only videos with a lower number
    (the earlier ones: a later video that copied this one is its problem, not this script's)."""
    out = []
    this = Path(this_path).resolve()
    this_id = this.parent.name[:3] if VIDEOS.exists() and this.parent.parent == VIDEOS.resolve() else None
    for p in sorted(VIDEOS.glob("*/script.md")) if VIDEOS.exists() else []:
        vid = p.parent.name[:3]
        if p.resolve() == this or vid in ignore:
            continue
        if against == "earlier" and this_id and this_id.isdigit() and vid.isdigit() and int(vid) >= int(this_id):
            continue
        for b, s in re.findall(r"^\[(S\w+)\] VOICE: (.*)$", p.read_text(encoding="utf-8"), re.M):
            out.append((vid, b, re.sub(r"\*([^*]+)\*", r"\1", s).strip()))
    return out


def ngrams(toks, n):
    return {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def copies(lines, others):
    """Lines also in another script. Each sentence of 6+ tokens against every other such sentence: the same tokens; a shared run of six
    words with three content words in it (names and numbers don't count: 'Acme, the company that owns Brightline' is the naming rule's
    own phrasing, not a copy); four or more shared content words that are 65%+ of the shorter sentence's; or nearly the same words
    (difflib 0.8+). The channel's own recurring lines pass."""
    index = []
    for vid, b, s in others:
        for sent in sentences(s):
            toks = norm_tokens(sent)
            if len(toks) >= 6:
                index.append((vid, b, sent, toks, ngrams(toks, 6), content_words(sent)))
    hits = {}
    for beat, text in lines:
        if STOCK_LINE.search(text):
            continue
        for sent in sentences(text):
            toks = norm_tokens(sent)
            if len(toks) < 6:
                continue
            g6, cw = ngrams(toks, 6), content_words(sent)
            for vid, b, osent, otoks, og6, ocw in index:
                shared6 = [g for g in g6 & og6 if len(content_words(g)) >= 3]
                shared = cw & ocw
                if toks == otoks:
                    why = "the same sentence"
                elif shared6:
                    why = f"shares '{sorted(shared6, key=len)[-1]}'"
                elif len(shared) >= 5 and len(shared) >= 0.65 * max(1, min(len(cw), len(ocw))):
                    why = "the same words: " + ", ".join(sorted(shared)[:6])
                elif len(toks) >= 8 and difflib.SequenceMatcher(None, toks, otoks).ratio() >= 0.8:
                    why = "nearly the same words"
                else:
                    continue
                hits.setdefault(beat, []).append((f"also in {vid} {b} ({why})", osent[:110]))
                break
    return hits


# ----------------------------------------------------------------------------------------------------------------------------------- the lint
# a beat that opens on "that/this + a thing" points at something the listener may not have: "That recipe is their own" right after an
# opinion, long after the recipe was last mentioned and before it was ever named
DEMONSTRATIVE = re.compile(r"(that|this|these|those)\s+(?!(?:is|was|are|were|means|meant|will|would|could|can|did|does|happens|happened|same|year|day|night|time|week|month|summer|way|one|ones|much|many|kind|part)\b)([a-z]+)\b", re.I)
THE_THING = re.compile(rf"\bthe (story|studio|company|series|team|show|brand|{TH})\b", re.I)


def lint(path, fmt=None, ignore=(), check_copies=True, against="earlier"):
    lines3, raw = load_lines(path)
    lines = [(b, t) for b, t, _ in lines3]
    starts = {b: s for b, _, s in lines3}
    is_short = (fmt == "short") if fmt else ("short" in Path(path).parent.name.lower())
    out_lines, flags = [], 0
    texts = [t for _, t in lines]
    words_total = max(1, sum(len(t.split()) for t in texts))
    copy_hits = copies(lines, other_scripts(path, set(ignore), against)) if check_copies and Path(path).suffix == ".md" else {}
    for i, (beat, text) in enumerate(lines):
        hits = []
        stock = bool(STOCK_LINE.search(text))
        for n, rx, src in RULES:
            if stock and n.startswith(("'this time'", "a count without")):
                continue
            for m in re.finditer(rx, text, re.I):
                hits.append((n, m.group(0), src))
        for m in NAME_ROLE.finditer(text):
            if not name_before(text, m.start()):
                hits.append(("a role where a name belongs: say who, with the name", m.group(0),
                             "'the boss of the company that owns the brand' -> the person's name, then the role"))
        m = THE_THING.search(text)
        if m and not has_name(text) and not stock:
            hits.append(("'the product' / 'the story' with no name in the line: name it (its name, its story)", m.group(0),
                         "a listener who just tuned in can't tell which one"))
        if starts.get(beat) and BARE_PRONOUN.match(text) and i > 0:
            hits.append(("a bare pronoun opens a new section: a listener who just tuned in can't tell what it is", BARE_PRONOUN.match(text).group(0),
                         "a new section starts on the name"))
        dm = DEMONSTRATIVE.match(text)
        if dm and i > 0 and not stock:
            hits.append(("a line opens on 'that/this + a thing': name the thing the first time (its name, what it is) and say how it follows "
                         "the line before", dm.group(0), "'That recipe is their own' before the recipe was ever named"))
        dated = PAST_YEAR.search(text) or (RELATIVE_TIME.match(text) and i > 0 and PAST_YEAR.search(texts[i - 1]))
        for m in DESCRIPTOR_TODAY.finditer(text):
            if dated and not re.search(r"\b(was|were) (known|famous) for\b|\bat (the|that) time\b|\bback then\b", text, re.I):
                hits.append(("a descriptor said as of today in a dated line: 'who was known for X at that time'", m.group(0),
                             "'Acme, the company behind the best-selling phone' in a line set in 2008 sounds like today"))
        sents = sentences(text)
        for s in sents:
            for clause in re.split(r"[,;:]", s):   # 'For one pound, plus its debts': the debts' clause has no figure
                for m in MONEY_NOUN.finditer(clause):
                    if not NUMBER_WORD.search(clause[:m.start()] + " " + clause[m.end():]):
                        hits.append(("a money word with no figure: say how much", m.group(0),
                                     "'plus its debts' leaves the listener asking how much"))
        nxt = texts[i + 1] if i + 1 < len(texts) else ""
        for k, s in enumerate(sents):
            prev_named = k > 0 and has_name(sents[k - 1])
            if unowned_number(s) and not prev_named and not stock:
                hits.append(("a number with no owner in its sentence: say whose it is (the product's sales, the company's staff)", s[:70],
                             "'Analysts expect forty million units' is heard as the wrong thing's size"))
            if len(s.split()) > 45:
                hits.append(("long sentence for the voice (over 45 words: more than one breath)", f"{len(s.split())} words: {s[:60]}...",
                             "standard/SCRIPTS_AND_PACKAGING.md 'The rhythm' (no ~10-word band: sentence lengths vary by meaning)"))
            if BIG_NUMBER.search(s) and not POINT.search(s) and not POINT.search(nxt) and not OPINION.search(s):
                hits.append(("a big number stated without its point: what does it mean (times, than, so)", s[:80],
                             "'$38 billion' alone means nothing: 'the first offer was 2 billion, now it's worth 19 times that, so it was the right call'"))
        if OPINION.search(text) and i > 0 and not OPINION.search(texts[i - 1]) and len(content_words(text)) >= 2:
            # a take led in by its own line's first sentence ("The rebuild took two years. But ... I think it was worth it") is led in
            led_in_line = sents and not OPINION.search(sents[0])
            prev = " ".join(texts[max(0, i - 3):i])
            if not led_in_line and not (content_words(text) & content_words(prev)):
                hits.append(("an opinion with no lead-in: the lines before it share nothing with it", OPINION.search(text).group(0),
                             "a take right after an unrelated line has no correlation with what was just said"))
        if len(re.findall(r"\bliterally\b", text, re.I)) > 1:
            hits.append(("'literally' twice in a line", "literally", "one 'literally' a video at most"))
        if is_short and i == 0 and not has_name(text):
            hits.append(("a Short's hook with no name people know", text[:60], "names people know are what hook them"))
        for why, other in copy_hits.get(beat, []):
            hits.append(("a line " + why + ": new words for the same fact", other,
                         "a line heard in an earlier video sounds copy-pasted"))
        out_lines.append({"beat": beat, "text": text, "flags": [{"rule": n, "match": w, "source": s, "level": "look" if n.startswith(LOOK) else "fix"}
                                                                for n, w, s in hits]})
        flags += len(hits)

    # ---- the whole script
    text = " ".join(texts)
    words = words_total
    sents = [s for s in sentences(text) if len(s.split()) > 2]
    ann = sum(len(re.findall(ANNOUNCER, t, re.I)) for t in texts)
    openers = Counter((t.split()[0].strip(",").lower() if t.split() else "") for t in texts)
    longest = max(sents, key=lambda s: len(s.split())) if sents else ""
    script = {"lines": len(lines), "words": words, "sentences": len(sents), "words_per_sentence": round(words / max(1, len(sents)), 1),
              "longest_sentence_words": len(longest.split()), "announcer_per_1k": round(1000 * ann / words, 2),
              "literally": len(re.findall(r"\bliterally\b", text, re.I)), "openers": openers.most_common(5), "format": "short" if is_short else "long",
              "notes": [], "shape_flags": []}
    connectives = {"and", "then", "so", "but", "now", "also", "next", "after", "because", "plus", "like"}   # the list tics, not "The"
    for k, v in openers.most_common(3):
        if k in connectives and v >= 3 and v / len(lines) > 0.15:   # two in a 9-line Short is no list
            script["shape_flags"].append((f"'{k}' opens {v} of {len(lines)} lines (over 15%: reads like a list)", "one opener on line after line reads like a list"))
    fan = len(re.findall(r"\b(I|I'm|I'd|I'll|my|me|we|we're|our|you|you're|your)\b", text))
    script["fan_per_1k"] = round(1000 * fan / words, 1)
    attributed = sum(1 for t in texts if ATTRIBUTION.search(t))
    script["attribution_share"] = round(attributed / max(1, len(lines)), 2)
    opinions = [b for b, t in lines if OPINION.search(t)]
    script["opinion_lines"] = opinions
    dated = [bool(DATE_OPENER.match(t)) for t in texts]
    script["date_openers"] = sum(dated)
    searched = {}
    for name, rx in WORD_SEARCH:
        beats = [b for b, t in lines if re.search(rx, t, re.I)]
        if beats:
            searched[name] = beats
    script["word_search"] = searched
    if not is_short:
        # the sub ask comes at a real break, past the early part (a third of the way in is too early)
        seen = 0
        for b, t in lines:
            if SUB_ASK.search(t):
                share = seen / words
                script["sub_ask"] = {"beat": b, "at_share": round(share, 2)}
                if share < 0.35 and len(lines) >= 40:
                    script["shape_flags"].append((f"the sub ask ({b}) comes at {share:.0%} of the words: too early", "the viewer has not got anything yet"))
                break
            seen += len(t.split())
        if "sub_ask" not in script and len(lines) >= 40:
            script["notes"].append("no sub ask found (a long video asks at a real break)")
        block = raw[: [m.start() for m in re.finditer(r"^## (Beats|v\d+ )", raw, re.M)][1]] if len(re.findall(r"^## (Beats|v\d+ )", raw, re.M)) >= 2 else raw
        chapters = len(re.findall(r"chapter=", block))
        script["chapters"] = chapters
        if chapters >= 2:
            script["shape_flags"].append((f"{chapters} chapter cards: chapters only where the video tells a story in parts; a topic video runs as one",
                                          "chapter cards break a topic video that tells no story in parts"))
        if len(lines) >= 20:
            worst, where = 0, 0
            for k in range(0, len(dated) - 19):
                share = sum(dated[k:k + 20]) / 20
                if share > worst:
                    worst, where = share, k
            script["timeline_window"] = {"from": lines[where][0], "to": lines[min(where + 19, len(lines) - 1)][0], "date_openers": round(worst, 2)}
            if worst >= 0.4:
                announced = any(RUNDOWN_ANNOUNCED.search(t) for t in texts[: where + 20])
                where_s = f"{lines[where][0]}-{lines[min(where + 19, len(lines) - 1)][0]}: {worst:.0%} of 20 lines open on a date"
                if announced:   # an announced rundown: a note to keep it quick, not a fault
                    script["notes"].append(where_s + ": the announced rundown; keep it quick (quick really means quick)")
                else:
                    script["shape_flags"].append((where_s + ", the timeline of a report, and no line announces the rundown",
                                                  "the past goes in a quick, announced rundown ('before we talk about what's next, let me quickly ...')"))
        if len(lines) >= 40 and script["attribution_share"] > 0.25:
            script["shape_flags"].append((f"{script['attribution_share']:.0%} of the lines report what someone said/told/expects: a reporter's share",
                                          "the creator talks as a fan, not a neutral reporter"))
        if words >= 600 and script["fan_per_1k"] < 8:
            script["shape_flags"].append((f"I/you/we {script['fan_per_1k']} per 1,000 words: nobody in the room (off-the-cuff talk runs about I 23, you 29)",
                                          "a person talks to the viewer"))
        # the house-style tells blind judges keyed on; limits = the 90th percentile of real narrations (voice_metrics.py), the
        # rhythm's floor = their 10th
        lens = [len(s.split()) for s in sents]
        sd = (sum((x - sum(lens) / len(lens)) ** 2 for x in lens) / len(lens)) ** 0.5 if lens else 0
        script["sentence_sd"] = round(sd, 1)
        per1k = lambda rx: round(1000 * len(re.findall(rx, text, re.I)) / words, 1)
        script["numbers_per_1k"] = per1k(r"\b(?:\d[\d,.]*|eleven|twelve|thirteen|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|"
                                         r"hundred|thousand|million|billion)\b")
        script["attribution_per_1k"] = per1k(r"\b(?:says|said|according to|reported|told|thinks|believes)\b")
        script["subject_per_1k"] = per1k(rf"\b(?:{alt(SUBJECT)})\b") if SUBJECT else 0.0
        script["gloss_per_1k"] = per1k(r"\b(?:is|are|it'?s|that'?s) called\b|\bwhich (?:is|means)\b|\bmeaning\b|\bknown as\b|\bshort for\b|"
                                       r"\bstands for\b|\bthe (?:name|word|term) for\b")
        if words >= 600:
            checks = [(script["sentence_sd"], 7.5, "sentence lengths held to a band (spread {v} words; humans 7.5-12): vary by meaning"),
                      (script["numbers_per_1k"], 35, "{v} numbers per 1,000 words (humans 11-35): keep the ones that matter"),
                      (script["attribution_per_1k"], 3.1, "'X says' {v} per 1,000 words (humans 0.3-3.1): state what's known, quote who's the origin"),
                      (script["gloss_per_1k"], 2.5, "{v} definitions per 1,000 words (humans 0.3-2.5): explain few terms, from the picture")]
            if SUBJECT:
                checks.append((script["subject_per_1k"], 3.0, f"'{SUBJECT[0]}' {{v}} per 1,000 words (real creators about 1.35, then 'it' or a "
                                                              "short name)"))
            for val, limit, what in checks:
                low = what.startswith("sentence")
                if (low and val < limit) or (not low and val > limit):
                    script["shape_flags"].append((what.format(v=val), "blind judges key on these: 'one tidy fact per sentence', "
                                                                         "'term-then-gloss', 'stat-stacking', 'source-per-claim'"))
        if words >= 600 and not opinions:
            script["shape_flags"].append(("no take of the creator's anywhere: interview the creator after the script and blend the answers in",
                                          "a video with no person's opinion reads as AI"))
        last = texts[-1] if texts else ""
        if texts and SIGN_ALT and SIGN_OFF.search(last) and not re.search(rf"\b(?:{SIGN_ALT})\b", last, re.I):
            script["shape_flags"].append((f"the last line ({lines[-1][0]}) doesn't end on '{SIGN[0]}'", "a long video always ends on the sign-off word"))
        elif texts and not SIGN_OFF.search(last) and len(lines) >= 40:
            script["notes"].append("no sign-off at the end (a long video ends on the like/comment ask, then the sign-off word)")
    flags += len(script["shape_flags"])
    script["flags"] = flags
    script["copy_flags"] = sum(1 for ln in out_lines for f in ln["flags"] if f["rule"].startswith("a line also in"))
    # "fix" flags fail the gate (--strict); "look" flags (a take's lead-in, a number's point, long sentences, shared lines, a reporter's
    # share) are read and kept or fixed by hand
    script["fix_flags"] = sum(1 for ln in out_lines for f in ln["flags"] if f["level"] == "fix") + \
        sum(1 for why, _ in script["shape_flags"] if "reporter's share" not in why)
    return out_lines, script


def print_report(out_lines, script, show_all):
    for ln in out_lines:
        if ln["flags"]:
            print(f"{ln['beat']}: {ln['text'][:150]}")
            for f in ln["flags"]:
                print(f"    - {f['rule']}: \"{f['match']}\"  [{f['source']}]")
        elif show_all:
            print(f"{ln['beat']}: ok")
    print("\n== whole script")
    print(f"- {script['lines']} lines, {script['words']} words, {script['sentences']} sentences, {script['words_per_sentence']} words a sentence "
          f"(no band: humans spread 7.5-12, see sentence_sd); the longest {script['longest_sentence_words']} words (split at ~45)")
    print(f"- announcer phrases: {script['announcer_per_1k']} per 1,000 words (real creators 0-0.4; a channel its viewers called AI, 2.6)")
    top = ", ".join(f"{k} {100 * v / max(1, script['lines']):.0f}%" for k, v in script["openers"])
    print(f"- line openers: {top} (one opener over ~15% of lines reads like a list)")
    print(f"- 'literally': {script['literally']} (the cap: 1 a video)")
    print(f"- I/you/we: {script['fan_per_1k']} per 1,000 words (off-the-cuff talk: I 23, you 29); said/told/says lines: "
          f"{script['attribution_share']:.0%}; takes: {len(script['opinion_lines'])} line(s) {', '.join(script['opinion_lines'][:8])}")
    if "timeline_window" in script:
        w = script["timeline_window"]
        print(f"- date openers: {script['date_openers']} lines; the densest 20 lines {w['from']}-{w['to']} at {w['date_openers']:.0%}")
    if "sub_ask" in script:
        print(f"- the sub ask: {script['sub_ask']['beat']} at {script['sub_ask']['at_share']:.0%} of the words (at a real break, past the early part)")
    if script.get("chapters"):
        print(f"- chapter cards: {script['chapters']}")
    if script["word_search"]:
        print("- the word search (standard/SCRIPTS_AND_PACKAGING.md): " + "; ".join(f"{k} x{len(v)} ({', '.join(v[:6])}{'...' if len(v) > 6 else ''})"
                                                                                   for k, v in script["word_search"].items()))
    for n in script["notes"]:
        print(f"- note: {n}")
    for why, src in script["shape_flags"]:
        print(f"    - FLAG: {why}  [{src}]")
    print(f"- flags: {script['flags']}: {script['fix_flags']} to fix, {script['flags'] - script['fix_flags']} to look at "
          f"({script['copy_flags']} lines other scripts also have)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path")
    ap.add_argument("--all", action="store_true", help="list clean beats too")
    ap.add_argument("--strict", action="store_true", help="exit 1 when anything is flagged (the gate)")
    ap.add_argument("--json", help="write every flag and number here")
    ap.add_argument("--ignore", default="", help="video ids whose shared lines are by design (a prototype that became the film): 12,15")
    ap.add_argument("--against", choices=["earlier", "all"], default="earlier", help="compare lines with earlier videos only (default) or all")
    ap.add_argument("--no-copies", action="store_true", help="skip the copy check against the other scripts")
    ap.add_argument("--format", choices=["long", "short"])
    a = ap.parse_args()
    out_lines, script = lint(a.path, a.format, [x.strip() for x in a.ignore.split(",") if x.strip()], not a.no_copies, a.against)
    print_report(out_lines, script, a.all)
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps({"file": str(a.path), "lines": out_lines, "script": script}, indent=1, ensure_ascii=False), encoding="utf-8")
    if a.strict and script["fix_flags"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
