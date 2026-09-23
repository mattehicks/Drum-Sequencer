import sys
p='C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
src=open(p).read()
fails=[]
def rep(old,new,label):
    global src
    if src.count(old)!=1: fails.append(f"{label}: {src.count(old)} matches"); return
    src=src.replace(old,new)

# ---- CSS: armed/recording states + button ----
rep(""".solo-hint{flex-basis:100%;color:#8f8b86;font-size:11.5px;line-height:1.5;max-width:70ch;}""",
""".solo-hint{flex-basis:100%;color:#8f8b86;font-size:11.5px;line-height:1.5;max-width:70ch;}
#soloRecBtn{margin-top:4px;}
#soloRecBtn.armed{border-color:#e9c46a;color:#e9c46a;}
#soloRecBtn.recording{border-color:#ff5d5d;color:#ff5d5d;}
#soloPad.recording{border-color:#ff5d5d;box-shadow:0 0 18px rgba(255,93,93,0.3) inset;}
#soloRecStatus{font-size:11.5px;color:#8f8b86;min-height:1.2em;}""",
"css")

# ---- HTML: Arm button + status under the solo controls ----
rep("""          <div class="lab-row"><label for="soloSnap">Snap</label><input type="checkbox" id="soloSnap"><output></output></div>
        </div>""",
"""          <div class="lab-row"><label for="soloSnap">Snap</label><input type="checkbox" id="soloSnap"><output></output></div>
          <button type="button" class="lab-btn" id="soloRecBtn">&#9210; Arm Recorder</button>
          <div id="soloRecStatus">Arm, then play: recording starts at your first note. Enter stops it (2 s max) and saves it to the rack.</div>
        </div>""",
"html")

# ---- JS: recorder wired into the solo gate ----
rep("""const soloToggle=document.getElementById('soloToggle');""",
"""/* ---------- Solo sample recorder ---------- */
// Captures the Solo Pad's own output (post volume-gesture, so the swell is
// part of the take) into a buffer, then registers it as a rack instrument.
// Armed -> the first gate-open starts the capture, so the sample begins at
// the note attack rather than at the moment the button was clicked. Enter
// or the 2-second cap ends it. The take is stored inside project files as
// 16-bit PCM, so recorded instruments survive save/load like Lab sounds.
const SOLO_REC_MAX_S=2.0;
let recArmed=false, recActive=false, recChunks=[], recLen=0, recNode=null, recMute=null, recSeq=1;
const soloRecBtn=document.getElementById('soloRecBtn');
const soloRecStatus=document.getElementById('soloRecStatus');

function recSetStatus(t){ soloRecStatus.textContent=t; }
function recUpdateBtn(){
  soloRecBtn.classList.toggle('armed', recArmed && !recActive);
  soloRecBtn.classList.toggle('recording', recActive);
  soloPadEl.classList.toggle('recording', recActive);
  soloRecBtn.innerHTML=recActive ? '&#9209; Stop (Enter)' : (recArmed ? 'Armed &mdash; play to record' : '&#9210; Arm Recorder');
}

function recStart(){
  if(recActive || !ctx || !soloGainNode) return;
  recChunks=[]; recLen=0; recActive=true;
  // ScriptProcessor tap: the node only runs while routed to the destination,
  // so it flows through a muted gain -- captured, never heard twice.
  recNode=ctx.createScriptProcessor(4096, 1, 1);
  recMute=ctx.createGain(); recMute.gain.value=0;
  soloGainNode.connect(recNode);
  recNode.connect(recMute); recMute.connect(ctx.destination);
  recNode.onaudioprocess=(e)=>{
    if(!recActive) return;
    recChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    recLen+=e.inputBuffer.length;
    const secs=recLen/ctx.sampleRate;
    recSetStatus('REC '+secs.toFixed(1)+' s \\u2014 Enter to stop');
    if(secs>=SOLO_REC_MAX_S) recStop();
  };
  recUpdateBtn();
}

function recStop(){
  if(!recActive) return;
  recActive=false; recArmed=false;
  try{ soloGainNode.disconnect(recNode); }catch(_){ }
  try{ recNode.disconnect(); recMute.disconnect(); }catch(_){ }
  recNode.onaudioprocess=null; recNode=null; recMute=null;
  const sr=ctx.sampleRate;
  const n=Math.min(recLen, Math.floor(sr*SOLO_REC_MAX_S));
  if(n<sr*0.05){ recUpdateBtn(); recSetStatus('Nothing captured \\u2014 arm and play again.'); return; }
  const data=new Float32Array(n);
  let o=0;
  for(const c of recChunks){ if(o>=n) break; data.set(c.subarray(0, Math.min(c.length, n-o)), o); o+=c.length; }
  // 5ms fades so the take never clicks on trigger or loop.
  const f=Math.floor(sr*0.005);
  for(let i=0;i<f;i++){ data[i]*=i/f; data[n-1-i]*=i/f; }
  const buf=new AudioBuffer({length:n, sampleRate:sr, numberOfChannels:1});
  buf.copyToChannel(data, 0);
  const name='Sample '+(recSeq++);
  const voice=makeSampleVoice({sr:sr, pcm:recEncodePCM16(data)}, null, name);
  labBuffers[voice.id]=buf; // already decoded -- no queue needed
  VOICES.push(voice);
  state.voices[voice.id]={level:0.85, pitch:1.0};
  renderVoices();
  recUpdateBtn();
  recSetStatus('Saved "'+name+'" to the rack ('+(n/sr).toFixed(2)+' s).');
  showHint('"'+name+'" recorded \\u2014 assign it to a sequencer row like any instrument.');
}

// 16-bit PCM <-> base64, the persistence format for recorded takes: a full
// 2 s mono take is ~250 KB in a project file, small enough to embed.
function recEncodePCM16(f32){
  const i16=new Int16Array(f32.length);
  for(let i=0;i<f32.length;i++){
    const s=Math.max(-1, Math.min(1, f32[i]));
    i16[i]=s<0 ? s*0x8000 : s*0x7FFF;
  }
  const bytes=new Uint8Array(i16.buffer);
  let bin='';
  for(let i=0;i<bytes.length;i+=8192) bin+=String.fromCharCode.apply(null, bytes.subarray(i, i+8192));
  return btoa(bin);
}
function recDecodePCM16(b64, sr){
  const bin=atob(b64);
  const bytes=new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
  const i16=new Int16Array(bytes.buffer);
  const buf=new AudioBuffer({length:i16.length, sampleRate:sr, numberOfChannels:1});
  const d=buf.getChannelData(0);
  for(let i=0;i<i16.length;i++) d[i]=i16[i]/0x8000;
  return buf;
}

// Same shape as a Lab voice -- buffer playback behind Level + Pitch -- but
// carrying raw audio (sampleData) instead of a synth recipe.
function makeSampleVoice(sampleData, saved, name){
  const id=(saved && saved.id) || ('smp-'+Date.now().toString(36)+'-'+Math.floor(Math.random()*1e4));
  return {
    id,
    key:(saved && saved.key)||'',
    name:(saved && saved.name) || name || 'Sample',
    isClone:false,
    clonedFrom:null,
    sampleData:sampleData,
    trigger:(p, when)=>{
      const buffer=labBuffers[id];
      if(!buffer || !ctx) return false;
      const t=(when!=null)?when:ctx.currentTime;
      const bus=ctx.createGain(); bus.gain.value=p.level; bus.connect(master);
      const s=ctx.createBufferSource(); s.buffer=buffer; s.playbackRate.value=p.pitch;
      s.connect(bus); s.start(t);
      setTimeout(()=>bus.disconnect(), (buffer.duration/Math.max(0.1,p.pitch)+0.1)*1000);
      return true;
    },
    theory:'A take recorded live from the Solo Pad: the pad\\'s output, volume gesture included, captured to a mono buffer with 5 ms edge fades and replayed per hit. Level and playback-rate Pitch are live; the audio itself is embedded in the project file as 16-bit PCM and rebuilt on load.',
    params:[
      {id:'level',label:'Level',min:0,max:1,step:0.01,value:0.85,unit:''},
      {id:'pitch',label:'Pitch',min:0.5,max:2.0,step:0.01,value:1.0,unit:''}
    ]
  };
}

soloRecBtn.addEventListener('click', ()=>{
  if(recActive){ recStop(); return; }
  recArmed=!recArmed;
  recUpdateBtn();
  recSetStatus(recArmed ? 'Armed \\u2014 recording starts on your first note.' : 'Disarmed.');
});
document.addEventListener('keydown', (e)=>{
  if(e.key!=='Enter' || !recActive) return;
  const t=e.target;
  if(t && (t.tagName==='INPUT' || t.tagName==='TEXTAREA' || t.isContentEditable)) return;
  e.preventDefault();
  recStop();
});

const soloToggle=document.getElementById('soloToggle');""",
"js core")

# ---- hook: gate-open starts an armed recording ----
rep("""async function soloGateChanged(){
  soloUpdateUI(); // reflect the gate immediately, even while audio spins up
  if(soloGated()){
    if(await labEnsureAudioRunning()) soloApply();
  }else if(soloOsc){
    soloApply(); // ramps to silence; the osc keeps running for the next gate
  }
}""",
"""async function soloGateChanged(){
  soloUpdateUI(); // reflect the gate immediately, even while audio spins up
  if(soloGated()){
    if(await labEnsureAudioRunning()){
      soloApply();
      if(recArmed && !recActive) recStart(); // armed: the note itself starts the take
    }
  }else if(soloOsc){
    soloApply(); // ramps to silence; the osc keeps running for the next gate
  }
}""",
"gate hook")

# ---- save: carry sampleData ----
rep("""      labParams:v.labParams||undefined,
      params:{...state.voices[v.id]}
    }))""",
"""      labParams:v.labParams||undefined,
      sampleData:v.sampleData||undefined,
      params:{...state.voices[v.id]}
    }))""",
"save")

# ---- load: rebuild recorded voices ----
rep("""      if(sv.labParams){""",
"""      if(sv.sampleData && sv.sampleData.pcm){
        // A recorded take: decode the embedded PCM straight back into a
        // buffer (AudioBuffer needs no live context), register, done.
        const smp=makeSampleVoice(sv.sampleData, sv);
        try{ labBuffers[smp.id]=recDecodePCM16(sv.sampleData.pcm, sv.sampleData.sr||44100); }
        catch(err){ console.warn('Sample decode failed for', smp.id, err); }
        rebuilt.push(smp);
        byId[smp.id]=smp;
        newVoiceState[smp.id]=sv.params ? {...sv.params} : {level:0.85, pitch:1.0};
        return;
      }
      if(sv.labParams){""",
"load")

if fails:
    print("FAILURES:", fails); sys.exit(1)
open(p,'w').write(src)
print("OK", len(src))
