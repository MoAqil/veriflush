"""Edit the one-minute VeriFlush video from the team's recordings and the digital-prototype assets.

Inputs (in ../video_raw): vidA.mp4 (rig running), vidB.mp4 (presenter), rec25.m4a (voice-over),
rec26.m4a (rig voice), words.json (word timings from faster-whisper).
Output: 1920x1080 30 fps H.264 MP4 with burned-in subtitles, <= 60 s.
Speech is sped up 1.09x and long pauses trimmed so the cut fits 60 s; nothing else is changed.
Run:  python video/build_video.py <output.mp4>
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

DP = Path(__file__).resolve().parents[1]
RAW = DP.parent / "video_raw"
B = RAW / "build"
B.mkdir(exist_ok=True)
OUT = Path(sys.argv[1])

W, H, FPS, TEMPO, XF = 1920, 1080, 30, 1.09, 0.5
NAVY, INK, WHITE = (11, 31, 51), (20, 28, 38), (255, 255, 255)
AMBER, BLUE, GREEN, RED = (232, 155, 46), (66, 146, 226), (46, 158, 91), (192, 57, 43)
FONTS = "C:/Windows/Fonts/"


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


WORDS = json.load(open(RAW / "words.json"))
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS)]


def run(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, check=True, cwd=B)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, cwd=B)
    return float(r.stdout.strip())


def w(src, i):
    return WORDS[src][i]          # (word, start, end)


# ---------------- audio: trim pauses, clean, speed up ----------------
def make_audio(src, intervals, out, denoise="afftdn=nf=-25"):
    parts, labels = [], []
    for k, (a, b) in enumerate(intervals):
        parts.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[p{k}]")
        labels.append(f"[p{k}]")
    chain = (";".join(parts) + ";" + "".join(labels) + f"concat=n={len(intervals)}:v=0:a=1,"
             f"highpass=f=80,{denoise},atempo={TEMPO},loudnorm=I=-16:TP=-1.5:LRA=11,"
             "aresample=48000[out]")
    run(["-i", str(src), "-filter_complex", chain, "-map", "[out]", "-ac", "2", out])

    def tmap(t):
        acc = 0.0
        for a, b in intervals:
            if t <= b:
                return (acc + max(t - a, 0.0)) / TEMPO
            acc += b - a
        return acc / TEMPO
    return duration(B / out), tmap


# ---------------- stills ----------------
def cover(img):
    img = img.convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def tag(img, text, color=BLUE):
    d = ImageDraw.Draw(img)
    f = font("seguisb.ttf", 30)
    tw = d.textbbox((0, 0), text, font=f)[2]
    d.rounded_rectangle((56, 48, 56 + tw + 44, 48 + 56), radius=28, fill=(0, 0, 0, 170) if img.mode == "RGBA"
                        else (14, 22, 32))
    d.ellipse((74, 68, 90, 84), fill=color)
    d.text((100, 56), text, font=f, fill=WHITE)
    return img


def overlay_png(text, color, name):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tag(img, text, color)
    img.save(B / name)
    return name


def zoom_clip(img, dur, out, z1=1.07, cx=0.5, cy=0.5):
    png = out.replace(".mp4", ".png")
    img.save(B / png)
    n = int(round(dur * FPS))
    vf = (f"scale=3840:2160,zoompan=z='1+({z1}-1)*on/{n}':x='(iw-iw/zoom)*{cx}':y='(ih-ih/zoom)*{cy}'"
          f":d={n}:s={W}x{H}:fps={FPS},format=yuv420p")
    run(["-loop", "1", "-i", png, "-vf", vf, "-frames:v", str(n)] + ENC + ["-an", out])


def video_clip(src, start, length, dur, out, extra="", overlay=None, stab=False):
    """take [start, start+length] of src, retime to dur, upscale, clean, optional overlay"""
    speed = length / dur
    vf = "vidstabtransform=input=t.trf:smoothing=25:zoom=4," if stab else ""
    vf += f"trim={start:.3f}:{start + length:.3f},setpts=(PTS-STARTPTS)/{speed:.5f}"
    vf += (f",scale={W}:{H}:flags=lanczos,hqdn3d=1.5:1.5:0:0,eq=contrast=1.06:saturation=1.12:brightness=0.015,"
           f"unsharp=5:5:0.45,fps={FPS}{extra}")
    args = ["-i", str(src)]
    if overlay:
        args += ["-i", overlay]
        fc = f"[0:v]{vf}[v];[v][1:v]overlay=0:0,format=yuv420p[o]"
        run(args + ["-filter_complex", fc, "-map", "[o]", "-t", f"{dur:.3f}"] + ENC + ["-an", out])
    else:
        run(args + ["-vf", vf + ",format=yuv420p", "-t", f"{dur:.3f}"] + ENC + ["-an", out])


def xfade(clips, durs, out):
    if len(clips) == 1:
        run(["-i", clips[0], "-c", "copy", out])
        return
    args, fc, prev, off = [], [], "[0:v]", 0.0
    for c in clips:
        args += ["-i", c]
    for k in range(1, len(clips)):
        off += durs[k - 1] - XF
        lab = f"[x{k}]"
        fc.append(f"{prev}[{k}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}{lab}")
        prev = lab
    run(args + ["-filter_complex", ";".join(fc), "-map", prev] + ENC + ["-an", out])


def shots(boundaries, total):
    """durations of crossfaded clips whose cut points land on the given times"""
    cuts = boundaries + [total]
    return [(cuts[k + 1] - cuts[k]) + (XF if k < len(cuts) - 2 else 0) for k in range(len(cuts) - 1)]


def mux(video, audio, dur, out, fade_in=0.2, fade_out=0.2):
    vf = f"fade=t=in:st=0:d={fade_in},fade=t=out:st={dur - fade_out:.3f}:d={fade_out}"
    af = f"afade=t=in:st=0:d=0.05,afade=t=out:st={dur - 0.1:.3f}:d=0.1"
    run(["-i", video, "-i", audio, "-vf", vf, "-af", af, "-t", f"{dur:.3f}"] + ENC +
        ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", out])


R = DP / "3d" / "renders"
segments, subs = [], []


def add_subs(src, chunks, tmap, offset):
    for i, j, text in chunks:
        subs.append((offset + tmap(w(src, i)[1]), offset + tmap(w(src, j)[2]) + 0.15, text))


# ================= segment 1: title + hook =================
iv1 = [(0.70, w("rec25.wav", 16)[2] + 0.25)]
d1, m1 = make_audio(RAW / "rec25.m4a", iv1, "a1.wav")
title = cover(Image.open(R / "S01_healthy_wide_t0.png"))
title = Image.blend(title, Image.new("RGB", (W, H), NAVY), 0.66)
dr = ImageDraw.Draw(title)
dr.rectangle((160, 352, 300, 360), fill=AMBER)
dr.text((156, 380), "VeriFlush", font=font("bahnschrift.ttf", 168), fill=WHITE)
dr.text((162, 590), "Smart Verification of Water Exchange", font=font("seguisb.ttf", 54), fill=WHITE)
dr.text((162, 660), "in Building Plumbing Systems", font=font("seguisb.ttf", 54), fill=WHITE)
dr.text((162, 780), "CMAT-00196   ·   Theme 3: Smart, Digital and AI-Enabled Water Systems   ·   Team Gurt",
        font=font("segoeui.ttf", 32), fill=(200, 214, 228))
hook = tag(cover(Image.open(R / "S01_healthy_wide_t0.png")), "Stagnant water in a low-use branch  ·  3D model",
           AMBER)
b1 = [0.0, min(4.6, d1 - 1.2)]
s1 = shots(b1, d1)
zoom_clip(title, s1[0], "v1a.mp4", 1.04)
zoom_clip(hook, s1[1], "v1b.mp4", 1.10, 0.55, 0.45)
xfade(["v1a.mp4", "v1b.mp4"], s1, "v1.mp4")
mux("v1.mp4", "a1.wav", d1, "seg1.mp4", fade_in=0.01)
add_subs("rec25.wav", [(0, 8, "Hotel rooms and school wings sit empty for days,"),
                       (9, 16, "and before they're reused, their pipes get flushed.")], m1, 0.0)
segments.append("seg1.mp4")

# ================= segment 2: presenter (live audio) =================
a, b = w("vidB.wav", 0)[1] - 0.30, w("vidB.wav", 28)[2] + 0.35
d2, m2 = make_audio(RAW / "vidB.mp4", [(a, b)], "a2.wav", denoise="afftdn=nf=-20,afftdn=nf=-20")
video_clip(RAW / "vidB.mp4", a, b - a, d2, "v2.mp4")
mux("v2.mp4", "a2.wav", d2, "seg2.mp4")
off2 = duration(B / "seg1.mp4")
add_subs("vidB.wav", [(0, 10, "But a flush log only says a timer ran out."),
                      (11, 20, "It doesn't actually prove that the stagnant water was replaced."),
                      (21, 28, "This is the gap that VeriFlush closes.")], m2, off2)
segments.append("seg2.mp4")

# ================= segment 3: the digital prototype =================
src = "rec25.wav"
iv3 = [(w(src, 17)[1] - 0.20, w(src, 24)[2] + 0.15), (w(src, 25)[1] - 0.15, w(src, 43)[2] + 0.15),
       (w(src, 44)[1] - 0.15, w(src, 68)[2] + 0.30)]
d3, m3 = make_audio(RAW / "rec25.m4a", iv3, "a3.wav")
b3 = [0.0, m3(w(src, 25)[1]), m3(w(src, 38)[1]), m3(w(src, 44)[1]), m3(w(src, 59)[1])]
s3 = shots(b3, d3)
hero = tag(cover(Image.open(R / "S01_healthy_wide_t22.png")), "VeriFlush digital twin  ·  SIMULATED")
zoom_clip(hero, s3[0], "v3a.mp4", 1.12, 0.55, 0.5)
anim_tag = overlay_png("3D flush driven by the simulation  ·  amber = old, blue = fresh  ·  SIMULATED", BLUE,
                       "tag_anim.png")
video_clip(R / "S01_healthy_flush.mp4", 1.0, 14.0, s3[1], "v3b.mp4", overlay=anim_tag)
chips = cover(Image.open(R / "S01_healthy_coil_t22.png")).filter(ImageFilter.GaussianBlur(14))
chips = Image.blend(chips, Image.new("RGB", (W, H), NAVY), 0.55)
dc = ImageDraw.Draw(chips)
dc.text((W // 2, 300), "Every flush gets one of three verdicts", font=font("seguisb.ttf", 56), fill=WHITE,
        anchor="mm")
for k, (lab, col) in enumerate([("VERIFIED", GREEN), ("FAILED", RED), ("UNCERTAIN", AMBER)]):
    x0 = 300 + k * 460
    dc.rounded_rectangle((x0, 440, x0 + 400, 600), radius=34, fill=col)
    dc.text((x0 + 200, 520), lab, font=font("bahnschrift.ttf", 62), fill=WHITE, anchor="mm")
for k, sub in enumerate(["enough water reached the end", "blocked or too little flow", "evidence missing: staff check"]):
    dc.text((500 + k * 460, 650), sub, font=font("segoeui.ttf", 30), fill=(215, 225, 235), anchor="mm")
tag(chips, "Decision logic  ·  SIMULATED")
zoom_clip(chips, s3[2], "v3c.mp4", 1.05)
epa = tag(cover(Image.open(DP / "outputs/epanet_gui/S05_diversion_map_t30s.png").crop((0, 130, 1389, 822))),
          "EPANET 2.2  ·  side branch open: half the water leaves early  ·  SIMULATED", AMBER)
zoom_clip(epa, s3[3], "v3d.mp4", 1.12, 0.35, 0.6)
dash = Image.open(DP / "outputs/screenshots/S05_diversion__veriflush_end.png").crop((0, 140, 1366, 908))
dash = tag(cover(dash), "VeriFlush dashboard  ·  keeps flushing until the branch is exchanged  ·  SIMULATED",
           GREEN)
zoom_clip(dash, s3[4], "v3e.mp4", 1.10, 0.8, 0.3)
xfade(["v3a.mp4", "v3b.mp4", "v3c.mp4", "v3d.mp4", "v3e.mp4"], s3, "v3.mp4")
mux("v3.mp4", "a3.wav", d3, "seg3.mp4")
off3 = off2 + duration(B / "seg2.mp4")
add_subs(src, [(17, 24, "VeriFlush is a digital twin and controller."),
               (25, 37, "It tracks flow, volume and the temperature at the end of the pipe,"),
               (38, 43, "then decides: Verified, Failed or Uncertain."),
               (44, 53, "Here, half of the water escapes through a side branch,"),
               (54, 58, "then the timer says done."),
               (59, 68, "VeriFlush keeps going until the branch is really exchanged.")], m3, off3)
segments.append("seg3.mp4")

# ================= segment 4: results chart (animated) =================
iv4 = [(w(src, 69)[1] - 0.20, w(src, 91)[2] + 0.45)]
d4, m4 = make_audio(RAW / "rec25.m4a", iv4, "a4.wav")
fr = B / "chart"
fr.mkdir(exist_ok=True)
bars = [("Fixed timer", 37, AMBER, m4(w(src, 78)[1])), ("Flow + volume", 31, AMBER, m4(w(src, 87)[1])),
        ("VeriFlush", 0, BLUE, m4(w(src, 91)[1]))]
fT, fL, fV, fS = font("seguisb.ttf", 54), font("seguisb.ttf", 42), font("bahnschrift.ttf", 86), font("segoeui.ttf", 30)
n4 = int(round(d4 * FPS))
for f in range(n4):
    t = f / FPS
    im = Image.new("RGB", (W, H), NAVY)
    dr = ImageDraw.Draw(im)
    dr.text((160, 170), "False passes in 520 simulated flushes per method", font=fT, fill=WHITE)
    dr.text((160, 245), "\u201cVerified\u201d while more than 5 % old water was still in the pipe", font=fS,
            fill=(185, 200, 216))
    for k, (lab, val, col, t0) in enumerate(bars):
        y = 400 + k * 190
        p = min(max((t - t0 + 0.15) / 0.7, 0.0), 1.0)
        p = 1 - (1 - p) ** 3
        dr.text((160, y + 30), lab, font=fL, fill=WHITE)
        dr.rounded_rectangle((620, y + 10, 620 + 900, y + 110), radius=18, fill=(26, 52, 78))
        if val and p > 0:
            dr.rounded_rectangle((620, y + 10, 620 + int(900 * val / 40 * p), y + 110), radius=18, fill=col)
        if p > 0:
            dr.text((1560, y + 8), f"{round(val * p)} %", font=fV, fill=col if val else (120, 200, 255))
    tag(im, "Digital prototype results  ·  SIMULATED")
    im.save(fr / f"f{f:04d}.jpg", quality=94)
run(["-framerate", str(FPS), "-i", "chart/f%04d.jpg"] + ENC + ["-an", "v4.mp4"])
mux("v4.mp4", "a4.wav", d4, "seg4.mp4")
off4 = off3 + duration(B / "seg3.mp4")
add_subs(src, [(69, 72, "Across 520 simulated flushes,"), (73, 82, "timers passed stale water 37% of the time,"),
               (83, 87, "and flow meters only 31%,"), (88, 91, "but VeriFlush: zero.")], m4, off4)
segments.append("seg4.mp4")

# ================= segment 5: the physical prototype running =================
s5 = "rec26.wav"
iv5 = [(w(s5, 0)[1] - 0.20, w(s5, 10)[2] + 0.20), (w(s5, 11)[1] - 0.15, w(s5, 22)[2] + 0.35)]
d5, m5 = make_audio(RAW / "rec26.m4a", iv5, "a5.wav")
phys = overlay_png("PHYSICAL PROTOTYPE  ·  pump on, sensors logging live", GREEN, "tag_phys.png")
tail = 1.1                                   # serial-monitor close-up at the end of the walk-around
run(["-i", str(RAW / "vidA.mp4"), "-vf", "deshake=rx=32:ry=32:edge=mirror,crop=iw*0.94:ih*0.94",
     "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-an", "vidA_stab.mp4"])   # vidstab garbled this clip
video_clip(B / "vidA_stab.mp4", 1.0, 11.2, d5 - tail + XF, "v5a.mp4", overlay=phys)
video_clip(RAW / "vidA.mp4", 15.15, 0.8, tail, "v5b.mp4", overlay=phys)
xfade(["v5a.mp4", "v5b.mp4"], [d5 - tail + XF, tail], "v5.mp4")
mux("v5.mp4", "a5.wav", d5, "seg5.mp4")
off5 = off4 + duration(B / "seg4.mp4")
add_subs(s5, [(0, 10, "And this is our physical prototype: the same sensors, logging live."),
              (11, 15, "Dubai already requires weekly flushing."),
              (16, 22, "VeriFlush turns that log into evidence.")], m5, off5)
segments.append("seg5.mp4")

# ================= segment 6: end card =================
end = Image.new("RGB", (W, H), NAVY)
de = ImageDraw.Draw(end)
de.rectangle((W // 2 - 70, 250, W // 2 + 70, 258), fill=AMBER)
de.text((W // 2, 360), "Team Gurt", font=font("bahnschrift.ttf", 130), fill=WHITE, anchor="mm")
de.text((W // 2, 470), "Khalifa University", font=font("seguisb.ttf", 50), fill=(210, 222, 234), anchor="mm")
de.text((W // 2, 590), "Mohammed Aqil Mohideen   ·   Fawaz Ahmad   ·   Mohamad Zaheen (team leader)   ·   "
        "Alvin Alex", font=font("segoeui.ttf", 36), fill=WHITE, anchor="mm")
de.text((W // 2, 690), "VeriFlush   ·   CMAT-00196   ·   Theme 3", font=font("segoeui.ttf", 34),
        fill=(185, 200, 216), anchor="mm")
de.text((W // 2, 900), "Digital results SIMULATED (VeriFlush v1.2.0)  ·  physical prototype under calibration  ·  "
        "no music  ·  github.com/MoAqil/veriflush", font=font("segoeui.ttf", 26), fill=(150, 170, 190), anchor="mm")
d6 = 2.2
zoom_clip(end, d6, "v6.mp4", 1.03)
run(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(d6), "a6.wav"])
mux("v6.mp4", "a6.wav", d6, "seg6.mp4", fade_out=0.4)
segments.append("seg6.mp4")

# ================= assemble, subtitles, export =================
args, fc = [], []
for k, sg in enumerate(segments):           # re-encode join: segments differ in colour range (chart is full-range)
    args += ["-i", sg]
    fc.append(f"[{k}:v]scale={W}:{H}:in_range=auto:out_range=tv,format=yuv420p,setsar=1,fps={FPS}[v{k}]")
fc.append("".join(f"[v{k}][{k}:a]" for k in range(len(segments))) + f"concat=n={len(segments)}:v=1:a=1[v][a]")
run(args + ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]"] + ENC +
    ["-c:a", "aac", "-b:a", "160k", "joined.mp4"])


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round(t % 1 * 1000)) % 1000:03d}"


subs.sort()
lines = []
for k, (s, e, text) in enumerate(subs):
    if k + 1 < len(subs):
        e = min(e, subs[k + 1][0] - 0.05)
    e = max(e, s + 0.8)
    lines.append(f"{k + 1}\n{ts(s)} --> {ts(e)}\n{text}\n")
(B / "subs.srt").write_text("\n".join(lines), encoding="utf-8")
style = ("FontName=Segoe UI Semibold,FontSize=13,PrimaryColour=&H00FFFFFF,OutlineColour=&H8C000000,"
         "BorderStyle=3,Outline=5,Shadow=0,MarginV=26,MarginL=60,MarginR=60")
run(["-i", "joined.mp4", "-vf", f"subtitles=subs.srt:force_style='{style}'"] + ENC +
    ["-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(OUT)])
print(f"saved {OUT}  duration {duration(OUT):.2f} s  size {OUT.stat().st_size / 1e6:.1f} MB")
