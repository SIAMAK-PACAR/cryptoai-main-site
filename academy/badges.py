from PIL import Image, ImageDraw
exec(open('frame.py').read().split("# ================= 16:9 long-video frame")[0])
S=2; W,H=900*S,260*S
im=Image.new("RGB",(W,H),BG)
def badge2(im,bx,by,up):
    col=UP if up else DN
    ov=Image.new("RGBA",im.size,(0,0,0,0)); od=ImageDraw.Draw(ov)
    od.rounded_rectangle((bx,by,bx+380*S,by+150*S),radius=int(24*S),fill=col+(40,),outline=col+(255,),width=int(3*S)); im.paste(ov,(0,0),ov)
    d=ImageDraw.Draw(im); ax=bx+82*S; ay=by+75*S; k=1 if up else -1
    d.polygon([(ax,ay-50*S*k),(ax-44*S,ay+2*S*k),(ax-16*S,ay+2*S*k),(ax-16*S,ay+48*S*k),(ax+16*S,ay+48*S*k),(ax+16*S,ay+2*S*k),(ax+44*S,ay+2*S*k)],fill=col)
    d.text((bx+150*S,by+22*S),"LONG" if up else "SHORT",font=F("InterDisplay-Black.otf",54*S),fill=col)
    d.text((bx+152*S,by+96*S),"BUY SETUP" if up else "SELL SETUP",font=F("Inter-SemiBold.otf",22*S),fill=TXT)
badge2(im,60*S,55*S,True); badge2(im,510*S,55*S,False)
im.resize((900,260),Image.LANCZOS).save("badges.png"); print("ok")
