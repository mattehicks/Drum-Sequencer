import sys
p='C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
src=open(p).read()
fails=[]
def rep(old,new,label):
    global src
    if src.count(old)!=1: fails.append(f"{label}: {src.count(old)} matches"); return
    src=src.replace(old,new)

# ---- CSS: after .rack-head rule ----
rep(""".rack-head{margin-bottom:14px;}""",
""".rack-head{margin-bottom:14px;}
/* ---- Sound Lab: the organic/layered sound designer. Deliberately its own
   container, fully separate from the basic sequencer + mono-chain voices
   above -- the simple drum machine stays simple, and everything "produced"
   (layers, space, glue) lives and grows in here. Interface scaffold first;
   the render engine plugs into soundLab state later. ---- */
.lab-intro{color:var(--muted,#8f8b86);font-size:12.5px;margin:0 0 14px;max-width:70ch;line-height:1.5;}
.lab-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;align-items:start;}
.lab-group{background:rgba(255,255,255,0.03);border:1px solid var(--border,rgba(255,255,255,0.14));border-radius:10px;padding:12px;}
.lab-group h4{margin:0 0 4px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:var(--accent-2,#e9c46a);}
.lab-group .lab-sub{margin:0 0 10px;font-size:11px;color:var(--muted,#8f8b86);line-height:1.4;}
.lab-strip{border-top:1px dashed rgba(255,255,255,0.12);padding-top:8px;margin-top:8px;}
.lab-strip:first-of-type{border-top:none;padding-top:0;margin-top:0;}
.lab-strip-head{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:12px;font-weight:700;}
.lab-strip-head input[type=checkbox]{accent-color:var(--accent,#7ad0ff);}
.lab-row{display:grid;grid-template-columns:74px 1fr 46px;align-items:center;gap:8px;margin:4px 0;font-size:11.5px;}
.lab-row label{color:#cfcbc6;}
.lab-row output{text-align:right;color:#eee;font-variant-numeric:tabular-nums;}
.lab-row select{background:var(--panel-2,#1c1c24);color:#eee;border:1px solid var(--border,rgba(255,255,255,0.2));border-radius:6px;padding:3px 6px;font-size:11.5px;grid-column:2 / span 2;}
.lab-row input[type=range]{width:100%;}
.lab-actions{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:14px;}
.lab-actions input[type=text]{background:var(--panel-2,#1c1c24);color:#eee;border:1px solid var(--border,rgba(255,255,255,0.2));border-radius:6px;padding:6px 10px;font-size:13px;min-width:180px;}
.lab-btn{background:rgba(255,255,255,0.08);border:1px solid var(--border,rgba(255,255,255,0.25));color:#eee;border-radius:8px;padding:7px 14px;cursor:pointer;font-size:13px;}
.lab-btn.primary{border-color:var(--accent,#7ad0ff);color:var(--accent,#7ad0ff);}
.lab-btn:disabled{opacity:0.45;cursor:not-allowed;}""",
"css")

# ---- HTML: new section between patterns and footer ----
rep("""  <footer class="notes">""",
"""  <section class="rack-panel" id="soundLabSection">
    <div class="rack-head">
      <button type="button" class="analysis-toggle" id="soundLabToggle" aria-expanded="false" aria-controls="soundLab">
        <span class="chevron">&#9656;</span> Sound Lab
      </button>
    </div>
    <section class="lab" id="soundLab" hidden>
      <p class="lab-intro">A separate space from the drum machine above. The sequencer's voices stay simple single-chain synths on purpose; the Lab is for building bigger, produced, organic-feeling sounds -- layered hits with real length, room, and glue -- rendered offline and added to the rack as playable instruments. This is the interface scaffold; the render engine is the next build.</p>
      <div class="lab-grid">

        <div class="lab-group" id="labLayers">
          <h4>Layers</h4>
          <p class="lab-sub">Big sounds are stacked, not synthesized in one pass: a sub for weight, a body for tone, a transient for attack, air for texture. Each layer has its own envelope.</p>
          <div class="lab-strip" data-layer="sub">
            <div class="lab-strip-head"><input type="checkbox" id="labSubOn" checked> Sub &mdash; sine weight</div>
            <div class="lab-row"><label for="labSubLevel">Level</label><input type="range" id="labSubLevel" min="0" max="1" step="0.01" value="0.9"><output>0.90</output></div>
            <div class="lab-row"><label for="labSubFreq">Freq</label><input type="range" id="labSubFreq" min="30" max="120" step="1" value="48"><output>48 Hz</output></div>
            <div class="lab-row"><label for="labSubDecay">Decay</label><input type="range" id="labSubDecay" min="0.2" max="4" step="0.05" value="1.4"><output>1.40 s</output></div>
          </div>
          <div class="lab-strip" data-layer="body">
            <div class="lab-strip-head"><input type="checkbox" id="labBodyOn" checked> Body &mdash; tonal core</div>
            <div class="lab-row"><label for="labBodyWave">Wave</label><select id="labBodyWave"><option value="sine">Sine</option><option value="triangle" selected>Triangle</option><option value="square">Square</option><option value="sawtooth">Saw</option></select></div>
            <div class="lab-row"><label for="labBodyLevel">Level</label><input type="range" id="labBodyLevel" min="0" max="1" step="0.01" value="0.6"><output>0.60</output></div>
            <div class="lab-row"><label for="labBodyFreq">Freq</label><input type="range" id="labBodyFreq" min="60" max="800" step="1" value="160"><output>160 Hz</output></div>
            <div class="lab-row"><label for="labBodySpread">Spread</label><input type="range" id="labBodySpread" min="0" max="100" step="1" value="12"><output>12</output></div>
            <div class="lab-row"><label for="labBodyDecay">Decay</label><input type="range" id="labBodyDecay" min="0.05" max="3" step="0.05" value="0.6"><output>0.60 s</output></div>
          </div>
          <div class="lab-strip" data-layer="transient">
            <div class="lab-strip-head"><input type="checkbox" id="labTransOn" checked> Transient &mdash; the attack</div>
            <div class="lab-row"><label for="labTransType">Type</label><select id="labTransType"><option value="click" selected>Click</option><option value="knock">Knock</option><option value="snap">Snap</option></select></div>
            <div class="lab-row"><label for="labTransLevel">Level</label><input type="range" id="labTransLevel" min="0" max="1" step="0.01" value="0.7"><output>0.70</output></div>
            <div class="lab-row"><label for="labTransDecay">Decay</label><input type="range" id="labTransDecay" min="0.005" max="0.08" step="0.001" value="0.02"><output>20 ms</output></div>
          </div>
          <div class="lab-strip" data-layer="air">
            <div class="lab-strip-head"><input type="checkbox" id="labAirOn"> Air &mdash; noise texture</div>
            <div class="lab-row"><label for="labAirLevel">Level</label><input type="range" id="labAirLevel" min="0" max="1" step="0.01" value="0.3"><output>0.30</output></div>
            <div class="lab-row"><label for="labAirColor">Color</label><input type="range" id="labAirColor" min="200" max="10000" step="10" value="3000"><output>3000 Hz</output></div>
            <div class="lab-row"><label for="labAirDecay">Decay</label><input type="range" id="labAirDecay" min="0.05" max="4" step="0.05" value="1.0"><output>1.00 s</output></div>
          </div>
        </div>

        <div class="lab-group" id="labMovement">
          <h4>Movement</h4>
          <p class="lab-sub">Pitch motion is what separates a thwomp (deep, slow drop) from a boom (barely any) and a riser (upward). Applies to Sub + Body together.</p>
          <div class="lab-row"><label for="labSweepDepth">Sweep</label><input type="range" id="labSweepDepth" min="-48" max="48" step="1" value="-12"><output>-12 st</output></div>
          <div class="lab-row"><label for="labSweepTime">Sweep Time</label><input type="range" id="labSweepTime" min="0.01" max="1.5" step="0.01" value="0.25"><output>0.25 s</output></div>
        </div>

        <div class="lab-group" id="labSpace">
          <h4>Space</h4>
          <p class="lab-sub">A boom is mostly the room it happens in: convolution reverb rendered into the sound itself, not a live effect.</p>
          <div class="lab-row"><label for="labRoomSize">Room Size</label><input type="range" id="labRoomSize" min="0" max="1" step="0.01" value="0.5"><output>0.50</output></div>
          <div class="lab-row"><label for="labTail">Tail</label><input type="range" id="labTail" min="0" max="4" step="0.05" value="1.2"><output>1.20 s</output></div>
          <div class="lab-row"><label for="labWet">Wet Mix</label><input type="range" id="labWet" min="0" max="1" step="0.01" value="0.35"><output>0.35</output></div>
        </div>

        <div class="lab-group" id="labGlue">
          <h4>Glue</h4>
          <p class="lab-sub">Saturation and compression squash the layers into one fat event -- the difference between "computed" and "produced."</p>
          <div class="lab-row"><label for="labDrive">Drive</label><input type="range" id="labDrive" min="0" max="1" step="0.01" value="0.3"><output>0.30</output></div>
          <div class="lab-row"><label for="labComp">Compress</label><input type="range" id="labComp" min="0" max="1" step="0.01" value="0.5"><output>0.50</output></div>
          <div class="lab-row"><label for="labLength">Length</label><input type="range" id="labLength" min="0.2" max="5" step="0.05" value="2.0"><output>2.00 s</output></div>
          <div class="lab-row"><label for="labOut">Output</label><input type="range" id="labOut" min="0" max="1" step="0.01" value="0.85"><output>0.85</output></div>
        </div>

      </div>
      <div class="lab-actions">
        <label style="font-size:12px;color:#cfcbc6;">Start from
          <select id="labPreset">
            <option value="">&mdash;</option>
            <option value="boom808">808 Boom</option>
            <option value="subdrop">EDM Sub Drop</option>
            <option value="thwomp">Thwomp</option>
            <option value="trapsnare">Trap Snare + Tail</option>
            <option value="riser">Riser Hit</option>
            <option value="gated">Gated Reverb Snare</option>
          </select>
        </label>
        <input type="text" id="labName" placeholder="Instrument name" value="Lab Sound 1">
        <button type="button" class="lab-btn primary" id="labPreviewBtn">&#9654; Preview</button>
        <button type="button" class="lab-btn" id="labAddBtn">Add to Rack</button>
      </div>
    </section>
  </section>

  <footer class="notes">""",
"html")

# ---- JS: state + wiring, inserted before init ----
rep("""/* ---------- init ---------- */""",
"""/* ---------- Sound Lab (interface scaffold) ---------- */
// Isolated from the sequencer's voices on purpose: the drum machine above
// stays a simple mono-chain synth rack, and the Lab is where the layered,
// rendered, "produced" sounds will live. This block is the UI + state only.
// The next build adds labRender(): an OfflineAudioContext pass (same baking
// trick the cymbal already uses) that turns soundLab's state into a buffer,
// previews it, and registers it as a rack voice.
const soundLab={
  layers:{
    sub:{on:true, level:0.9, freq:48, decay:1.4},
    body:{on:true, wave:'triangle', level:0.6, freq:160, spread:12, decay:0.6},
    transient:{on:true, type:'click', level:0.7, decay:0.02},
    air:{on:false, level:0.3, color:3000, decay:1.0}
  },
  movement:{sweepDepth:-12, sweepTime:0.25},
  space:{roomSize:0.5, tail:1.2, wet:0.35},
  glue:{drive:0.3, comp:0.5, length:2.0, out:0.85},
  name:'Lab Sound 1'
};

// Every control maps to one path into soundLab. fmt renders the readout.
const LAB_BINDINGS=[
  ['labSubOn','layers.sub.on'], ['labSubLevel','layers.sub.level'], ['labSubFreq','layers.sub.freq', v=>v+' Hz'], ['labSubDecay','layers.sub.decay', v=>v.toFixed(2)+' s'],
  ['labBodyOn','layers.body.on'], ['labBodyWave','layers.body.wave'], ['labBodyLevel','layers.body.level'], ['labBodyFreq','layers.body.freq', v=>v+' Hz'], ['labBodySpread','layers.body.spread', v=>String(v)], ['labBodyDecay','layers.body.decay', v=>v.toFixed(2)+' s'],
  ['labTransOn','layers.transient.on'], ['labTransType','layers.transient.type'], ['labTransLevel','layers.transient.level'], ['labTransDecay','layers.transient.decay', v=>Math.round(v*1000)+' ms'],
  ['labAirOn','layers.air.on'], ['labAirLevel','layers.air.level'], ['labAirColor','layers.air.color', v=>v+' Hz'], ['labAirDecay','layers.air.decay', v=>v.toFixed(2)+' s'],
  ['labSweepDepth','movement.sweepDepth', v=>(v>0?'+':'')+v+' st'], ['labSweepTime','movement.sweepTime', v=>v.toFixed(2)+' s'],
  ['labRoomSize','space.roomSize'], ['labTail','space.tail', v=>v.toFixed(2)+' s'], ['labWet','space.wet'],
  ['labDrive','glue.drive'], ['labComp','glue.comp'], ['labLength','glue.length', v=>v.toFixed(2)+' s'], ['labOut','glue.out'],
];

function labSetPath(path, value){
  const parts=path.split('.');
  let o=soundLab;
  for(let i=0;i<parts.length-1;i++) o=o[parts[i]];
  o[parts[parts.length-1]]=value;
}

LAB_BINDINGS.forEach(([id, path, fmt])=>{
  const el=document.getElementById(id);
  if(!el) return;
  const out=el.closest('.lab-row') ? el.closest('.lab-row').querySelector('output') : null;
  const apply=()=>{
    let v;
    if(el.type==='checkbox') v=el.checked;
    else if(el.tagName==='SELECT') v=el.value;
    else v=parseFloat(el.value);
    labSetPath(path, v);
    if(out){
      if(fmt) out.textContent=fmt(v);
      else out.textContent=(typeof v==='number') ? v.toFixed(2) : String(v);
    }
  };
  el.addEventListener('input', apply);
  el.addEventListener('change', apply);
  apply(); // sync readouts to initial values
});

document.getElementById('labName').addEventListener('input', (e)=>{ soundLab.name=e.target.value; });

// Presets: each is just a full soundLab state, pushed into the controls so
// every slider lands where the sound needs it -- the "make your own
// sandwich" panel pre-filled to a known good order.
const LAB_PRESETS={
  boom808:{ layers:{sub:{on:true,level:1,freq:44,decay:2.5}, body:{on:true,wave:'sine',level:0.4,freq:88,spread:0,decay:0.8}, transient:{on:true,type:'click',level:0.5,decay:0.012}, air:{on:false,level:0.2,color:2000,decay:0.5}}, movement:{sweepDepth:-7,sweepTime:0.06}, space:{roomSize:0.35,tail:0.8,wet:0.2}, glue:{drive:0.45,comp:0.6,length:3,out:0.9} },
  subdrop:{ layers:{sub:{on:true,level:1,freq:55,decay:4}, body:{on:false,wave:'sine',level:0.3,freq:110,spread:0,decay:1}, transient:{on:false,type:'click',level:0.3,decay:0.01}, air:{on:false,level:0.2,color:1500,decay:1}}, movement:{sweepDepth:-24,sweepTime:1.2}, space:{roomSize:0.2,tail:0.5,wet:0.12}, glue:{drive:0.25,comp:0.5,length:5,out:0.9} },
  thwomp:{ layers:{sub:{on:true,level:0.95,freq:40,decay:1.2}, body:{on:true,wave:'triangle',level:0.7,freq:120,spread:8,decay:0.4}, transient:{on:true,type:'knock',level:0.8,decay:0.03}, air:{on:false,level:0.2,color:1200,decay:0.6}}, movement:{sweepDepth:-19,sweepTime:0.35}, space:{roomSize:0.6,tail:1.4,wet:0.4}, glue:{drive:0.5,comp:0.65,length:2.2,out:0.9} },
  trapsnare:{ layers:{sub:{on:false,level:0.5,freq:60,decay:0.5}, body:{on:true,wave:'triangle',level:0.6,freq:240,spread:25,decay:0.15}, transient:{on:true,type:'snap',level:0.9,decay:0.015}, air:{on:true,level:0.7,color:4500,decay:1.6}}, movement:{sweepDepth:-5,sweepTime:0.05}, space:{roomSize:0.7,tail:1.8,wet:0.5}, glue:{drive:0.35,comp:0.55,length:2.4,out:0.85} },
  riser:{ layers:{sub:{on:true,level:0.6,freq:70,decay:2}, body:{on:true,wave:'sawtooth',level:0.7,freq:200,spread:40,decay:2}, transient:{on:false,type:'click',level:0.3,decay:0.01}, air:{on:true,level:0.6,color:6000,decay:2.5}}, movement:{sweepDepth:24,sweepTime:1.5}, space:{roomSize:0.8,tail:2.5,wet:0.55}, glue:{drive:0.3,comp:0.5,length:4,out:0.85} },
  gated:{ layers:{sub:{on:false,level:0.4,freq:60,decay:0.3}, body:{on:true,wave:'triangle',level:0.7,freq:190,spread:15,decay:0.2}, transient:{on:true,type:'snap',level:0.85,decay:0.02}, air:{on:true,level:0.8,color:3500,decay:0.35}}, movement:{sweepDepth:-4,sweepTime:0.05}, space:{roomSize:0.9,tail:0.4,wet:0.65}, glue:{drive:0.4,comp:0.7,length:0.8,out:0.9} }
};

function labApplyState(stateObj){
  // Deep-merge into soundLab, then push every value back into its control
  // and let the control's own handler re-sync state + readout.
  (function merge(dst, srcObj){
    for(const k in srcObj){
      if(srcObj[k] && typeof srcObj[k]==='object' && !Array.isArray(srcObj[k])) merge(dst[k]||(dst[k]={}), srcObj[k]);
      else dst[k]=srcObj[k];
    }
  })(soundLab, stateObj);
  LAB_BINDINGS.forEach(([id, path])=>{
    const el=document.getElementById(id);
    if(!el) return;
    const parts=path.split('.');
    let v=soundLab;
    for(const part of parts) v=v[part];
    if(el.type==='checkbox') el.checked=!!v;
    else el.value=String(v);
    el.dispatchEvent(new Event('input'));
  });
}

document.getElementById('labPreset').addEventListener('change', (e)=>{
  const p=LAB_PRESETS[e.target.value];
  if(p) labApplyState(p);
});

// Stubs: the engine (offline layered render -> baked buffer -> rack voice)
// is the next build. The buttons exist now so the workflow reads complete.
document.getElementById('labPreviewBtn').addEventListener('click', ()=>{
  showHint('Sound Lab engine is the next build -- this panel is the interface. Settings for "'+soundLab.name+'" are captured and ready.');
});
document.getElementById('labAddBtn').addEventListener('click', ()=>{
  showHint('Add to Rack comes with the render engine -- the Lab state is already structured for it.');
});

const soundLabToggle=document.getElementById('soundLabToggle');
const soundLabBody=document.getElementById('soundLab');
let soundLabExpanded=false;
function setSoundLabExpanded(expanded){
  soundLabExpanded=expanded;
  soundLabBody.hidden=!expanded;
  soundLabToggle.setAttribute('aria-expanded', String(expanded));
  soundLabToggle.querySelector('.chevron').innerHTML=expanded ? '&#9662;' : '&#9656;';
}
soundLabToggle.addEventListener('click', ()=> setSoundLabExpanded(!soundLabExpanded));
setSoundLabExpanded(false);

/* ---------- init ---------- */""",
"js")

if fails:
    print("FAILURES:", fails); sys.exit(1)
open(p,'w').write(src)
print("OK", len(src))
