from PIL import Image, ImageDraw, ImageFilter
exec(open('frame.py').read().split('# ================= 16:9 long-video frame')[0])
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
