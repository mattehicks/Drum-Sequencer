import json, os

SCHEMA = {
 'kick':    {'level':(0,1),'startFreq':(40,300),'endFreq':(20,120),'pitchDecay':(0.01,0.3),'ampDecay':(0.05,1.0),'click':(0,1),'drive':(0,1)},
 'snare':   {'level':(0,1),'tone1':(120,400),'tone2':(150,500),'toneDecay':(0.02,0.5),'noiseFreq':(500,6000),'noiseQ':(0.3,8),'noiseDecay':(0.03,0.6)},
 'hihat':   {'level':(0,1),'fundamental':(200,500),'hpFreq':(2000,9000),'decay':(0.03,1.5)},
 'cymbal':  {'level':(0,1),'length':(0.2,3.2),'brightness':(200,6000),'pitch':(0.6,1.6)},
 'clap':    {'level':(0,1),'centerFreq':(800,3000),'bursts':(2,5),'spacing':(0.008,0.04),'tailLength':(0.1,0.6),'tailDecay':(1,6),'tailMix':(0,1)},
 'cowbell': {'level':(0,1),'freq1':(400,1000),'ratio':(1.1,2.0),'q':(1,15),'decay':(0.1,1.2)},
 'tom':     {'level':(0,1),'startFreq':(150,500),'endFreq':(60,250),'pitchDecay':(0.02,0.2),'decay':(0.1,0.8),'noiseAmt':(0,1)},
 'ks':      {'level':(0,1),'frequency':(60,800),'damping':(0.8,0.999)},
 'chaos':   {'level':(0,1),'centerFreq':(400,4000),'q':(0.5,6),'decay':(0.05,0.6),'chaosR':(3.5,4.0)},
 'click1':  {'level':(0,1),'pitch':(0.5,2.0)},
 'click2':  {'level':(0,1),'pitch':(0.5,2.0)},
}
STOCK_KEYS = {'kick':'1','snare':'2','hihat':'3','cymbal':'4','clap':'5','cowbell':'6','tom':'7','ks':'8','chaos':'9','click1':'','click2':''}

def V(vid, name, **params):
    return {'id':vid,'name':name,'key':STOCK_KEYS[vid],'isClone':False,'clonedFrom':None,'params':params}
def C(cid, src, name, **params):
    return {'id':cid,'name':name,'key':'','isClone':True,'clonedFrom':src,'params':params}

KITS = {}

KITS['kit-808-classic'] = ('808 Classic', 'Boomy analog-style kit: long sine kick, snappy snare, classic cowbell, closed + open hats.', [
 V('kick','808 Kick', level=0.95, startFreq=80, endFreq=45, pitchDecay=0.03, ampDecay=0.7, click=0.05, drive=0.1),
 V('snare','808 Snare', level=0.88, tone1=180, tone2=330, toneDecay=0.1, noiseFreq=1800, noiseQ=1.0, noiseDecay=0.15),
 V('hihat','Closed Hat', level=0.75, fundamental=320, hpFreq=7000, decay=0.05),
 C('hihat-open','hihat','Open Hat', level=0.7, fundamental=320, hpFreq=7000, decay=0.5),
 V('cymbal','Crash', level=0.7, length=2.0, brightness=800, pitch=1.0),
 V('clap','808 Clap', level=0.85, centerFreq=1200, bursts=3, spacing=0.012, tailLength=0.3, tailDecay=3, tailMix=0.6),
 V('cowbell','808 Cowbell', level=0.8, freq1=587, ratio=1.48, q=6, decay=0.35),
 V('tom','Mid Tom', level=0.85, startFreq=220, endFreq=90, pitchDecay=0.04, decay=0.4, noiseAmt=0.05),
 C('tom-low','tom','Low Tom', level=0.85, startFreq=170, endFreq=70, pitchDecay=0.04, decay=0.45, noiseAmt=0.05),
 C('tom-hi','tom','Hi Tom', level=0.85, startFreq=320, endFreq=140, pitchDecay=0.04, decay=0.35, noiseAmt=0.05),
 V('ks','Perc Pluck', level=0.7, frequency=110, damping=0.98),
 V('chaos','Maraca', level=0.65, centerFreq=3200, q=2.0, decay=0.08, chaosR=3.97),
 V('click1','Click Hi', level=0.8, pitch=1.0),
 V('click2','Click Lo', level=0.8, pitch=0.75),
])

KITS['kit-909-punch'] = ('909 Punch', 'House/techno kit: clicky driven kick, cutting snare, bright hats, four-burst clap.', [
 V('kick','909 Kick', level=0.95, startFreq=160, endFreq=48, pitchDecay=0.05, ampDecay=0.45, click=0.5, drive=0.35),
 V('snare','909 Snare', level=0.9, tone1=200, tone2=340, toneDecay=0.08, noiseFreq=2600, noiseQ=0.8, noiseDecay=0.22),
 V('hihat','Closed Hat', level=0.75, fundamental=340, hpFreq=8000, decay=0.04),
 C('hihat-open','hihat','Open Hat', level=0.7, fundamental=340, hpFreq=8000, decay=0.35),
 V('cymbal','Crash', level=0.7, length=1.6, brightness=1500, pitch=1.15),
 V('clap','909 Clap', level=0.88, centerFreq=1500, bursts=4, spacing=0.01, tailLength=0.3, tailDecay=3.5, tailMix=0.55),
 V('cowbell','Bell', level=0.75, freq1=700, ratio=1.5, q=8, decay=0.2),
 V('tom','Tom', level=0.85, startFreq=260, endFreq=105, pitchDecay=0.05, decay=0.28, noiseAmt=0.3),
 V('ks','Pluck', level=0.7, frequency=220, damping=0.99),
 V('chaos','Shaker', level=0.6, centerFreq=1600, q=1.2, decay=0.12, chaosR=3.99),
 V('click1','Click Hi', level=0.8, pitch=1.0),
 V('click2','Click Lo', level=0.8, pitch=0.75),
])

KITS['kit-trap-modern'] = ('Trap Modern', 'Long sub 808 kick, bright tight hats for rolls, layered clap, bass pluck on KS.', [
 V('kick','808 Sub', level=1.0, startFreq=120, endFreq=28, pitchDecay=0.09, ampDecay=1.0, click=0.25, drive=0.3),
 V('snare','Trap Snare', level=0.9, tone1=240, tone2=480, toneDecay=0.06, noiseFreq=4200, noiseQ=1.5, noiseDecay=0.18),
 V('hihat','Roll Hat', level=0.7, fundamental=400, hpFreq=8500, decay=0.03),
 C('hihat-open','hihat','Open Hat', level=0.65, fundamental=400, hpFreq=8500, decay=0.25),
 V('cymbal','Crash', level=0.65, length=1.2, brightness=2500, pitch=1.3),
 V('clap','Trap Clap', level=0.9, centerFreq=2000, bursts=4, spacing=0.009, tailLength=0.35, tailDecay=2.5, tailMix=0.7),
 V('cowbell','Metal Blip', level=0.7, freq1=800, ratio=1.6, q=10, decay=0.15),
 V('tom','Tom', level=0.8, startFreq=300, endFreq=120, pitchDecay=0.04, decay=0.2, noiseAmt=0.1),
 V('ks','Bass Pluck', level=0.85, frequency=82, damping=0.997),
 V('chaos','Tick', level=0.55, centerFreq=2800, q=3.0, decay=0.06, chaosR=3.97),
 V('click1','Click Hi', level=0.8, pitch=1.0),
 V('click2','Click Lo', level=0.8, pitch=0.75),
])

KITS['kit-acoustic-room'] = ('Acoustic Room', 'Natural-leaning kit: short punchy kick, buzzy snare, three toms, long dark crash.', [
 V('kick','Room Kick', level=0.9, startFreq=95, endFreq=52, pitchDecay=0.04, ampDecay=0.28, click=0.55, drive=0.08),
 V('snare','Wood Snare', level=0.88, tone1=185, tone2=315, toneDecay=0.14, noiseFreq=2400, noiseQ=0.9, noiseDecay=0.3),
 V('hihat','Closed Hat', level=0.7, fundamental=300, hpFreq=5500, decay=0.12),
 C('hihat-open','hihat','Open Hat', level=0.65, fundamental=300, hpFreq=5500, decay=0.8),
 V('cymbal','Dark Crash', level=0.7, length=3.0, brightness=900, pitch=0.95),
 V('clap','Slap', level=0.75, centerFreq=1400, bursts=2, spacing=0.02, tailLength=0.4, tailDecay=4, tailMix=0.4),
 V('cowbell','Woodblock', level=0.7, freq1=540, ratio=1.4, q=4, decay=0.5),
 V('tom','Mid Tom', level=0.85, startFreq=250, endFreq=115, pitchDecay=0.05, decay=0.45, noiseAmt=0.35),
 C('tom-hi','tom','Hi Tom', level=0.85, startFreq=330, endFreq=160, pitchDecay=0.05, decay=0.4, noiseAmt=0.35),
 C('tom-low','tom','Floor Tom', level=0.85, startFreq=180, endFreq=80, pitchDecay=0.05, decay=0.55, noiseAmt=0.35),
 V('ks','Muted String', level=0.7, frequency=196, damping=0.993),
 V('chaos','Brush', level=0.55, centerFreq=1000, q=0.8, decay=0.25, chaosR=3.9),
 V('click1','Click Hi', level=0.8, pitch=1.0),
 V('click2','Click Lo', level=0.8, pitch=0.75),
])

KITS['kit-industrial'] = ('Industrial', 'Heavy drive kick with big sweep, beating detuned snare, trashy low hats, max-chaos noise perc.', [
 V('kick','Slam Kick', level=0.95, startFreq=200, endFreq=40, pitchDecay=0.06, ampDecay=0.5, click=0.7, drive=0.9),
 V('snare','Grind Snare', level=0.9, tone1=160, tone2=210, toneDecay=0.2, noiseFreq=3400, noiseQ=2.5, noiseDecay=0.45),
 V('hihat','Trash Hat', level=0.7, fundamental=260, hpFreq=4000, decay=0.2),
 V('cymbal','Grind Wash', level=0.7, length=2.8, brightness=3000, pitch=0.75),
 V('clap','Machine Clap', level=0.85, centerFreq=1000, bursts=5, spacing=0.03, tailLength=0.5, tailDecay=1.5, tailMix=0.8),
 V('cowbell','Clang', level=0.75, freq1=450, ratio=1.9, q=13, decay=0.8),
 V('tom','Drop Tom', level=0.9, startFreq=400, endFreq=65, pitchDecay=0.08, decay=0.6, noiseAmt=0.5),
 V('ks','Wire', level=0.75, frequency=98, damping=0.985),
 V('chaos','Static Hit', level=0.8, centerFreq=900, q=5.0, decay=0.4, chaosR=4.0),
 V('click1','Click Hi', level=0.8, pitch=1.0),
 V('click2','Click Lo', level=0.8, pitch=0.75),
])

KITS['kit-dub-lofi'] = ('Dub Lo-fi', 'Deep round kick, dark fat snare, muffled hats, long low crash, deep KS bass pluck.', [
 V('kick','Deep Kick', level=0.92, startFreq=70, endFreq=41, pitchDecay=0.05, ampDecay=0.6, click=0.1, drive=0.2),
 V('snare','Fat Snare', level=0.85, tone1=170, tone2=260, toneDecay=0.25, noiseFreq=1200, noiseQ=2.0, noiseDecay=0.35),
 V('hihat','Soft Hat', level=0.65, fundamental=280, hpFreq=4500, decay=0.07),
 C('hihat-open','hihat','Open Hat', level=0.6, fundamental=280, hpFreq=4500, decay=0.6),
 V('cymbal','Low Wash', level=0.6, length=3.2, brightness=500, pitch=0.85),
 V('clap','Room Clap', level=0.8, centerFreq=900, bursts=3, spacing=0.018, tailLength=0.6, tailDecay=5, tailMix=0.65),
 V('cowbell','Dub Bell', level=0.7, freq1=500, ratio=1.33, q=5, decay=0.6),
 V('tom','Dub Tom', level=0.8, startFreq=200, endFreq=85, pitchDecay=0.05, decay=0.5, noiseAmt=0.15),
 V('ks','Bass', level=0.9, frequency=65, damping=0.998),
 V('chaos','Crackle', level=0.5, centerFreq=700, q=1.0, decay=0.3, chaosR=3.85),
 V('click1','Click Hi', level=0.8, pitch=1.0),
 V('click2','Click Lo', level=0.8, pitch=0.75),
])

KITS['kit-latin-perc'] = ('Latin Percussion', 'Surdo kick, timbale snare, shaker hat, two cowbells, conga toms, cabasa on chaos.', [
 V('kick','Surdo', level=0.9, startFreq=110, endFreq=60, pitchDecay=0.03, ampDecay=0.5, click=0.2, drive=0.1),
 V('snare','Timbale', level=0.85, tone1=280, tone2=420, toneDecay=0.12, noiseFreq=3000, noiseQ=1.2, noiseDecay=0.12),
 V('hihat','Shaker', level=0.65, fundamental=450, hpFreq=7500, decay=0.06),
 V('cymbal','Ride Wash', level=0.6, length=2.4, brightness=1800, pitch=1.2),
 V('clap','Palmas', level=0.8, centerFreq=1600, bursts=2, spacing=0.035, tailLength=0.2, tailDecay=4, tailMix=0.3),
 V('cowbell','Campana Hi', level=0.8, freq1=620, ratio=1.35, q=7, decay=0.3),
 C('cowbell-low','cowbell','Campana Lo', level=0.8, freq1=480, ratio=1.35, q=7, decay=0.35),
 V('tom','Conga Hi', level=0.85, startFreq=380, endFreq=190, pitchDecay=0.02, decay=0.25, noiseAmt=0.25),
 C('tom-low','tom','Conga Lo', level=0.85, startFreq=240, endFreq=120, pitchDecay=0.02, decay=0.3, noiseAmt=0.25),
 V('ks','Cuatro Pluck', level=0.7, frequency=330, damping=0.99),
 V('chaos','Cabasa', level=0.6, centerFreq=3500, q=2.5, decay=0.07, chaosR=3.95),
 V('click1','Click Hi', level=0.8, pitch=1.0),
 V('click2','Click Lo', level=0.8, pitch=0.75),
])

KITS['kit-minimal-glitch'] = ('Minimal Glitch', 'Tiny dry hits: thump kick, rim snare, tick hats, pinged cowbell, blip tom, everything short.', [
 V('kick','Thump', level=0.9, startFreq=60, endFreq=45, pitchDecay=0.02, ampDecay=0.12, click=0.3, drive=0.0),
 V('snare','Rim', level=0.8, tone1=350, tone2=500, toneDecay=0.03, noiseFreq=5000, noiseQ=4.0, noiseDecay=0.05),
 V('hihat','Tick Hat', level=0.6, fundamental=500, hpFreq=9000, decay=0.03),
 V('cymbal','Shimmer', level=0.5, length=0.4, brightness=4000, pitch=1.5),
 V('clap','Dry Snap', level=0.75, centerFreq=2400, bursts=2, spacing=0.008, tailLength=0.1, tailDecay=6, tailMix=0.1),
 V('cowbell','Ping', level=0.65, freq1=1000, ratio=1.1, q=15, decay=0.1),
 V('tom','Blip', level=0.75, startFreq=500, endFreq=250, pitchDecay=0.02, decay=0.1, noiseAmt=0.0),
 V('ks','Pluck Tick', level=0.65, frequency=600, damping=0.9),
 V('chaos','Grain', level=0.55, centerFreq=4000, q=6.0, decay=0.05, chaosR=3.7),
 V('click1','Click Hi', level=0.8, pitch=1.5),
 V('click2','Click Lo', level=0.8, pitch=0.75),
])

# validate
errors=[]
for fname,(kname,desc,voices) in KITS.items():
    seen=set()
    for v in voices:
        base = v['clonedFrom'] if v['isClone'] else v['id']
        if v['id'] in seen: errors.append(f"{fname}: duplicate id {v['id']}")
        seen.add(v['id'])
        if base not in SCHEMA: errors.append(f"{fname}: unknown base {base}"); continue
        sch=SCHEMA[base]
        for p,val in v['params'].items():
            if p not in sch: errors.append(f"{fname}/{v['id']}: unknown param {p}")
            else:
                lo,hi=sch[p]
                if not (lo<=val<=hi): errors.append(f"{fname}/{v['id']}: {p}={val} outside [{lo},{hi}]")
        missing=set(sch)-set(v['params'])
        if missing: errors.append(f"{fname}/{v['id']}: missing {missing}")
    # all stock ids present
    stock_present={v['id'] for v in voices if not v['isClone']}
    if stock_present != set(STOCK_KEYS): errors.append(f"{fname}: stock set {stock_present}")

if errors:
    print("ERRORS:"); [print(' ',e) for e in errors]
else:
    os.makedirs('C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/instrument-library', exist_ok=True)
    for fname,(kname,desc,voices) in KITS.items():
        out={'format':'d20-synth-project','version':1,'name':kname,'description':desc,'voices':voices}
        with open(f'C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/instrument-library/{fname}.json','w') as f:
            json.dump(out,f,indent=2)
    print("OK — wrote", len(KITS), "kit files")
