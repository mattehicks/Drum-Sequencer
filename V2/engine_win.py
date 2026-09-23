import sys
p='C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
src=open(p).read()
fails=[]
def rep(old,new,label):
    global src
    if src.count(old)!=1: fails.append(f"{label}: {src.count(old)} matches"); return
    src=src.replace(old,new)

# ---- A. engine core, after the Keys button wiring ----
rep("""seqKeysBtn.addEventListener('click', ()=>{ if(keysPanel.hidden) seqOpenKeys(); else seqCloseKeys(); });""",
"""seqKeysBtn.addEventListener('click', ()=>{ if(keysPanel.hidden) seqOpenKeys(); else seqCloseKeys(); });

/* ---------- Sound Lab render engine ---------- */
// The Lab's whole design premise: the expensive, layered, produced sound is
// rendered ONCE through an OfflineAudioContext (the same baking trick the
// cymbal uses) into a buffer, and each hit just replays that buffer. Density
// and length therefore cost nothing per trigger.
let labBuffers={};            // lab voice id -> baked AudioBuffer
let labPreviewBuffer=null;    // last previewed bake of the panel's current state
let labDirty=true;            // any control change invalidates the preview cache
let labPendingRenders=[];     // lab voices loaded from a file before audio started
let labRenderSeq=0;           // strictly increasing; lets a late slow render lose to a newer one

function labMarkDirty(){ labDirty=true; labPreviewBuffer=null; }

// Deep-copy of the panel state, so a rack voice keeps the recipe it was
// added with even as the panel moves on.
function labSnapshotState(){ return JSON.parse(JSON.stringify(soundLab)); }

// Renders one Lab recipe to a stereo buffer. Independent of the live ctx --
// it only borrows the sample rate so playback needs no resampling.
async function labRender(cfg){
  const sr=(typeof ctx!=='undefined' && ctx) ? ctx.sampleRate : 44100;
  const dur=Math.max(0.2, cfg.glue.length);
  const off=new OfflineAudioContext(2, Math.ceil(sr*dur), sr);
  const t0=0.002;

  // Sum bus for the dry layers, then glue: drive -> (dry + convolved wet) ->
  // compressor -> out. Saturating the SUM, not each layer, is what fuses the
  // stack into one event instead of four coincident sounds.
  const sum=off.createGain(); sum.gain.value=1;
  const shaper=off.createWaveShaper();
  shaper.curve=makeSaturationCurve(cfg.glue.drive*0.6); // reuse the voices' tanh curve, scaled to taste
  shaper.oversample='2x';
  sum.connect(shaper);

  const comp=off.createDynamicsCompressor();
  comp.threshold.value=-10-cfg.glue.comp*28;
  comp.ratio.value=2+cfg.glue.comp*10;
  comp.knee.value=20;
  comp.attack.value=0.04;  // slow enough to let the transient through, then squash the body up behind it
  comp.release.value=0.2;
  comp.connect(off.destination);

  const dry=off.createGain();
  shaper.connect(dry); dry.connect(comp);

  const wetAmt=cfg.space.wet, tail=cfg.space.tail;
  if(wetAmt>0.01 && tail>0.03){
    // Synthetic impulse response: decaying stereo noise. Room size sets how
    // slowly it dies (big room = long ring within the same tail length), and
    // a lowpass on the wet path keeps the tail darker than the hit, which is
    // what makes it read as a space rather than added noise.
    const irLen=Math.max(0.05, tail);
    const ir=off.createBuffer(2, Math.ceil(sr*irLen), sr);
    const rate=3+(1-cfg.space.roomSize)*9; // decay steepness
    for(let ch=0;ch<2;ch++){
      const d=ir.getChannelData(ch);
      for(let i=0;i<d.length;i++){
        const t=i/sr;
        d[i]=(Math.random()*2-1)*Math.exp(-rate*t/irLen);
      }
    }
    const conv=off.createConvolver(); conv.buffer=ir; conv.normalize=true;
    const pre=off.createDelay(0.1); pre.delayTime.value=0.02; // 20ms predelay keeps the attack clean before the tail blooms
    const wetLP=off.createBiquadFilter(); wetLP.type='lowpass'; wetLP.frequency.value=4500;
    const wet=off.createGain(); wet.gain.value=wetAmt;
    shaper.connect(pre); pre.connect(conv); conv.connect(wetLP); wetLP.connect(wet); wet.connect(comp);
    dry.gain.value=1-wetAmt*0.4; // keep the dry hit dominant even at high mixes
  }

  // -- movement: the note is where the pitch LANDS; sweepDepth is how far
  // away it starts. A -19 st thwomp starts 19 st above and falls onto the
  // pitch; a +24 riser starts 2 octaves below and climbs up to it.
  const sweep=(oscNode, f)=>{
    const d=cfg.movement.sweepDepth, st=Math.max(0.01, cfg.movement.sweepTime);
    const f1=Math.max(1, f);
    if(Math.abs(d)<0.5){ oscNode.frequency.setValueAtTime(f1, t0); return; }
    const f0=Math.max(1, f1*Math.pow(2, -d/12));
    oscNode.frequency.setValueAtTime(f0, t0);
    oscNode.frequency.exponentialRampToValueAtTime(f1, t0+st);
  };
  const env=(g, peak, decay)=>{
    g.gain.setValueAtTime(0, 0);
    g.gain.linearRampToValueAtTime(Math.max(0.0001, peak), t0+0.003);
    g.gain.exponentialRampToValueAtTime(0.0001, t0+0.003+Math.max(0.02, decay));
  };
  const noiseBuf=(seconds)=>{
    const b=off.createBuffer(1, Math.ceil(sr*Math.max(0.05, seconds)), sr);
    const d=b.getChannelData(0);
    for(let i=0;i<d.length;i++) d[i]=Math.random()*2-1;
    return b;
  };

  const L=cfg.layers;
  if(L.sub.on && L.sub.level>0){
    const o=off.createOscillator(); o.type='sine';
    sweep(o, L.sub.freq);
    const g=off.createGain(); env(g, L.sub.level, L.sub.decay);
    o.connect(g); g.connect(sum); o.start(0); o.stop(dur);
  }
  if(L.body.on && L.body.level>0){
    // Three detuned oscillators; spread in cents. At 0 they phase-lock into
    // one thick osc, wide they chorus into an aggressive stack.
    [-1,0,1].forEach(k=>{
      const o=off.createOscillator(); o.type=L.body.wave;
      o.detune.value=k*L.body.spread;
      sweep(o, L.body.freq);
      const g=off.createGain(); env(g, L.body.level*0.4, L.body.decay);
      o.connect(g); g.connect(sum); o.start(0); o.stop(dur);
    });
  }
  if(L.transient.on && L.transient.level>0){
    const g=off.createGain(); env(g, L.transient.level, L.transient.decay);
    g.connect(sum);
    if(L.transient.type==='knock'){
      const o=off.createOscillator(); o.type='sine';
      o.frequency.setValueAtTime(220, t0);
      o.frequency.exponentialRampToValueAtTime(90, t0+Math.max(0.02, L.transient.decay));
      o.connect(g); o.start(0); o.stop(t0+0.15);
    }else{
      const s=off.createBufferSource(); s.buffer=noiseBuf(0.12);
      const f=off.createBiquadFilter();
      if(L.transient.type==='snap'){ f.type='bandpass'; f.frequency.value=1800; f.Q.value=1.8; }
      else { f.type='highpass'; f.frequency.value=3000; }
      s.connect(f); f.connect(g); s.start(0);
    }
  }
  if(L.air.on && L.air.level>0){
    const s=off.createBufferSource(); s.buffer=noiseBuf(dur);
    const f=off.createBiquadFilter(); f.type='lowpass'; f.frequency.value=L.air.color; f.Q.value=0.7;
    const g=off.createGain(); env(g, L.air.level*0.8, L.air.decay);
    s.connect(f); f.connect(g); g.connect(sum); s.start(0);
  }

  const buf=await off.startRendering();

  // Normalize to a consistent hot-but-safe peak scaled by Output, then a
  // 20ms fade at the very end so retriggers and pattern loops never click.
  let peak=0;
  for(let ch=0;ch<2;ch++){
    const d=buf.getChannelData(ch);
    for(let i=0;i<d.length;i++){ const a=Math.abs(d[i]); if(a>peak) peak=a; }
  }
  const scale=peak>0 ? (0.9*cfg.glue.out)/peak : 1;
  const fadeN=Math.floor(sr*0.02);
  for(let ch=0;ch<2;ch++){
    const d=buf.getChannelData(ch);
    for(let i=0;i<d.length;i++){
      d[i]*=scale;
      if(i>d.length-fadeN) d[i]*=(d.length-i)/fadeN;
    }
  }
  return buf;
}

// A rack voice whose trigger replays this lab sound's baked buffer -- the
// same Level + Pitch surface as the click voices, so it slots into every
// existing system unchanged: sequencer rows, velocity, clones, the per-cell
// override menu, and the note keyboard (via applyNoteToParams' pitch case).
function makeLabVoice(labParams, saved){
  const id=(saved && saved.id) || ('lab-'+Date.now().toString(36)+'-'+Math.floor(Math.random()*1e4));
  const voice={
    id,
    key:(saved && saved.key)||'',
    name:(saved && saved.name) || labParams.name || 'Lab Sound',
    isClone:false,
    clonedFrom:null,
    labParams:JSON.parse(JSON.stringify(labParams)),
    trigger:(p, when)=>{
      const buffer=labBuffers[id];
      if(!buffer || !ctx) return false; // not rendered yet (or audio not started)
      const t=(when!=null)?when:ctx.currentTime;
      const bus=ctx.createGain(); bus.gain.value=p.level; bus.connect(master);
      const s=ctx.createBufferSource(); s.buffer=buffer; s.playbackRate.value=p.pitch;
      s.connect(bus); s.start(t);
      setTimeout(()=>bus.disconnect(), (buffer.duration/Math.max(0.1,p.pitch)+0.1)*1000);
      return true;
    },
    theory:'A Sound Lab creation: sub/body/transient/air layers with pitch movement, rendered offline through saturation, convolution space and compression into a baked stereo buffer, then replayed per hit. Only Level and a playback-rate Pitch are live; the recipe itself is stored with the voice and re-rendered on project load.',
    params:[
      {id:'level',label:'Level',min:0,max:1,step:0.01,value:0.85,unit:''},
      {id:'pitch',label:'Pitch',min:0.5,max:2.0,step:0.01,value:1.0,unit:''}
    ]
  };
  return voice;
}

function labQueueRender(voice){
  if(typeof ctx!=='undefined' && ctx){
    labRender(voice.labParams).then(buf=>{ labBuffers[voice.id]=buf; })
      .catch(err=>console.warn('Lab render failed for', voice.id, err));
  }else{
    labPendingRenders.push(voice); // audio engine not started yet; bake on first start
  }
}
function labFlushPendingRenders(){
  const pend=labPendingRenders; labPendingRenders=[];
  pend.forEach(v=>labQueueRender(v));
}

// Preview needs a running live context to be audible; starting it here on
// the button's own user gesture mirrors what the engine button does.
async function labEnsureAudioRunning(){
  if(!ctx || ctx.state!=='running'){
    engineBtn.click();
    for(let i=0;i<50 && (!ctx || ctx.state!=='running');i++) await new Promise(r=>setTimeout(r,100));
  }
  return !!(ctx && ctx.state==='running');
}""",
"A engine core")

# ---- B. real button handlers replace the stubs ----
rep("""// Stubs: the engine (offline layered render -> baked buffer -> rack voice)
// is the next build. The buttons exist now so the workflow reads complete.
document.getElementById('labPreviewBtn').addEventListener('click', ()=>{
  showHint('Sound Lab engine is the next build -- this panel is the interface. Settings for "'+soundLab.name+'" are captured and ready.');
});
document.getElementById('labAddBtn').addEventListener('click', ()=>{
  showHint('Add to Rack comes with the render engine -- the Lab state is already structured for it.');
});""",
"""document.getElementById('labPreviewBtn').addEventListener('click', async ()=>{
  const btn=document.getElementById('labPreviewBtn');
  if(!(await labEnsureAudioRunning())){ showHint('Could not start the audio engine.'); return; }
  const mySeq=++labRenderSeq;
  if(labDirty || !labPreviewBuffer){
    btn.disabled=true;
    try{
      const buf=await labRender(soundLab);
      if(mySeq!==labRenderSeq) return; // a newer render superseded this one
      labPreviewBuffer=buf; labDirty=false;
    }catch(err){
      console.warn('Lab preview render failed', err);
      showHint('Render failed -- see console.');
      btn.disabled=false;
      return;
    }
    btn.disabled=false;
  }
  const bus=ctx.createGain(); bus.gain.value=1; bus.connect(master);
  const s=ctx.createBufferSource(); s.buffer=labPreviewBuffer; s.connect(bus);
  s.start();
  setTimeout(()=>bus.disconnect(), (labPreviewBuffer.duration+0.1)*1000);
  showHint('Previewing "'+soundLab.name+'" ('+labPreviewBuffer.duration.toFixed(2)+' s render).');
});

document.getElementById('labAddBtn').addEventListener('click', ()=>{
  const snap=labSnapshotState();
  snap.name=soundLab.name;
  const voice=makeLabVoice(snap);
  VOICES.push(voice);
  state.voices[voice.id]={level:0.85, pitch:1.0};
  // Reuse the already-rendered preview when the panel hasn't changed since,
  // otherwise bake fresh in the background; hits stay silent until ready.
  if(!labDirty && labPreviewBuffer) labBuffers[voice.id]=labPreviewBuffer;
  else labQueueRender(voice);
  renderVoices();
  showHint('"'+voice.name+'" added to the rack -- assign it to a sequencer row or clone it for variants.');
  // Bump the default name so the next creation doesn't collide.
  const m=/^(.*?)(\\d+)\\s*$/.exec(soundLab.name);
  const next=m ? (m[1]+(parseInt(m[2],10)+1)) : (soundLab.name+' 2');
  soundLab.name=next;
  document.getElementById('labName').value=next;
});""",
"B handlers")

# ---- C. dirty tracking on every control change ----
rep("""    labSetPath(path, v);""",
"""    labSetPath(path, v);
    labMarkDirty();""",
"C dirty hook")

# ---- D. bake deferred lab sounds when the engine first starts ----
rep("""    await setupKSWorklet();""",
"""    await setupKSWorklet();
    labFlushPendingRenders();""",
"D engine init")

# ---- E. project load rebuilds lab voices from their stored recipe ----
rep("""    if(!sv.isClone){
      const stock=stockVoices.find(v=>v.id===sv.id);""",
"""    if(!sv.isClone){
      if(sv.labParams){
        // A Sound Lab creation: no stock definition exists for it -- rebuild
        // the voice from its stored recipe and queue an offline re-render
        // (deferred until the audio engine starts if it hasn't yet).
        const lv=makeLabVoice(sv.labParams, sv);
        rebuilt.push(lv);
        byId[lv.id]=lv;
        newVoiceState[lv.id]=sv.params ? {...sv.params} : {level:0.85, pitch:1.0};
        labQueueRender(lv);
        return;
      }
      const stock=stockVoices.find(v=>v.id===sv.id);""",
"E load")

# ---- F. save carries the recipe ----
rep("""      isClone:!!v.isClone,
      clonedFrom:v.clonedFrom||null,
      params:{...state.voices[v.id]}
    }))""",
"""      isClone:!!v.isClone,
      clonedFrom:v.clonedFrom||null,
      labParams:v.labParams||undefined,
      params:{...state.voices[v.id]}
    }))""",
"F save")

# ---- G. note keyboard retunes lab voices via their pitch knob ----
rep("""    case 'cymbal':
    case 'click1':
    case 'click2':
      // These expose a playback-rate style Pitch knob rather than a
      // frequency -- treat middle C as rate 1.0.
      clamp('pitch', freq/261.63);
      break;
  }""",
"""    case 'cymbal':
    case 'click1':
    case 'click2':
      // These expose a playback-rate style Pitch knob rather than a
      // frequency -- treat middle C as rate 1.0.
      clamp('pitch', freq/261.63);
      break;
    default:
      // Lab-made voices (and anything else with a playback-rate Pitch knob)
      // retune the same way the clicks do.
      if('pitch' in p) clamp('pitch', freq/261.63);
      break;
  }""",
"G note map")

if fails:
    print("FAILURES:", fails); sys.exit(1)
open(p,'w').write(src)
print("OK", len(src))
