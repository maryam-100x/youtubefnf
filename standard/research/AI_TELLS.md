# What makes text read as LLM-written: an evidence catalogue

*The question: by the evidence, what makes a text read as written by a large language model, and what do practitioners say about
writing narration for the ear? Compiled for narration scripts. Read with: `standard/research/VIEWER_AI_TELLS.md` (what viewers name),
`standard/research/HUMAN_SCRIPT_STUDY.md`, `standard/research/LINGO.md`, `standard/SCRIPTS_AND_PACKAGING.md` and
`standard/SCRIPT_TRAINING.md`; the checks that act on it are `tools/script/script_lint.py` and `tools/script/tell_lint.py`.
Quotes are kept under 25 words; the rest is paraphrase. "Couldn't confirm" means the page could not be read (paywall, block) and
nothing is built on it. Every date in this file is a source's own date.*

Grades used: **A** = peer-reviewed / top venue; **B** = arXiv preprint or large data study by a named org; **C** = named practitioner,
single-person experience; **D** = vendor or anonymous blog (direction only, numbers not trusted).

---

## 1. Wikipedia: "Signs of AI writing" (WikiProject AI Cleanup)

- URL: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
- Read in full as raw wikitext (`action=raw`), revision **1381428541**. Grade **B** (a community field guide built from real cases,
  with research citations; the page calls itself descriptive, not prescriptive).
- Scope warning from the page itself: it is a guide for *informational* writing on Wikipedia; fiction tells (e.g. "whispering woods",
  "Elara Voss") are deliberately left out, and not every sign applies outside Wikipedia. It also warns: do not just "fix the signs",
  since the signs point to deeper problems (generic, unsupported content), and masking them only makes detection harder.
- Its stated root cause (section "Content"): LLMs regress to the mean and RLHF pushes them toward "broadly palatable prose", so
  specific, unusual facts get replaced by generic, positive ones. The page's example: "inventor of the first train-coupling device"
  becomes "a revolutionary titan of industry". The subject becomes "simultaneously less specific and more exaggerated."
- At that revision, the page lists the most common signs of new AI text on Wikipedia as: Markdown, AI edit summaries, hedging
  disclaimers about sources, vague connection/association wording, and canned emphasis on attribution/media coverage.

### 1.0 Caveats the page gives

| Heading | What it says |
|---|---|
| AI detection tools | GPTZero, Pangram etc. beat chance but have non-trivial error rates; paraphrasing, markup and unseen models fool them. |
| Your detection ability | Humans are poor detectors: one 2025 study found people at chance; a study of student theses found 57 % recognition of AI texts and 64 % of human ones. A 2025 preprint (Russell et al., see 2.13) found frequent-LLM-user "experts" caught 90 % of AI texts with 3.3 % false positives; light users were near chance. Human speech is drifting toward LLM wording (Yakura et al., see 2.11), but LLM output is not drifting toward human writing. |

### 1.1 Content

| # | Sign (page heading) | One-line description | Words / phrases to watch (as listed on the page) |
|---|---|---|---|
| 1 | Undue emphasis on significance, legacy, and broader trends | Puffs up importance by saying arbitrary details "represent" or "contribute to" something bigger; situates the subject in broader "debates"; even mundane facts get importance statements; hedged preambles ("relatively minor, but..."); in biology, over-links to "the broader ecosystem" and conservation. Since mid-2026, paired with "this distinction matters" editorializing. | stands/serves as; is a testament/reminder; a crucial/pivotal/vital/significant/key role/moment; underscores/highlights its importance/significance; reflects broader; symbolizing its ongoing/enduring/lasting; contributing to the; setting the stage for; marking/shaping the; represents/marks a shift; key turning point; evolving landscape; focal point; indelible mark; deeply rooted; distinction [matters/is important] because |
| 2 | Canned emphasis on notability, attribution, and media coverage | Proves importance by listing *that* sources covered the subject and what kind of sources they are, instead of saying what the sources said; often misattributes its own analysis to them. More common in 2025+ tools. "Maintains an active social media presence" is called particularly idiosyncratic. | independent coverage; local/regional/national/[country] media outlets; music/business/tech outlets; trade publications; cited/featured/profiled in; written by a leading expert; active social media presence; was identified by |
| 3 | Superficial analyses | Tacks a shallow significance comment onto a fact, usually as a present-participle ("-ing") phrase at the end of the sentence, sometimes credited to a named source that never said it. | highlighting/underscoring/emphasizing...; ensuring...; reflecting/symbolizing...; contributing to...; cultivating/fostering...; encompassing...; enhancing...; valuable insights; align/resonate with |
| 4 | Promotional and advertisement-like language | Cannot hold a neutral tone; drifts into ad copy or travel-guide prose, even when told to be neutral. Older models (GPT-4) were blatantly positive; newer ones are more subtly positive and avoid "the best". Subtypes: "cultural heritage" topics get constant importance reminders; people/companies get a press-release tone. | boasts a; vibrant; rich; profound; enhancing; showcasing; exemplifies; commitment to; natural beauty; nestled; in the heart of; groundbreaking; renowned; featuring; diverse array |
| 5 | Vague expression of connection or association | Instead of stating the plain relation ("was CEO of", "taught science at"), says the two things are "connected to" or "associated with" each other. | in connection with/to; connected with/to; in association with; associated with (often "particularly/widely associated") |
| 6 | Vague attributions and overgeneralization of opinions | Weasel wording: credits claims to vague authorities and inflates how many sources hold a view; "such as" before a list that is actually complete. | Industry reports; Observers have cited; Experts argue; Some critics argue; several sources/publications (when few are cited); such as (before exhaustive lists) |
| 7 | Outline-like conclusions about challenges and future prospects | Rigid closing formula: "Despite its [praise], [subject] faces challenges..." ending on a vaguely positive note or speculation about future initiatives; often a "Future Outlook" section. The sign is the formula, not mentioning challenges. | Despite its... faces several challenges...; Despite these challenges; Challenges and Legacy; Future Outlook |
| 8 | "Awards and recognition" section | "X and Y" style section headers, especially "Awards and recognition" / "Recognition", far more common in AI articles than in human ones, even promotional ones. | Awards and recognition; Recognition |

### 1.2 Language and grammar

The page says these patterns hold regardless of subject, which gives AI text an identifiable "voice"; GPT-4o (ChatGPT's model May 2024
to Aug 2025) deviated from human writing more than its contemporaries.

| # | Sign | Description | Words / phrases |
|---|---|---|---|
| 9 | High density of "AI vocabulary" words | Specific words LLMs overuse; they cluster (where one appears, others follow). One or two may be chance; many, many times, is "one of the strongest tells". The list is literal: synonyms are *not* implicated. | **Core list:** Additionally (esp. sentence-initial); align with; boasts (= "has"); bolstered; crucial; deep dive; delve; emphasizing; enduring; enhance; fostering; garner; highlight (verb); interplay; intricate/intricacies; landscape (abstract); meticulous/meticulously; pivotal; robust; showcase; tapestry (abstract); testament; underscore (verb); valuable; vibrant. **By era:** 2023 to mid-2024 (GPT-4): Additionally, boasts, bolstered, crucial, delve, emphasizing, enduring, garner, intricate/intricacies, interplay, key, landscape, meticulously, pivotal, underscore, tapestry, testament, valuable, vibrant. Mid-2024 to mid-2025 (GPT-4o): align with, bolstered, crucial, emphasizing, enhance, enduring, fostering, highlighting, pivotal, showcasing, underscore, vibrant. Mid-2025 to mid-2026 (GPT-5): emphasizing, enhance, highlighting, showcasing (+ the attribution words of sign 2). **Mid-2026 on (GPT-6):** challenge, clearer, dependable, echoed, foster, leverage, matters, multifaceted, practical, prioritize, quietly, steady, universally, plus much more period/comma use and **shorter sentences held to a strict 8-20 word band**. Grok: pseudo-scientific causal, empirical, correlate; still "underscore" in 2026. "Delve" peaked 2023 to early 2024 and dropped sharply in 2025. |
| 10 | Avoidance of basic copulatives ("is"/"are") | Replaces "is/are/has" with "serves as", "stands as", "marks", "represents", "features", "offers"; newer output dresses it up further ("ventured into politics as a candidate" for "was a candidate"; "began his career as" for "was"). One study found a >10 % drop in "is"/"are" in 2023 academic writing; GPT-3.5 "revise this sentence" also cut them. | serves as / stands as / marks / functions as / operates as / represents [a]; boasts / features / maintains / offers [a]; refers to |
| 11 | Negative parallelisms | Text sounds like it is correcting a misconception nobody raised. Three forms: **(a) Not just X, but also Y** ("Not only... but...", "It is not just..., it's..."), also spread across two sentences; **(b) Not X, but Y** ("It's not..., it's...", "no..., no..., just..."); **(c) Y rather than X**, the reversed form, "particularly common in recent LLM output". Common in human myth-busting listicles too, but "stereotypically an AI sign". | not only... but also; it's not just..., it's...; it's not..., it's...; no..., no..., just...; ...rather than... |
| 12 | Leads treating lists or broad titles as proper nouns | Defines a generic topic title (e.g. a list) as if it were a real-world entity. | (structural) |
| 13 | Rule of three | Overuses triplets: "adjective, adjective, adjective" or "short phrase, short phrase, and short phrase", often to make shallow analysis look comprehensive. Stronger sign where no human would bother with a flourish. | (structural) |

### 1.3 Style (mostly visual/formatting; listed for completeness)

| # | Sign | Description |
|---|---|---|
| 14 | Title case | Capitalizes all main words in section headings. |
| 15 | Overuse of boldface | Mechanical bolding of every instance of a key phrase, "key takeaways" style (inherited from readmes, slide decks, listicles). |
| 16 | Inline-header vertical lists | Bullets of the form "**Bold header:** description", often with stray •, -, –, # or emoji as bullet markers. |
| 17 | Heading errors | Title heading repeating the article name; skipping heading levels; overuse of level-1 headings; headings that contain only other headings. |
| 18 | Emoji as formatting | Emoji in front of headings/bullets; rarer now. |
| 19 | Unusual use of tables | Small, thin tables that should be prose; Markdown tables inside wikitables. |
| 20 | Curly quotation marks and apostrophes | ChatGPT and DeepSeek use curly quotes/apostrophes, sometimes mixed with straight ones; not proof on its own (Word, macOS, iOS do it too); Gemini and Claude typically don't. |

### 1.4 Communication intended for the user

| # | Sign | Description | Words / phrases |
|---|---|---|---|
| 21 | Collaborative communication | Chatbot chatter pasted into content: offers, sign-offs, notes to the user, instructions like "delete this section before submission". | a Wikipedia-style article; I hope this helps; Of course!; Certainly!; You're absolutely right!; Would you like...; is there anything else; let me know; more detailed breakdown; here is a |
| 22 | Hedging disclaimers about source availability and recommended usage | Fills gaps by pointing at the gaps. **2023-24:** didactic "it's important to note/remember" advice to an imagined reader. **2024-25:** search-enabled bots claim info "isn't widely documented", then speculate what it "likely" is; for people, "maintains a low profile". **Mid-2026 on** (from ~GPT-5.6, July 2026): "corrective framings": "[claim] should be treated as [speculative] rather than [verified]"; "the available information does not establish..."; "should not be confused with..." (less reliable). Almost unheard-of before July 2026. | While specific details are limited/scarce...; not widely available/documented/disclosed; ...in the provided/available sources / search results...; [claim] should be [treated/presented] as... rather than...; based on available information; ...does not by itself establish...; it's important to note; it is crucial to differentiate |
| 23 | Phrasal templates and placeholder text | Unfilled Mad-Libs blanks ("[Entertainer's Name]", "(Add your channel URL here)"), placeholder dates like "2025-xx-xx", "add if available" comments. | [Name]; (Add ... here); (If available); 20xx-xx-xx |

### 1.5 Markup (Wikipedia/chat-export specific)

| # | Sign | Description |
|---|---|---|
| 24 | Use of Markdown | Markdown (`**bold**`, `#` headings, `[text](url)`, `---`) instead of wikitext; Markdown mixed with broken wikitext, esp. fenced ```` ```wikitext ```` blocks, is a strong sign; Markdown alone is weak. Sub-signs: misuse of asterisks; misuse of `##`; unusual link formatting; thematic breaks between every section. |
| 25 | Broken wikitext | Garbled template syntax (e.g. AfC submission code). |
| 26 | Internal formatting and reference-markup bugs | Unambiguous leaks: ChatGPT `:contentReference[oaicite:0]`, `oai_citation`, `turn0search0`, `iturn0image0`, `attributableIndex` JSON; Gemini `[cite: 1]`, `[span_1](start_span)`; Grok `grok_card`, `grok_render_citation_card_json`; DeepSeek `【85†L261-269】`; Perplexity `[attached_file:1]`, `[web:1]`, `ppl-ai-file-upload`; unclassified `:::writing{variant="document" id=...}` (seen from 2026-06-01). |
| 27 | Non-existent or out-of-place categories | Hallucinated or obsolete categories; "Category people"-style word-dropping breakage is a strong tell. |
| 28 | Non-existent templates | Hallucinated infobox types/parameters; deleted templates. |

### 1.6 Citations

| # | Sign | Description |
|---|---|---|
| 29 | Broken external links | Several dead links never archived. |
| 30 | Invalid DOIs and ISBNs | Bad checksums, unresolvable DOIs. |
| 31 | DOIs that lead to unrelated articles | Real-looking DOIs pointing to other papers. |
| 32 | Book citations without page numbers or URLs | Plausible general books, no page; or pages that don't support the claim. |
| 33 | Incorrect or unconventional use of references | Broken ref re-use syntax after every sentence; the ↩ character. |
| 34 | utm_source= | `utm_source=chatgpt.com` / `openai`; Copilot `utm_source=copilot.com`; Grok `referrer=grok.com` (proves the tool found the link, not that it wrote the text). |
| 35 | Named references declared but unused | Refs in `<references>` never cited inline. |

### 1.7 Comments, edit summaries, miscellaneous

| # | Sign | Description |
|---|---|---|
| 36 | Comment-specific indicators | Misquoted policies and made-up shortcuts; sectioned, headed long comments; claims of "human effort"; "let's focus on the content"; clerk/customer-service tone ("carefully reviewed", apologizing for inconvenience they "may have" caused, "I hope this message finds you well", "I respectfully request"). |
| 37 | Edit summaries | Rigid templates: canned assurance of policy compliance (ensured... adheres to, refined, enhanced, streamlined, in compliance with, neutral/encyclopedic tone, clarity, flow); "preserved/retained/avoided" statements about what was *not* changed; overemphasis on "sourced"/"verified"/"independent sources"; itemized parameter names; "addressing reviewer feedback". The more stacked, the stronger. |
| 38 | Pronounced shift in writing style | Sudden flawless prose vs the person's other writing; long-term users' style tracks each year's model. |
| 39 | "Submission statements" in AfC drafts | Notes to reviewers arguing notability. |
| 40 | Pre-placed maintenance templates | Drafts born "declined", or with implausible maintenance tags. |
| 41 | Canned user pages | "About Me / My Interests / Let's Connect!" with emoji and bold lists. |
| 42 | Farming user rights | Many quick throwaway AI edits to reach a user right. |
| 43 | Differences between LLMs | Each model has an idiolect; ChatGPT/Grok focus on broader context more than Gemini/Claude; Gemini/Claude are more concise. |
| 44 | Biases in content: pro-authoritarian bias | Frontier models show pro-authoritarian lean on some prompts (2026). |

### 1.8 Signs of *human* writing (the page's own list)

- Text older than 2022-11-30 (ChatGPT launch).
- The writer can explain their own choices and mistakes.
- **Syntax humans use more than AI** ("empirically observed over 25 years of Wikipedia"):
  - simple is/has phrases ("there is a", "it has a");
  - plain verbs over stiff synonyms: *wrote* not authored, *moved* not relocated, *used* not utilized, *tried* not attempted, *died*
    not passed away;
  - superlative/definitive statements: "one of the best", "is the only", "was the first";
  - qualifiers and intensifiers: "very", "perhaps", "tends to";
  - isolated wordy constructions: "as a result of", "in order to", "all of the", "a part of", "the fact that".

### 1.9 Ineffective indicators (the page says these do NOT work)

Perfect grammar; mixed casual/formal register; "bland" or "robotic" prose (AI skews positive and verbose, which doesn't read as
robotic); "fancy"/academic prose in general (only *specific* words are overused); transition words in isolation ("Additionally",
"Consequently", "Notably" were an older tell but are weak alone); unsourced content; bizarre wikitext; correct wikitext.

### 1.10 Historical indicators (older models)

| Sign | Description |
|---|---|
| Statements about knowledge cutoffs (2022-2023) | "as of my last knowledge update". |
| Section summaries | "In summary", "In conclusion", "Overall"; a "Conclusion" section restating the point. |
| Prompt refusal | "as an AI language model", "I'm sorry". |
| Overuse of em dashes (2022 to September 2026) | More em dashes than non-professional humans, used formulaically to punch up clauses/parallelisms, usually spaced. A July 2026 study (cited to The Economist) found only Claude used more em dashes than professional writers. Since ~September 2026 the newest models are hard-coded to avoid them, and the page says the side effect is low punctuation variety: commas and periods more than in human text, "now ... its own sign" (that last claim carries a *citation needed* tag). |
| Abrupt cut-offs | Truncated output. |
| Outdated access-date parameters | Stale default dates. |
| Lexical diversity / elegant variation | Older models' repetition penalty made them cycle synonyms for the same thing ("the constraints of socialist realism" / "Soviet artistic constraints" / "state-imposed artistic norms"); Wikipedia text after 2023 shows it. The page notes non-native writers (e.g. Italian schooling) also avoid repeats. |

**Not on the page:** the page names "whispering woods"/"Elara Voss" fiction tells only to exclude them, and links an external pattern
directory (https://tropes.fyi/directory) that was not read here.

---

## 2. Research on LLM vs human style (2023-2026)

### 2.1 Kobak, González-Márquez, Horvát, Lause (2025). "Delving into LLM-assisted writing in biomedical publications through excess vocabulary." *Science Advances* 11(27). Grade A.
- URLs: https://www.science.org/doi/10.1126/sciadv.adt3813 (403 for the fetcher), read via https://arxiv.org/abs/2406.07016 and
  https://arxiv.org/html/2406.07016v5
- Data: >15 million PubMed abstracts, 2010-2024.
- 454 excess words in 2024 (343 unique lemmas, vs 180 in the 2021 Covid peak); 379 of them were **style** words, 66 % verbs and 14 %
  adjectives (content words dominated earlier excess years, e.g. Covid).
- Frequency ratios: "delves" r = 28.0, "underscores" r = 13.8, "showcasing" r = 10.7; common words with the biggest gaps:
  "potential", "findings", "crucial".
- Lower bound: at least 13.5 % of 2024 abstracts were LLM-processed, up to ~40 % in some subcorpora (e.g. 0.41 for computation papers
  from China).
- Takeaway: the LLM fingerprint is in *style* words (verbs/adjectives), not topic words.

### 2.2 Reinhart, Markey, Laudenbach, Pantusen, Yurko, Weinberg, Brown (2025). "Do LLMs write like humans? Variation in grammatical and rhetorical styles." *PNAS* 122(8). Grade A.
- URLs: https://pnas.org/doi/10.1073/pnas.2422455122 (403), read via https://arxiv.org/abs/2410.16107 and
  https://arxiv.org/html/2410.16107v2
- Method: parallel human/LLM corpora from the same prompts; Llama 3 variants and GPT-4o; Douglas Biber's lexical/grammatical/rhetorical
  features.
- GPT-4o vs humans: **present participial clauses 5.3x** (2-5x across instruction-tuned models); **nominalizations 2.1x** (1.5-2x);
  "that"-clauses as subjects 2.6x; phrasal coordination 1.9x; agentless passives ~0.5x. GPT-4o avoids clausal coordination; Llama
  overuses it; GPT-4o overuses downtoners.
- Differences are larger for instruction-tuned models than base models and persist as models grow. Human vs a given LLM is separable
  at 93-98 % accuracy (random forest).
- Takeaway: the "-ing tail" (sign 3 above) and noun-heavy phrasing are measured, not anecdotal.

### 2.3 Juzek & Ward (2025). "Why Does ChatGPT 'Delve' So Much? Exploring the Sources of Lexical Overrepresentation in Large Language Models." COLING 2025. Grade A.
- URL: https://arxiv.org/abs/2412.11385
- 21 "focal words" (e.g. delve, intricate, underscore) whose rise in scientific abstracts is linked to LLMs. No evidence that
  architecture, algorithms or training data cause it; results are consistent with RLHF (learning from human feedback) playing a role.
- Follow-up: Juzek & Ward (2025), "Word Overuse and Alignment in Large Language Models: The Influence of Learning from Human Feedback",
  BIAS workshop @ ECML PKDD, https://arxiv.org/abs/2508.01930: in an experiment emulating human-feedback rating, participants
  "systematically prefer text variants that include certain words". (Abstract gives no effect sizes.)

### 2.4 Shaib, Elazar, Li, Wallace (2024). "Detection and Measurement of Syntactic Templates in Generated Text." EMNLP 2024. Grade A.
- URL: https://arxiv.org/abs/2407.00211
- Models produce repeated part-of-speech templates at a higher rate than human reference texts; **76 % of templates in model output
  also appear in pre-training data vs 35 % for human text**; RLHF does not remove them; templates can tell models, tasks and domains
  apart.
- Takeaway: AI sameness is structural (sentence shapes), not only word choice.

### 2.5 Muñoz-Ortiz, Gómez-Rodríguez, Vilares (2024). "Contrasting Linguistic Patterns in Human and LLM-Generated News Text." *Artificial Intelligence Review* 57:265. Grade A.
- URL: https://arxiv.org/abs/2308.09067
- Human news text: **more spread-out sentence lengths**, more varied vocabulary, shorter constituents, more negative emotions (fear,
  disgust) and less joy. LLMs: more numbers, symbols and auxiliaries, more pronouns. Differences between LLMs and humans are larger
  than between LLMs.

### 2.6 Guo, Zhang, Wang, Jiang, Nie, Ding, Yue, Wu (2023). "How Close is ChatGPT to Human Experts? Comparison Corpus, Evaluation, and Detection" (HC3). arXiv. Grade B.
- URL: https://arxiv.org/abs/2301.07597 (read via https://ar5iv.labs.arxiv.org/html/2301.07597)
- ChatGPT answers were longer (English 198.14 words vs 142.50 for humans) yet had a smaller vocabulary (66,622 vs 79,157 words; density
  1.41 vs 2.33).
- ChatGPT: more nouns, verbs, determiners, adjectives, auxiliaries, coordinating conjunctions; **fewer adverbs and less punctuation**;
  strictly on-topic, define-then-step-through-then-summarize structure; neutral, formal, objective; logical connectors ("In general",
  "On the other hand").
- Humans: digress, use slang, abbreviations, humor, irony, metaphors, memes; **more "!", "?", "..." and brackets**; more negative (and
  slightly more positive) sentiment; a long tail of high-perplexity (surprising) text where ChatGPT's perplexity is low and
  concentrated.
- Detection: experts shown one answer spotted ChatGPT 81 % (EN); amateurs 48 %.

### 2.7 Venkatraman, Uchendu, Lee (2024). "GPT-who: An Information Density-based Machine-Generated Text Detector." Findings of NAACL 2024. Grade A.
- URL: https://arxiv.org/abs/2310.06202 (HTML v3 read)
- Uses Uniform Information Density (how evenly "surprise" is spread across a text). Finding: human text is "more non-uniform and
  diverse" than machine text; human UID-variance scores have a higher mean and spread. This is the measured basis of the "burstiness"
  idea (humans spike and dip; LLMs stay even). The paper gives figures as plots, not table values.

### 2.8 Sourati, Karimi-Malekabadi, Ozcan, McDaniel, Ziabari, Trager, Tak, Chen, Morstatter, Dehghani (2025/2026). "The Shrinking Landscape of Linguistic Diversity in the Age of Large Language Models." *Nature Human Behaviour* (2026, per arXiv page). Grade A.
- URL: https://arxiv.org/abs/2502.11266
- 3 studies, 7 datasets, >880,000 texts: LLM writing assistance cut the **variance of writing complexity by 21-50 %** (p <= .05);
  styles homogenize toward dominant patterns while content is retained.

### 2.9 O'Sullivan (2025). "Stylometric comparisons of human versus AI-generated creative writing." *Humanities and Social Sciences Communications* 12. Grade A.
- URL: https://research.ucc.ie/en/publications/stylometric-comparisons-of-human-versus-ai-generated-creative-wri/ (read via search
  summary of the UCC record and press release; full text not opened)
- Burrows' Delta on short stories from fixed prompts (humans vs GPT-3.5, GPT-4, Llama 70b): human texts form broad, varied clusters;
  each model's output clusters tightly; GPT-4 is more uniform than GPT-3.5. Overlap with humans is rare.

### 2.10 Sun, Yin, Xu, Kolter, Liu (2025). "Idiosyncrasies in Large Language Models." ICML 2025. Grade A.
- URL: https://arxiv.org/abs/2502.12150
- A classifier names which of ChatGPT, Claude, Grok, Gemini, DeepSeek wrote a text with **97.1 %** accuracy; the signal is rooted in
  word-level distributions and survives rewriting, translation and summarizing by another LLM.

### 2.11 Yakura, Lopez-Lopez, Brinkmann, de la Serna, Kirfel, Gupta, Soraperra, Eisenmann, Wulff, Rahwan (2024; v4 2026-07-16). "Empirical evidence of Large Language Model's influence on human spoken communication." arXiv. Grade B.
- URL: https://arxiv.org/abs/2409.01754
- 737,083 hours of unscripted podcast speech (824,634 episodes): ChatGPT-preferred words ("delve", "showcase", "boast", "intricacies",
  "meticulous") rose abruptly in *spoken* English after ChatGPT's release (synthetic-control analysis). Preregistered experiment
  (N = 496): a short chatbot chat made people adopt its words.
- Relevance: listeners now hear these words in speech too, and still recognize them as ChatGPT's.

### 2.12 Paech, Roush, Goldfeder, Shwartz-Ziv (2025). "Antislop: A Comprehensive Framework for Identifying and Eliminating Repetitive Patterns in Language Models." ICLR 2026. Grade A.
- URL: https://arxiv.org/abs/2510.15061
- "Some slop patterns appear over 1,000x more frequently in LLM output than human text." Their sampler suppresses 8,000+ patterns;
  their fine-tuning cuts slop 90 %. (The abstract names no phrases; a search summary says the paper singles out "it's not just X, it's
  Y", which could not be confirmed from the abstract.)

### 2.13 Russell, Karpinska, Iyyer (2025). "People who frequently use ChatGPT for writing tasks are accurate and robust detectors of AI-generated text." ACL 2025. Grade A.
- URL: https://aclanthology.org/2025.acl-long.267/
- 300 non-fiction articles (GPT-4o, Claude, o1 vs humans): the majority vote of 5 frequent-LLM-user annotators misclassified **1 of
  300**, beating most automatic detectors, even on paraphrased/"humanized" text. Their cues: "AI vocabulary", plus formality,
  originality and clarity.
- Relevance: the people who call a script "ChatGPT" are often heavy LLM users themselves, and they are accurate.

### 2.14 Industry / data-journalism studies (large data, not peer-reviewed)

**Graphite, "AI Tells"** (Druck, Paredes, Smith; 2026). Grade B. https://graphite.io/five-percent/research/ai-tells
- 10,000 pre-ChatGPT human web articles vs 90,000 AI articles on the same topics from 9 models (GPT-4.1, GPT-5, GPT-5.6 Sol, GPT-6
  Astra, Claude Opus 4 / 4.6 / 5, Gemini 2.5 Pro / 3.1 Pro). A tell = >= 2x the human rate.
- 12,877 tells; 65 % unique to one model family; 55-72 % change between consecutive versions. Well-known tells fell 41-86 % across
  versions, but total tells did not vanish (GPT's rose 48 %).
- **Corrective framing** ("not X, but Y" family) keeps rising: GPT-6 Astra ~12x humans ("not simply" 157x, "rather than relying"
  187x); Claude Opus 5 "rather than merely" 160x, "less like a _ and more like" 105x, "less X, more Y" ~82x; Gemini 3.1 Pro "is not
  just a _ it is" 153x.
- **Flagging importance:** "matters because" 357x (Astra), 132x (Opus 5); "distinction matters" never appears in the human set.
- Evaluative adjectives: dependable 59x, practical 26x, meaningful 13x (Astra); deliberate 26x, steady 6x (Opus 5); profound 25x,
  immense 22x, incredibly 18x (Gemini). Transitions: "together these" 95x, "looking ahead the" 33x, "ultimately this" 78x. "Without
  sacrificing/losing" 2.6-70x.
- Em dashes: Astra ~1/8 of the human rate; Opus 5 near human; Gemini nearly none.
- **Sentence length varies much less in AI text.** Words are longer (5.2-5.7 characters vs 4.9). Within-article lexical diversity
  (MTLD) is *higher* in AI text.
- **Human-only traits:** humans use exclamation marks >100x more than each current model, far more parenthetical asides, more first
  person, direct address, casual qualifiers, anecdotes and personal enthusiasm.
- Mannered prose (scored by Claude Opus 5): Opus 5 and Gemini 3.1 Pro ~2.5x human; Astra ~1.2x.
- The authors warn against judging authorship from single tells.

**The Washington Post analysis** (Merrill, Chen, Kumer; 2025-11-13), original
https://www.washingtonpost.com/technology/interactive/2025/how-detect-chatgpt-em-dash/ (403; the Wayback Machine blocked the fetch),
read via the syndicated copy https://www.bostonglobe.com/2025/11/13/business/chatgpt-writing-style-clues/. Grade B.
- 328,744 public English GPT-4o messages, May 2024 to July 2025. Em dash: <1 in 10 responses a year earlier, >half by summer 2025.
  "Not just X, but Y" in 6 % of chats (July 2025). Emoji in 70 % of messages. "Delve" down to 1 in 1,000 chats. "Ensure, various,
  crucial, significant, approach" declining; "core" 5x up; "modern" in >8 % of messages; contractions way up.

**Zanotto & Aroyehun (2025).** "Linguistic and Embedding-Based Profiling of Texts Generated by Humans and Large Language Models."
arXiv (EMNLP 2025 per the Underline listing). Grade B. https://arxiv.org/html/2507.13614v3
- RAID data, ~468k texts, 8 domains, 11 models: human texts vary more across domains and on the linguistic features; newer models'
  outputs are similarly variable among themselves (homogenization). Mean sentence length: humans 23.53 words, ChatGPT 19.29.

### 2.15 What the evidence agrees on (our reading of 2.1-2.14 plus section 1)

1. **Sameness is the strongest measured signal.** Less variation in sentence length, information density and complexity (2.5, 2.7,
   2.8, 2.9, Graphite, Zanotto). Even, mid-length sentence after mid-length sentence reads as machine; the newest GPT is reported to
   hold an 8-20 word band (section 1, sign 9).
2. **Specific style words, not "fancy" words.** Overuse is concentrated in a shifting set of verbs/adjectives (2.1, 2.3, Graphite,
   WaPo; Wikipedia's era lists). The set changes per model and year, so a fixed banned-word list goes stale.
3. **Corrective framing / negative parallelism** ("not X, but Y", "rather than", "less X, more Y") is measured at 12x to 150x+ human
   rates and still rising in the newest models (Graphite, WaPo 6 % of chats, Antislop, Wikipedia sign 11).
4. **Significance commentary**: "-ing" tails and "this matters because" (2.2 present participles 5.3x; Graphite "matters because"
   357x; Wikipedia signs 1, 3).
5. **What humans have that LLMs lack**: exclamations, question marks, ellipses, parenthetical asides, first person, direct address,
   anecdotes, slang, humor, irony, negative emotion, digressions, definitive superlatives, plain "is/has" verbs (2.5, 2.6, Graphite,
   Wikipedia 1.8).
6. **Templates come from pre-training and survive tuning** (2.4), and each model has a fingerprint (2.10), so rewording one sentence
   at a time won't remove a model's shape.
7. **Conflicting evidence:** lexical diversity is not a reliable test: HC3 found lower vocabulary density in ChatGPT, Graphite found
   *higher* MTLD in 2026 models, and Wikipedia lists "elegant variation" (forced synonyms) as an older-model tell. Em dashes went from
   top tell to under-used in GPT/Gemini by 2026.
8. **Not found:** no peer-reviewed measurement of the "rule of three" was found. It is listed by Wikipedia (sign 13) and reported by
   secondary coverage of Sam Kriss's NYT Magazine essay "Why Does A.I. Write Like ... That?" (2025-12-03). The NYT page and its Wayback
   copy **couldn't be read** (blocked), so nothing here is built on Kriss's wording. The Economist's "How to spot AI writing"
   (2026-07-30) was not read (paywall).

---

## 3. Practitioners: writing YouTube narration for the ear

### 3.1 Jonathan Kern, *Sound Reporting: The NPR Guide to Audio Journalism and Production*, as summarized by Michael Hernandez, "Writing for Broadcast: How to Sound Like A Real Person", JEA, 2012-02-28. Grade C.
- URL: https://jea.org/digital-media/writing-for-broadcast-how-to-sound-like-a-real-person
- Write the way you speak; picture telling the story to one person you know well.
- Use contractions ("doesn't", "it's", "we'll").
- Use everyday words: "but" instead of "however"; no words you wouldn't say in conversation.
- Short sentences, subject first: a listener can't re-read a tangled sentence.
- Active voice, with the people doing the action as the subject.
- Avoid hypothetical/rhetorical questions like "Have you ever wondered...?"
- Don't overload the ear with names and numbers; put key figures on screen.

### 3.2 George Blackman, YouTube scriptwriter (began as Ali Abdaal's full-time scriptwriter; clients include Ed Lawrence of Film Booth and Colin & Samir). Grade C.
- Creator Science podcast, ep. 162, host Jay Clouse, 2023-08-29: https://creatorscience.com/podcast/george-blackman/
  - Reads every script aloud *in the voice of the person who will say it*, as the test of whether it works as speech.
  - The audience should know "pretty much at all times what it is they're waiting around for next": one grand payoff plus smaller
    signposted payoffs.
  - Don't pay off too early and then pad; delay the reveal, give context or a metaphor first.
  - Make the audience feel smart; let them guess before you explain.
- Vidpros interview, 2026: https://vidpros.com/insiders/george-blackman-youtube-scriptwriting/
  - Each segment = setup, tension, payoff; stakes first so viewers know why the information matters; a retention dip means a weak
    setup, unclear stakes, or a flat previous payoff.
  - On AI: use it for the skeleton (segment order, arc), then write the language yourself; a one-prompt AI script is "pointless" and
    "soulless".

### 3.3 "How to Succeed in MrBeast Production" (internal MrBeast handbook, leaked 2024). Grade C (authenticity not confirmed by MrBeast; per search results, Passionfruit reported two former producers confirmed it).
- Read via the copy summarized at https://www.alexanderjarvis.com/memo-how-to-succeed-in-mrbeast-production/ ; provenance per
  https://passionfru.it/mrbeast-leaked-document-81151/ (search summary).
- "The first minute of each video is the most important minute of each video": deliver what the title/thumbnail promised,
  immediately.
- After the opening, "stop telling people what they will be watching and start showing them".
- Plan re-engagement beats (around minutes 3 and 6); no dull moments; "the simpler the better"; endings abrupt to protect retention.
- The memo itself says to apply it "with a grain of salt".

### 3.4 Trey Parker & Matt Stone's "But/Therefore" rule (South Park), as written up by David Perell. Grade C.
- URL: https://perell.com/note/but-therefore-rule/ (undated)
- Beats joined by "and then" make a boring list; beats joined by "but" or "therefore" give cause and effect, which is a story.
- Applying it to a non-fiction narration (each line causes or complicates the next) is our extrapolation, not Perell's.

### 3.5 vidIQ, "How to Write a YouTube Video Script That Keeps Viewers Watching", Lydia Sweatt (Blog Manager), reviewed by Darryl Rentz, updated 2026-07-21. Grade C.
- URL: https://vidiq.com/blog/post/write-youtube-video-script/
- Write the way you talk; simple, casual words; talk to viewers, not at them.
- Short sentences but **varied lengths**; active voice.
- Read the script aloud; rewrite anything stiff or hard to say; trim filler and repetition.
- Budget ~125-150 spoken words per minute.
- If AI drafts, rewrite in your own voice, add original examples, verify every claim (quoting vidIQ's Alina Daineko on research
  mistakes).

### 3.6 ElevenLabs documentation, "Best practices" (no date on page). Grade C (vendor, but it is the voice tool's own manual).
- URL: https://elevenlabs.io/docs/best-practices/prompting
- Punctuation drives rhythm; ellipses add pause and weight; dashes give short, hesitant pauses; capitals add emphasis; too many break
  tags cause instability.
- If an LLM writes the script, have it spell out numbers, expand abbreviations and convert symbols to spoken form.
- Wording shapes delivery: write in a natural, narrative style; try alternate phrasing to change pacing or emotion; generate several
  takes and pick.

### 3.7 Lower-grade sources that name AI *narration* templates (direction only)
- **Haris Mazhar, "9 AI Script Patterns Killing Your YouTube Channel", Fyre Interactive, 2026-03-16.** Grade D (sells a script
  product; the frequency figures, e.g. "about 60 %", have no method). https://fyreinteractive.co/blog/9-ai-script-patterns-killing-your-channel/
  - Patterns: "To understand why..." setup lines; stock re-hooks ("...but what happened next was even worse"); "Now, let's talk
    about..." returns; formula transitions ("But things were about to get much worse"); rigid "First... Second... Finally..."
    evidence stacks; reaction lines after a fact ("Yeah, you read that right"); announced foreshadowing ("But they had no idea what
    was coming"); moral outros ("Their story shows us that..."); "However" as the default contrast word.
  - Fixes: start on the conflict or a specific detail; let concrete detail carry tension and surprise; transitions specific to what
    actually changes; end on a fact or open question.
- **"7 Ways I Make My AI Scripts Sound Human", The AI Personal Brand (Iman Oubou), Substack, 2026.** Grade D (credentials not
  stated). https://imanoubou.substack.com/p/7-ways-i-make-my-ai-scripts-sound
  - Join thoughts with "and/so/but/because" instead of chopping every idea into its own sentence; contractions; real numbers, names
    and mistakes ("receipts") that the AI must not invent; natural markers ("Okay, so...", "Honestly...") where they help rhythm;
    delete one-word dramatic sentences, manufactured rhetorical questions, three-item lists ("Faster. Smarter. Better.") and "It's not
    X, it's Y"; perform it aloud; talk to one person.

### 3.8 Searched, not found or not usable
- Paddy Galloway: his public interviews found (Colin & Samir, Creator Science) are about ideas and packaging; no written script-voice
  advice found.
- Hayden Hillier-Smith, Kallaway, Jenny Hoyos, Jake Thomas (Creator Hooks): only third-party or AI-generated summaries found; not used.
- NPR Training's own "writing for the ear" pages: training.npr.org now redirects to npr.org/sections/npr-training; not reached, so Kern
  is cited through JEA.

### 3.9 Practitioner consensus (our reading)
All the credible sources converge on: write it the way it's said (contractions, everyday words, one listener); vary sentence length;
subject-first, active voice; read it aloud in the speaker's voice; concrete specifics over announcements ("show, don't tell people
what they'll watch"); every beat caused by or complicating the one before (but/therefore); keep the viewer aware of what payoff
they're waiting for. The lower-grade sources add the narration-specific AI templates to cut: stock re-hooks, "Now let's talk about",
reaction lines after facts, moral outros, three-item lists, "It's not X, it's Y".
