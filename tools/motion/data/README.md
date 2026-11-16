# tools/motion/data

The creator's own lists that the motion tools read. Every file starts empty; a missing file counts as empty. One line per file: its
shape, then who reads it.

- `masters.json` `{}`: `{"<code>": {"file": "<the master's file name as the clips manifest names it>", "proxy": "<its 480p proxy in FOOTAGE/index/proxies>", "picture": [x0, y0, x1, y1]}}`, "picture" optional (the picture inside a letterboxed master's bars, as fractions); a master's frame-accurate shots go in `KB/footage/brain/<code>.json` as `{"shots": [{"in": s, "out": s}]}` or `{"fps": n, "shots": [{"f_in": n, "f_out": n}]}`. Read by qa_shots.py and qa_continued.py.
- `curate_masters.json` `{}`: `{"<key>": "<path under FOOTAGE, or a full path>"}`, the masters a hand-picked Short's shots and the cut-outs' `sigs.json` name by key. Read by curate.py, frame_cur.py, asset_ledger.py.
- `master_crops.json` `{}`: `{"<curate_masters key>": "<ffmpeg crop of the 16:9 picture inside a letterboxed master>"}`. Read by asset_ledger.py.
- `artwork.json` `{}`: `{"art": [...], "people_art": [...], "people": [...], "screenshots": [...]}`, folders relative to FOOTAGE: every key-art folder; key-art folders whose subfolders are named by the people they show (e.g. "Anna_and_Ben_Garden"); the source's own picture folders with one subfolder per person (e.g. "Anna Lee"); the source's own screenshot folders (never key art). Read by qa_shots.py.
- `house_avatars.json` `[]`: the creator's own avatar file names (logos, no face to centre), skipped by the icon checks. Read by qa_shots.py.
- `moment_words.json` `[]`: extra regexes on the lower-case words with punctuation dropped (e.g. `"in (?:the )?launch video"`) that name the source's own videos, for CARD_FOR_MOMENT. Read by qa_still_words.py.
- `ui_picture_names.json` `[]`: plain parts of picture file names that mark the source's own interface icon (drawn round as it is, never a crop). Read by qa_devices.py.
- `receipts.json` `{}`: `{"<key>": {"src": "<published path>", "c": [x, y, w, h]}}`, the page captures a hand-picked Short's shot can carry (`rc`), with the page crop. Read by curate.py and qa_framing.py.
- `delivered_videos.json` `[]`: `[{"video": "012", "title": "...", "kind": "long|short|proto", "comp": "<composition id>", "module": "<src folder>/<file, no .tsx>", "export": "<component>", "seconds": "<exported seconds const>" or "props_json": "<src-relative json>", "shots": "SHOTS" (optional), "size": [w, h], "date": "YYYY-MM-DDTHH:MM", "folders": ["<its own src folders>"], "delivered": "<mp4 path>"}]`, every finished video, added when it ships. Read by asset_ledger.py.
- `panel_scales.json` `{}`: `{"<Component>": {"clip": "<prop naming the clip>", "w": "<width prop>", "w_default": px, "push": x}}` (or `"push_prop"` + `"push_default": [from, to]`, or `"k"` + `"k_default": [from, to]` for an inset whose scale is given directly), the creator's own components that show a clip smaller than the screen. Read by qa_kept_area.py.
- `caption_phrases.json` `[]`: `[["<word>", "<word>", ...], ...]`, multi-word names that are always one caption, the longer phrases first. Read by finish_short.py.
- `numbered_titles.json` `[]`: `["<title word>", ...]`, titles followed by a number: the number always captioned as a digit (a Roman numeral becomes its digit) and title and number one caption. Read by finish_short.py.
