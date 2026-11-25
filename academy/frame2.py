import math
from PIL import Image, ImageDraw, ImageFilter
exec(open('frame.py').read().split("# ================= 16:9 long-video frame")[0])

def ema(v,n):
    k=2/(n+1); out=[]; e=v[0]
    for x in v: e=x*k+e*(1-k); out.append(e)
    return out
def rsi(cl,n=14):
    g=[0];l=[0]
    for i in range(1,len(cl)):
        dlt=cl[i]-cl[i-1]; g.append(max(dlt,0)); l.append(max(-dlt,0))
    ag=sum(g[1:n+1])/n; al=sum(l[1:n+1])/n; out=[50]*(n+1)
    for i in range(n+1,len(cl)):
        ag=(ag*(n-1)+g[i])/n; al=(al*(n-1)+l[i])/n
        out.append(100-100/(1+(ag/al if al else 99)))
    return out

def glow_ring(im,cx,cy,r,col,S):
    ov=Image.new("RGBA",im.size,(0,0,0,0)); od=ImageDraw.Draw(ov)
    od.ellipse((cx-r,cy-r,cx+r,cy+r),outline=col+(150,),width=int(10*S))
    ov=ov.filter(ImageFilter.GaussianBlur(8*S)); im.paste(ov,(0,0),ov)
    d=ImageDraw.Draw(im); d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=col,width=int(3*S)); return d

def badge(d,cx,cy,n,col,S,r=17):
    d.ellipse((cx-r*S,cy-r*S,cx+r*S,cy+r*S),fill=col)
    f=F("Inter-Bold.otf",19*S); tw=d.textlength(n,font=f); d.text((cx-tw/2,cy-12*S),n,font=f,fill=BG)

def callout(d,im,xy,title,lines,col,S,w=330):
    x,y=xy; ft=F("Inter-SemiBold.otf",20*S); fl=F("Inter-Regular.otf",17*S)
    h=(44+len(lines)*25)*S
    ov=Image.new("RGBA",im.size,(0,0,0,0)); ImageDraw.Draw(ov).rounded_rectangle((x,y,x+w*S,y+h),radius=int(12*S),fill=(12,16,26,235),outline=col+(255,),width=int(2*S)); im.paste(ov,(0,0),ov)
    d=ImageDraw.Draw(im)
    d.text((x+16*S,y+12*S),title,font=ft,fill=col)
    for i,t in enumerate(lines): d.text((x+16*S,y+42*S+i*25*S),t,font=fl,fill=TXT)
    return d,(x,y,x+w*S,y+h)

S=2; W,H=1920*S,1080*S
im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im); M=64*S
pill(d,(M,46*S),"LESSON 08  ·  INTERMEDIATE",F("Inter-SemiBold.otf",19*S),ACC,(40,33,10),S)
d.text((M,90*S),"Why go long here?",font=F("InterDisplay-Bold.otf",54*S),fill=TXT)
d.text((M,160*S),"Support retest  +  higher low  +  momentum turning up",font=F("Inter-Regular.otf",24*S),fill=MUTE)
br="CryptoAI Academy"; fb=F("Inter-SemiBold.otf",22*S); bw=d.textlength(br,font=fb)
d.ellipse((W-M-bw-34*S,54*S,W-M-bw-18*S,70*S),fill=BLUE); d.text((W-M-bw,46*S),br,font=fb,fill=TXT)
ft=F("Inter-Regular.otf",18*S); t="BTC / USDT · 4H · historical example"; d.text((W-M-d.textlength(t,font=ft),84*S),t,font=ft,fill=MUTE)

# panels
PX1=W-M-470*S
pb=(M,222*S,PX1-30*S,690*S); rb=(M,724*S,PX1-30*S,850*S)
for b in (pb,rb): d.rounded_rectangle((b[0]-18*S,b[1]-16*S,b[2]+18*S,b[3]+16*S),radius=int(16*S),fill=PANEL)
cs=make_candles(60); cl=[c[3] for c in cs]
cbox=(pb[0],pb[1]+30*S,pb[2]-90*S,pb[3]-10*S)
Y,step=chart(d,cbox,cs,S)
x=lambda i: cbox[0]+step*i+step/2
# volume
vmax=6; import random; random.seed(3)
for i,(o,h,l,c) in enumerate(cs):
    v=abs(c-o)+random.uniform(0.3,1.6)+(1.8 if 44<=i<=52 else 0)
    hh=min(v/vmax,1)*42*S; col=(UP if c>=o else DN)
    d.rectangle((x(i)-step*0.28,cbox[3]-hh,x(i)+step*0.28,cbox[3]),fill=tuple(int(cc*0.45+BG[k]*0.55) for k,cc in enumerate(col)))
# EMAs
e20=ema(cl,20); e50=ema(cl,50)
d.line([(x(i),Y(v)) for i,v in enumerate(e50)],fill=(176,128,255),width=int(2.4*S),joint="curve")
d.line([(x(i),Y(v)) for i,v in enumerate(e20)],fill=BLUE,width=int(2.4*S),joint="curve")
fl=F("Inter-Medium.otf",16*S)
lx=pb[0]; ly=pb[1]-4*S
d.text((lx,ly),"BTC/USDT 4H",font=F("Inter-SemiBold.otf",16*S),fill=TXT); lx+=140*S
for name,col in (("EMA 20",BLUE),("EMA 50",(176,128,255)),("Volume",MUTE)):
    d.line((lx,ly+11*S,lx+22*S,ly+11*S),fill=col,width=int(3*S)); d.text((lx+30*S,ly),name,font=fl,fill=MUTE); lx+=d.textlength(name,font=fl)+64*S
# support zone
sup=min(c[2] for c in cs[20:34])
overlay_rect(im,(cbox[0],Y(sup+1.6),cbox[2],Y(sup-0.6)),(38,166,154,30)); d=ImageDraw.Draw(im)
d.text((cbox[0]+8*S,Y(sup+1.6)-24*S),"SUPPORT ZONE",font=fl,fill=UP)
# trade box
hl_i=44; hl=cs[hl_i][2]; e_i=49; entry=cs[e_i][3]; stop=hl-1.2; target=entry+(entry-stop)*2.4
xe=x(e_i); xr=cbox[2]
overlay_rect(im,(xe,Y(target),xr,Y(entry)),(38,166,154,36)); overlay_rect(im,(xe,Y(entry),xr,Y(stop)),(239,83,80,36)); d=ImageDraw.Draw(im)
for v,col,lab in ((target,UP,"Target"),(entry,TXT,"Entry"),(stop,DN,"Stop")):
    dashed(d,(xe,Y(v)),(xr,Y(v)),col,S); pill(d,(xr+10*S,Y(v)-15*S),lab,F("Inter-SemiBold.otf",15*S),BG,col,S,(9,4))
# RSI
r=[]
for i in range(len(cl)):
    j=max(0,i-6); m=(cl[i]-cl[j])/max(1,i-j)
    r.append(50+38*math.tanh(m/1.1))
r=[sum(r[max(0,i-2):i+1])/len(r[max(0,i-2):i+1]) for i in range(len(r))]; lo,hi=0,100
RY=lambda v: rb[3]-(v-lo)/(hi-lo)*(rb[3]-rb[1])
overlay_rect(im,(rb[0],RY(70),cbox[2],RY(30)),(77,163,255,14)); d=ImageDraw.Draw(im)
for lv in (70,30): dashed(d,(rb[0],RY(lv)),(cbox[2],RY(lv)),GRID,S,6,6,1.5)
d.line([(x(i),RY(v)) for i,v in enumerate(r)],fill=(176,128,255),width=int(2.4*S))
d.text((rb[0],rb[1]-8*S),"RSI 14",font=F("Inter-SemiBold.otf",15*S),fill=MUTE)
d.text((cbox[2]+8*S,RY(70)-10*S),"70",font=fl,fill=MUTE); d.text((cbox[2]+8*S,RY(30)-10*S),"30",font=fl,fill=MUTE)

clean=im.copy()
# ---- focus markers
i1=min(range(20,34),key=lambda i: cs[i][2]); p1=(x(i1),Y(cs[i1][2]))            # support retest
p2=(x(hl_i),Y(hl))                         # higher low
i3=48; p3=(x(i3),Y(e20[i3]))               # reclaim EMA20
rr=min(r[18:34]); i4=18+r[18:34].index(rr); p4=(x(i4),RY(rr))  # RSI higher low
d=glow_ring(im,p1[0],p1[1]+8*S,30*S,UP,S)
d=glow_ring(im,p2[0],p2[1]+12*S,28*S,ACC,S)
d=glow_ring(im,p3[0],p3[1],26*S,BLUE,S)
r2=min(r[40:47]); i5=40+r[40:47].index(r2)
d.line((p4[0],p4[1],x(i5),RY(r2)),fill=ACC,width=int(3*S))
d=glow_ring(im,x(i5),RY(r2),18*S,ACC,S)
badge(d,p1[0]+36*S,p1[1]-22*S,"1",UP,S); badge(d,p2[0]-38*S,p2[1]+30*S,"2",ACC,S); badge(d,p3[0]-34*S,p3[1]-30*S,"3",BLUE,S)
badge(d,x(i5)+30*S,RY(r2)-6*S,"4",ACC,S,15)
# ---- magnifier lens on marker 2 (higher low + EMA + volume), with explanation
src_w,src_h=150*S,120*S; sx,sy=p2[0]-src_w/2,p2[1]-src_h/2-6*S
crop=clean.crop((int(sx),int(sy),int(sx+src_w),int(sy+src_h)))
Z=2.3; LR=int(min(src_w,src_h)*Z/2)
big=crop.resize((int(src_w*Z),int(src_h*Z)),Image.LANCZOS)
lens_c=(p2[0]-330*S,pb[1]+150*S)
mask=Image.new("L",big.size,0); ImageDraw.Draw(mask).ellipse((big.size[0]/2-LR,big.size[1]/2-LR,big.size[0]/2+LR,big.size[1]/2+LR),fill=255)
# source marker (dashed ring) + connector lines
d=ImageDraw.Draw(im)
for a in range(0,360,20):
    t0=math.radians(a); t1=math.radians(a+11); rr_=src_h/2
    d.arc((p2[0]-rr_,p2[1]-6*S-rr_,p2[0]+rr_,p2[1]-6*S+rr_),a,a+11,fill=ACC,width=int(2*S))
for ang in (40,220):
    t=math.radians(ang)
    d.line((p2[0]+math.cos(t)*src_h/2,p2[1]-6*S-math.sin(t)*src_h/2,lens_c[0]+math.cos(t)*LR,lens_c[1]-math.sin(t)*LR),fill=ACC+(0,) if False else ACC,width=int(1.6*S))
# glow + lens
ov=Image.new("RGBA",im.size,(0,0,0,0)); od=ImageDraw.Draw(ov)
od.ellipse((lens_c[0]-LR-6*S,lens_c[1]-LR-6*S,lens_c[0]+LR+6*S,lens_c[1]+LR+6*S),fill=(0,0,0,200))
ov=ov.filter(ImageFilter.GaussianBlur(14*S)); im.paste(ov,(0,0),ov)
im.paste(big,(int(lens_c[0]-big.size[0]/2),int(lens_c[1]-big.size[1]/2)),mask)
d=glow_ring(im,lens_c[0],lens_c[1],LR,ACC,S)
d.ellipse((lens_c[0]-LR,lens_c[1]-LR,lens_c[0]+LR,lens_c[1]+LR),outline=ACC,width=int(4*S))
pill(d,(lens_c[0]-52*S,lens_c[1]+LR-14*S),"ZOOM 2.3×",F("Inter-SemiBold.otf",14*S),BG,ACC,S,(10,4))
# explanation paragraph next to the lens
d,cbx=callout(d,im,(lens_c[0]+LR+22*S,lens_c[1]-92*S),"② Why this is a buy signal",
    ["Price dipped but stopped ABOVE","the last low (higher low).","Volume dried up on the dip,","then expanded on the bounce.","→ Sellers are losing control."],ACC,S,330)

# ---- big direction badge: LONG (green, arrow up)
bx,by=W-M-640*S,40*S
ov=Image.new("RGBA",im.size,(0,0,0,0)); od=ImageDraw.Draw(ov)
od.rounded_rectangle((bx,by,bx+272*S,by+112*S),radius=int(20*S),fill=UP+(40,),outline=UP+(255,),width=int(3*S)); im.paste(ov,(0,0),ov)
d=ImageDraw.Draw(im)
ax=bx+62*S; ay=by+56*S
d.polygon([(ax,ay-40*S),(ax-34*S,ay+2*S),(ax-12*S,ay+2*S),(ax-12*S,ay+38*S),(ax+12*S,ay+38*S),(ax+12*S,ay+2*S),(ax+34*S,ay+2*S)],fill=UP)
d.text((bx+112*S,by+14*S),"LONG",font=F("InterDisplay-Black.otf",46*S),fill=UP)
d.text((bx+114*S,by+70*S),"BUY SETUP",font=F("Inter-SemiBold.otf",17*S),fill=TXT)

# side panel
px=PX1+10*S; py=222*S
d.rounded_rectangle((px-28*S,py-16*S,W-M,850*S+16*S),radius=int(16*S),fill=PANEL)
d.text((px,py),"WHAT TO LOOK FOR",font=F("Inter-SemiBold.otf",17*S),fill=MUTE)
steps=[("1",UP,"Support retest","Price came back to a level that","held before — and held again."),
       ("2",ACC,"Higher low","The dip stopped above the last low:","selling pressure is fading."),
       ("3",BLUE,"Reclaim EMA 20","A close back above the 20 EMA","shows momentum turning up."),
       ("4",ACC,"RSI higher low","RSI made a higher low too —","confirming the price signal.")]
yy=py+40*S
for n,col,tt,l1,l2 in steps:
    badge(d,px+16*S,yy+14*S,n,col,S,15)
    d.text((px+44*S,yy),tt,font=F("Inter-SemiBold.otf",20*S),fill=TXT)
    d.text((px+44*S,yy+28*S),l1,font=F("Inter-Regular.otf",16*S),fill=MUTE)
    d.text((px+44*S,yy+50*S),l2,font=F("Inter-Regular.otf",16*S),fill=MUTE); yy+=92*S
d.line((px,yy,W-M-28*S,yy),fill=GRID,width=S); yy+=16*S
d.text((px,yy),"RISK : REWARD",font=F("Inter-SemiBold.otf",17*S),fill=MUTE)
d.text((px+220*S,yy-8*S),"1 : 2.4",font=F("InterDisplay-Bold.otf",40*S),fill=ACC)
d.text((px,yy+44*S),"Stop below the higher low · risk 1% per trade",font=F("Inter-Regular.otf",15*S),fill=MUTE)

# subtitle
sub="اینجا قیمت دوباره به حمایت برگشت و یک کف بالاتر ساخت؛ اولین نشانهٔ قدرت خریدارها."
fs=FA(32*S,True); sw=d.textlength(sub,font=fs,**FAKW); sy=H-150*S
overlay_rect(im,((W-sw)/2-26*S,sy-12*S,(W+sw)/2+26*S,sy+58*S),(0,0,0,175)); d=ImageDraw.Draw(im)
d.text((W/2,sy),sub,font=fs,fill=TXT,anchor="ma",**FAKW)
# chapter progress
chs=["Context","Support","Higher low","Momentum","Entry & risk"]; cw=(W-2*M)/len(chs); y0=H-62*S
for k,c in enumerate(chs):
    xa=M+cw*k+3*S; xb=M+cw*(k+1)-3*S; col=BLUE if k<=2 else GRID
    d.rounded_rectangle((xa,y0,xb,y0+6*S),radius=3*S,fill=col)
    d.text((xa,y0+12*S),c,font=F("Inter-Medium.otf",14*S),fill=TXT if k==2 else MUTE)
t="Education only · not financial advice"; d.text((W-M-d.textlength(t,font=F("Inter-Regular.otf",14*S)),y0-26*S),t,font=F("Inter-Regular.otf",14*S),fill=MUTE)
im.resize((1920,1080),Image.LANCZOS).save("frame_long_v2.png")
print("ok")
