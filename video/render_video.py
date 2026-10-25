"""Render UNWRAP_video.html to a real MP4 (picture + voice-over + music).

How it works
  1. Opens the page in headless Chrome/Edge at 1280x720 and steps through it frame by frame. All CSS
     animations/transitions are paused and advanced by exactly one frame at a time, so the result is smooth and
     never drops frames, whatever the speed of the computer.
  2. Mixes the narration (placed at the exact times the page uses) and the music (ducked under the voice) into one track.
  3. ffmpeg joins both into UNWRAP_video.mp4.

Usage:  python render_video.py [fps]          (default 30; needs playwright, imageio-ffmpeg, numpy, scipy)
"""
import json, pathlib, subprocess, sys, time
import numpy as np
from scipy.io import wavfile
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
SR = 44100
OUT = HERE / "UNWRAP_video.mp4"
WAV = HERE / "audio" / "final_mix.wav"
URL = (HERE / "UNWRAP_video.html").resolve().as_uri()

STEP_JS = """
(() => {
  window.__seen = new Set();
  window.__step = (t, dtMs) => {
    for (const a of window.__seen) { try { if (a.playState === 'idle') window.__seen.delete(a); else a.currentTime = (a.currentTime || 0) + dtMs; } catch (e) {} }
    render(t);
    for (const a of document.getAnimations()) {
      if (!window.__seen.has(a)) { window.__seen.add(a); a.pause(); a.currentTime = 0; }
    }
  };
})()
"""

def decode(path):
    p = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype="<f4").reshape(-1, 2)

def build_audio(tl):
    total = tl["total"]
    n = int(total * SR) + SR
    mix = np.zeros((n, 2), dtype=np.float32)
    # music with the same ducking curve the page uses
    music = decode(HERE / "audio" / "music.mp3")[: n]
    pts = np.array(tl["pts"], dtype=float)
    tt = np.arange(len(music)) / SR
    music = music * np.interp(tt, pts[:, 0], pts[:, 1])[:, None].astype(np.float32)
    mix[: len(music)] += music
    # voice-over per scene
    for sc in tl["scenes"]:
        f = HERE / "audio" / f"{sc['id']}.mp3"
        if not f.exists():
            continue
        v = decode(f) * 1.25
        i = int((sc["start"] + tl["lead"]) * SR)
        j = min(n, i + len(v))
        mix[i:j] += v[: j - i]
    peak = float(np.max(np.abs(mix)))
    if peak > 0.95:
        mix *= 0.95 / peak
    wavfile.write(str(WAV), SR, (mix * 32767).astype("<i2"))
    print("audio mix written, peak", round(peak, 2))

def main():
    with sync_playwright() as p:
        browser = None
        for ch in ("chrome", "msedge"):
            try:
                browser = p.chromium.launch(channel=ch, headless=True, args=["--autoplay-policy=no-user-gesture-required"])
                break
            except Exception as e:
                print("could not start", ch, e)
        if browser is None:
            sys.exit("Install Google Chrome or Microsoft Edge")
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        page.goto(URL)
        page.wait_for_function("typeof SCENES!=='undefined' && typeof render==='function'")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(1500)
        page.evaluate("document.body.classList.add('rec'); fit(); document.getElementById('bar').style.display='none'")
        tl = page.evaluate("({total:TOTAL, lead:LEAD, pts:musicLevel(), scenes:SCENES.map(s=>({id:s.id,start:s.start,dur:s.dur}))})")
        print("timeline", round(tl["total"], 1), "s")
        build_audio(tl)
        page.evaluate(STEP_JS)
        frames = int(tl["total"] * FPS) if len(sys.argv) < 3 else int(sys.argv[2])
        cmd = [FFMPEG, "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
               "-i", str(WAV), "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
               "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(OUT)]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=open(HERE / "audio" / "ffmpeg.log", "w"))
        dt = 1000.0 / FPS
        t0 = time.time()
        for i in range(frames):
            t = i / FPS
            page.evaluate("([t,d])=>window.__step(t,d)", [t, 0 if i == 0 else dt])
            ff.stdin.write(page.screenshot(type="jpeg", quality=93))
            if i % 300 == 0:
                print(f"frame {i}/{frames}  ({time.time()-t0:.0f}s elapsed)", flush=True)
        ff.stdin.close(); ff.wait()
        browser.close()
    print("done:", OUT)

main()
