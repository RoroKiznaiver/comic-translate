"""Render the Bulle logo: a glossy 3D amber speech bubble.

Pure numpy/Pillow/scipy. Outputs resources/icons/{logo.png,icon.png,icon.ico,icon.icns,splash.png}.
Run: python tools/make_logo.py
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "icons")
S = 1024          # final size
K = 2             # supersampling
N = S * K


def shape_mask():
    m = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(m)
    # bubble body: squircle-ish rounded rect + tail bottom-left
    d.rounded_rectangle((0.12 * N, 0.12 * N, 0.88 * N, 0.74 * N), radius=0.25 * N, fill=255)
    d.polygon([(0.24 * N, 0.66 * N), (0.50 * N, 0.70 * N), (0.19 * N, 0.90 * N)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(0.012 * N))
    a = np.asarray(m, dtype=np.float32) / 255.0
    return (a > 0.5).astype(np.float32)


def letter_mask():
    f = ImageFont.truetype("/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf", int(0.46 * N))
    m = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(m)
    bbox = d.textbbox((0, 0), "B", font=f)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((0.50 * N - w / 2 - bbox[0], 0.43 * N - h / 2 - bbox[1]), "B", font=f, fill=255)
    return np.asarray(m, dtype=np.float32) / 255.0


def lerp(a, b, t):
    return a + (b - a) * t[..., None]


def render():
    mask = shape_mask()
    letter = np.zeros_like(mask)   # no letter: a clean bubble

    # height field: soft pillow + embossed letter
    pillow = gaussian_filter(mask, 0.075 * N)
    pillow = pillow / pillow.max()
    h = (pillow ** 0.8) * 0.28 * N
    lt = gaussian_filter(letter, 0.004 * N)
    
    gy, gx = np.gradient(h)
    nz = np.ones_like(h)
    norm = np.sqrt(gx ** 2 + gy ** 2 + nz ** 2)
    nx, ny, nz = -gx / norm, -gy / norm, nz / norm

    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N

    # base colour: vivid blue -> violet, lighter at the top
    top = np.array([1.00, 0.86, 0.38])
    mid = np.array([1.00, 0.66, 0.14])
    bot = np.array([0.94, 0.40, 0.06])
    t = np.clip((yy - 0.12) / 0.78, 0, 1)
    base = np.where(t[..., None] < 0.5, lerp(top, mid, np.clip(t * 2, 0, 1)),
                    lerp(mid, bot, np.clip(t * 2 - 1, 0, 1)))

    # lighting
    L = np.array([-0.45, -0.65, 0.62]); L /= np.linalg.norm(L)
    diff = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    col = base * (0.55 + 0.65 * diff[..., None])

    # bounce light from below (subsurface glow)
    bounce = np.clip(ny, 0, 1) * np.clip(1 - nz, 0, 1)
    col += np.array([1.0, 0.55, 0.15]) * (bounce[..., None] * 0.5)

    # specular
    V = np.array([0, 0, 1.0])
    Hh = L + V; Hh /= np.linalg.norm(Hh)
    nh = np.clip(nx * Hh[0] + ny * Hh[1] + nz * Hh[2], 0, 1)
    col += (nh ** 90)[..., None] * 0.9 + (nh ** 14)[..., None] * 0.16

    # fresnel rim
    fres = (1 - nz) ** 2.2
    col += np.array([1.0, 0.92, 0.65]) * fres[..., None] * 0.55

    # glass glare: elliptical sheen in the upper half
    gl = np.exp(-(((xx - 0.42) / 0.30) ** 2 + ((yy - 0.24) / 0.085) ** 2))
    gl = gl * np.clip((0.50 - yy) / 0.28, 0, 1)
    col = col + (gl * 0.55)[..., None] * (1 - col) * 1.0

    # letter: bright glassy white with its own shading
    lcol = np.array([1.0, 1.0, 1.0])[None, None, :] * (0.78 + 0.28 * diff[..., None])
    lcol = lcol + (nh ** 60)[..., None] * 0.4
    la = gaussian_filter(letter, 0.0015 * N)[..., None]
    col = col * (1 - la) + np.clip(lcol, 0, 1) * la
    # letter drop shadow inside the bubble
    sh = gaussian_filter(np.roll(np.roll(letter, int(0.012 * N), 0), int(0.006 * N), 1), 0.012 * N)
    col = col * (1 - 0.35 * sh[..., None] * (1 - la))

    col = np.clip(col, 0, 1)
    alpha = gaussian_filter(mask, 0.0012 * N)

    # drop shadow + glow
    shadow = gaussian_filter(np.roll(mask, int(0.045 * N), 0), 0.035 * N) * 0.55
    glow = gaussian_filter(mask, 0.06 * N) * 0.35

    canvas = np.zeros((N, N, 4), dtype=np.float32)
    # glow (blue) then shadow (dark indigo)
    canvas[..., :3] = np.array([0.3, 0.45, 1.0])
    canvas[..., 3] = glow * 0.0 + 0.0
    sh_col = np.array([0.30, 0.10, 0.02])
    out_rgb = np.zeros((N, N, 3), dtype=np.float32)
    out_a = np.zeros((N, N), dtype=np.float32)
    # layer 1: shadow
    out_rgb = sh_col[None, None, :] * np.ones((N, N, 3), np.float32)
    out_a = shadow
    # layer 2: bubble over it
    a2 = alpha
    out_rgb = col * a2[..., None] + out_rgb * (1 - a2[..., None])
    out_a = a2 + out_a * (1 - a2)
    img = np.dstack([out_rgb, out_a])
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA").resize((S, S), Image.LANCZOS)
    return im


def splash(logo):
    W, H = 2752, 1536
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H * 0.44
    r = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)
    bg = np.zeros((H, W, 3), np.float32)
    base = np.array([0.06, 0.055, 0.05]); glow = np.array([0.42, 0.24, 0.05])
    g = np.exp(-(r / 0.28) ** 2)[..., None]
    bg = base + glow * g
    im = Image.fromarray((np.clip(bg, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")
    size = 760
    lg = logo.resize((size, size), Image.LANCZOS)
    im.alpha_composite(lg, (W // 2 - size // 2, int(H * 0.40) - size // 2))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 150)
    bb = d.textbbox((0, 0), "Bulle", font=f)
    d.text((W / 2 - (bb[2] - bb[0]) / 2, int(H * 0.40) + size // 2 + 30), "Bulle", font=f, fill=(245, 245, 250, 255))
    f2 = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Regular.otf", 64)
    sub = "Manga & manhwa translation"
    bb = d.textbbox((0, 0), sub, font=f2)
    d.text((W / 2 - (bb[2] - bb[0]) / 2, int(H * 0.40) + size // 2 + 240), sub, font=f2, fill=(170, 160, 140, 255))
    return im


if __name__ == "__main__":
    logo = render()
    logo.save(os.path.join(OUT, "logo.png"))
    logo.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "icon.png"))
    logo.save(os.path.join(OUT, "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    try:
        logo.save(os.path.join(OUT, "icon.icns"))
    except Exception as e:
        print("icns skipped:", e)
    splash(logo).convert("RGB").save(os.path.join(OUT, "splash.png"))
    print("done")
