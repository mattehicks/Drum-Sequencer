import sys
p='C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
src=open(p).read()
fails=[]
def rep(old,new,label):
    global src
    if src.count(old)!=1: fails.append(f"{label}: {src.count(old)} matches"); return
    src=src.replace(old,new)

# ---- CSS ----
rep(""".pk-white.pk-down{fill:#ffe9a8;}
.pk-black.pk-down{fill:#4a4a52;}""",
""".pk-white.pk-down{fill:#ffe9a8;}
.pk-black.pk-down{fill:#4a4a52;}
/* ---- Solo Pad: XY performance surface. Y = pitch, X = volume. ---- */
.solo-wrap{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-start;}
#soloPad{
  position:relative;
  width:min(560px, 100%);
  height:260px;
  background:linear-gradient(to right, rgba(255,255,255,0.02), rgba(255,255,255,0.07)),
             linear-gradient(to top, rgba(122,208,255,0.10), rgba(233,196,106,0.10));
  border:1px solid var(--border,rgba(255,255,255,0.2));
  border-radius:12px;
  touch-action:none;      /* the pad owns every touch gesture on it */
  user-select:none;
  cursor:crosshair;
  overflow:hidden;
}
#soloPad.live{border-color:var(--accent,#7ad0ff);box-shadow:0 0 18px rgba(122,208,255,0.25) inset;}
#soloPad .solo-line{position:absolute;left:0;right:0;height:1px;background:rgba(255,255,255,0.07);pointer-events:none;}
#soloPad .solo-line.octave{background:rgba(255,255,255,0.18);}
#soloDot{
  position:absolute;
  width:14px;height:14px;
  border-radius:50%;
  background:var(--accent,#7ad0ff);
  box-shadow:0 0 12px var(--accent,#7ad0ff);
  transform:translate(-50%,-50%);
  pointer-events:none;
  opacity:0.45;
}
#soloPad.live #soloDot{opacity:1;}
#soloReadout{
  position:absolute;top:8px;left:10px;
  font-size:12px;color:#cfcbc6;
  font-variant-numeric:tabular-nums;
  pointer-events:none;
}
.solo-ctl{min-width:200px;display:flex;flex-direction:column;gap:6px;}
.solo-ctl .lab-row{grid-template-columns:64px 1fr 46px;}
.solo-hint{flex-basis:100%;color:#8f8b86;font-size:11.5px;line-height:1.5;max-width:70ch;}""",
"css")

# ---- HTML: section between Sound Lab and footer ----
rep("""  <footer class="notes">""",
"""  <section class="rack-panel" id="soloSection">
    <div class="rack-head">
      <button type="button" class="analysis-toggle" id="soloToggle" aria-expanded="false" aria-controls="soloBody">
        <span class="chevron">&#9656;</span> Solo Pad
      </button>
    </div>
    <section id="soloBody" hidden>
      <p class="solo-hint">A live lead over the sequencer. <b>Up/down = pitch, left/right = volume.</b> Two ways to gate the tone: press and drag on the pad (works on touch), or hold <b>Shift</b> while the cursor is over the pad to play theremin-style without clicking. Needs the engine running -- it starts itself on first use.</p>
      <div class="solo-wrap">
        <div id="soloPad">
          <div id="soloDot"></div>
          <div id="soloReadout">&mdash;</div>
        </div>
        <div class="solo-ctl">
          <div class="lab-row"><label for="soloWave">Wave</label><select id="soloWave"><option value="sawtooth" selected>Saw</option><option value="square">Square</option><option value="triangle">Triangle</option><option value="sine">Sine</option></select></div>
          <div class="lab-row"><label for="soloBase">Base</label><input type="range" id="soloBase" min="55" max="440" step="1" value="110"><output>110 Hz</output></div>
          <div class="lab-row"><label for="soloOct">Range</label><input type="range" id="soloOct" min="1" max="4" step="1" value="3"><output>3 oct</output></div>
          <div class="lab-row"><label for="soloGlide">Glide</label><input type="range" id="soloGlide" min="0" max="0.3" step="0.005" value="0.03"><output>30 ms</output></div>
          <div class="lab-row"><label for="soloSnap">Snap</label><input type="checkbox" id="soloSnap"><output></output></div>
        </div>
      </div>
    </section>
  </section>

  <footer class="notes">""",
"html")

# ---- JS ----
rep("""document.getElementById('seqTheory').textContent=""",
"""/* ---------- Solo Pad: realtime XY lead synth ---------- */
// One continuously-running oscillator whose frequency and gain chase the
// pointer with short time constants (setTargetAtTime), which is what makes
// it feel like an instrument instead of a stepped controller: pitch slides,
// volume swells, and the gate is just an amplitude envelope -- the osc never
// stops/starts mid-performance, so there are no clicks and no note-on lag.
const soloCfg={wave:'sawtooth', base:110, octaves:3, glide:0.03, snap:false};
let soloOsc=null, soloGainNode=null;
let soloShiftHeld=false, soloPointerDown=false, soloHover=false;
let soloPos={x:0.75, y:0.5}; // normalized, y measured from the top

const soloPadEl=document.getElementById('soloPad');
const soloDotEl=document.getElementById('soloDot');
const soloReadoutEl=document.getElementById('soloReadout');

function soloFreq(){
  let semis=(1-soloPos.y)*soloCfg.octaves*12;
  if(soloCfg.snap) semis=Math.round(semis);
  return soloCfg.base*Math.pow(2, semis/12);
}
function soloVol(){
  // Perceptual taper: linear finger travel maps to a curve so the quiet
  // half of the pad isn't wasted on near-silence.
  return Math.pow(soloPos.x, 1.6);
}
function soloGated(){ return soloPointerDown || (soloShiftHeld && soloHover); }

function soloDrawLines(){
  // One faint line per semitone, brighter per octave, so Snap mode has
  // visible targets. Rebuilt when the range changes.
  soloPadEl.querySelectorAll('.solo-line').forEach(el=>el.remove());
  const total=soloCfg.octaves*12;
  for(let s=0;s<=total;s++){
    const div=document.createElement('div');
    div.className='solo-line'+(s%12===0?' octave':'');
    div.style.top=(100*(1-s/total))+'%';
    soloPadEl.appendChild(div);
  }
}

function soloUpdateUI(){
  soloDotEl.style.left=(soloPos.x*100)+'%';
  soloDotEl.style.top=(soloPos.y*100)+'%';
  const f=soloFreq();
  soloReadoutEl.textContent=freqToNoteName(f)+' \\u00b7 '+f.toFixed(1)+' Hz \\u00b7 vol '+Math.round(soloVol()*100)+'%';
  soloPadEl.classList.toggle('live', soloGated());
}

function soloEnsureVoice(){
  if(soloOsc || !ctx) return;
  soloOsc=ctx.createOscillator();
  soloOsc.type=soloCfg.wave;
  soloOsc.frequency.value=soloFreq();
  soloGainNode=ctx.createGain();
  soloGainNode.gain.value=0;
  soloOsc.connect(soloGainNode);
  soloGainNode.connect(master);
  soloOsc.start();
}

function soloApply(){
  if(!ctx) return;
  soloEnsureVoice();
  const now=ctx.currentTime;
  soloOsc.type=soloCfg.wave;
  soloOsc.frequency.setTargetAtTime(soloFreq(), now, Math.max(0.001, soloCfg.glide));
  const target=soloGated() ? soloVol() : 0;
  // Fast-but-not-instant gain chase: ~10ms feels immediate and never clicks.
  soloGainNode.gain.setTargetAtTime(target, now, soloGated() ? 0.01 : 0.03);
}

async function soloGateChanged(){
  soloUpdateUI(); // reflect the gate immediately, even while audio spins up
  if(soloGated()){
    if(await labEnsureAudioRunning()) soloApply();
  }else if(soloOsc){
    soloApply(); // ramps to silence; the osc keeps running for the next gate
  }
}

function soloPointerToPos(e){
  const r=soloPadEl.getBoundingClientRect();
  soloPos.x=Math.min(1, Math.max(0, (e.clientX-r.left)/r.width));
  soloPos.y=Math.min(1, Math.max(0, (e.clientY-r.top)/r.height));
}

soloPadEl.addEventListener('pointerenter', ()=>{ soloHover=true; soloGateChanged(); });
soloPadEl.addEventListener('pointerleave', ()=>{ soloHover=false; if(!soloPointerDown) soloGateChanged(); });
soloPadEl.addEventListener('pointermove', (e)=>{
  soloPointerToPos(e);
  if(soloGated()) soloApply();
  soloUpdateUI();
});
soloPadEl.addEventListener('pointerdown', (e)=>{
  e.preventDefault();
  soloPointerToPos(e);
  soloPointerDown=true;
  // Capture keeps the glide alive when the finger wanders off the pad
  // mid-phrase; some synthetic/headless pointers can't be captured, and
  // that must never kill the gate itself.
  try{ soloPadEl.setPointerCapture(e.pointerId); }catch(_){}
  soloGateChanged();
});
const soloRelease=(e)=>{ if(soloPointerDown){ soloPointerDown=false; soloGateChanged(); } };
soloPadEl.addEventListener('pointerup', soloRelease);
soloPadEl.addEventListener('pointercancel', soloRelease);

// Shift gates only while hovering the pad, so it never collides with
// Shift+drag velocity editing over in the sequencer grid.
document.addEventListener('keydown', (e)=>{
  if(e.key==='Shift' && !soloShiftHeld){ soloShiftHeld=true; if(soloHover) soloGateChanged(); }
});
document.addEventListener('keyup', (e)=>{
  if(e.key==='Shift'){ soloShiftHeld=false; soloGateChanged(); }
});
// A tab-switch mid-note would otherwise leave the tone droning.
window.addEventListener('blur', ()=>{ soloShiftHeld=false; soloPointerDown=false; soloGateChanged(); });

document.getElementById('soloWave').addEventListener('change', (e)=>{ soloCfg.wave=e.target.value; soloApply(); });
[['soloBase','base', v=>v+' Hz'], ['soloOct','octaves', v=>v+' oct'], ['soloGlide','glide', v=>Math.round(v*1000)+' ms']].forEach(([id,key,fmt])=>{
  const el=document.getElementById(id);
  const out=el.closest('.lab-row').querySelector('output');
  el.addEventListener('input', ()=>{
    soloCfg[key]=parseFloat(el.value);
    out.textContent=fmt(parseFloat(el.value));
    if(key==='octaves') soloDrawLines();
    soloApply(); soloUpdateUI();
  });
});
document.getElementById('soloSnap').addEventListener('change', (e)=>{ soloCfg.snap=e.target.checked; soloApply(); soloUpdateUI(); });

const soloToggle=document.getElementById('soloToggle');
const soloBody=document.getElementById('soloBody');
let soloExpanded=false;
function setSoloExpanded(x){
  soloExpanded=x;
  soloBody.hidden=!x;
  soloToggle.setAttribute('aria-expanded', String(x));
  soloToggle.querySelector('.chevron').innerHTML=x ? '&#9662;' : '&#9656;';
}
soloToggle.addEventListener('click', ()=> setSoloExpanded(!soloExpanded));
setSoloExpanded(false);
soloDrawLines();
soloUpdateUI();

document.getElementById('seqTheory').textContent=""",
"js")

if fails:
    print("FAILURES:", fails); sys.exit(1)
open(p,'w').write(src)
print("OK", len(src))
