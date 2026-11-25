import math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, features
I="/usr/share/fonts/opentype/inter/"
def F(name,s): return ImageFont.truetype(I+name,s)
VZ="/home/claude/cryptoai-main-site/static/fonts/Vazirmatn-Bold.ttf"
BG=(5,9,19); CY=(34,211,238); AM=(255,201,77); UP=(51,211,154); DN=(255,106,95); FG=(236,240,248); MU=(140,153,178)

def glow_bg(W,H,cx,cy,r,col,alpha=120):
    im=Image.new("RGB",(W,H),BG)
    g=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(g)
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=col+(alpha,))
    g=g.filter(ImageFilter.GaussianBlur(r//2))
    im.paste(g,(0,0),g); return im

def candles(d,x0,y_base,w,gap,heights,s=1):
    x=x0
    for i,(h,up) in enumerate(heights):
        col=UP if up else DN
        bh=h; top=y_base-bh
        d.line((x+w/2,top-30*s,x+w/2,y_base+22*s),fill=col,width=max(3,int(6*s)))
        d.rounded_rectangle((x,top,x+w,y_base),radius=int(8*s),fill=col)
        x+=w+gap

# ---------- profile 800x800 (rendered at 2x)
S=2; W=800*S
im=glow_bg(W,W,W//2,int(W*0.42),int(W*0.42),CY,70)
d=ImageDraw.Draw(im)
c=W//2
d.ellipse((c-int(W*0.40),c-int(W*0.40),c+int(W*0.40),c+int(W*0.40)),outline=CY,width=10*S)
# candles rising
hs=[(70,True),(120,False),(95,True),(170,True),(240,True)]
cw=56*S; gap=26*S; total=len(hs)*cw+(len(hs)-1)*gap
candles(d,c-total//2,int(W*0.52),cw,gap,[(h*S,u) for h,u in hs],S)
# trend arrow
pts=[(c-total//2-10*S,int(W*0.46)),(c-60*S,int(W*0.38)),(c+20*S,int(W*0.41)),(c+total//2+20*S,int(W*0.23))]
d.line(pts,fill=AM,width=12*S,joint="curve")
ax,ay=pts[-1]; d.polygon([(ax+18*S,ay-14*S),(ax-30*S,ay-10*S),(ax-4*S,ay+30*S)],fill=AM)
f=F("InterDisplay-Black.otf",104*S)
t="CRYPTO"; tw=d.textlength(t,font=f); d.text((c-tw/2,int(W*0.555)),t,font=f,fill=FG)
f2=F("InterDisplay-Black.otf",84*S); t2="AI"; tw=d.textlength(t2,font=f2)
d.text((c-tw/2,int(W*0.555)+112*S),t2,font=f2,fill=CY)
im.resize((800,800),Image.LANCZOS).save("profile.png")

# ---------- banner 2560x1440, safe area 1546x423 centered
W,H=2560,1440
im=glow_bg(W,H,W//2,H//2,700,CY,45)
g=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(g)
gd.ellipse((W//2+300-500,H//2-500,W//2+300+500,H//2+500),fill=AM+(28,)); g=g.filter(ImageFilter.GaussianBlur(250)); im.paste(g,(0,0),g)
d=ImageDraw.Draw(im)
# faint chart across full width
random.seed(7); y=H*0.80; pts=[]
for i in range(0,W+40,40):
    y+= random.uniform(-26,22); y=min(max(y,H*0.68),H*0.90); pts.append((i,y))
ov=Image.new("RGBA",(W,H),(0,0,0,0)); od=ImageDraw.Draw(ov)
od.line(pts,fill=CY+(70,),width=5)
for i,(x,yy) in enumerate(pts[::3]):
    up=random.random()>0.42; h=random.uniform(20,70)
    od.rounded_rectangle((x-9,yy-h/2,x+9,yy+h/2),radius=4,fill=(UP if up else DN)+(55,))
im.paste(ov,(0,0),ov); d=ImageDraw.Draw(im)
sx0=(W-1546)//2; sy0=(H-423)//2
fT=F("InterDisplay-Black.otf",150); fA=F("InterDisplay-Black.otf",150)
t1="CryptoAI"; t1w=d.textlength(t1,font=fT)
tag="ACADEMY"; fTag=F("Inter-ExtraBold.otf",52)
x=sx0+40; ytop=sy0+20
d.text((x,ytop),"Crypto",font=fT,fill=FG); cw_=d.textlength("Crypto",font=fT)
d.text((x+cw_,ytop),"AI",font=fA,fill=CY)
aw=d.textlength("AI",font=fA)
# academy pill
px=x+cw_+aw+34; py=ytop+48
pw=d.textlength(tag,font=fTag)+56
d.rounded_rectangle((px,py,px+pw,py+86),radius=43,fill=AM)
d.text((px+28,py+12),tag,font=fTag,fill=(10,14,26))
d.text((x,ytop+200),"Crypto news & trading lessons — from zero to pro",font=F("Inter-Bold.otf",54),fill=FG)
fa="آموزش و خبر کریپتو، از صفر تا حرفه‌ای"
ff=ImageFont.truetype(VZ,58,layout_engine=ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC)
kw=dict(direction="rtl",language="fa") if features.check("raqm") else {}
d.text((x,ytop+290),fa,font=ff,fill=MU,**kw)
# right side small badge
bt="NEW LESSONS · MON · WED · SAT"; fb=F("Inter-Bold.otf",34)
bw=d.textlength(bt,font=fb)
bx=sx0+1546-bw-80; by=sy0+423-60
im.save("banner.png")
# preview: safe area check
pv=im.copy(); pd=ImageDraw.Draw(pv); pd.rectangle((sx0,sy0,sx0+1546,sy0+423),outline=(255,0,0),width=4)
pv.resize((1280,720)).save("/tmp/banner_preview.png")
print("ok", features.check("raqm"))
