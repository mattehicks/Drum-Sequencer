import sys
p='C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
src=open(p).read()
fails=[]
def rep(old,new,label,count=1):
    global src
    if src.count(old)!=count: fails.append(f"{label}: {src.count(old)} matches (want {count})"); return
    src=src.replace(old,new)

# ---- CSS ----
rep(""".seq-tempo input{width:120px;}""",
"""/* Tempo ruler: the old range slider rebuilt as a notched ruler read through
   a round "planchette" window -- a ring with a needle whose arrowhead points
   at the exact BPM notch, so single-BPM moves are visible and deliberate.
   The native range input stays in the DOM (hidden) as the single source of
   truth: the ruler writes to it and fires 'input', so tap tempo, project
   load, and the BPM readout all keep working against the same element. */
.seq-tempo input.tempo-native{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;}
.tempo-ruler{
  position:relative;
  width:230px; height:36px;
  cursor:ew-resize;
  touch-action:none;
  user-select:none;
  outline:none;
}
.tempo-ruler:focus-visible{box-shadow:0 0 0 1px var(--accent);border-radius:6px;}
.tempo-track{position:absolute;left:15px;right:15px;top:0;bottom:0;}
.tempo-track .tt{position:absolute;bottom:4px;width:1px;background:rgba(255,255,255,0.22);height:7px;transform:translateX(-0.5px);pointer-events:none;}
.tempo-track .tt.med{height:11px;background:rgba(255,255,255,0.34);}
.tempo-track .tt.maj{height:15px;background:rgba(255,255,255,0.55);}
.tempo-track .tt-label{
  position:absolute;bottom:21px;
  transform:translateX(-50%);
  font-size:8.5px;color:var(--subtext);
  pointer-events:none;
  font-family:var(--mono);
}
.tempo-planchette{
  position:absolute;
  top:50%; left:0;
  width:30px; height:30px;
  margin-top:-15px;
  transform:translateX(-50%);
  border:2px solid var(--accent-2);
  border-radius:50%;
  background:radial-gradient(circle, rgba(16,16,22,0) 40%, rgba(16,16,22,0.55) 100%);
  box-shadow:0 0 10px rgba(var(--accent-2-rgb),0.35), inset 0 0 6px rgba(0,0,0,0.4);
  pointer-events:none;
}
.tempo-needle{
  position:absolute;
  left:50%; top:4px; bottom:9px;
  width:1px; margin-left:-0.5px;
  background:var(--accent-2);
}
.tempo-needle::after{
  /* the arrowhead: points down at the notch under the window's center */
  content:'';
  position:absolute;
  left:50%; bottom:-5px;
  border:4px solid transparent;
  border-top-color:var(--accent-2);
  transform:translateX(-50%);
}""",
"css")

# ---- HTML ----
rep("""        <input type="range" id="seqTempo" min="60" max="200" step="1" value="112">
        <output id="seqTempoOut">112 BPM</output>""",
"""        <input type="range" id="seqTempo" min="60" max="200" step="1" value="112" class="tempo-native" aria-hidden="true" tabindex="-1">
        <div class="tempo-ruler" id="tempoRuler" tabindex="0" role="slider" aria-label="Tempo" aria-valuemin="60" aria-valuemax="200" aria-valuenow="112" title="Drag the window along the ruler. Scroll wheel or arrow keys nudge 1 BPM (Shift: 10). Click any notch to jump.">
          <div class="tempo-track" id="tempoTrack"></div>
          <div class="tempo-planchette"><div class="tempo-needle"></div></div>
        </div>
        <output id="seqTempoOut">112 BPM</output>""",
"html")

# ---- JS: build + wire the ruler right after the native input's listener ----
rep("""seqTempoInput.addEventListener('input', ()=>{
  seq.bpm=parseFloat(seqTempoInput.value);
  seqTempoOut.textContent=seq.bpm+' BPM';
});""",
"""seqTempoInput.addEventListener('input', ()=>{
  seq.bpm=parseFloat(seqTempoInput.value);
  seqTempoOut.textContent=seq.bpm+' BPM';
});

/* ---------- tempo ruler (notched scale + planchette window) ---------- */
const tempoRulerEl=document.getElementById('tempoRuler');
const tempoTrackEl=document.getElementById('tempoTrack');
const tempoPlanchetteEl=tempoRulerEl.querySelector('.tempo-planchette');
const TEMPO_MIN=parseFloat(seqTempoInput.min), TEMPO_MAX=parseFloat(seqTempoInput.max);

// One notch per BPM; taller every 5, tallest with a label every 20. All
// positioned in % of the padded track so the ruler stays correct at any
// rendered width without a resize handler.
(function tempoBuildTicks(){
  const span=TEMPO_MAX-TEMPO_MIN;
  const frag=document.createDocumentFragment();
  for(let b=TEMPO_MIN;b<=TEMPO_MAX;b++){
    const t=document.createElement('div');
    t.className='tt'+(b%20===0?' maj':(b%5===0?' med':''));
    t.style.left=((b-TEMPO_MIN)/span*100)+'%';
    frag.appendChild(t);
    if(b%20===0){
      const l=document.createElement('div');
      l.className='tt-label';
      l.textContent=b;
      l.style.left=((b-TEMPO_MIN)/span*100)+'%';
      frag.appendChild(l);
    }
  }
  tempoTrackEl.appendChild(frag);
})();

function tempoDialSync(){
  const v=parseFloat(seqTempoInput.value);
  const frac=(v-TEMPO_MIN)/(TEMPO_MAX-TEMPO_MIN);
  // The planchette lives in ruler coordinates; the track is inset 15px each
  // side (half the window) so the ring never clips at the ends.
  tempoPlanchetteEl.style.left='calc(15px + '+(frac*100)+'% - '+(frac*30)+'px)';
  tempoRulerEl.setAttribute('aria-valuenow', String(v));
}

function tempoSetBpm(bpm, announce){
  bpm=Math.round(Math.min(TEMPO_MAX, Math.max(TEMPO_MIN, bpm)));
  if(parseFloat(seqTempoInput.value)!==bpm){
    seqTempoInput.value=bpm;
    seqTempoInput.dispatchEvent(new Event('input')); // one source of truth: the native input's own handler updates seq.bpm + readout
  }
  tempoDialSync();
}

function tempoBpmFromEvent(e){
  const r=tempoTrackEl.getBoundingClientRect();
  const frac=Math.min(1, Math.max(0, (e.clientX-r.left)/r.width));
  return TEMPO_MIN+frac*(TEMPO_MAX-TEMPO_MIN);
}

let tempoDragging=false;
tempoRulerEl.addEventListener('pointerdown', (e)=>{
  e.preventDefault();
  tempoRulerEl.focus();
  tempoDragging=true;
  try{ tempoRulerEl.setPointerCapture(e.pointerId); }catch(_){ }
  tempoSetBpm(tempoBpmFromEvent(e));
});
tempoRulerEl.addEventListener('pointermove', (e)=>{ if(tempoDragging) tempoSetBpm(tempoBpmFromEvent(e)); });
const tempoDragEnd=()=>{ tempoDragging=false; };
tempoRulerEl.addEventListener('pointerup', tempoDragEnd);
tempoRulerEl.addEventListener('pointercancel', tempoDragEnd);
// The precision paths: wheel and arrows move exactly one notch (Shift: ten).
tempoRulerEl.addEventListener('wheel', (e)=>{
  e.preventDefault();
  tempoSetBpm(parseFloat(seqTempoInput.value)+(e.deltaY<0?1:-1)*(e.shiftKey?10:1));
}, {passive:false});
tempoRulerEl.addEventListener('keydown', (e)=>{
  const step=e.shiftKey?10:1;
  if(e.key==='ArrowRight'||e.key==='ArrowUp'){ e.preventDefault(); tempoSetBpm(parseFloat(seqTempoInput.value)+step); }
  else if(e.key==='ArrowLeft'||e.key==='ArrowDown'){ e.preventDefault(); tempoSetBpm(parseFloat(seqTempoInput.value)-step); }
  else if(e.key==='Home'){ e.preventDefault(); tempoSetBpm(TEMPO_MIN); }
  else if(e.key==='End'){ e.preventDefault(); tempoSetBpm(TEMPO_MAX); }
});
tempoDialSync();""",
"js")

# ---- keep the planchette in step with the three external setters ----
rep("""  seq.bpm=bpm;
  seqTempoInput.value=bpm;
  seqTempoOut.textContent=bpm+' BPM';""",
"""  seq.bpm=bpm;
  seqTempoInput.value=bpm;
  seqTempoOut.textContent=bpm+' BPM';
  tempoDialSync();""",
"tap sync")
rep("""  seqTempoInput.value=seq.bpm;""",
"""  seqTempoInput.value=seq.bpm;
  tempoDialSync();""",
"load/reset sync", count=2)

if fails:
    print("FAILURES:", fails); sys.exit(1)
# count==2 rep uses replace-all semantics via str.replace default; confirm both got the sync
assert src.count("seqTempoInput.value=seq.bpm;\n  tempoDialSync();")==2
open(p,'w').write(src)
print("OK", len(src))
