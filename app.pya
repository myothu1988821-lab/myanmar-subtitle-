import re, subprocess, urllib.request, tempfile, os
from pathlib import Path
import imageio_ffmpeg, streamlit as st

st.set_page_config(page_title="မြန်မာစာတန်း Burn", page_icon="🎬", layout="centered")

CSS="""<style>
.stApp{background:linear-gradient(135deg,#0f2027 0%,#203a43 55%,#2c5364 100%)}
.stApp h1{background:linear-gradient(90deg,#7fe7dc,#ffd76e);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:800}
.stApp p,.stApp label,.stMarkdown{color:#eaf6f6!important}
div.stButton>button{background:linear-gradient(90deg,#00bfa5,#00acc1);color:#fff;border:none;border-radius:12px;padding:.6rem 2rem;font-size:1.1rem;font-weight:700;box-shadow:0 4px 14px rgba(0,191,165,.35);width:100%}
div.stButton>button:hover{filter:brightness(1.12)}
div[data-testid="stTextArea"] textarea{background-color:#16323c!important;color:#fff!important;border-radius:12px;border:1px solid rgba(255,255,255,.3)!important;font-size:1.05rem}
div[data-testid="stTextArea"] textarea::placeholder{color:rgba(255,255,255,.45)!important}
div[data-testid="stRadio"] label{color:#eaf6f6!important}
div[data-testid="stSlider"]{color:#fff}
header[data-testid="stHeader"]{background:rgba(0,0,0,0)}
footer{visibility:hidden}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)
st.title("🎬 မြန်မာစာတန်း Burn")
st.markdown("Video + Myanmar SRT → Eng/China စာတန်း ဖျောက် + မြန်မာစာတန်း ကပ်", unsafe_allow_html=True)
st.caption("🔖 v2026-10-06-padauk")
st.write("")

ff = imageio_ffmpeg.get_ffmpeg_exe()
FD = Path("fonts")
FU = "https://github.com/silnrsi/font-padauk/releases/download/v6.000/Padauk-6.000.zip"
FONT_NAME = "Padauk"

@st.cache_resource(show_spinner="Font ဒေါင်းနေတယ်... (ပထမတစ်ကြိမ်သာ)")
def get_font():
    FD.mkdir(exist_ok=True)
    d = FD / "Padauk-Regular.ttf"
    if not d.exists():
        import zipfile
        zpath = FD / "padauk.zip"
        urllib.request.urlretrieve(FU, zpath)
        with zipfile.ZipFile(zpath) as z:
            for n in z.namelist():
                if n.endswith("Padauk-Regular.ttf"):
                    with z.open(n) as src, open(d, "wb") as dst:
                        dst.write(src.read())
                    break
        zpath.unlink(missing_ok=True)
    return d

@st.cache_resource
def get_zgtools():
    try:
        from myanmartools import ZawgyiDetector
        from myanmar import converter
        return ZawgyiDetector(), converter, ""
    except Exception as e:
        return None, None, str(e)[:200]

def count_segs(t):
    return len(re.findall(r"-->", t))

def shift_srt(text, delta):
    """SRT အချိန်တွေကို delta စက္ကန့် ရွှေ့တယ်"""
    out = []
    for line in text.splitlines():
        if "-->" in line:
            def rep(m):
                h, mi, s, ms = map(int, m.groups())
                t = max(0, h * 3600 + mi * 60 + s + ms / 1000 + delta)
                return (f"{int(t // 3600):02d}:{int((t % 3600) // 60):02d}:"
                        f"{int(t % 60):02d},{int(round((t % 1) * 1000)):03d}")
            line = re.sub(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", rep, line)
        out.append(line)
    return "\n".join(out)

try:
    _fnt = get_font()
    if _fnt.exists():
        st.caption(f"🔤 Font: {_fnt.name} ({_fnt.stat().st_size//1024} KB) ✅")
    else:
        st.caption("🔤 Font file မတွေ့ဘူး ❌")
except Exception as e:
    st.caption(f"🔤 Font download error: {str(e)[:120]}")

video = st.file_uploader("🎬 Video တင်ပါ", type=["mp4", "mov", "mkv", "webm"])

srt_up = st.file_uploader("📄 Myanmar SRT file တင်ပါ", type=["srt"])
srt_prefill = ""
if srt_up:
    try:
        srt_prefill = srt_up.read().decode("utf-8-sig")
        n = len(re.findall(r"-->", srt_prefill))
        st.success(f"SRT ဖတ်ပြီးပြီ ✓ (အပိုင်း {n} ပိုင်း)")
    except Exception as e:
        st.error(f"SRT ဖတ်မရဘူး: {e}")

srt_text = st.text_area("SRT စာသား", value=srt_prefill, height=180,
    placeholder="SRT file မတင်ရင် ဒီမှာ SRT စာသား paste လုပ်ပါ...")

st.markdown("**Eng / China စာတန်း ဖျောက်နည်း**")
method = st.radio("", ["Blur — ဝါးမယ် (မူရင်း frame အပြည့်ကျန်တယ်)",
                       "Crop — အောက်ပိုင်း ဖြတ်မယ်",
