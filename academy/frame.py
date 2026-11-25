import random, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, features
I="/usr/share/fonts/opentype/inter/"
VZB="/home/claude/cryptoai-main-site/static/fonts/Vazirmatn-Bold.ttf"; VZR="/home/claude/cryptoai-main-site/static/fonts/Vazirmatn-Regular.ttf"
RAQM=features.check("raqm")
def F(n,s): return ImageFont.truetype(I+n,s)
def FA(s,b=False): return ImageFont.truetype(VZB if b else VZR,s,layout_engine=ImageFont.Layout.RAQM if RAQM else ImageFont.Layout.BASIC)
FAKW=dict(direction="rtl",language="fa") if RAQM else {}
BG=(9,12,19); PANEL=(15,19,29); GRID=(27,33,46); TXT=(232,236,243); MUTE=(122,133,153)
UP=(38,166,154); DN=(239,83,80); ACC=(242,183,5); BLUE=(77,163,255)

def make_candles(n,seed=4):
    random.seed(seed); p=100.0; out=[]
    # downtrend, base, retest, higher low, breakout
    drift=[-0.9]*22+[0.15]*10+[0.9]*8+[-0.6]*5+[0.2]*4+[1.1]*12
    for i in range(n):
        d=drift[i] if i<len(drift) else 0.6
        o=p; c=o+d+random.uniform(-1.1,1.1)
        h=max(o,c)+random.uniform(0.2,1.2); l=min(o,c)-random.uniform(0.2,1.2)
        out.append((o,h,l,c)); p=c
    return out

def chart(d,box,cs,S,annot=True,future_from=None):
    x0,y0,x1,y1=box
    lo=min(c[2] for c in cs)-3; hi=max(c[1] for c in cs)+3
    Y=lambda v: y1-(v-lo)/(hi-lo)*(y1-y0)
    n=len(cs); step=(x1-x0)/n; w=step*0.56
    for k in range(1,6):
        yy=y0+(y1-y0)*k/6; d.line((x0,yy,x1,yy),fill=GRID,width=S)
    for i,(o,h,l,c) in enumerate(cs):
        if future_from and i>=future_from: continue
        cx=x0+step*i+step/2; col=UP if c>=o else DN
        d.line((cx,Y(h),cx,Y(l)),fill=col,width=max(1,int(1.6*S)))
        t,b=sorted((Y(o),Y(c)))
        d.rectangle((cx-w/2,t,cx+w/2,max(b,t+1.5*S)),fill=col)
    return Y,step

def dashed(d,a,b,col,S,dash=10,gap=7,width=2):
    (xa,ya),(xb,yb)=a,b; L=math.hypot(xb-xa,yb-ya); n=int(L/((dash+gap)*S))+1
    for k in range(n):
        s=k*(dash+gap)*S/L; e=min(1,(k*(dash+gap)+dash)*S/L)
        d.line((xa+(xb-xa)*s,ya+(yb-ya)*s,xa+(xb-xa)*e,ya+(yb-ya)*e),fill=col,width=int(width*S))

def pill(d,xy,text,font,fg,bg,S,pad=(14,7)):
    x,y=xy; tw=d.textlength(text,font=font); bb=font.getbbox(text)
    h=bb[3]-bb[1]
    d.rounded_rectangle((x,y,x+tw+2*pad[0]*S,y+h+2*pad[1]*S+4*S),radius=int(8*S),fill=bg)
    d.text((x+pad[0]*S,y+pad[1]*S-bb[1]+2*S),text,font=font,fill=fg)
    return x+tw+2*pad[0]*S

def overlay_rect(im,box,fill):
    ov=Image.new("RGBA",im.size,(0,0,0,0)); ImageDraw.Draw(ov).rectangle(box,fill=fill); im.paste(ov,(0,0),ov)

# ================= 16:9 long-video frame
S=2; W,H=1920*S,1080*S
im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
M=72*S
# header
pill(d,(M,58*S),"LESSON 08  ·  INTERMEDIATE",F("Inter-SemiBold.otf",20*S),ACC,(40,33,10),S)
d.text((M,108*S),"Why go long here?",font=F("InterDisplay-Bold.otf",60*S),fill=TXT)
d.text((M,186*S),"Reading a support retest and a higher low",font=F("Inter-Regular.otf",26*S),fill=MUTE)
br="CryptoAI Academy"; fb=F("Inter-SemiBold.otf",22*S); bw=d.textlength(br,font=fb)
d.ellipse((W-M-bw-34*S,64*S,W-M-bw-18*S,80*S),fill=BLUE); d.text((W-M-bw,58*S),br,font=fb,fill=TXT)
d.text((W-M-d.textlength("BTC / USDT · 4H · historical example",font=F("Inter-Regular.otf",18*S)),98*S),"BTC / USDT · 4H · historical example",font=F("Inter-Regular.otf",18*S),fill=MUTE)
# chart panel
cb=(M,250*S,W-M-560*S,H-210*S)
d.rounded_rectangle((cb[0]-24*S,cb[1]-24*S,cb[2]+24*S,cb[3]+24*S),radius=int(18*S),fill=PANEL)
cs=make_candles(60)
Y,step=chart(d,cb,cs,S)
x=lambda i: cb[0]+step*i+step/2
# support zone
sup=min(c[2] for c in cs[20:34])
overlay_rect(im,(cb[0],Y(sup+1.6),cb[2],Y(sup-0.6)),(38,166,154,34)); d=ImageDraw.Draw(im)
fl=F("Inter-Medium.otf",17*S)
d.text((cb[0]+10*S,Y(sup+1.6)-26*S),"SUPPORT ZONE",font=fl,fill=UP)
# higher low marker
hl_i=44; hl=cs[hl_i][2]
d.ellipse((x(hl_i)-9*S,Y(hl)+10*S,x(hl_i)+9*S,Y(hl)+28*S),outline=ACC,width=int(2.5*S))
d.text((x(hl_i)-60*S,Y(hl)+38*S),"Higher low",font=fl,fill=ACC)
# entry / stop / target
e_i=49; entry=cs[e_i][3]; stop=hl-1.2; target=entry+(entry-stop)*2.4
xe=x(e_i); xr=cb[2]
overlay_rect(im,(xe,Y(target),xr,Y(entry)),(38,166,154,40)); overlay_rect(im,(xe,Y(entry),xr,Y(stop)),(239,83,80,40)); d=ImageDraw.Draw(im)
for v,col,lab in ((target,UP,"Target"),(entry,TXT,"Entry"),(stop,DN,"Stop-loss")):
    dashed(d,(xe,Y(v)),(xr,Y(v)),col,S)
    t=f"{lab}"; pill(d,(xr+12*S,Y(v)-17*S),t,F("Inter-SemiBold.otf",16*S),BG,col,S,(10,5))
# side panel
px=W-M-380*S; py=250*S
d.rounded_rectangle((px-24*S,py-24*S,W-M,H-210*S+24*S),radius=int(18*S),fill=PANEL)
d.text((px,py),"THE SETUP",font=F("Inter-SemiBold.otf",18*S),fill=MUTE)
items=[("1","Downtrend, then a base"),("2","Support held on the retest"),("3","A higher low formed"),("4","Stop below the higher low")]
yy=py+44*S
for n,t in items:
    d.ellipse((px,yy+2*S,px+30*S,yy+32*S),outline=BLUE,width=int(2*S))
    d.text((px+10*S,yy+4*S),n,font=F("Inter-SemiBold.otf",18*S),fill=BLUE)
    d.text((px+46*S,yy+3*S),t,font=F("Inter-Regular.otf",21*S),fill=TXT); yy+=60*S
d.line((px,yy+6*S,W-M-24*S,yy+6*S),fill=GRID,width=S); yy+=30*S
d.text((px,yy),"RISK : REWARD",font=F("Inter-SemiBold.otf",18*S),fill=MUTE)
d.text((px,yy+30*S),"1 : 2.4",font=F("InterDisplay-Bold.otf",64*S),fill=ACC)
d.text((px,yy+112*S),"Risk 1% of the account per trade",font=F("Inter-Regular.otf",19*S),fill=MUTE)
# subtitle bar
sub="اینجا قیمت دوباره به حمایت برگشت و یک کف بالاتر ساخت؛ این اولین نشانهٔ قدرت خریدارهاست."
fs=FA(34*S,True); sw=d.textlength(sub,font=fs,**FAKW)
sy=H-150*S
overlay_rect(im,((W-sw)/2-28*S,sy-12*S,(W+sw)/2+28*S,sy+62*S),(0,0,0,170)); d=ImageDraw.Draw(im)
d.text((W/2,sy),sub,font=fs,fill=TXT,anchor="ma",**FAKW)
# progress + disclaimer
d.rounded_rectangle((M,H-46*S,W-M,H-40*S),radius=3*S,fill=GRID); d.rounded_rectangle((M,H-46*S,M+(W-2*M)*0.42,H-40*S),radius=3*S,fill=BLUE)
d.text((M,H-36*S),"Education only · not financial advice",font=F("Inter-Regular.otf",15*S),fill=MUTE)
im.resize((1920,1080),Image.LANCZOS).save("frame_long.png")

# ================= 9:16 short frame
S=2; W,H=1080*S,1920*S
im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im); M=64*S
pill(d,(M,150*S),"LONG vs SHORT  ·  60s",F("Inter-SemiBold.otf",26*S),ACC,(40,33,10),S)
d.text((M,220*S),"Why a long",font=F("InterDisplay-Bold.otf",92*S),fill=TXT)
d.text((M,322*S),"made sense here",font=F("InterDisplay-Bold.otf",92*S),fill=BLUE)
cb=(M+10*S,560*S,W-M-10*S,1250*S)
d.rounded_rectangle((M-14*S,cb[1]-30*S,W-M+14*S,cb[3]+30*S),radius=int(26*S),fill=PANEL)
cs=make_candles(60)
Y,step=chart(d,cb,cs,S)
x=lambda i: cb[0]+step*i+step/2
sup=min(c[2] for c in cs[20:34])
overlay_rect(im,(cb[0],Y(sup+1.6),cb[2],Y(sup-0.6)),(38,166,154,34)); d=ImageDraw.Draw(im)
hl=cs[44][2]
e_i=49; entry=cs[e_i][3]; stop=hl-1.2; target=entry+(entry-stop)*2.4; xe=x(e_i); xr=cb[2]
overlay_rect(im,(xe,Y(target),xr,Y(entry)),(38,166,154,40)); overlay_rect(im,(xe,Y(entry),xr,Y(stop)),(239,83,80,40)); d=ImageDraw.Draw(im)
for v,col in ((target,UP),(entry,TXT),(stop,DN)): dashed(d,(xe,Y(v)),(xr,Y(v)),col,S)
d.ellipse((x(44)-12*S,Y(hl)+10*S,x(44)+12*S,Y(hl)+34*S),outline=ACC,width=int(3*S))
d.text((cb[0]+12*S,Y(sup+1.6)-34*S),"SUPPORT",font=F("Inter-Medium.otf",24*S),fill=UP)
d.text((x(44)-150*S,Y(hl)+44*S),"Higher low",font=F("Inter-Medium.otf",26*S),fill=ACC)
# steps
yy=1340*S
for n,t in (("1","Support held"),("2","Higher low formed"),("3","Stop below the low")):
    d.ellipse((M,yy,M+44*S,yy+44*S),outline=BLUE,width=int(3*S)); d.text((M+14*S,yy+4*S),n,font=F("Inter-SemiBold.otf",28*S),fill=BLUE)
    d.text((M+66*S,yy+2*S),t,font=F("Inter-Regular.otf",34*S),fill=TXT); yy+=70*S
sub="حمایت حفظ شد و کف بالاتر ساخته شد"
fs=FA(44*S,True); sw=d.textlength(sub,font=fs,**FAKW); sy=1590*S
overlay_rect(im,((W-sw)/2-28*S,sy-14*S,(W+sw)/2+28*S,sy+78*S),(0,0,0,170)); d=ImageDraw.Draw(im)
d.text((W/2,sy),sub,font=fs,fill=TXT,anchor="ma",**FAKW)
d.text((M,H-150*S),"Full lesson on the channel  →",font=F("Inter-SemiBold.otf",30*S),fill=ACC)
d.text((M,H-100*S),"CryptoAI Academy · historical example · not financial advice",font=F("Inter-Regular.otf",22*S),fill=MUTE)
im.resize((1080,1920),Image.LANCZOS).save("frame_short.png")
print("ok")
