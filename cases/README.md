# The casebooks: the creator's line in every craft, learned until it can be predicted

The rules (`rules/`) and the standards (`standard/`) say what to do. The casebooks keep the cases the lines were drawn from, both
sides: what the creator FLAGGED and what they PASSED, so the line between "fine" and "too much" can be seen. It works the way a
student works beside a master: every verdict written down, every prediction scored, until the chat judges a piece the way the creator
would and the creator has less and less to say. That is the goal of these books: a chat that can work on its own and satisfy the
creator fully.

## What is here
| Craft | Book | Read by |
|---|---|---|
| Does it make sense (the words, the picture under the words, each clip in its place) | `COHERENCE.md` | the coherency read (its packet, `tools/pipeline/coherency.py packet <video>`, carries this file whole), every builder, every reviewer |
| The picture (footage, framing, motion, cuts, graphics, marks, text on screen) | `PICTURE.md` | every builder brief points at it; the reviewer's eye (`.claude/agents/reviewers-eye.md`) |
| Sound (effects, music, the mix) | `SOUND.md` | every sound pass |
| The voice (takes, accent, pronunciation, pauses) | `VOICE.md` | every voice round |
| The script (words, lines, facts as said, structure, titles) | `SCRIPT.md` | every script round and every voice round |
| The prediction log | `PREDICTIONS.md` | written before every piece goes to the creator, scored after |

Both chats read the books of the crafts they work in. A line marked **(long form)** holds for the main chat's videos, **(Shorts)** for
the Shorts chat's; an unmarked line holds for both.

## The starting taste
Each book starts with seed cases: the lines a working studio's own verdicts drew, told in neutral words (what was on screen or heard,
and the line it taught), with no quotes and no history. They are the starting taste, exactly like the rules. From the first video on,
the creator's own verdicts are added, and they win:
- a creator case that **contradicts** a seed line replaces it, in place: the seed line is deleted, never mentioned, never argued from;
- a creator case that **agrees** with a seed line is written into that entry (their words beside it): the line is theirs now;
- a creator case on a line the book doesn't have yet becomes a new entry under the heading it belongs to.

## The method, every turn
1. **Every verdict lands the same turn it is given**, in its craft's book: what the creator flagged and what they passed (a plain
   "fine", a "keep that"; a piece uploaded or scheduled with no note is a pass of the whole piece). A pass is written down as surely
   as a flag: the passes are what shows where the line is.
2. **One verdict, every craft it touches.** A note on a scene that is both a script fault and a picture fault goes into SCRIPT and
   PICTURE, each with the part that belongs there.
3. **The line is written for the class, not the instance.** "This zoom" becomes the kind of zoom; every other place in the video with
   the same fault is found and fixed with it, and the entry says the class.
4. **Merge, don't pile up.** A new case on a line already in the book goes into that entry; a distinct line gets its own entry under
   its heading, newest at the bottom. Every distinct line is kept.
5. **A rule changes where it lives.** When a verdict sets a new rule or changes one, the rule file changes too (CLAUDE.md, the office
   rule on the creator's taste); the case here is the evidence the rule was drawn from.

## The format of an entry
- A seed case: `**PI12** FLAGGED: <what was on screen or heard, in neutral words> -> the line: <the rule it teaches>`
- A creator case: `**PI57** FLAGGED (<video> · <time> · <beat>): <what was on screen or heard> | the creator: "<their words,
  verbatim>" -> the line: <the rule it teaches>`
- One entry can hold both sides when one pair of verdicts draws one line ("FLAGGED: ... PASSED: ... -> the line: ...").
- IDs per book, never reused: `CO` coherence, `PI` picture, `SC` script, `SO` sound, `VO` voice. A replaced line keeps its ID.
- Interpretation stays out of the quote: the creator's words verbatim, the line in the chat's words after the arrow.

## The prediction log: how the student becomes the master
Before a piece goes to the creator (a sample, a prototype, a version, a cut), the chat writes in `PREDICTIONS.md` the verdict it
expects, per piece or per section: "passes" or "flags X because Y", leaning on the cases it read. When the verdict comes, each
prediction is scored HIT or MISS, **every MISS becomes a case in its book the same turn** (that is the line that was not known yet), and
the running score per craft is kept at the top of `PREDICTIONS.md`. A rising hit rate is the measure that the line is learned.

A MISS on a line already in a book is the gravest kind: the case was there and was not used. Its fix goes where the miss started (the
brief that did not point at the book, the check that did not read it), never only into the one video.

## Who reads what, and when
- A builder's brief names its craft's books and the entries closest to the piece being built.
- A reviewer (the reviewer's eye, the coherency read) reads the books before it flags anything: it flags what the creator would flag
  and passes what the creator passed.
- The chat reads the book before judging a flag, and again before writing a prediction.
