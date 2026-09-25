"""Checks an LGPL wheel: GPL encoders absent, replacement encoders present and encoding."""
import sys
from fractions import Fraction

import av
import av._core

failures = []


def check(ok, message):
    print(("PASS " if ok else "FAIL ") + message)
    if not ok:
        failures.append(message)


def has_encoder(name):
    try:
        av.Codec(name, "w")
        return True
    except Exception:
        return False


config = av._core.library_meta["libavcodec"]["configuration"]
for flag in ("--disable-libx264", "--disable-libx265", "--enable-libopenh264"):
    check(flag in config, f"configuration has {flag}")
check("--enable-gpl" not in config, "configuration has no --enable-gpl")
check("--enable-nonfree" not in config, "configuration has no --enable-nonfree")

for name in ("libx264", "libx265"):
    check(not has_encoder(name), f"{name} encoder is absent")

hardware = {
    "win32": ["h264_nvenc", "h264_amf", "h264_qsv", "h264_mf", "hevc_nvenc", "hevc_amf", "hevc_qsv", "hevc_mf"],
    "linux": ["h264_vaapi", "h264_nvenc", "h264_amf", "h264_qsv", "hevc_vaapi", "hevc_nvenc", "hevc_amf", "hevc_qsv"],
    "darwin": ["h264_videotoolbox", "hevc_videotoolbox"],
}[sys.platform]
for name in hardware:
    check(has_encoder(name), f"{name} encoder is registered")

# Software encoders the app relies on must actually encode (hardware ones need a GPU the runner lacks)
software = [
    ("libopenh264", "yuv420p", {}),
    ("libsvtav1", "yuv420p", {}),
    ("prores_ks", "yuv422p10le", {"profile": "2"}),
    ("dnxhd", "yuv422p", {"profile": "dnxhr_sq"}),
]
for name, pix_fmt, options in software:
    try:
        ctx = av.CodecContext.create(name, "w")
        ctx.width, ctx.height, ctx.pix_fmt = 320, 240, pix_fmt
        ctx.time_base = Fraction(1, 24)
        ctx.framerate = Fraction(24, 1)
        ctx.bit_rate = 2_000_000
        ctx.options = options
        packets = []
        for i in range(8):
            frame = av.VideoFrame(320, 240, "yuv420p").reformat(format=pix_fmt)
            frame.pts = i
            packets += ctx.encode(frame)
        packets += ctx.encode(None)
        check(len(packets) > 0, f"{name} encodes ({len(packets)} packets)")
    except Exception as e:
        check(False, f"{name} encodes ({type(e).__name__}: {e})")

print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
