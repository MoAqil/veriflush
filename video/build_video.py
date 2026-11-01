"""Edit the one-minute VeriFlush video: clean editorial style, cuts only in real silences.

Inputs (in ../video_raw): vidA.mp4 (rig running), vidB.mp4 (presenter), rec25.m4a (voice-over),
rec26.m4a (rig voice), words.json (word timings from faster-whisper, used for subtitles and visual cues).
Audio is cut only inside pauses measured with silencedetect (never mid-word); long pauses are shortened
to 0.4 s and speech is played 1.05x. Output: 1920x1080 30 fps H.264, burned-in subtitles, < 60 s.
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

W, H, FPS, TEMPO, XF = 1920, 1080, 30, 1.05, 0.5
BG, INK, MUTE, LINE = (244, 242, 237), (30, 32, 36), (118, 122, 128), (214, 210, 202)
BLUE, AMBER, GREEN, RED = (38, 104, 168), (196, 138, 62), (46, 122, 86), (168, 62, 52)
FONTS = "C:/Windows/Fonts/"
WORDS = json.load(open(RAW / "words.json"))
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS)]


def font(name, size):
    return ImageFont.truetype(FONTS + name, size)


LIGHT, SEMI, BOLD, REG = (lambda s: font("segoeuil.ttf", s)), (lambda s: font("segoeuisl.ttf", s)), \
    (lambda s: font("seguisb.ttf", s)), (lambda s: font("segoeui.ttf", s))


def run(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, check=True, cwd=B)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, cwd=B)
    return float(r.stdout.strip())


def w(src, i):
    return WORDS[src][i]          # (word, start, end)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


# ---------------- audio: cut only inside measured silences ----------------
def silences(src):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-vn", "-af",
                        "pan=mono|c0=0.5*c0+0.5*c1,highpass=f=100,silencedetect=noise=-32dB:d=0.22", "-f", "null", "-"],
                       capture_output=True, text=True)
    gaps, s = [], None
    for line in r.stderr.splitlines():
        if "silence_start:" in line:
            s = float(line.split("silence_start:")[1].split()[0])
        elif "silence_end:" in line and s is not None:
            e = float(line.split("silence_end:")[1].split()[0])
            if gaps and s - gaps[-1][1] < 0.02:          # merge touching gaps
                gaps[-1] = (gaps[-1][0], e)
            else:
                gaps.append((s, e))
            s = None
    return gaps


def intervals(start, end, gaps, shrink=True, max_gap=0.5, keep=0.4):
    """speech from start to end; gaps longer than max_gap are shortened to `keep` by cutting their middle"""
    out, a = [], start
    if shrink:
        for gs, ge in gaps:
            if gs > start and ge < end and ge - gs > max_gap:
                out.append((a, gs + keep / 2))
                a = ge - keep / 2
    out.append((a, end))
    return out


def make_audio(src, ivs, out, chain):
    parts = [f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,"
             f"afade=t=out:st={b - a - 0.03:.3f}:d=0.03[p{k}]" for k, (a, b) in enumerate(ivs)]
    fc = (";".join(parts) + ";" + "".join(f"[p{k}]" for k in range(len(ivs))) +
          f"concat=n={len(ivs)}:v=0:a=1,{chain},atempo={TEMPO},loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[out]")
    run(["-i", str(src), "-filter_complex", fc, "-map", "[out]", "-ac", "2", out])

    def tmap(t):
        acc = 0.0
        for a, b in ivs:
            if t <= b:
                return (acc + max(t - a, 0.0)) / TEMPO
            acc += b - a
        return acc / TEMPO
    return duration(B / out), tmap


VOICE_NEAR = "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=2:attack=10:release=200"
VOICE_FAR = ("pan=mono|c0=0.5*c0+0.5*c1,highpass=f=90,lowpass=f=7500,afftdn=nr=10:nf=-45:tn=1,"
             "equalizer=f=220:t=q:w=1:g=-3,equalizer=f=3200:t=q:w=1.2:g=3,"
             "acompressor=threshold=-26dB:ratio=3:attack=5:release=150:makeup=2,"
             "agate=threshold=0.015:ratio=3:attack=8:release=250:range=0.3")


# ---------------- frame helpers (clean editorial style) ----------------
def canvas():
    return Image.new("RGB", (W, H), BG)


def label(img, text, light_bg=True):
    d = ImageDraw.Draw(img)
    if light_bg:
        d.text((96, 74), text.upper(), font=SEMI(24), fill=MUTE)
    else:
        d.text((98, 76), text.upper(), font=SEMI(24), fill=(0, 0, 0))
        d.text((96, 74), text.upper(), font=SEMI(24), fill=(240, 240, 240))


def fade_text(img, xy, text, f, fill, alpha, anchor="la", rise=0):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((xy[0], xy[1] + rise * (1 - alpha)), text, font=f,
                               fill=fill + (int(255 * alpha),), anchor=anchor)
    img.paste(layer, (0, 0), layer)


def encode_frames(frames_dir, n, out):
    run(["-framerate", str(FPS), "-i", f"{frames_dir}/f%04d.jpg", "-frames:v", str(n)] + ENC + ["-an", out])


def render(name, dur, draw):
    fd = B / name
    fd.mkdir(exist_ok=True)
    n = int(round(dur * FPS))
    for f in range(n):
        draw(f / FPS).save(fd / f"f{f:04d}.jpg", quality=95)
    encode_frames(name, n, f"{name}.mp4")


def video_clip(src, start, length, dur, out, crop="", overlay=None):
    speed = length / dur
    vf = f"trim={start:.3f}:{start + length:.3f},setpts=(PTS-STARTPTS)/{speed:.5f}"
    if crop:
        vf += f",{crop}"
    vf += (f",scale={W}:{H}:flags=lanczos,hqdn3d=1.5:1.5:0:0,eq=contrast=1.04:saturation=0.92:brightness=0.01,"
           f"unsharp=5:5:0.4,fps={FPS}")
    if overlay:
        run(["-i", str(src), "-loop", "1", "-i", overlay, "-filter_complex",
             f"[0:v]{vf}[v];[v][1:v]overlay=0:0:shortest=1,format=yuv420p[o]", "-map", "[o]", "-t", f"{dur:.3f}"]
            + ENC + ["-an", out])
    else:
        run(["-i", str(src), "-vf", vf + ",format=yuv420p", "-t", f"{dur:.3f}"] + ENC + ["-an", out])


def mux(video, audio, out):
    run(["-i", video, "-i", audio, "-map", "0:v", "-map", "1:a"] + ENC +
        ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", out])


segments, subs = [], []


def add_subs(src, chunks, tmap, offset):
    for i, j, text in chunks:
        subs.append((offset + tmap(w(src, i)[1]), offset + tmap(w(src, j)[2]) + 0.15, text))


# ================= 1. title card =================
g25, g26, gB = silences(RAW / "rec25.m4a"), silences(RAW / "rec26.m4a"), silences(RAW / "vidB.mp4")
iv1 = intervals(1.15, 9.30, g25)
d1, m1 = make_audio(RAW / "rec25.m4a", iv1, "a1.wav", VOICE_NEAR)


def title_frame(t):
    im = canvas()
    d = ImageDraw.Draw(im)
    a1, a2, a3 = ease(t / 0.9), ease((t - 0.7) / 0.9), ease((t - 1.3) / 0.9)
    d.line((160, 352, 160 + int(150 * ease((t - 0.3) / 0.8)), 352), fill=BLUE, width=4)
    fade_text(im, (152, 380), "VeriFlush", LIGHT(176), INK, a1, rise=18)
    fade_text(im, (160, 610), "Smart Verification of Water Exchange", SEMI(52), INK, a2, rise=12)
    fade_text(im, (160, 676), "in Building Plumbing Systems", SEMI(52), INK, a2, rise=12)
    fade_text(im, (160, 812), "CMAT-00196   ·   Theme 3: Smart, Digital and AI-Enabled Water Systems   ·   Team Gurt",
              REG(28), MUTE, a3)
    return im


render("t1", d1, title_frame)
mux("t1.mp4", "a1.wav", "seg1.mp4")
add_subs("rec25.wav", [(0, 8, "Hotel rooms and school wings sit empty for days,"),
                       (9, 16, "and before they're reused, their pipes get flushed.")], m1, 0.0)
segments.append("seg1.mp4")

# ================= 2. presenter (live audio, no internal cuts) =================
iv2 = intervals(1.80, 11.60, gB, shrink=False)
d2, m2 = make_audio(RAW / "vidB.mp4", iv2, "a2.wav", VOICE_FAR)
video_clip(RAW / "vidB.mp4", 1.80, 9.80, d2, "v2.mp4", crop="crop=iw*0.84:ih*0.84:iw*0.08:ih*0.02")
mux("v2.mp4", "a2.wav", "seg2.mp4")
add_subs("vidB.wav", [(0, 10, "But a flush log only says a timer ran out."),
                      (11, 20, "It doesn't actually prove that the stagnant water was replaced."),
                      (21, 28, "This is the gap that VeriFlush closes.")], m2, 0.0)
segments.append("seg2.mp4")

# ================= 3. the digital twin: dashboard, then an animated pipe diagram =================
src = "rec25.wav"
iv3 = intervals(9.65, 31.20, g25)
d3, m3 = make_audio(RAW / "rec25.m4a", iv3, "a3.wav", VOICE_NEAR)
T = {k: m3(w(src, i)[1]) for k, i in {"it": 25, "then": 38, "ver": 40, "fail": 41, "unc": 43, "here": 44,
                                       "done": 58, "keeps": 59}.items()}
dash = Image.open(DP / "outputs/screenshots/S05_diversion__veriflush_end.png").convert("RGB").crop((0, 140, 1366, 908))
dash = dash.resize((1340, int(1340 * dash.height / dash.width)), Image.LANCZOS)
shadow = Image.new("RGBA", (dash.width + 80, dash.height + 80), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rounded_rectangle((40, 48, dash.width + 40, dash.height + 48), radius=18, fill=(0, 0, 0, 60))
shadow = shadow.filter(ImageFilter.GaussianBlur(22))

PX0, PX1, PY, BX = 330, 1590, 600, 820          # main pipe, side-branch x


def pipe(im, front, side_open=False, side_front=0.0):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((170, 520, 300, 680), radius=14, outline=LINE, width=4, fill=BG)
    d.rectangle((178, 560, 292, 672), fill=BLUE)
    d.text((235, 700), "Feed", font=REG(26), fill=MUTE, anchor="ma")
    d.line((300, PY, PX1, PY), fill=LINE, width=40)
    d.line((300, PY, PX1, PY), fill=AMBER, width=26)
    fx = PX0 + (PX1 - PX0) * front
    d.line((300, PY, fx, PY), fill=BLUE, width=26)
    if side_open:
        d.line((BX, PY, BX, 820), fill=LINE, width=40)
        d.line((BX, PY + 14, BX, 820), fill=AMBER, width=26)
        if side_front > 0:
            d.line((BX, PY + 14, BX, PY + 14 + (820 - PY - 14) * side_front), fill=BLUE, width=26)
        d.text((BX + 34, 790), "Side branch open", font=REG(26), fill=MUTE)
    d.rounded_rectangle((520, 570, 600, 630), radius=10, fill=BG, outline=INK, width=3)
    d.text((560, 650), "Flow meter", font=REG(26), fill=MUTE, anchor="ma")
    end_col = BLUE if front >= 0.995 else AMBER
    d.ellipse((PX1 - 24, PY - 24, PX1 + 24, PY + 24), fill=end_col, outline=INK, width=3)
    d.text((PX1, 650), "End sensor", font=REG(26), fill=MUTE, anchor="ma")
    d.rectangle((170, 900, 196, 922), fill=AMBER)
    d.text((208, 896), "old water", font=REG(24), fill=MUTE)
    d.rectangle((370, 900, 396, 922), fill=BLUE)
    d.text((408, 896), "fresh water", font=REG(24), fill=MUTE)


def readouts(im, flow, vol, temp, a=1.0):
    for k, (lab, val, col) in enumerate([("Flow", f"{flow:.2f} L/min", INK), ("Volume", f"{vol:.2f} L", INK),
                                         ("End temperature", f"{temp:.1f} °C", BLUE if temp < 18 else AMBER)]):
        fade_text(im, (1080 + k * 290, 236), lab, REG(24), MUTE, a)
        fade_text(im, (1080 + k * 290, 270), val, SEMI(44), col, a)


def pill(im, x, y, text, col, a):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = SEMI(46)
    tw = d.textbbox((0, 0), text, font=f)[2]
    d.rounded_rectangle((x - tw // 2 - 44, y - 44, x + tw // 2 + 44, y + 44), radius=44,
                        outline=col + (int(255 * a),), width=4)
    d.text((x, y), text, font=f, fill=col + (int(255 * a),), anchor="mm")
    im.paste(layer, (0, 0), layer)


def digital_frame(t):
    im = canvas()
    if t < T["it"] + 0.4:                                  # dashboard, framed on the page
        z = 1 + 0.03 * t / max(T["it"], 0.1)
        dz = dash.resize((int(dash.width * z), int(dash.height * z)), Image.LANCZOS)
        x, y = (W - dz.width) // 2, 140 + (H - 140 - dz.height) // 2
        im.paste(shadow.resize((dz.width + 80, dz.height + 80)), (x - 40, y - 40), shadow.resize((dz.width + 80, dz.height + 80)))
        im.paste(dz, (x, y))
        label(im, "VeriFlush digital twin  ·  dashboard  ·  simulated")
        frame_a = im
        if t < T["it"]:
            return frame_a
    if t < T["then"] + 0.4:                                # healthy flush: tracks flow, volume, end temperature
        p = (t - T["it"]) / (T["then"] - T["it"])
        im2 = canvas()
        label(im2, "Digital twin  ·  healthy flush  ·  simulated")
        front = ease(p * 1.15)
        pipe(im2, front)
        readouts(im2, 0.63 if p > 0.05 else 0.0, 0.95 * min(p * 1.15, 1), 24.0 - 10.6 * ease((front - 0.85) / 0.15))
        if t < T["it"] + 0.4:
            return Image.blend(im, im2, (t - T["it"]) / 0.4)
        im = im2
        if t < T["then"]:
            return im
    if t < T["here"] + 0.4:                                # three verdicts
        im3 = canvas()
        label(im3, "Decision logic")
        fade_text(im3, (W // 2, 330), "Every flush ends with one verdict", LIGHT(64), INK, 1.0, anchor="mm")
        for x, key, text, col in [(560, "ver", "Verified", GREEN), (960, "fail", "Failed", RED),
                                  (1360, "unc", "Uncertain", AMBER)]:
            pill(im3, x, 560, text, col, ease((t - T[key] + 0.25) / 0.45))
        for x, key, text in [(560, "ver", "enough water reached the end"), (960, "fail", "blocked or too little flow"),
                             (1360, "unc", "evidence missing, staff check")]:
            fade_text(im3, (x, 650), text, REG(26), MUTE, ease((t - T[key]) / 0.5), anchor="ma")
        if t < T["then"] + 0.4:
            return Image.blend(im, im3, (t - T["then"]) / 0.4)
        im = im3
        if t < T["here"]:
            return im
    # diversion: half the water leaves early; the timer stops; VeriFlush keeps going
    im4 = canvas()
    label(im4, "Digital twin  ·  side branch open  ·  simulated")
    span = d3 - T["here"]
    p = (t - T["here"]) / span
    pk = (T["keeps"] - T["here"]) / span
    front = 0.62 * ease(p / pk) if p < pk else 0.62 + 0.38 * ease((p - pk) / (1 - pk) * 1.25)
    pipe(im4, front, side_open=True, side_front=ease((front - 0.33) / 0.15) if front > 0.33 else 0.0)
    tm = min((t - T["here"]) / max(T["done"] - T["here"], 0.1), 1.0)
    fade_text(im4, (170, 236), "Fixed timer", REG(24), MUTE, 1.0)
    fade_text(im4, (170, 270), f"{int(90 * tm) // 60}:{int(90 * tm) % 60:02d}", SEMI(44), INK, 1.0)
    if t >= T["done"]:
        pill(im4, 520, 300, "Timer: done", RED, ease((t - T["done"]) / 0.3))
        fade_text(im4, (PX1, 520), "end still old water", REG(26), RED,
                  ease((t - T["done"]) / 0.4) * (1 - ease((front - 0.97) / 0.03)), anchor="mm")
    if t >= T["keeps"]:
        fade_text(im4, (1080, 236), "VeriFlush", REG(24), MUTE, ease((t - T["keeps"]) / 0.4))
        fade_text(im4, (1080, 270), "keeps flushing", SEMI(44), INK, ease((t - T["keeps"]) / 0.4))
        if front >= 0.995:
            pill(im4, 1680, 300, "Verified", GREEN, 1.0)
    if t < T["here"] + 0.4:
        return Image.blend(im, im4, (t - T["here"]) / 0.4)
    return im4


render("t3", d3, digital_frame)
mux("t3.mp4", "a3.wav", "seg3.mp4")
add_subs(src, [(17, 24, "VeriFlush is a digital twin and controller."),
               (25, 37, "It tracks flow, volume and the temperature at the end of the pipe,"),
               (38, 43, "then decides: Verified, Failed or Uncertain."),
               (44, 53, "Here, half of the water escapes through a side branch,"),
               (54, 58, "then the timer says done."),
               (59, 68, "VeriFlush keeps going until the branch is really exchanged.")], m3, 0.0)
segments.append("seg3.mp4")

# ================= 4. results =================
iv4 = intervals(31.50, 43.70, g25)
d4, m4 = make_audio(RAW / "rec25.m4a", iv4, "a4.wav", VOICE_NEAR)
bars = [("Fixed timer", 37, AMBER, m4(w(src, 78)[1])), ("Flow + configured volume", 31, AMBER, m4(w(src, 87)[1])),
        ("VeriFlush", 0, BLUE, m4(w(src, 91)[1]))]


def chart_frame(t):
    im = canvas()
    d = ImageDraw.Draw(im)
    label(im, "Digital twin results  ·  simulated")
    fade_text(im, (160, 170), "False passes in 520 simulated flushes", LIGHT(64), INK, ease(t / 0.6), rise=10)
    fade_text(im, (162, 262), "A false pass is a \u201cVerified\u201d while more than 5 % old water was still in the pipe.",
              REG(28), MUTE, ease((t - 0.3) / 0.6))
    for k, (lab, val, col, t0) in enumerate(bars):
        y = 420 + k * 170
        a = ease((t - 0.5 - 0.15 * k) / 0.5)
        fade_text(im, (160, y + 8), lab, SEMI(36), INK, a)
        d.rounded_rectangle((720, y + 14, 1520, y + 46), radius=16, fill=LINE)
        p = ease((t - t0 + 0.1) / 0.8)
        if val and p > 0:
            d.rounded_rectangle((720, y + 14, 720 + int(800 * val / 40 * p), y + 46), radius=16, fill=col)
        if t >= t0 - 0.1:
            fade_text(im, (1580, y - 6), f"{round(val * p)} %", LIGHT(72), col, ease((t - t0 + 0.1) / 0.3))
    return im


render("t4", d4, chart_frame)
mux("t4.mp4", "a4.wav", "seg4.mp4")
add_subs(src, [(69, 72, "Across 520 simulated flushes,"), (73, 82, "timers passed stale water 37% of the time,"),
               (83, 87, "and flow meters only 31%,"), (88, 91, "but VeriFlush: zero.")], m4, 0.0)
segments.append("seg4.mp4")

# ================= 5. the physical prototype, credits over the last seconds =================
s5 = "rec26.wav"
iv5 = intervals(3.00, 14.25, g26)
d5, m5 = make_audio(RAW / "rec26.m4a", iv5, "a5v.wav", VOICE_NEAR)
TAIL = 2.0
run(["-i", "a5v.wav", "-af", f"apad=pad_dur={TAIL}", "-t", f"{d5 + TAIL:.3f}", "a5.wav"])
lab_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
label(lab_img, "Physical prototype", light_bg=False)
lab_img.save(B / "lab_phys.png")
run(["-i", str(RAW / "vidA.mp4"), "-vf", "deshake=rx=32:ry=32:edge=mirror,crop=iw*0.94:ih*0.94",
     "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-an", "vidA_stab.mp4"])
d5t = d5 + TAIL
video_clip(B / "vidA_stab.mp4", 1.0, 11.2, d5t, "v5.mp4", overlay="lab_phys.png")
cred = Image.new("RGBA", (W, H), (0, 0, 0, 150))
dc = ImageDraw.Draw(cred)
dc.line((W // 2 - 60, 330, W // 2 + 60, 330), fill=(255, 255, 255, 255), width=3)
dc.text((W // 2, 420), "Team Gurt", font=LIGHT(110), fill=(255, 255, 255, 255), anchor="mm")
dc.text((W // 2, 510), "Khalifa University", font=SEMI(44), fill=(235, 235, 235, 255), anchor="mm")
dc.text((W // 2, 610), "Mohammed Aqil Mohideen   ·   Fawaz Ahmed   ·   Mohamad Zaheen (team leader)   ·   Alvin Titus Alex",
        font=REG(32), fill=(255, 255, 255, 255), anchor="mm")
dc.text((W // 2, 680), "VeriFlush   ·   CMAT-00196   ·   Theme 3   ·   github.com/MoAqil/veriflush",
        font=REG(28), fill=(215, 215, 215, 255), anchor="mm")
dc.text((W // 2, 740), "Digital results simulated  ·  physical prototype in calibration  ·  no music",
        font=REG(24), fill=(190, 190, 190, 255), anchor="mm")
cred.save(B / "credits.png")
st = d5t - TAIL - 0.3
run(["-i", "v5.mp4", "-loop", "1", "-i", "credits.png", "-filter_complex",
     f"[1:v]format=rgba,fade=t=in:st={st:.3f}:d=0.6:alpha=1[c];[0:v][c]overlay=0:0:shortest=1,format=yuv420p[o]",
     "-map", "[o]"] + ENC + ["-an", "v5c.mp4"])
mux("v5c.mp4", "a5.wav", "seg5.mp4")
add_subs(s5, [(0, 10, "And this is our physical prototype: the same sensors, logging live."),
              (11, 15, "Dubai already requires weekly flushing."),
              (16, 22, "VeriFlush turns that log into evidence.")], m5, 0.0)
segments.append("seg5.mp4")

# ================= join with crossfades (no time added), subtitles, export =================
durs = [duration(B / s) for s in segments]
offsets, acc = [], 0.0
for dd in durs:
    offsets.append(acc)
    acc += dd
k_sub, shifted = 0, []
counts = [2, 3, 6, 4, 3]
for seg_i, cnt in enumerate(counts):
    for s, e, text in subs[k_sub:k_sub + cnt]:
        shifted.append((s + offsets[seg_i], e + offsets[seg_i], text))
    k_sub += cnt
args, fc = [], []
for k, sg in enumerate(segments):
    args += ["-i", sg]
    pad = f",tpad=stop_mode=clone:stop_duration={XF}" if k < len(segments) - 1 else ""
    fc.append(f"[{k}:v]scale={W}:{H}:in_range=auto:out_range=tv,format=yuv420p,setsar=1,fps={FPS}{pad}[v{k}]")
prev = "[v0]"
for k in range(1, len(segments)):
    fc.append(f"{prev}[v{k}]xfade=transition=fade:duration={XF}:offset={offsets[k]:.3f}[x{k}]")
    prev = f"[x{k}]"
fc.append("".join(f"[{k}:a]" for k in range(len(segments))) + f"concat=n={len(segments)}:v=0:a=1[a]")
run(args + ["-filter_complex", ";".join(fc), "-map", prev, "-map", "[a]"] + ENC +
    ["-c:a", "aac", "-b:a", "192k", "joined.mp4"])


def ts(t):
    t = max(t, 0)
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round(t % 1 * 1000)) % 1000:03d}"


shifted.sort()
lines = []
for k, (s, e, text) in enumerate(shifted):
    if k + 1 < len(shifted):
        e = min(e, shifted[k + 1][0] - 0.05)
    lines.append(f"{k + 1}\n{ts(s)} --> {ts(max(e, s + 0.8))}\n{text}\n")
(B / "subs.srt").write_text("\n".join(lines), encoding="utf-8")
style = ("FontName=Segoe UI Semibold,FontSize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H78202020,"
         "BorderStyle=3,Outline=6,Shadow=0,MarginV=30,MarginL=80,MarginR=80")
run(["-i", "joined.mp4", "-vf", f"subtitles=subs.srt:force_style='{style}'"] + ENC +
    ["-c:a", "copy", "-movflags", "+faststart", str(OUT)])
print(f"saved {OUT}  duration {duration(OUT):.2f} s  size {OUT.stat().st_size / 1e6:.1f} MB")
