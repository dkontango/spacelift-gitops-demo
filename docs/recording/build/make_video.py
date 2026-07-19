#!/usr/bin/env python3
"""Assemble the 17-step workflow.mp4.

Live-captured steps (Playwright cursor tours) are used as-is. For the steps that
weren't captured live, we synthesize a short cursor-pan clip over the polished,
already-redacted walkthrough asset — so every one of the 17 steps appears, with
the same yellow-halo cursor throughout. All frames are letterboxed to a uniform
canvas, an over-frame step title is burned in, then ffmpeg stitches to MP4.
"""
import os, glob, subprocess, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = "/home/leonardo/git/spacelift-gitops-demo"
FR = f"{ROOT}/docs/recording/frames17"        # live frames
ASSETS = f"{ROOT}/site/assets/steps"          # polished step PNGs (gap fallback)
STAGE = f"{ROOT}/docs/recording/build/stage"  # normalized, titled frames
os.makedirs(STAGE, exist_ok=True)

W, H = 1280, 720
BG = (11, 16, 32)  # matches the guide theme --bg

# ordered step -> (title, live?, gap-asset basename)
STEPS = [
    ("00", "The pipeline — Forgejo → GitHub → Spacelift → AWS", False, "step-00-architecture"),
    ("01", "Step 1 — Where the tutorial lives (Spacelift Stacks)", True,  None),
    ("02", "Step 2 — Register Spacelift as an OIDC provider (AWS)", True, None),
    ("03", "Step 3 — Create the IAM role Spacelift assumes (AWS)", True,  None),
    ("04", "Step 4 — Attach S3 + EC2 permissions to the role (AWS)", True, None),
    ("05", "Step 5 — Create the AWS cloud integration in Spacelift", False, "step-05-aws-integration-dialog"),
    ("06", "Step 6 — The integration exists at the account level", True, None),
    ("07", "Step 7 — The sandbox stack (tracked runs)", True, None),
    ("08", "Step 8 — Create a stack: connect source code", False, "step-08-create-stack-source"),
    ("09", "Step 9 — Create a stack: choose OpenTofu", False, "step-09-create-stack-vendor"),
    ("10", "Step 10 — Attach the integration TO the stack", False, "step-10-integration-attached-to-stack"),
    ("11", "Step 11 — The OPA Plan policy (plan-block-public-s3)", True, None),
    ("12", "Step 12 — Attach the policy to the stack", False, "step-12-policy-attached"),
    ("13", "Step 13 — Deploy: a finished run (real S3 bucket)", False, "step-13-deploy-finished"),
    ("14", "Step 14 — The guardrail in action: PR blocked", True, None),
    ("15", "Step 15 — Why it failed: the policy denial", True, None),
    ("16", "Step 16 — Fix it: the PR passes, merge deploys", True, None),
]

def font(sz):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

TF = font(22)

def canvas_with(img):
    """Letterbox an image onto the WxH themed canvas."""
    c = Image.new("RGB", (W, H), BG)
    iw, ih = img.size
    scale = min(W / iw, (H - 56) / ih)  # leave room for title bar
    nw, nh = int(iw * scale), int(ih * scale)
    img2 = img.resize((nw, nh), Image.LANCZOS)
    x = (W - nw) // 2
    y = 56 + (H - 56 - nh) // 2
    c.paste(img2, (x, y))
    return c, (x, y, scale)

def title_bar(c, text):
    d = ImageDraw.Draw(c, "RGBA")
    d.rectangle([0, 0, W, 48], fill=(17, 26, 46, 255))
    d.line([(0, 48), (W, 48)], fill=(36, 49, 73, 255), width=2)
    # accent tick
    d.rectangle([0, 0, 6, 48], fill=(110, 168, 254, 255))
    d.text((18, 12), text, font=TF, fill=(231, 236, 245, 255))

def draw_cursor(c, x, y):
    """Yellow halo + pointer, matching the live overlay."""
    glow = Image.new("RGBA", (c.width, c.height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a in [(34, 60), (20, 120), (11, 220)]:
        gd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 214, 0, a))
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    c.alpha_composite(glow)
    d = ImageDraw.Draw(c, "RGBA")
    # pointer arrow
    d.polygon([(x, y - 2), (x - 7, y + 12), (x, y + 8), (x + 7, y + 14)],
              fill=(40, 30, 0, 235))

def gap_frames(step, title, asset, out_prefix, n=22):
    """Make a cursor-pan clip from a static asset."""
    src = Image.open(f"{ASSETS}/{asset}.png").convert("RGB")
    base, (ox, oy, sc) = canvas_with(src)
    iw, ih = src.size
    # a gentle path: left-third -> center -> right-third at ~40% height
    def pt(fx, fy):
        return (int(ox + fx * iw * sc), int(oy + fy * ih * sc))
    path = [pt(0.25, 0.35), pt(0.55, 0.5), pt(0.78, 0.4)]
    frames = []
    # ease along the polyline
    segs = list(zip(path, path[1:]))
    per = max(1, n // max(1, len(segs)))
    seq = []
    for (ax, ay), (bx, by) in segs:
        for i in range(per):
            t = i / per
            e = t * t * (3 - 2 * t)
            seq.append((ax + (bx - ax) * e, ay + (by - ay) * e))
    seq = ([path[0]] * 3) + seq + ([path[-1]] * 4)  # holds
    fi = 0
    for (x, y) in seq:
        c = base.convert("RGBA").copy()
        title_bar(c, title)
        draw_cursor(c, int(x), int(y))
        c.convert("RGB").save(f"{STAGE}/{out_prefix}-{fi:03d}.png")
        fi += 1
    return fi

def live_frames(step, title, out_prefix):
    """Letterbox live frames onto the themed canvas + title bar."""
    files = sorted(glob.glob(f"{FR}/step{step}-*.png"))
    fi = 0
    for f in files:
        img = Image.open(f).convert("RGB")
        c, _ = canvas_with(img)
        c = c.convert("RGBA")
        title_bar(c, title)
        c.convert("RGB").save(f"{STAGE}/{out_prefix}-{fi:03d}.png")
        fi += 1
    return fi

def main():
    # clear stage
    for f in glob.glob(f"{STAGE}/*.png"):
        os.remove(f)
    order = 0
    manifest = []
    for step, title, live, asset in STEPS:
        prefix = f"seq{order:02d}"
        if live and glob.glob(f"{FR}/step{step}-*.png"):
            n = live_frames(step, title, prefix)
            kind = "live"
        else:
            n = gap_frames(step, title, asset, prefix)
            kind = "gap"
        manifest.append((step, kind, n))
        order += 1
    total = len(glob.glob(f"{STAGE}/*.png"))
    print("manifest:")
    for s, k, n in manifest:
        print(f"  step {s}: {k:4s} {n} frames")
    print(f"total staged frames: {total}")

    # build the ffmpeg concat list (each frame held; global fps sets pace)
    listp = f"{STAGE}/frames.txt"
    files = sorted(glob.glob(f"{STAGE}/seq*.png"))
    with open(listp, "w") as fh:
        for f in files:
            fh.write(f"file '{f}'\n")
            fh.write("duration 0.14\n")
        fh.write(f"file '{files[-1]}'\n")  # last frame needs a final entry
    out = f"{ROOT}/docs/recording/workflow.mp4"
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listp,
           "-vf", "fps=25,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
           "-movflags", "+faststart", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FFMPEG ERROR:\n", r.stderr[-2000:])
    else:
        sz = os.path.getsize(out)
        print(f"wrote {out} ({sz//1024} KB)")

if __name__ == "__main__":
    main()
