# PinP2-YOLO offline presentation

Double-click **index.html** in Chrome or Edge. Keep this folder and its **assets/** subfolder together. All slides, figures, CSS, JavaScript and the original MP4 are local. The presentation uses a fixed 16:9 canvas scaled to the available window. **F** or the **Full screen** button fills the display in slide-show mode.

- **Next**, **Previous**, **→**, **←**, **Page Down**, **Page Up**, or **Space** advance or return as appropriate. Keyboard focus on a button or link retains its normal Space/Enter behavior.
- **F** toggles slideshow fullscreen. **Esc** exits fullscreen. On page 12, **Previous** returns to the conclusion.
- **Export PDF** opens the browser print dialog. Choose **Save as PDF** in Chrome or Edge. The export uses the 13 slides, one per page, and shows a still image on the video slide.
- A small animated drone follows the mouse. Press **M** to toggle it. Native video controls use the regular pointer. The rotor animation follows the system's reduced-motion preference.
- The deck contains 13 pages. Page 11 is the conclusion, page 12 is the video demonstration, and page 13 is the closing page. Use **Next** or **Previous** to move between them.
- On page 12, **Play full video** starts the 3:46 recording in fullscreen. The browser returns to page 12 after the recording ends. You can also use the native playback controls or press **Esc** to leave fullscreen early.
- Use **speaker_notes.md** for the English script, Chinese prompts and timing. **qa_backup.md** contains English answers. **data_audit.md** traces each figure and measurement.
- On page 5, use **Table I** and **Fig. 3** to switch between benchmark numbers and qualitative results. On page 9, **Fig. 4** shows the same-image NMS example and **Threshold sweep** shows the aggregate false positives. Both switches work offline.
- The bottom-right GitHub links open the evidence for the current slide in a new tab and require internet access. A short walkthrough can use **Full model diagram** (page 4), **Training scale results** (page 8), and **Full NMS threshold chart** (page 9). The demo page links to the public release. Close the GitHub tab to return to the same slide. If needed, press **F** again to restore fullscreen.

The original user-provided **项目演示.mp4** is copied as **assets/project-demo.mp4** (about 38 MB). If a managed browser blocks local media playback, open a terminal in this folder and run:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Then visit **http://127.0.0.1:8000/**. This fallback stays on the local computer and requires Python. The direct file version requires no installation. If media playback is unavailable on the presentation computer, switch to the still screenshot.

The course guideline allocates 10 minutes for the main talk and 5 minutes for Q&A. It mentions a separate setup allowance for teams demonstrating. Confirm playback time with the session chair. The 10-slide talk can be presented on its own.
