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
                       "မဖျောက်ဘူး"], label_visibility="collapsed")

area_h = 15
if not method.startswith("မဖျောက်"):
    area_h = st.slider("ဖျောက်မယ့် အောက်ပိုင်း အမြင့် (%)", 5, 30, 15)

fsize = st.slider("မြန်မာစာတန်း အရွယ်အစား", 14, 36, 22)
color = st.color_picker("🎨 စာတန်း အရောင်", "#FFFFFF")
r, g, b = color[1:3], color[3:5], color[5:7]
ass_color = f"&H00{b}{g}{r}".upper()
zg_fix = st.checkbox("🔄 Zawgyi စာသားဆို Unicode သို့ auto-ပြောင်းမယ်", value=True)
shift = st.slider("⏱️ စာတန်း အချိန် ရွှေ့ (စက္ကန့်)", -5.0, 5.0, 0.0, 0.5,
    help="SRT အချိန်တွေ တစ်ဆက်တည်း စောနေရင် + ၊ နောက်ကျနေရင် − ရွှေ့ပါ")

if st.button("🎬 Video ထုတ်မယ်", type="primary"):
    if not video:
        st.error("Video တင်ပေးပါ။"); st.stop()
    if not srt_text.strip() or "-->" not in srt_text:
        st.error("SRT စာသား မှန်မှန်ထည့်ပေးပါ။"); st.stop()

    if zg_fix:
        det, conv, err = get_zgtools()
        if det is None:
            st.warning("⚠️ Zawgyi auto-convert အလုပ်မလုပ်ဘူး — requirements.txt မှာ "
                       "package တွေ လိုနေတယ်။ requirements.txt အသစ်တင်ပြီး Reboot လုပ်ပါ।")
        elif det.get_zawgyi_probability(srt_text) > 0.5:
            srt_text = conv.convert(srt_text, "zawgyi", "unicode")
            st.info("🔄 Zawgyi တွေ့လို့ Unicode သို့ ပြောင်းပေးလိုက်ပြီ ✓")
        else:
            st.caption("SRT က Unicode အမှန် — မပြောင်းဘူး")

    get_font()
    tmp = tempfile.mkdtemp()
    vp = os.path.join(tmp, "in.mp4")
    with open(vp, "wb") as f:
        f.write(video.read())
    sp = os.path.join(tmp, "subs.srt")
    srt_out = shift_srt(srt_text, shift) if abs(shift) > 0.01 else srt_text
    with open(sp, "w", encoding="utf-8") as f:
        f.write(srt_out)
    out = os.path.join(tmp, "out.mp4")

    vfs = []
    h = area_h / 100
    if method.startswith("Blur"):
        vfs.append(f"split[a][b];[a]crop=iw:ih*{h}:0:ih*{1-h},boxblur=12[bb];[b][bb]overlay=0:H-h")
    elif method.startswith("Crop"):
        vfs.append(f"crop=iw:ih*{1-h}")
    vfs.append(
        f"subtitles={sp}:fontsdir={FD}:force_style='FontName={FONT_NAME},"
        f"FontSize={fsize},PrimaryColour={ass_color},OutlineColour=&H80000000,"
        f"BorderStyle=1,Outline=2,Alignment=2,MarginV=30'")

    cmd = [ff, "-y", "-v", "error", "-i", vp,
           "-vf", ",".join(vfs),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", out]
    try:
        with st.spinner("Video ထုတ်နေတယ်... (ခနစောင့်ပါ)"):
            subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=1200)
        st.success("ပြီးပြီ! ✓")
        st.video(out)
        with open(out, "rb") as f:
            st.download_button("⬇️ Video ဒေါင်းမယ်", f,
                               file_name="myanmar_subtitled.mp4", mime="video/mp4")
    except subprocess.TimeoutExpired:
        st.error("Video ကြာလွန်းလို့ ရပ်လိုက်တယ်။ Video အတိုနဲ့ စမ်းကြည့်ပါ။")
    except subprocess.CalledProcessError as ex:
        st.error("Video ထုတ်ရာမှာ အမှားတက်တယ်:")
        st.code((ex.stderr or "unknown")[-1500:])
