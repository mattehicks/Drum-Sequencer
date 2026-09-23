import sys, os
p='C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
lame_path=os.path.join(os.path.dirname(os.path.abspath(__file__)) or '.', 'lame.min.js')
lame=open(lame_path, encoding='utf-8').read()
src=open(p).read()
fails=[]
def rep(old,new,label):
    global src
    if src.count(old)!=1: fails.append(f"{label}: {src.count(old)} matches"); return
    src=src.replace(old,new)

# ---- inline the MP3 encoder as its own script tag before the app script ----
rep("""<script>""",
"""<script>
/* lamejs 1.2.1 (LGPL) -- pure-JS MP3 encoder, inlined so the workbench stays
   a single self-contained file with no network dependency. Exposes the
   global `lamejs` with Mp3Encoder, used by the Export Audio popup. */
"""+lame+"""
</script>
<script>""",
"lame inline")

# ---- CSS ----
rep(""".file-ctrl{display:flex; align-items:center; gap:8px; flex-wrap:wrap;}""",
""".file-ctrl{display:flex; align-items:center; gap:8px; flex-wrap:wrap;}
/* Export Audio popup: centered modal, filename + format, big record toggle. */
#exportOverlay{
  position:fixed; inset:0;
  background:rgba(0,0,0,0.55);
  display:flex; align-items:center; justify-content:center;
  z-index:70; /* above the note keyboard (55) and context menu (60) */
}
#exportModal{
  background:var(--panel,#16161c);
  border:1px solid rgba(255,255,255,0.25);
  border-radius:14px;
  padding:20px 22px;
  width:min(360px, calc(100vw - 32px));
  box-shadow:0 18px 60px rgba(0,0,0,0.7);
  display:flex; flex-direction:column; gap:12px;
}
#exportModal h3{margin:0; font-size:15px;}
#exportModal .exp-row{display:flex; align-items:center; gap:10px; font-size:13px;}
#exportModal .exp-row label{width:64px; color:#cfcbc6;}
#exportModal input[type=text], #exportModal select{
  flex:1;
  background:var(--panel-2,#1c1c24); color:#eee;
  border:1px solid rgba(255,255,255,0.25);
  border-radius:6px; padding:7px 10px; font-size:13px;
  min-width:0;
}
#exportRecBtn{
  padding:10px;
  font-size:14px;
  border-radius:8px;
  border:1px solid var(--accent,#7ad0ff);
  color:var(--accent,#7ad0ff);
  background:rgba(122,208,255,0.08);
  cursor:pointer;
}
#exportRecBtn.rec{border-color:#ff5d5d; color:#ff5d5d; background:rgba(255,93,93,0.10);}
#exportStatus{font-size:12px; color:#8f8b86; min-height:1.2em;}
#exportModal .exp-foot{display:flex; justify-content:flex-end;}
#exportCloseBtn{background:none; border:none; color:#8f8b86; cursor:pointer; font-size:13px; padding:4px 8px;}
#exportCloseBtn:hover{color:#eee;}""",
"css")

# ---- toolbar button ----
rep("""      <input type="file" id="importInstrumentsInput" accept="application/json,.json" hidden>""",
"""      <input type="file" id="importInstrumentsInput" accept="application/json,.json" hidden>
      <button id="exportAudioBtn" class="file-btn" type="button" title="Record everything you hear (sequencer, solo pad, all of it) and save it as an MP3 or WAV file">Export Audio</button>""",
"button")

# ---- module ----
rep("""  if(metroMode>0) metroStartFreeRun();
  else if(metroTimer){ clearTimeout(metroTimer); metroTimer=null; }
});""",
"""  if(metroMode>0) metroStartFreeRun();
  else if(metroTimer){ clearTimeout(metroTimer); metroTimer=null; }
});

/* ---------- Export Audio (record the master bus to MP3/WAV) ---------- */
// Captures whatever the master bus is playing -- pattern, solo pad, lab
// sounds, metronome, all mixed exactly as heard -- into stereo buffers via
// the same ScriptProcessor tap the solo recorder uses, then encodes on stop:
// MP3 through the inlined lamejs encoder, or WAV built by hand (44-byte
// RIFF header + interleaved 16-bit PCM). The browser can't encode MP3
// natively, which is why lamejs ships inside this file.
const EXPORT_MAX_S=180;
let expOverlay=null, expRecording=false, expNode=null, expMute=null, expL=[], expR=[], expLen=0, expTimerEl=null;

function exportBuildModal(){
  if(expOverlay) return;
  expOverlay=document.createElement('div');
  expOverlay.id='exportOverlay';
  expOverlay.hidden=true;
  expOverlay.innerHTML=
    '<div id="exportModal">'+
      '<h3>Export Audio</h3>'+
      '<div class="exp-row"><label for="exportName">Filename</label><input type="text" id="exportName" value="d20-take"></div>'+
      '<div class="exp-row"><label for="exportFmt">Format</label><select id="exportFmt">'+
        (typeof lamejs!=='undefined' ? '<option value="mp3" selected>MP3 (192 kbps)</option>' : '')+
        '<option value="wav">WAV (lossless)</option>'+
      '</select></div>'+
      '<button id="exportRecBtn" type="button">&#9210; Record</button>'+
      '<div id="exportStatus">Start the pattern (or play live), hit Record, then Stop to save. '+EXPORT_MAX_S/60+' min max.</div>'+
      '<div class="exp-foot"><button id="exportCloseBtn" type="button">Close</button></div>'+
    '</div>';
  document.body.appendChild(expOverlay);
  expTimerEl=expOverlay.querySelector('#exportStatus');
  expOverlay.addEventListener('pointerdown', (e)=>{ if(e.target===expOverlay && !expRecording) exportClose(); });
  expOverlay.querySelector('#exportCloseBtn').addEventListener('click', ()=>{ if(expRecording) exportStop(); exportClose(); });
  expOverlay.querySelector('#exportRecBtn').addEventListener('click', ()=>{ expRecording ? exportStop() : exportStart(); });
}
function exportOpen(){ exportBuildModal(); expOverlay.hidden=false; }
function exportClose(){ if(expOverlay) expOverlay.hidden=true; }

async function exportStart(){
  if(expRecording) return;
  if(!(await labEnsureAudioRunning())){ expTimerEl.textContent='Could not start the audio engine.'; return; }
  expL=[]; expR=[]; expLen=0; expRecording=true;
  expNode=ctx.createScriptProcessor(4096, 2, 2);
  expMute=ctx.createGain(); expMute.gain.value=0;
  master.connect(expNode);
  expNode.connect(expMute); expMute.connect(ctx.destination);
  expNode.onaudioprocess=(e)=>{
    if(!expRecording) return;
    expL.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    expR.push(new Float32Array(e.inputBuffer.getChannelData(1)));
    expLen+=e.inputBuffer.length;
    const secs=expLen/ctx.sampleRate;
    expTimerEl.textContent='REC '+secs.toFixed(1)+' s';
    if(secs>=EXPORT_MAX_S) exportStop();
  };
  const btn=expOverlay.querySelector('#exportRecBtn');
  btn.classList.add('rec');
  btn.innerHTML='&#9209; Stop & Save';
}

function exportStop(){
  if(!expRecording) return;
  expRecording=false;
  try{ master.disconnect(expNode); }catch(_){ }
  try{ expNode.disconnect(); expMute.disconnect(); }catch(_){ }
  expNode.onaudioprocess=null; expNode=null; expMute=null;
  const btn=expOverlay.querySelector('#exportRecBtn');
  btn.classList.remove('rec');
  btn.innerHTML='&#9210; Record';
  if(expLen<ctx.sampleRate*0.2){ expTimerEl.textContent='Nothing captured.'; return; }
  const fmt=expOverlay.querySelector('#exportFmt').value;
  expTimerEl.textContent='Encoding '+fmt.toUpperCase()+'...';
  // Yield one frame so the status paints before the synchronous encode.
  setTimeout(()=>{
    const name=(expOverlay.querySelector('#exportName').value.trim()||'d20-take').replace(/[\\\\/:*?"<>|]/g,'_');
    const L=exportFlatten(expL), R=exportFlatten(expR);
    let blob;
    if(fmt==='mp3' && typeof lamejs!=='undefined') blob=exportEncodeMp3(L, R, ctx.sampleRate);
    else blob=exportEncodeWav(L, R, ctx.sampleRate);
    const ext=(fmt==='mp3' && typeof lamejs!=='undefined') ? '.mp3' : '.wav';
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download=name+ext;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(a.href), 5000);
    expTimerEl.textContent='Saved '+name+ext+' ('+(L.length/ctx.sampleRate).toFixed(1)+' s, '+(blob.size/1024/1024).toFixed(2)+' MB).';
  }, 30);
}

function exportFlatten(chunks){
  const out=new Float32Array(expLen);
  let o=0;
  for(const c of chunks){ out.set(c, o); o+=c.length; }
  return out;
}
function exportF32toI16(f32){
  const i16=new Int16Array(f32.length);
  for(let i=0;i<f32.length;i++){
    const s=Math.max(-1, Math.min(1, f32[i]));
    i16[i]=s<0 ? s*0x8000 : s*0x7FFF;
  }
  return i16;
}
function exportEncodeMp3(L, R, sr){
  const enc=new lamejs.Mp3Encoder(2, sr, 192);
  const l=exportF32toI16(L), r=exportF32toI16(R);
  const parts=[], BLOCK=1152;
  for(let i=0;i<l.length;i+=BLOCK){
    const d=enc.encodeBuffer(l.subarray(i, i+BLOCK), r.subarray(i, i+BLOCK));
    if(d.length) parts.push(new Uint8Array(d));
  }
  const end=enc.flush();
  if(end.length) parts.push(new Uint8Array(end));
  return new Blob(parts, {type:'audio/mp3'});
}
function exportEncodeWav(L, R, sr){
  const n=L.length, bytesPerFrame=4; // 2ch x 16-bit
  const buf=new ArrayBuffer(44+n*bytesPerFrame);
  const v=new DataView(buf);
  const wstr=(o,s)=>{ for(let i=0;i<s.length;i++) v.setUint8(o+i, s.charCodeAt(i)); };
  wstr(0,'RIFF'); v.setUint32(4, 36+n*bytesPerFrame, true); wstr(8,'WAVE');
  wstr(12,'fmt '); v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,2,true);
  v.setUint32(24,sr,true); v.setUint32(28,sr*bytesPerFrame,true); v.setUint16(32,bytesPerFrame,true); v.setUint16(34,16,true);
  wstr(36,'data'); v.setUint32(40, n*bytesPerFrame, true);
  const l=exportF32toI16(L), r=exportF32toI16(R);
  let o=44;
  for(let i=0;i<n;i++){ v.setInt16(o, l[i], true); o+=2; v.setInt16(o, r[i], true); o+=2; }
  return new Blob([buf], {type:'audio/wav'});
}

document.getElementById('exportAudioBtn').addEventListener('click', exportOpen);""",
"module")

if fails:
    print("FAILURES:", fails); sys.exit(1)
open(p,'w').write(src)
print("OK", len(src))
