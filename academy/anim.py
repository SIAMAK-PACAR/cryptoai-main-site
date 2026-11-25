import math, sys, os, random
from PIL import Image, ImageDraw, ImageFilter
exec(open('frame.py').read().split("# ================= 16:9 long-video frame")[0])
from frame2_helpers import *  # noqa

S=1; W,H=1920,1080; M=64; FPS=24; T_END=37.0
cs=make_candles(60); cl=[c[3] for c in cs]; NC=len(cs)
PX1=W-M-470
pb=(M,222,PX1-30,690); rb=(M,724,PX1-30,850)
cbox=(pb[0],pb[1]+30,pb[2]-90,pb[3]-10)
lo=min(c[2] for c in cs)-3; hi=max(c[1] for c in cs)+9
Y=lambda v: cbox[3]-(v-lo)/(hi-lo)*(cbox[3]-cbox[1])
step=(cbox[2]-cbox[0])/NC; cw_=step*0.56
x=lambda i: cbox[0]+step*i+step/2
random.seed(3); VOL=[abs(c-o)+random.uniform(0.3,1.6)+(1.8 if 44<=i<=52 else 0) for i,(o,h,l,c) in enumerate(cs)]
e20=ema(cl,20); e50=ema(cl,50)
r=[]
for i in range(len(cl)):
    j=max(0,i-6); m=(cl[i]-cl[j])/max(1,i-j); r.append(50+38*math.tanh(m/1.1))
r=[sum(r[max(0,i-2):i+1])/len(r[max(0,i-2):i+1]) for i in range(len(r))]
RY=lambda v: rb[3]-v/100*(rb[3]-rb[1])
sup=min(c[2] for c in cs[20:34])
hl_i=44; hl=cs[hl_i][2]; e_i=49; entry=cs[e_i][3]; stop=hl-1.2; target=entry+(entry-stop)*2.4
i1=min(range(20,34),key=lambda i: cs[i][2]); p1=(x(i1),Y(cs[i1][2]))
p2=(x(hl_i),Y(hl)); i3=48; p3=(x(i3),Y(e20[i3]))
r2=min(r[40:47]); i5=40+r[40:47].index(r2); rr=min(r[18:34]); i4=18+r[18:34].index(rr)
PURP=(176,128,255)
price=lambda v: f"{v*640:,.0f}"

def ease(a): a=max(0,min(1,a)); return a*a*(3-2*a)
def ramp(t,a,b): return ease((t-a)/(b-a)) if b>a else float(t>=a)
def win(t,a,b,f=0.4): return min(ramp(t,a,a+f),1-ramp(t,b-f,b))

# ---------- timeline
def N_of(t):
    for a,b,n0,n1 in ((0.8,6,0,34),(10.5,12.5,34,45),(20,21.5,45,49),(33,36.5,49,60)):
        if t<a: return n0 if a>0.8 else 0
        if t<=b: return n0+(n1-n0)*(t-a)/(b-a)
    return 60
STEPS=[(6,10.5),(12.5,20),(21.5,25),(25,28.5)]
SUBS=[(0,6,"اول ببینیم بازار چه کرده: روند نزولی، بعد قیمت آرام می‌شود."),
      (6,10.5,"قیمت به همان سطح حمایت قبلی برگشت و دوباره از آن دفاع شد."),
      (10.5,12.5,"حالا ببینیم بعد از برگشت چه اتفاقی می‌افتد…"),
      (12.5,20,"این بار کف بالاتر ساخت؛ فروشنده‌ها دیگر قدرت قبل را ندارند."),
      (20,21.5,"و حالا اولین کندل‌های قوی…"),
      (21.5,25,"قیمت دوباره بالای EMA 20 بسته شد؛ مومنتوم رو به بالا برگشت."),
      (25,28.5,"RSI هم کف بالاتر زد و سیگنال قیمت را تأیید کرد."),
      (28.5,33,"ورود اینجاست؛ حد ضرر زیر کف بالاتر، هدف ۲.۴ برابر ریسک."),
      (33,37,"صبر و مدیریت ریسک، مهم‌تر از پیدا کردن نقطهٔ ورود است.")]
CH=[(0,6),(6,12.5),(12.5,21.5),(21.5,28.5),(28.5,99)]
CHN=["Context","Support","Higher low","Momentum","Entry & risk"]

# ---------- small-area glow (fast)
def glow(im,cx,cy,rad,col,width=3,a=1.0):
    pad=int(rad+30); box=(int(cx-pad),int(cy-pad),int(cx+pad),int(cy+pad))
    ov=Image.new("RGBA",(2*pad,2*pad),(0,0,0,0)); od=ImageDraw.Draw(ov)
    od.ellipse((pad-rad,pad-rad,pad+rad,pad+rad),outline=col+(int(150*a),),width=10)
    ov=ov.filter(ImageFilter.GaussianBlur(8))
    od=ImageDraw.Draw(ov); od.ellipse((pad-rad,pad-rad,pad+rad,pad+rad),outline=col+(int(255*a),),width=width)
    im.alpha_composite(ov,(box[0],box[1]))

def layer_fade(im,draw_fn,a):
    if a<=0.01: return
    ov=Image.new("RGBA",im.size,(0,0,0,0)); draw_fn(ov)
    if a<0.99:
        al=ov.getchannel("A").point(lambda v: int(v*a)); ov.putalpha(al)
    im.alpha_composite(ov)

def callout_rgba(ov,xy,title,lines,col,w=330):
    x0,y0=xy; d=ImageDraw.Draw(ov); h=44+len(lines)*25
    d.rounded_rectangle((x0,y0,x0+w,y0+h),radius=12,fill=(12,16,26,240),outline=col+(255,),width=2)
    d.text((x0+16,y0+12),title,font=F("Inter-SemiBold.otf",20),fill=col)
    for i,tx in enumerate(lines): d.text((x0+16,y0+42+i*25),tx,font=F("Inter-Regular.otf",17),fill=TXT)

# ---------- static base
def make_base():
    im=Image.new("RGBA",(W,H),BG+(255,)); d=ImageDraw.Draw(im)
    for b in (pb,rb): d.rounded_rectangle((b[0]-18,b[1]-16,b[2]+18,b[3]+16),radius=16,fill=PANEL)
    px=PX1+10; d.rounded_rectangle((px-28,222-16,W-M,866),radius=16,fill=PANEL)
    for k in range(1,6):
        yy=cbox[1]+(cbox[3]-cbox[1])*k/6; d.line((cbox[0],yy,cbox[2],yy),fill=GRID,width=1)
    fl=F("Inter-Medium.otf",16); lx=pb[0]; ly=pb[1]-4
    d.text((lx,ly),"BTC/USDT 4H",font=F("Inter-SemiBold.otf",16),fill=TXT); lx+=140
    for name,col in (("EMA 20",BLUE),("EMA 50",PURP),("Volume",MUTE)):
        d.line((lx,ly+11,lx+22,ly+11),fill=col,width=3); d.text((lx+30,ly),name,font=fl,fill=MUTE); lx+=d.textlength(name,font=fl)+64
    ov=Image.new("RGBA",im.size,(0,0,0,0)); ImageDraw.Draw(ov).rectangle((rb[0],RY(70),cbox[2],RY(30)),fill=(77,163,255,14)); im.alpha_composite(ov); d=ImageDraw.Draw(im)
    for lv in (70,30): dashed(d,(rb[0],RY(lv)),(cbox[2],RY(lv)),GRID,1,6,6,1.5); d.text((cbox[2]+8,RY(lv)-10),str(lv),font=fl,fill=MUTE)
    d.text((rb[0],rb[1]-8),"RSI 14",font=F("Inter-SemiBold.otf",15),fill=MUTE)
    d.text((px,222),"WHAT TO LOOK FOR",font=F("Inter-SemiBold.otf",17),fill=MUTE)
    return im
BASE=make_base()

def header(ov):
    d=ImageDraw.Draw(ov)
    pill(d,(M,46),"LESSON 08  ·  INTERMEDIATE",F("Inter-SemiBold.otf",19),ACC,(40,33,10),1)
    d.text((M,90),"Why go long here?",font=F("InterDisplay-Bold.otf",54),fill=TXT)
    d.text((M,160),"Support retest  +  higher low  +  momentum turning up",font=F("Inter-Regular.otf",24),fill=MUTE)
    br="CryptoAI Academy"; fb=F("Inter-SemiBold.otf",22); bw=d.textlength(br,font=fb)
    d.ellipse((W-M-bw-34,54,W-M-bw-18,70),fill=BLUE); d.text((W-M-bw,46),br,font=fb,fill=TXT)
    ft=F("Inter-Regular.otf",18); s="BTC / USDT · 4H · historical example"; d.text((W-M-d.textlength(s,font=ft),84),s,font=ft,fill=MUTE)

def draw_chart(im,t,N):
    d=ImageDraw.Draw(im); k=int(N); f=N-k
    live=[]  # candles to draw (OHLC), last one may be forming
    for i in range(min(k,NC)): live.append(cs[i])
    if k<NC and f>0.02:
        o,h,l,c=cs[k]; cc=o+(c-o)*f+math.sin(t*11)*0.35*(1-f)
        live.append((o,max(o,cc)+(h-max(o,c))*f,min(o,cc)-(min(o,c)-l)*f,cc))
    elif live:  # tick wiggle on last closed candle while paused
        o,h,l,c=live[-1]; cc=c+math.sin(t*7)*0.18; live[-1]=(o,max(h,cc),min(l,cc),cc)
    n=len(live)
    for i,(o,h,l,c) in enumerate(live):
        v=VOL[i]*(f if (i==n-1 and k<NC and f>0.02) else 1); hh=min(v/6,1)*42; col=UP if c>=o else DN
        d.rectangle((x(i)-step*0.28,cbox[3]-hh,x(i)+step*0.28,cbox[3]),fill=tuple(int(cc_*0.45+BG[q]*0.55) for q,cc_ in enumerate(col)))
    for i,(o,h,l,c) in enumerate(live):
        col=UP if c>=o else DN; d.line((x(i),Y(h),x(i),Y(l)),fill=col,width=2)
        tp,bt=sorted((Y(o),Y(c))); d.rectangle((x(i)-cw_/2,tp,x(i)+cw_/2,max(bt,tp+1.5)),fill=col)
    if n>=2:
        cl_=[c[3] for c in live]; a20=ema(cl_,20); a50=ema(cl_,50)
        d.line([(x(i),Y(v)) for i,v in enumerate(a50)],fill=PURP,width=2,joint="curve")
        d.line([(x(i),Y(v)) for i,v in enumerate(a20)],fill=BLUE,width=2,joint="curve")
        rl=r[:n-1]+[r[n-1] if n-1<len(r) else r[-1]]
        if n-1<len(r): rl[-1]=r[n-2]+(r[n-1]-r[n-2])*(f if f>0.02 else 1)+math.sin(t*7)*0.8
        d.line([(x(i),RY(v)) for i,v in enumerate(rl)],fill=PURP,width=2)
        cp=live[-1][3]; col=UP if live[-1][3]>=live[-1][0] else DN
        dashed(d,(x(n-1)+cw_,Y(cp)),(cbox[2],Y(cp)),col,1,4,5,1)
        pill(d,(cbox[2]+6,Y(cp)-13),price(cp),F("Inter-SemiBold.otf",14),BG,col,1,(8,4))
    return n

def frame(t):
    im=BASE.copy(); N=N_of(t)
    layer_fade(im,header,ramp(t,0,0.8))
    # support zone (step1 onward)
    a=ramp(t,6,6.6)
    if a>0:
        def sz(ov):
            dd=ImageDraw.Draw(ov); dd.rectangle((cbox[0],Y(sup+1.6),cbox[2],Y(sup-0.6)),fill=(38,166,154,32))
            dd.text((cbox[0]+8,Y(sup+1.6)-24),"SUPPORT ZONE",font=F("Inter-Medium.otf",16),fill=UP)
        layer_fade(im,sz,a)
    # trade box (entry phase)
    a=ramp(t,29.2,29.9)
    if a>0:
        xe=x(e_i); xr=cbox[2]
        def tb(ov):
            dd=ImageDraw.Draw(ov)
            dd.rectangle((xe,Y(target),xr,Y(entry)),fill=(38,166,154,40)); dd.rectangle((xe,Y(entry),xr,Y(stop)),fill=(239,83,80,40))
            for v,col,lab in ((target,UP,"Target"),(entry,TXT,"Entry"),(stop,DN,"Stop")):
                dashed(dd,(xe,Y(v)),(xr,Y(v)),col,1); pill(dd,(xe+8,Y(v)-30 if lab!="Stop" else Y(v)+6),lab+"  "+price(v),F("Inter-SemiBold.otf",14),BG,col,1,(8,4))
        layer_fade(im,tb,a)
    draw_chart(im,t,N)
    clean=im.copy()
    pulse=0.5+0.5*math.sin(t*5)
    # markers: bright while explained, dim afterwards
    mk=[(0,p1[0],p1[1]+8,30,UP,"1"),(1,p2[0],p2[1]+12,28,ACC,"2"),(2,p3[0],p3[1],26,BLUE,"3"),(3,x(i5),RY(r2),18,ACC,"4")]
    for si,cx,cy,rad,col,num in mk:
        a0,b0=STEPS[si]; on=ramp(t,a0,a0+0.35)
        if on<=0: continue
        active=a0<=t<b0; amt=on*(1.0 if active else 0.35)
        if si==3:
            ImageDraw.Draw(im).line((x(i4),RY(rr),cx,cy),fill=ACC+(int(255*amt),),width=3)
        rad_=rad*(0.6+0.4*on)+(3*pulse if active else 0)
        glow(im,cx,cy,rad_,col,3,amt)
        if active or t>=a0:
            def bd(ov,cx=cx,cy=cy,col=col,num=num,rad=rad):
                badge(ImageDraw.Draw(ov),cx+rad*1.1,cy-rad*0.9,num,col,1,14)
            layer_fade(im,bd,amt)
    # callouts for steps 1,3,4 (only while explained)
    for si,xy,title,lines,col in ((0,(p1[0]+50,p1[1]-150),"① Support retest",["Price came back to a level","that held before — and it","held again. Buyers defend it."],UP),
                                   (2,(p3[0]-400,p3[1]-170),"③ Back above EMA 20",["A candle closed above the","blue 20 EMA → short-term","momentum turned up."],BLUE),
                                   (3,(x(i5)-420,RY(r2)-150),"④ RSI confirms",["Price made a higher low AND","RSI made a higher low →","the move has real strength."],ACC)):
        a0,b0=STEPS[si]; a=win(t,a0+0.25,b0)
        if a>0:
            yo=int((1-a)*14)
            layer_fade(im,lambda ov: callout_rgba(ov,(xy[0],xy[1]+yo),title,lines,col,320),a)
    # step 2: magnifier lens
    a0,b0=STEPS[1]; a=win(t,a0+0.3,b0,0.6)
    if a>0:
        src_w,src_h=150,120; sx,sy=p2[0]-src_w/2,p2[1]-src_h/2-6
        crop=clean.crop((int(sx),int(sy),int(sx+src_w),int(sy+src_h)))
        Z=2.3; LR=int(min(src_w,src_h)*Z/2*a)
        if LR>6:
            big=crop.resize((int(src_w*Z*a),int(src_h*Z*a)),Image.LANCZOS)
            lc=(p2[0]-330,pb[1]+150)
            def conn(ov):
                dd=ImageDraw.Draw(ov); rr_=src_h/2
                for an in range(0,360,20): dd.arc((p2[0]-rr_,p2[1]-6-rr_,p2[0]+rr_,p2[1]-6+rr_),an,an+11,fill=ACC,width=2)
                for ang in (40,220):
                    tt=math.radians(ang); dd.line((p2[0]+math.cos(tt)*rr_,p2[1]-6-math.sin(tt)*rr_,lc[0]+math.cos(tt)*LR,lc[1]-math.sin(tt)*LR),fill=ACC,width=2)
            layer_fade(im,conn,a)
            sh=Image.new("RGBA",(2*LR+80,2*LR+80),(0,0,0,0)); ImageDraw.Draw(sh).ellipse((34,34,2*LR+46,2*LR+46),fill=(0,0,0,int(200*a)))
            sh=sh.filter(ImageFilter.GaussianBlur(14)); im.alpha_composite(sh,(int(lc[0]-LR-40),int(lc[1]-LR-40)))
            mask=Image.new("L",big.size,0); ImageDraw.Draw(mask).ellipse((big.size[0]/2-LR,big.size[1]/2-LR,big.size[0]/2+LR,big.size[1]/2+LR),fill=int(255*min(1,a*1.3)))
            im.paste(big,(int(lc[0]-big.size[0]/2),int(lc[1]-big.size[1]/2)),mask)
            glow(im,lc[0],lc[1],LR,ACC,4,a)
            layer_fade(im,lambda ov: pill(ImageDraw.Draw(ov),(lc[0]-52,lc[1]+LR-14),"ZOOM 2.3×",F("Inter-SemiBold.otf",14),BG,ACC,1,(10,4)),a)
            ca=win(t,a0+0.9,b0-0.2)
            layer_fade(im,lambda ov: callout_rgba(ov,(lc[0]+LR+22,lc[1]-92+int((1-ca)*14)),"② Why this is a buy signal",
                ["Price dipped but stopped ABOVE","the last low (higher low).","Volume dried up on the dip,","then expanded on the bounce.","→ Sellers are losing control."],ACC,330),ca)
    # LONG badge pop
    a=ramp(t,28.6,29.1)
    if a>0:
        sc=1+0.18*math.sin(min(1,(t-28.6)/0.5)*math.pi)
        bw,bh=272,112; bx,by=W-M-660,40
        b=Image.new("RGBA",(bw+8,bh+8),(0,0,0,0)); bd=ImageDraw.Draw(b)
        bd.rounded_rectangle((4,4,bw+4,bh+4),radius=20,fill=UP+(40,),outline=UP+(255,),width=3)
        ax,ay=66,60; bd.polygon([(ax,ay-40),(ax-34,ay+2),(ax-12,ay+2),(ax-12,ay+38),(ax+12,ay+38),(ax+12,ay+2),(ax+34,ay+2)],fill=UP)
        bd.text((116,18),"LONG",font=F("InterDisplay-Black.otf",46),fill=UP); bd.text((118,74),"BUY SETUP",font=F("Inter-SemiBold.otf",17),fill=TXT)
        b=b.resize((int(b.width*sc),int(b.height*sc)),Image.LANCZOS)
        if a<1: b.putalpha(b.getchannel("A").point(lambda v: int(v*a)))
        im.alpha_composite(b,(int(bx+bw/2-b.width/2),int(by+bh/2-b.height/2)))
    # side panel: revealed one by one, current highlighted
    px=PX1+10; yy0=222+40
    items=[("1",UP,"Support retest","Price came back to a level that","held before — and held again."),
           ("2",ACC,"Higher low","The dip stopped above the last low:","selling pressure is fading."),
           ("3",BLUE,"Reclaim EMA 20","A close back above the 20 EMA","shows momentum turning up."),
           ("4",ACC,"RSI higher low","RSI made a higher low too —","confirming the price signal.")]
    for k_,(n_,col,tt,l1,l2) in enumerate(items):
        a0,b0=STEPS[k_]; on=ramp(t,a0,a0+0.4)
        if on<=0: continue
        act=a0<=t<b0; yy=yy0+k_*92
        def it(ov,yy=yy,n_=n_,col=col,tt=tt,l1=l1,l2=l2,act=act):
            dd=ImageDraw.Draw(ov)
            if act: dd.rounded_rectangle((px-14,yy-10,W-M-14,yy+78),radius=10,fill=col+(26,),outline=col+(120,),width=1)
            badge(dd,px+16,yy+14,n_,col,1,15)
            dd.text((px+44,yy),tt,font=F("Inter-SemiBold.otf",20),fill=TXT if act else MUTE)
            dd.text((px+44,yy+28),l1,font=F("Inter-Regular.otf",16),fill=MUTE); dd.text((px+44,yy+50),l2,font=F("Inter-Regular.otf",16),fill=MUTE)
        layer_fade(im,it,on*(1 if act else 0.55))
    a=ramp(t,29.4,30)
    if a>0:
        yy=yy0+4*92
        def rr_(ov):
            dd=ImageDraw.Draw(ov); dd.line((px,yy,W-M-28,yy),fill=GRID,width=1)
            dd.text((px,yy+16),"RISK : REWARD",font=F("Inter-SemiBold.otf",17),fill=MUTE)
            dd.text((px+220,yy+8),"1 : 2.4",font=F("InterDisplay-Bold.otf",40),fill=ACC)
            dd.text((px,yy+60),"Stop below the higher low · risk 1% per trade",font=F("Inter-Regular.otf",15),fill=MUTE)
        layer_fade(im,rr_,a)
    # subtitle
    for a0,b0,tx in SUBS:
        a=win(t,a0,b0,0.25)
        if a>0:
            def sb(ov,tx=tx):
                dd=ImageDraw.Draw(ov); fs=FA(32,True); sw=dd.textlength(tx,font=fs,**FAKW); sy=H-150
                dd.rounded_rectangle(((W-sw)/2-26,sy-12,(W+sw)/2+26,sy+58),radius=10,fill=(0,0,0,175))
                dd.text((W/2,sy),tx,font=fs,fill=TXT,anchor="ma",**FAKW)
            layer_fade(im,sb,a)
    # chapter progress
    d=ImageDraw.Draw(im); cw=(W-2*M)/5; y0=H-62
    for k_,(a0,b0) in enumerate(CH):
        xa=M+cw*k_+3; xb=M+cw*(k_+1)-3
        d.rounded_rectangle((xa,y0,xb,y0+6),radius=3,fill=GRID)
        fr=max(0,min(1,(t-a0)/(min(b0,T_END)-a0)))
        if fr>0: d.rounded_rectangle((xa,y0,xa+(xb-xa)*fr,y0+6),radius=3,fill=BLUE)
        d.text((xa,y0+12),CHN[k_],font=F("Inter-Medium.otf",14),fill=TXT if a0<=t<b0 else MUTE)
    s="Education only · not financial advice"; d.text((W-M-d.textlength(s,font=F("Inter-Regular.otf",14)),y0-26),s,font=F("Inter-Regular.otf",14),fill=MUTE)
    return im.convert("RGB")

if __name__=="__main__":
    a,b=int(sys.argv[1]),int(sys.argv[2]); os.makedirs("fr",exist_ok=True)
    for fi in range(a,b): frame(fi/FPS).save(f"fr/{fi:05d}.jpg",quality=92)
