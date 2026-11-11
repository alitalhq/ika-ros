# docs/kablolama.svg kablolama şemasını üretir: python3 docs/kablolama.py docs/kablolama.svg
# Pinler src/ika_bringup/config/hardware.yaml ile aynı tutulmalıdır.
import sys
W,H=1420,1010
o=[]
def a(s): o.append(s)
C=dict(pwr='#c62828',gnd='#222',pwm='#e65100',dig='#1565c0',enc='#2e7d32',uart='#6a1b9a',usb='#546e7a',v33='#ad1457',ana='#00838f')
def box(x,y,w,h,title,sub=None,dash=False,fill='#fafafa'):
    d=' stroke-dasharray="6 4"' if dash else ''
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="#444" stroke-width="1.6"{d}/>')
    a(f'<text x="{x+w/2}" y="{y+20}" text-anchor="middle" font-weight="700" font-size="14">{title}</text>')
    if sub: a(f'<text x="{x+w/2}" y="{y+37}" text-anchor="middle" font-size="11" fill="#555">{sub}</text>')
def t(x,y,s,anchor='start',size=12,col='#111',w='400'):
    a(f'<text x="{x}" y="{y+4}" text-anchor="{anchor}" font-size="{size}" fill="{col}" font-weight="{w}">{s}</text>')
def line(pts,col,wd=2,dash=False):
    d=' stroke-dasharray="6 4"' if dash else ''
    p=' '.join(f'{x},{y}' for x,y in pts)
    a(f'<polyline points="{p}" fill="none" stroke="{col}" stroke-width="{wd}"{d}/>')
def dot(x,y,col): a(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{col}"/>')

a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, Arial, sans-serif">')
a(f'<rect width="{W}" height="{H}" fill="#fff"/>')
t(W/2,22,'İKA robotu kablolama şeması','middle',18,w='700')
t(W/2,42,'Kaynak: src/ika_bringup/config/hardware.yaml (6 Kasım 2026 kablolaması). Sol/sağ: robotun arkasından, çizgi sensörüne (öne) bakarak.','middle',11,'#555')

GX,GY,GW,GH=560,150,320,740
# --- güç
box(30,62,200,80,'3S Li-Po','11.1 V · 4200 mAh · 40C')
t(130,128,'+ düşük gerilim alarmı (balans)','middle',10,'#c62828')
box(250,64,130,50,'Anahtar + 10 A','sigorta (önerilir)',dash=True,fill='#fff')
line([(230,82),(250,82)],C['pwr'],3)
line([(380,82),(620,82)],C['pwr'],3)
line([(400,82),(400,170)],C['pwr'],3); dot(400,82,C['pwr'])
line([(620,82),(620,GY)],C['pwr'],3)
t(410,100,'+12V','start',11,C['pwr'],'700')
t(630,100,'+','start',11,C['pwr'],'700')
line([(230,124),(245,124),(245,132),(440,132),(440,170)],C['gnd'],3)
line([(440,132),(680,132),(680,GY)],C['gnd'],3); dot(440,132,C['gnd'])
t(450,150,'GND','start',11,C['gnd'],'700'); t(690,146,'−','start',12,C['gnd'],'700')
t(720,72,'pilden ayrı kablolar (yıldız bağlantı); L298N girişine 470–1000 µF','start',10,'#555')

# --- Gemstone
box(GX,GY,GW,GH,'T3 Gemstone O1','40 pin header · DC girişi J4 (5–12 V) üstte')
t(GX+GW/2,GY+GH-20,'IMU (ICM-20948) kart üzerinde, SPI','middle',10,'#555')
# --- L298N
LX,LY,LW,LH=330,170,150,240
box(LX,LY,LW,LH,'L298N')
t(LX+LW/2,LY+LH-14,'ENA/ENB jumper\'ı yok','middle',10,'#555')
L=[(205,'IN1','15','GPIO22',C['dig']),(235,'IN2','11','GPIO17',C['dig']),(265,'ENA','32','GPIO12 · ecap0',C['pwm']),
   (305,'IN3','37','GPIO26',C['dig']),(335,'IN4','22','GPIO25',C['dig']),(365,'ENB','33','GPIO13 · epwm1 B',C['pwm'])]
for y,n,p,g,c in L:
    t(LX+LW-8,y,n,'end',12,c,'700')
    line([(LX+LW,y),(GX,y)],c)
    t(GX+8,y,f'<tspan font-weight="700">{p}</tspan>  {g}','start',12)
# motors
box(40,180,160,90,'Motor 1 · SAĞ','DCGM-3865 12 V 1:42')
box(40,300,160,90,'Motor 2 · SOL','DCGM-3865 · invert')
for y,n in [(212,'OUT1'),(242,'OUT2'),(332,'OUT3'),(362,'OUT4')]:
    t(LX+8,y,n,'start',11,'#333','700'); line([(200,y),(LX,y)],'#795548',2.4)
# encoders
def enc(y0,title,rows):
    box(270,y0,210,150,title,'motor kablosundaki enkoder uçları')
    for i,(n,p,g,c) in enumerate(rows):
        y=y0+58+i*24
        t(472,y,n,'end',12,c,'700'); line([(480,y),(GX,y)],c)
        t(GX+8,y,f'<tspan font-weight="700">{p}</tspan>  {g}','start',12)
enc(440,'Enkoder · SAĞ (Motor 1)',[('VCC','1','3V3',C['v33']),('C1 (A)','7','GPIO4',C['enc']),('C2 (B)','29','GPIO5',C['enc']),('GND','—','GND',C['gnd'])])
enc(610,'Enkoder · SOL (Motor 2)',[('VCC','17','3V3',C['v33']),('C1 (A)','13','GPIO27',C['enc']),('C2 (B)','16','GPIO23',C['enc']),('GND','—','GND',C['gnd'])])
t(270,776,'Enkoderleri yalnızca 3.3 V ile besleyin','start',10,'#c62828')
t(270,790,'(5 V GPIO\'yu yakar).','start',10,'#c62828')
t(30,800,'GND: header\'daki herhangi bir GND','start',10,'#555')
t(30,814,'(pin 6, 9, 14, 20, 25, 30, 34, 39).','start',10,'#555')

# --- right side: Deneyap
DX,DY,DW,DH=990,150,190,330
box(DX,DY,DW,DH,'Deneyap Mini v2','ESP32-S2')
R=[(205,'RX · D0 (GPIO44)','8','UART TX · GPIO14',C['uart']),(235,'TX · D1 (GPIO43)','10','UART RX · GPIO15',C['uart']),(265,'GND','6','GND',C['gnd'])]
for y,n,p,g,c in R:
    t(DX+8,y,n,'start',11,c,'700'); line([(GX+GW,y),(DX,y)],c)
    t(GX+GW-8,y,f'{g}  <tspan font-weight="700">{p}</tspan>','end',12)
t(GX+GW+12,219,'/dev/ttyS3 · 115200','start',10,C['uart'])
t(GX+GW+12,282,'çapraz: TX→RX, RX←TX','start',10,'#555')
y=320; t(GX+GW-8,y,'USB-A','end',12,C['usb'],'700'); line([(GX+GW,y),(DX,y)],C['usb'],3)
t(DX+8,y,'USB-C','start',12,C['usb'],'700'); t(GX+GW+12,y-10,'besleme + firmware','start',10,C['usb'])
t(GX+GW+12,y+14,'(/dev/ttyACM0)','start',10,C['usb'])
# line sensor
SX,SY,SW,SH=1250,150,150,330
box(SX,SY,SW,SH,'Çizgi sensörü','8 kanal analog')
for y,dn,sn,c in [(205,'3V3','VCC + IR',C['v33']),(235,'GND','GND',C['gnd'])]:
    t(DX+DW-8,y,dn,'end',12,c,'700'); line([(DX+DW,y),(SX,y)],c); t(SX+8,y,sn,'start',12,c,'700')
gp=[7,8,9,10,11,12,13,16]
for k in range(8):
    y=290+k*24
    t(DX+DW-8,y,f'A{k} <tspan fill="#777" font-weight="400" font-size="10">(G{gp[k]})</tspan>','end',12,C['ana'],'700')
    line([(DX+DW,y),(SX,y)],C['ana'])
    t(SX+8,y,f'D{k+1}','start',12,C['ana'],'700')
t(DX,494,'Sensör: yalnızca 3.3 V, "3.3V" köprüsü lehimli, zemine 3–6 mm.','start',10,'#c62828')
t(DX,508,'Dizi ters takılı: yazılımda spacing = −0.009525; A0…A7 sırası','start',10,'#c62828')
t(DX,522,'düzeltilirse spacing yeniden pozitif yapılmalı.','start',10,'#c62828')

# lidar
y=575
t(GX+GW-8,y,'USB-A','end',12,C['usb'],'700'); line([(GX+GW,y),(DX,y)],C['usb'],3)
box(DX,545,DW,62,'CP210x adaptör','lidarın kendi kartı')
line([(DX+DW,y),(SX,y)],'#555',4)
box(SX,545,SW,62,'RPLIDAR A1','yaw ≈ 180°')
t(GX+GW+12,y-10,'/dev/serial/by-id/*CP210*','start',10,C['usb'])

# PC usb-c
y=655
t(GX+GW-8,y,'USB-C','end',12,C['usb'],'700'); line([(GX+GW,y),(DX,y)],C['usb'],2,True)
box(DX,627,SX+SW-DX,56,'Bilgisayar (isteğe bağlı)','ssh gemstone@192.168.7.2 · takılıysa kart USB\'den beslenir',dash=True,fill='#fff')

# reserved
box(GX+GW+20,700,505,205,'Bu robotta boşta / yedek bağlantılar',None,fill='#fffde7')
rows=['pin 12 · GPIO18 (ecap2) → lidar MOTOCTL — yalnız GPIO lidar',
      'pin 18 TX / pin 26 RX (ttyS0) → lidar — yalnız GPIO lidar;',
      '   overlay: ika-bt-off + uart-ttys0, spidev0-2cs yerine 1cs',
      'pin 2, 4 · 5V → lidar V5/VMOTO — yalnız GPIO lidar',
      'type: digital çizgi: D1…D8 → pin 40, 31, 35, 3, 36, 38, 24, 5',
      '   (pin 3/5 için i2c1 overlay\'i kapalı olmalı)',
      'Pin 37 artık L298N IN3; eski şemadaki pin 18 lidara verildi.']
for i,s in enumerate(rows): t(GX+GW+32,745+i*21,s,'start',11,'#333')

# legend
lx,ly=30,840
items=[('Pil +',C['pwr']),('GND',C['gnd']),('PWM',C['pwm']),('Yön (GPIO)',C['dig']),('Enkoder',C['enc']),('3.3 V',C['v33']),('UART',C['uart']),('USB',C['usb']),('Analog',C['ana']),('Motor',  '#795548')]
for i,(n,c) in enumerate(items):
    x=lx+(i%5)*105; yy=ly+(i//5)*26
    line([(x,yy),(x+26,yy)],c,3); t(x+32,yy,n,'start',11)
t(30,920,'Pin numarası = Gemstone 40 pin header\'daki fiziksel numara (kalın). Kesik çizgi: isteğe bağlı/önerilen.','start',10,'#555')
t(30,936,'Gemstone DC girişi: resmi 5–12 V; v0.2 şemasında eFuse ~14.7 V\'ta keser, dolu 3S (12.6 V) güvenli. Pili Type-C\'ye asla bağlamayın.','start',10,'#555')
t(30,952,'Bkz. docs/donanim.md (pin tablosu) ve docs/guvenlik.md (pil güvenliği).','start',10,'#555')
a('</svg>')
open(sys.argv[1],'w').write('\n'.join(o))
