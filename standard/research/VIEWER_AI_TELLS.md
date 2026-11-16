# What viewers call an AI script: one thread of viewer replies

*The question: which script habits do ordinary viewers name when they say a YouTube narration "feels like a ChatGPT script"? The
source is one public X post and the replies under it, read from screenshots: the post (by @ArtofGerald, 2026; ~150K views, 16K likes)
says that hearing a narrator use "and honestly?" and "it's not X, it's Y" within one minute gives the script away, and it quotes the
author's own earlier post that small creators on YouTube often sound like they are reading a chatbot script. Irony posts (replies
written in the style to mock it) were told apart from criticism and set aside, and only the direct contents of a script were counted.
Quotes are kept short. Read with: `standard/research/AI_TELLS.md` (the measured catalogue behind these habits),
`standard/research/HUMAN_SCRIPT_STUDY.md`, `standard/SCRIPTS_AND_PACKAGING.md`, and the checks `tools/script/script_lint.py` and
`tools/script/tell_lint.py`.*

*Grade: **C** as evidence of what an audience notices (direct viewer testimony, one thread; like and view counts show reach, not
agreement); **D** for how often a habit occurs (nobody counted).*

## The tells they name (the script)

| Tell | How viewers put it | What a script does instead |
|---|---|---|
| "It's not X, it's Y" | "done the "it's not X, it's Y" thing like 5 times within 10 minutes"; "The x of y isn't [noun], it's you/us/audience" | Say the thing itself; no reveal by denial (`script_lint.py` flags "isn't X, it's Y" reveals) |
| "No X, no Y, just Z" | "the "no x, y, just z" claude script combo" (several replies name it as one model's habit) | State Z plainly; no stacked denials before it |
| "And honestly?" | the post itself; "Oh my god "and honestly"" (1.2K views); "The "and honestly" thing makes wanna kill somebody" (2.8K) | Never as a filler (`script_lint.py` flags it) |
| A question the narrator answers | "and (thing)? that's (adjective) / but now that (cause)? (consequence)" | No "X? Y." beats (`script_lint.py` flags them): say the sentence |
| Mirrored template lines | "they (verb) and (verb), but they never (opposite verb)"; "(thing) first, (other thing) later" | No symmetrical template lines; tell what happened in its own words |
| Groups of three | "Don't forget the groups of three" | No triplet flourishes (`tell_lint.py` flags `triplet`) |
| Announcing the next line | "and here's the part that really surprised me" five times | No announcer lines: the next line is the surprise (`script_lint.py`) |
| Made-up comparisons | "they ALWAYS use dumb metaphors like "it's like *ai generated senario*"" | No textbook analogies; a comparison only with a real thing the viewer knows |
| Saying it again in new words | "he reiterates the exact same sentence he already said but with slightly different wording" | Say each thing once; no line that restates the line before |
| Intensifier stacks as humour | ""It's not just hard, it's a complete *insert random asd word that compliments the topic* nightmare"" (561 likes) | No "not just A, it's a complete B" escalations as jokes |
| One tone throughout | "always with the same f*cking tone too" (2.4K) | Delivery, not script: the voice is the creator's choice; noted only |
| Dashes in subtitles | "when the subtitles have a double dash" | No em dash or "--" in voice lines or in the .srt |
| Writer's words in a talker's mouth | reading a "full report" with "words he couldn't even pronounce"; "his talking style changed fully when explaining the examples" | Plain spoken words only, in the same register in the examples as everywhere else |
| The fix they name | "Sometimes you don't even need a script, just say what you think and what you've learned"; "just improvise like speak from your mind" | The human-script method (`standard/SCRIPTS_AND_PACKAGING.md`, `standard/research/HUMAN_SCRIPT_STUDY.md`) |

**The fair caveat (one reply):** normal people use these phrasings too, and the reply advises finding several different signs at
once before calling it. So one tell rarely gives a script away; the stack of them, and their repetition, does.

**The picture side (not the script, but the same thread):** viewers also named "slick programmatically generated animations to
illustrate mechanics", "editing has weird disjointed cuts", and "a channel that's making several videos a week". The house standard
already answers these: real material first, graphics premium or none, every cut on meaning (`standard/LONG_FORM.md`,
`standard/research/AI_SLOP_VS_PREMIUM.md`).

**Irony to ignore:** "And honestly? -- That's growth. 🌿✨" and "It's not just annoying, it's repulsive. And honestly? Creators
shouldn't do it." are written in the style to mock it; "its not pingas, its dinner" is a meme.
