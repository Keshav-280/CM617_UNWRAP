# UNWRAP: Unpacking Whether Replacement Alternatives Perform

CM617 Sustainability Principles and Practices, IIT Bombay (course research project, October 2026)

Paridhi Mittal (23B0387), Eshika Mishra (23B0371), Keshav Goyal (23B2121), Kunal Jain (23B0670)

A paired meta-analysis of packaging life cycle assessments under Indian collection rates and an honest functional unit
(31 within-study pairs from 16 LCAs, an India recycling model for beverage containers, and a per-kg-of-product-used model for shampoo packs).

## Contents

| Folder | What is inside |
|---|---|
| `report/` | `UNWRAP_report_final.pdf` - the full report |
| `data/` | `UNWRAP_data_and_results.xlsx` (all extracted data, results and model sheets), `paired_comparisons.csv` (the 46 extracted pairs), `prisma_log.csv` (screening flow) |
| `video/` | The explainer video: **`UNWRAP_video.mp4`** (final render, 4:15, with voice-over and music), the interactive source `UNWRAP_video.html`, the narration script, and the scripts that generate the voice-over, music and the mp4 (`make_voiceover.py`, `make_music.py`, `render_video.py`) |
| `archive/` | Earlier drafts and duplicate exports, kept for reference |

## Watching the video

Open `video/UNWRAP_video.html` in Chrome or Edge. Keep `voiceover.js` and `music.js` in the same folder.
Press Play (or `R` for record mode). Wait for "voice + music ready" in the control bar first.

To regenerate the audio: `pip install edge-tts numpy scipy lameenc`, then
`python make_voiceover.py` and `python make_music.py` (the voice step needs internet).
