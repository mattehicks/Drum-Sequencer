import sys
p='C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
src=open(p).read()
fails=[]
def rep(old,new,label):
    global src
    if src.count(old)!=1: fails.append(f"{label}: {src.count(old)} matches"); return
    src=src.replace(old,new)

# ---- CSS ----
rep(""".tempo-needle::after{
  /* the arrowhead: points down at the notch under the window's center */
  content:'';
  position:absolute;
  left:50%; bottom:-5px;
  border:4px solid transparent;
  border-top-color:var(--accent-2);
  transform:translateX(-50%);
}""",
""".tempo-needle::after{
  /* the arrowhead: points down at the notch under the window's center */
  content:'';
  position:absolute;
  left:50%; bottom:-5px;
  border:4px solid transparent;
  border-top-color:var(--accent-2);
  transform:translateX(-50%);
}
/* Metronome: black rounded-square button with an LED above it.
   Click cycles: off -> LED blinks the beat -> LED + audible beep -> off. */
.metro-wrap{display:flex;flex-direction:column;align-items:center;gap:3px;}
#metroLed{
  width:8px;height:8px;border-radius:50%;
  background:#1c1c22;
  border:1px solid rgba(255,255,255,0.25);
  transition:background 60ms, box-shadow 60ms;
}
#metroLed.blink{background:var(--accent-2);box-shadow:0 0 8px var(--accent-2);}
#metroLed.blink.accent{background:#ffd166;box-shadow:0 0 12px #ffd166;}
#metroBtn{
  width:30px;height:30px;
  background:#0a0a0e;
  border:1px solid rgba(255,255,255,0.3);
  border-radius:8px;
  cursor:pointer;
  color:rgba(255,255,255,0.55);
  font-size:12px;
  line-height:1;
  padding:0;
}
#metroBtn:hover{border-color:rgba(255,255,255,0.55);}
#metroBtn.visual{border-color:var(--accent);color:var(--accent);}
#metroBtn.audible{border-color:var(--accent-2);color:var(--accent-2);}""",
"css")

# ---- HTML: LED + button to the right of the tempo readout ----
rep("""        <output id="seqTempoOut">112 BPM</output>""",
"""        <output id="seqTempoOut">112 BPM</output>
        <div class="metro-wrap">
          <div id="metroLed"></div>
          <button id="metroBtn" type="button" title="Metronome: off. Click: LED blinks the beat. Click again: adds an audible beep.">&#9654;&#9664;</button>
        </div>""",
"html")

# ---- scheduler hook: beats come from the transport while playing ----
rep("""      triggerRowStep(row, seqMasterStep % n, seqMasterNextTime);
    });
    seqMasterNextTime += seqSecondsPerStep();""",
"""      triggerRowStep(row, seqMasterStep % n, seqMasterNextTime);
    });
    // Metronome rides the same lookahead clock as the voices, so its blink
    // and beep are sample-aligned with the pattern instead of free-running
    // against it. barPos===0 marks the downbeat for the accent.
    seqMetroOnStep(seqMasterStep, seqMasterNextTime, barPos===0);
    seqMasterNextTime += seqSecondsPerStep();""",
"hook")

# ---- metronome module, after the tempo ruler wiring ----
rep("""  else if(e.key==='End'){ e.preventDefault(); tempoSetBpm(TEMPO_MAX); }
});
tempoDialSync();""",
"""  else if(e.key==='End'){ e.preventDefault(); tempoSetBpm(TEMPO_MAX); }
});
tempoDialSync();

/* ---------- metronome ---------- */
// Three states cycled by the button: 0 off, 1 LED-only, 2 LED + beep.
// While the sequencer plays, beats come from the scheduler hook above
// (transport-aligned); while stopped, a drift-corrected timer free-runs at
// the current BPM so the LED still shows the tempo, accenting every 4th.
let metroMode=0, metroTimer=null, metroNextMs=0, metroFreeBeat=0;
const metroBtn=document.getElementById('metroBtn');
const metroLed=document.getElementById('metroLed');

function metroFlash(accent){
  metroLed.classList.add('blink');
  metroLed.classList.toggle('accent', !!accent);
  setTimeout(()=>{ metroLed.classList.remove('blink'); metroLed.classList.remove('accent'); }, 90);
}
function metroBeep(t, accent){
  if(!ctx) return;
  const o=ctx.createOscillator(); o.type='sine';
  o.frequency.value=accent ? 1320 : 880;
  const g=ctx.createGain();
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(accent ? 0.5 : 0.35, t+0.003);
  g.gain.exponentialRampToValueAtTime(0.0001, t+0.05);
  o.connect(g); g.connect(master);
  o.start(t); o.stop(t+0.08);
}
function seqMetroOnStep(step, t, barStart){
  if(metroMode===0 || !ctx) return;
  const div=seq.stepDivision||4;
  if(step % div !== 0) return; // only quarter-note beats, whatever the grid resolution
  const delay=Math.max(0, (t-ctx.currentTime)*1000);
  setTimeout(()=> metroFlash(barStart), delay);
  if(metroMode===2) metroBeep(t, barStart);
}
function metroFreeTick(){
  if(metroMode===0){ metroTimer=null; return; }
  if(!seq.playing){
    const accent=(metroFreeBeat % 4)===0;
    metroFlash(accent);
    if(metroMode===2 && ctx && ctx.state==='running') metroBeep(ctx.currentTime, accent);
    metroFreeBeat++;
  }
  // Drift-corrected: each tick is scheduled from an absolute target, so a
  // slow timer callback shortens the next wait instead of accumulating.
  metroNextMs += 60000/seq.bpm;
  metroTimer=setTimeout(metroFreeTick, Math.max(0, metroNextMs-performance.now()));
}
function metroStartFreeRun(){
  if(metroTimer) clearTimeout(metroTimer);
  metroFreeBeat=0;
  metroNextMs=performance.now();
  metroFreeTick();
}
metroBtn.addEventListener('click', ()=>{
  metroMode=(metroMode+1)%3;
  metroBtn.classList.toggle('visual', metroMode===1);
  metroBtn.classList.toggle('audible', metroMode===2);
  metroBtn.title=metroMode===0
    ? 'Metronome: off. Click: LED blinks the beat. Click again: adds an audible beep.'
    : (metroMode===1
      ? 'Metronome: LED only, blinking the beat (downbeat accented). Click for LED + beep.'
      : 'Metronome: LED + beep on every beat. Click to turn off.');
  if(metroMode===2) labEnsureAudioRunning(); // beeps need the live context
  if(metroMode>0) metroStartFreeRun();
  else if(metroTimer){ clearTimeout(metroTimer); metroTimer=null; }
});""",
"module")

if fails:
    print("FAILURES:", fails); sys.exit(1)
open(p,'w').write(src)
print("OK", len(src))
