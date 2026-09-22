import re, sys
p = 'C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
src = open(p).read()
orig_len = len(src)
fails = []

def rep(old, new, label):
    global src
    if src.count(old) != 1:
        fails.append(f"{label}: found {src.count(old)} matches")
        return
    src = src.replace(old, new)

# ---------- A. CSS additions (after the vel-num display:flex rule) ----------
rep(
""".step.vel-dragging .step-vel-num{
  display:flex;
}""",
""".step.vel-dragging .step-vel-num{
  display:flex;
}
/* Active cell: the last cell clicked or right-clicked. It's the target for
   Ctrl+C / Ctrl+V cell copy-paste and for the note keyboard below. */
.step.cell-active{
  outline:2px solid var(--accent-2);
  outline-offset:1px;
}
/* A cell carrying a per-cell voice override and/or a pinned note gets a
   small corner dot; the cell's title tooltip names the override/note. */
.step.has-cellmeta::after{
  content:'';
  position:absolute;
  top:2px; right:2px;
  width:6px; height:6px;
  border-radius:50%;
  background:var(--accent-2);
  box-shadow:0 0 4px rgba(0,0,0,0.6);
  pointer-events:none;
}
/* ---- note keyboard overlay ---- */
#keysPanel{
  position:fixed;
  left:50%;
  transform:translateX(-50%);
  bottom:14px;
  z-index:55; /* under .context-menu (60) so a menu opened over it still wins */
  background:rgba(18,18,24,0.96);
  border:1px solid rgba(255,255,255,0.18);
  border-radius:12px;
  padding:10px 12px 12px;
  box-shadow:0 10px 40px rgba(0,0,0,0.6);
  max-width:calc(100vw - 20px);
  overflow-x:auto;
}
.keys-head{
  display:flex;
  align-items:center;
  gap:8px;
  margin-bottom:8px;
  font-size:12px;
  color:#cfcbc6;
  flex-wrap:wrap;
}
.keys-title{font-weight:700;}
.keys-oct,.keys-close{
  background:rgba(255,255,255,0.08);
  border:1px solid rgba(255,255,255,0.2);
  color:#eee;
  border-radius:6px;
  padding:2px 8px;
  cursor:pointer;
  font-size:12px;
}
.keys-close{margin-left:auto;}
.keys-hint{flex-basis:100%;color:#8f8b86;font-size:11px;}
#keysPanel svg{display:block;touch-action:none;}
.pk-white,.pk-black{cursor:pointer;}
.pk-white.pk-down{fill:#ffe9a8;}
.pk-black.pk-down{fill:#4a4a52;}""",
"A css")

# ---------- B. Toolbar: Keys button next to Clear ----------
rep(
"""      <button id="seqClearBtn" class="seq-clear" type="button">Clear</button>""",
"""      <button id="seqClearBtn" class="seq-clear" type="button">Clear</button>
      <button id="seqKeysBtn" class="seq-clear" type="button" title="Open the note keyboard: click a grid cell, then press a key to pin that pitch to the cell">Keys</button>""",
"B toolbar")

# ---------- C. seq state: sparse per-cell meta maps ----------
rep(
"""  velocity:{}
};""",
"""  velocity:{},
  // Per-cell voice override and pinned note, both sparse maps of
  // {rowId: {stepIndex: value}} -- a plain row costs nothing, and files
  // saved before these existed simply load with both empty. cellVoice
  // holds a voiceId (a clone in the row voice's family, chosen from the
  // cell's right-click menu) played INSTEAD of the row's voice on that one
  // step; cellNote holds a frequency in Hz (set from the Keys panel) that
  // retunes whichever voice the step resolves to.
  cellVoice:{},
  cellNote:{}
};""",
"C seq state")

# ---------- D. triggerRowStep: resolve override + note ----------
rep(
"""function triggerRowStep(row, idx, time){
  const pat=seq.pattern[row.id];
  if(pat && pat[idx] && !rowIsSilenced(row)){
    const voice=VOICES.find(v=>v.id===row.voiceId);
    if(voice){
      const baseParams=state.voices[row.voiceId];
      // Row volume and this one step's own velocity both trim the level,
      // multiplicatively -- neither is the voice's own Level, so only the
      // params passed to THIS trigger call are scaled, leaving other
      // rows/pads sharing the same voice unaffected.
      const vol=(rowVolume(row)/100)*(rowCellVelocity(row, idx)/100);
      const params=(vol===1 || !baseParams) ? baseParams : {...baseParams, level:(baseParams.level||0)*vol};
      voice.trigger(params, time);
    }
  }""",
"""function triggerRowStep(row, idx, time){
  const pat=seq.pattern[row.id];
  if(pat && pat[idx] && !rowIsSilenced(row)){
    // A per-cell voice override (set from the cell's right-click menu)
    // replaces the row's voice for this one step; if the override points at
    // a voice that no longer exists (its clone was deleted), fall back to
    // the row's own voice rather than dropping the hit.
    const ovMap=seq.cellVoice[row.id];
    const ovId=ovMap && ovMap[idx];
    const voice=(ovId && VOICES.find(v=>v.id===ovId)) || VOICES.find(v=>v.id===row.voiceId);
    if(voice){
      const baseParams=state.voices[voice.id];
      // Row volume and this one step's own velocity both trim the level,
      // multiplicatively -- neither is the voice's own Level, so only the
      // params passed to THIS trigger call are scaled, leaving other
      // rows/pads sharing the same voice unaffected.
      const vol=(rowVolume(row)/100)*(rowCellVelocity(row, idx)/100);
      let params=(vol===1 || !baseParams) ? baseParams : {...baseParams, level:(baseParams.level||0)*vol};
      const noteMap=seq.cellNote[row.id];
      const noteFreq=noteMap && noteMap[idx];
      if(noteFreq) params=applyNoteToParams(voice, params, noteFreq);
      voice.trigger(params, time);
    }
  }""",
"D triggerRowStep")

# ---------- E/F. remap cell meta on group-structure rebuild ----------
rep(
"""  seq.pattern[row.id]=next;
}""",
"""  seq.pattern[row.id]=next;
  seqRemapCellMeta(row.id, oldGroupSlots, newGroupSlots);
}

// Keeps a row's sparse per-cell voice/note maps aligned with its pattern
// through a group-structure change, using the same per-group keep-what-fits
// walk as the pattern rebuild above -- an override on beat 3 slot 2 stays on
// beat 3 slot 2 even when beat 1 grew or shrank underneath it.
function seqRemapCellMeta(rowId, oldGroupSlots, newGroupSlots){
  ['cellVoice','cellNote'].forEach(kind=>{
    const old=seq[kind][rowId];
    if(!old || !Object.keys(old).length) return;
    const oldBounds=seqGroupBoundaries(oldGroupSlots);
    const next={};
    let pos=0;
    newGroupSlots.forEach((newCount, g)=>{
      const oldCount=oldGroupSlots[g]||0;
      const oldStart=oldBounds[g]||0;
      for(let i=0;i<newCount;i++){
        if(i<oldCount && old[oldStart+i]!=null) next[pos]=old[oldStart+i];
        pos++;
      }
    });
    seq[kind][rowId]=next;
  });
}""",
"E rebuild remap")

# ---------- G. cell creation: active cell, meta style, context menu ----------
rep(
"""        if(pat[i]) btn.classList.add('on');
        seqApplyCellVelStyle(btn, row, i);
        btn.addEventListener('pointerdown', (e)=>{""",
"""        if(pat[i]) btn.classList.add('on');
        seqApplyCellVelStyle(btn, row, i);
        seqApplyCellMetaStyle(btn, row, i);
        if(seqActiveCell && seqActiveCell.rowId===row.id && seqActiveCell.col===i) btn.classList.add('cell-active');
        btn.addEventListener('contextmenu', (e)=>{
          e.preventDefault();
          e.stopPropagation(); // the row header's own context menu must not also open
          seqOpenCellMenu(row, i, e.clientX, e.clientY);
        });
        btn.addEventListener('pointerdown', (e)=>{
          if(e.button===2) return; // right-click is the context menu's, not a toggle/paint
          seqSetActiveCell(row.id, i);""",
"G cell creation")

# ---------- H. rowPasteGroup: pasted range drops stale cell meta ----------
rep(
"""  for(let i=0;i<rowClipboard.slotCount;i++){
    seq.pattern[row.id][start+i]=!!rowClipboard.values[i];
    vel[start+i]=(rowClipboard.velocities && rowClipboard.velocities[i]!=null) ? rowClipboard.velocities[i] : 100;
  }
  renderSequencer();
}""",
"""  const cvMap=seq.cellVoice[row.id], cnMap=seq.cellNote[row.id];
  for(let i=0;i<rowClipboard.slotCount;i++){
    seq.pattern[row.id][start+i]=!!rowClipboard.values[i];
    vel[start+i]=(rowClipboard.velocities && rowClipboard.velocities[i]!=null) ? rowClipboard.velocities[i] : 100;
    // The clipboard's group knows nothing about the target's old per-cell
    // overrides/notes -- clear them so the pasted stretch plays what was
    // copied, not a mix of both.
    if(cvMap) delete cvMap[start+i];
    if(cnMap) delete cnMap[start+i];
  }
  renderSequencer();
}""",
"H rowPasteGroup")

# ---------- I. seqAddRow / seqDeleteRow ----------
rep(
"""  seq.pattern[id]=new Array(SEQ_STEPS).fill(false);
  seq.velocity[id]=new Array(SEQ_STEPS).fill(100);
  renderSequencer();
}""",
"""  seq.pattern[id]=new Array(SEQ_STEPS).fill(false);
  seq.velocity[id]=new Array(SEQ_STEPS).fill(100);
  seq.cellVoice[id]={};
  seq.cellNote[id]={};
  renderSequencer();
}""",
"I addRow")

rep(
"""  delete seq.pattern[rowId];
  delete seq.velocity[rowId];
  delete seqSyncRuntime[rowId];""",
"""  delete seq.pattern[rowId];
  delete seq.velocity[rowId];
  delete seq.cellVoice[rowId];
  delete seq.cellNote[rowId];
  if(seqActiveCell && seqActiveCell.rowId===rowId) seqActiveCell=null;
  delete seqSyncRuntime[rowId];""",
"I deleteRow")

# ---------- J. Clear button also clears cell meta ----------
rep(
"""seqClearBtn.addEventListener('click', ()=>{
  seq.rows.forEach(row=>{
    seq.pattern[row.id].fill(false);
    if(seq.velocity[row.id]) seq.velocity[row.id].fill(100);
  });
  document.querySelectorAll('.step').forEach(el=>{
    el.classList.remove('on');
    el.style.setProperty('--cell-vel', '1.000');
  });
});""",
"""seqClearBtn.addEventListener('click', ()=>{
  seq.rows.forEach(row=>{
    seq.pattern[row.id].fill(false);
    if(seq.velocity[row.id]) seq.velocity[row.id].fill(100);
    seq.cellVoice[row.id]={};
    seq.cellNote[row.id]={};
  });
  document.querySelectorAll('.step').forEach(el=>{
    el.classList.remove('on');
    el.style.setProperty('--cell-vel', '1.000');
    el.classList.remove('has-cellmeta');
    el.title='';
  });
});""",
"J clear")

# ---------- K. main feature block, after the context-menu helpers ----------
rep(
"""document.addEventListener('keydown', (e)=>{
  if(e.key==='Escape') closeContextMenu();
});

document.getElementById('seqTheory').textContent=""",
"""document.addEventListener('keydown', (e)=>{
  if(e.key==='Escape') closeContextMenu();
});

/* ---------- per-cell selection, copy/paste, voice override, pinned note ---------- */
// The "active cell" is simply the last step cell clicked or right-clicked,
// shown with an outline. It's what cell copy/paste and the note keyboard
// act on -- both need a target, and "the one you just touched" is the only
// selection model that costs zero extra gestures.
let seqActiveCell=null;   // {rowId, col} or null
let cellClipboard=null;   // {on, velocity, cellVoice, cellNote} -- one cell's full state

function seqFindCellEl(rowId, col){
  return document.querySelector('.step[data-row="'+rowId+'"][data-col="'+col+'"]');
}

function seqSetActiveCell(rowId, col){
  if(seqActiveCell){
    const prev=seqFindCellEl(seqActiveCell.rowId, seqActiveCell.col);
    if(prev) prev.classList.remove('cell-active');
  }
  seqActiveCell={rowId, col};
  const el=seqFindCellEl(rowId, col);
  if(el) el.classList.add('cell-active');
}

// A cell's corner dot + tooltip: on when the cell carries a voice override
// and/or a pinned note, naming both in the title so hovering explains the dot.
function seqApplyCellMetaStyle(btn, row, i){
  const ov=seq.cellVoice[row.id] && seq.cellVoice[row.id][i];
  const note=seq.cellNote[row.id] && seq.cellNote[row.id][i];
  btn.classList.toggle('has-cellmeta', !!(ov||note));
  let t='';
  if(ov){
    const v=VOICES.find(x=>x.id===ov);
    t+=(v ? v.name : ov);
  }
  if(note) t+=(t?' \\u00b7 ':'')+freqToNoteName(note);
  if(t) btn.title=t; else btn.removeAttribute('title');
}

const NOTE_NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
function freqToNoteName(f){
  const midi=Math.round(69+12*Math.log2(f/440));
  return NOTE_NAMES[((midi%12)+12)%12]+(Math.floor(midi/12)-1);
}
function midiToFreq(m){ return 440*Math.pow(2,(m-69)/12); }

function seqCopyActiveCell(){
  if(!seqActiveCell){ showHint('Click a cell first.'); return; }
  const {rowId, col}=seqActiveCell;
  if(!seq.pattern[rowId]) return;
  const vel=seq.velocity[rowId]||[];
  cellClipboard={
    on: !!seq.pattern[rowId][col],
    velocity: (vel[col]!=null) ? vel[col] : 100,
    cellVoice: (seq.cellVoice[rowId]||{})[col] || null,
    cellNote: (seq.cellNote[rowId]||{})[col] || null
  };
  showHint('Cell copied.');
}

function seqPasteActiveCell(){
  if(!cellClipboard){ showHint('Nothing copied yet -- Ctrl+C on a cell first.'); return; }
  if(!seqActiveCell){ showHint('Click a cell first.'); return; }
  const {rowId, col}=seqActiveCell;
  const row=seq.rows.find(r=>r.id===rowId);
  if(!row || !seq.pattern[rowId] || col>=seq.pattern[rowId].length) return;
  seq.pattern[rowId][col]=cellClipboard.on;
  (seq.velocity[rowId]||(seq.velocity[rowId]=[]))[col]=cellClipboard.velocity;
  const cv=(seq.cellVoice[rowId]||(seq.cellVoice[rowId]={}));
  // A copied override can land on any row -- the trigger path plays the
  // override voice with its OWN params, so it stays correct cross-row. It's
  // only dropped if that voice has since been deleted from the rack.
  if(cellClipboard.cellVoice && VOICES.some(v=>v.id===cellClipboard.cellVoice)) cv[col]=cellClipboard.cellVoice;
  else delete cv[col];
  const cn=(seq.cellNote[rowId]||(seq.cellNote[rowId]={}));
  if(cellClipboard.cellNote) cn[col]=cellClipboard.cellNote;
  else delete cn[col];
  const btn=seqFindCellEl(rowId, col);
  if(btn){
    btn.classList.toggle('on', cellClipboard.on);
    seqApplyCellVelStyle(btn, row, col);
    seqApplyCellMetaStyle(btn, row, col);
  }
  showHint('Cell pasted.');
}

// Ctrl/Cmd+C and Ctrl/Cmd+V act on the active cell -- but never while the
// user is typing in a field, and Ctrl+C is only claimed when no page text is
// selected, so copying text out of the theory panels still works normally.
document.addEventListener('keydown', (e)=>{
  const t=e.target;
  if(t && (t.tagName==='INPUT' || t.tagName==='TEXTAREA' || t.isContentEditable)) return;
  if(!(e.ctrlKey||e.metaKey) || e.altKey) return;
  if(e.key==='c' || e.key==='C'){
    if(seqActiveCell && !String(window.getSelection())){ e.preventDefault(); seqCopyActiveCell(); }
  }else if(e.key==='v' || e.key==='V'){
    if(seqActiveCell){ e.preventDefault(); seqPasteActiveCell(); }
  }
});

// Every voice in the same engine family as voiceId: the base stock voice
// plus all of its clones. That's the population of a cell's right-click
// menu -- a cymbal row offers only cymbal variants, a tom row only toms.
function seqVoiceFamily(voiceId){
  const v=VOICES.find(x=>x.id===voiceId);
  if(!v) return [];
  const baseId=v.isClone ? v.clonedFrom : v.id;
  return VOICES.filter(x=> (x.isClone ? x.clonedFrom : x.id)===baseId);
}

function seqSetCellVoice(row, i, voiceId){
  const map=seq.cellVoice[row.id]||(seq.cellVoice[row.id]={});
  if(voiceId) map[i]=voiceId; else delete map[i];
  const btn=seqFindCellEl(row.id, i);
  if(btn) seqApplyCellMetaStyle(btn, row, i);
}

function seqSetCellNote(row, i, freq){
  const map=seq.cellNote[row.id]||(seq.cellNote[row.id]={});
  if(freq){
    map[i]=freq;
    // Pinning a note to a silent cell almost always means "play this here" --
    // turn the step on so the note is audible without a second click.
    if(seq.pattern[row.id] && !seq.pattern[row.id][i]){
      seq.pattern[row.id][i]=true;
      const b=seqFindCellEl(row.id, i);
      if(b) b.classList.add('on');
    }
  }else{
    delete map[i];
  }
  const btn=seqFindCellEl(row.id, i);
  if(btn) seqApplyCellMetaStyle(btn, row, i);
}

function seqOpenCellMenu(row, i, x, y){
  seqSetActiveCell(row.id, i);
  const fam=seqVoiceFamily(row.voiceId);
  const cur=(seq.cellVoice[row.id]||{})[i]||null;
  const rowVoice=VOICES.find(v=>v.id===row.voiceId);
  const items=[];
  items.push({
    label:(cur ? '' : '\\u2713 ')+'Row default ('+(rowVoice ? rowVoice.name : row.voiceId)+')',
    onSelect:()=> seqSetCellVoice(row, i, null)
  });
  fam.forEach(v=>{
    if(v.id===row.voiceId) return;
    items.push({
      label:(cur===v.id ? '\\u2713 ' : '')+v.name,
      onSelect:()=> seqSetCellVoice(row, i, v.id)
    });
  });
  if(fam.length<=1){
    items.push({label:'Clone this instrument in the rack to add variants', disabled:true, onSelect:()=>{}});
  }
  const note=(seq.cellNote[row.id]||{})[i];
  items.push({label:'Set note\\u2026 (opens keyboard)', onSelect:()=> seqOpenKeys()});
  if(note) items.push({label:'Clear note ('+freqToNoteName(note)+')', onSelect:()=> seqSetCellNote(row, i, null)});
  items.push({label:'Copy cell', onSelect:seqCopyActiveCell});
  items.push({label:'Paste cell', disabled:!cellClipboard, onSelect:seqPasteActiveCell});
  openContextMenu(x, y, items);
}

// Sparse save shape for one of the two per-cell maps: only rows that
// actually carry entries, undefined when nothing does, so untouched
// projects serialize byte-identical to before these features existed.
function seqCollectCellMeta(kind){
  const out={};
  seq.rows.forEach(r=>{
    const m=seq[kind][r.id];
    if(m && Object.keys(m).length) out[r.id]={...m};
  });
  return Object.keys(out).length ? out : undefined;
}

/* ---------- note keyboard (SVG piano) ---------- */
// A two-octave clickable piano drawn as inline SVG. Pressing a key pins
// that pitch to the ACTIVE cell (and turns the cell on), then auditions
// exactly what the cell will play -- override voice included. How a pitch
// lands on a voice is per-engine (see applyNoteToParams): KS gets the
// frequency directly, kick/tom transpose their whole sweep, cymbal/clicks
// retune playback rate, and so on, always clamped to that voice's own
// slider ranges.
const keysPanel=document.createElement('div');
keysPanel.id='keysPanel';
keysPanel.hidden=true;
document.body.appendChild(keysPanel);
let keysOctave=3; // leftmost octave shown

function applyNoteToParams(voice, params, freq){
  const p={...(params||{})};
  const base=voice.isClone ? voice.clonedFrom : voice.id;
  const clamp=(pid, val)=>{
    const def=(voice.params||[]).find(d=>d.id===pid);
    p[pid]=def ? Math.min(def.max, Math.max(def.min, val)) : val;
  };
  switch(base){
    case 'ks':
      clamp('frequency', freq);
      break;
    case 'kick':
    case 'tom': {
      // Transpose the whole pitch sweep: the note sets where the drum LANDS
      // (endFreq), and startFreq scales by the same ratio so the sweep's
      // character survives the retune.
      const end=p.endFreq||50;
      const ratio=freq/end;
      clamp('endFreq', freq);
      clamp('startFreq', (p.startFreq||150)*ratio);
      break;
    }
    case 'snare': {
      const t1=p.tone1||190;
      const ratio=freq/t1;
      clamp('tone1', freq);
      clamp('tone2', (p.tone2||330)*ratio);
      break;
    }
    case 'cowbell':
      clamp('freq1', freq);
      break;
    case 'hihat':
      clamp('fundamental', freq);
      break;
    case 'chaos':
    case 'clap':
      clamp('centerFreq', freq);
      break;
    case 'cymbal':
    case 'click1':
    case 'click2':
      // These expose a playback-rate style Pitch knob rather than a
      // frequency -- treat middle C as rate 1.0.
      clamp('pitch', freq/261.63);
      break;
  }
  return p;
}

function seqRenderKeys(){
  const OCTAVES=2, WK_W=34, WK_H=110, BK_W=20, BK_H=66;
  const totalW=OCTAVES*7*WK_W;
  const whiteSemis=[0,2,4,5,7,9,11];
  const blackSemis={1:0, 3:1, 6:3, 8:4, 10:5}; // semitone -> index of the white key it sits after
  let svg='<svg xmlns="http://www.w3.org/2000/svg" width="'+totalW+'" height="'+WK_H+'" viewBox="0 0 '+totalW+' '+WK_H+'">';
  for(let o=0;o<OCTAVES;o++){
    for(let w=0;w<7;w++){
      const midi=(keysOctave+1+o)*12 + whiteSemis[w];
      const x=(o*7+w)*WK_W;
      svg+='<rect class="pk-white" data-midi="'+midi+'" x="'+x+'" y="0" width="'+WK_W+'" height="'+WK_H+'" rx="3" fill="#f4f1ec" stroke="#222"/>';
      if(whiteSemis[w]===0){
        svg+='<text x="'+(x+WK_W/2)+'" y="'+(WK_H-8)+'" text-anchor="middle" font-size="10" fill="#555" pointer-events="none">C'+(keysOctave+o)+'</text>';
      }
    }
  }
  for(let o=0;o<OCTAVES;o++){
    for(const semi in blackSemis){
      const midi=(keysOctave+1+o)*12 + (+semi);
      const x=(o*7+blackSemis[semi]+1)*WK_W - BK_W/2;
      svg+='<rect class="pk-black" data-midi="'+midi+'" x="'+x+'" y="0" width="'+BK_W+'" height="'+BK_H+'" rx="2" fill="#1a1a1e" stroke="#000"/>';
    }
  }
  svg+='</svg>';
  keysPanel.innerHTML=
    '<div class="keys-head">'+
      '<span class="keys-title">Note Keyboard</span>'+
      '<button type="button" class="keys-oct" id="keysOctDown">&minus; Oct</button>'+
      '<span class="keys-oct-val">C'+keysOctave+' \\u2013 B'+(keysOctave+1)+'</span>'+
      '<button type="button" class="keys-oct" id="keysOctUp">+ Oct</button>'+
      '<button type="button" class="keys-close" id="keysClose" aria-label="Close the note keyboard">\\u00d7</button>'+
      '<span class="keys-hint">Click a grid cell, then press a key: the note pins to that cell, the cell turns on, and the hit plays at that pitch.</span>'+
    '</div>'+svg;
  keysPanel.querySelector('#keysOctDown').addEventListener('click', ()=>{ keysOctave=Math.max(0, keysOctave-1); seqRenderKeys(); });
  keysPanel.querySelector('#keysOctUp').addEventListener('click', ()=>{ keysOctave=Math.min(7, keysOctave+1); seqRenderKeys(); });
  keysPanel.querySelector('#keysClose').addEventListener('click', ()=> seqCloseKeys());
  keysPanel.querySelectorAll('[data-midi]').forEach(el=>{
    el.addEventListener('pointerdown', (e)=>{
      e.preventDefault();
      seqKeyPressed(+el.dataset.midi, el);
    });
  });
}

function seqKeyPressed(midi, el){
  el.classList.add('pk-down');
  setTimeout(()=> el.classList.remove('pk-down'), 120);
  if(!seqActiveCell){ showHint('Click a grid cell first -- the note pins to the active cell.'); return; }
  const row=seq.rows.find(r=>r.id===seqActiveCell.rowId);
  if(!row) return;
  const col=seqActiveCell.col;
  const freq=midiToFreq(midi);
  seqSetCellNote(row, col, freq);
  // Audition exactly what this cell will now play, override voice included.
  const ovId=(seq.cellVoice[row.id]||{})[col];
  const voice=(ovId && VOICES.find(v=>v.id===ovId)) || VOICES.find(v=>v.id===row.voiceId);
  if(voice && ctx){
    voice.trigger(applyNoteToParams(voice, state.voices[voice.id], freq));
  }
}

const seqKeysBtn=document.getElementById('seqKeysBtn');
function seqOpenKeys(){ keysPanel.hidden=false; seqRenderKeys(); seqKeysBtn.classList.add('active'); }
function seqCloseKeys(){ keysPanel.hidden=true; seqKeysBtn.classList.remove('active'); }
seqKeysBtn.addEventListener('click', ()=>{ if(keysPanel.hidden) seqOpenKeys(); else seqCloseKeys(); });

document.getElementById('seqTheory').textContent=""",
"K feature block")

# ---------- L. save: include cell meta ----------
rep(
"""      velocity:Object.fromEntries(rowIds.map(id=>[id, (seq.velocity[id]||new Array(seq.pattern[id].length).fill(100)).slice()]))
    },""",
"""      velocity:Object.fromEntries(rowIds.map(id=>[id, (seq.velocity[id]||new Array(seq.pattern[id].length).fill(100)).slice()])),
      // Sparse per-cell voice overrides / pinned notes -- omitted entirely
      // when no cell carries either, so older tooling and untouched
      // projects see the exact same file shape as before.
      cellVoice:seqCollectCellMeta('cellVoice'),
      cellNote:seqCollectCellMeta('cellNote')
    },""",
"L save")

# ---------- M. load: restore cell meta ----------
rep(
"""    const savedVel=s.velocity && s.velocity[r.id];
    seq.velocity[r.id]=Array.isArray(savedVel) ? savedVel.slice(0, n) : [];
    while(seq.velocity[r.id].length<n) seq.velocity[r.id].push(100);
  });""",
"""    const savedVel=s.velocity && s.velocity[r.id];
    seq.velocity[r.id]=Array.isArray(savedVel) ? savedVel.slice(0, n) : [];
    while(seq.velocity[r.id].length<n) seq.velocity[r.id].push(100);
  });
  // Per-cell voice overrides and pinned notes: absent entirely in files
  // saved before these existed, and entries are dropped rather than kept if
  // they point past the row's length or at a voice this file didn't bring
  // along (applyVoicesState already ran above, so VOICES is final here).
  seq.cellVoice={};
  seq.cellNote={};
  seq.rows.forEach(r=>{
    const n=rowSteps(r);
    const sv=s.cellVoice && s.cellVoice[r.id];
    if(sv && typeof sv==='object'){
      const m={};
      for(const k in sv){
        const i=+k;
        if(i>=0 && i<n && VOICES.some(v=>v.id===sv[k])) m[i]=sv[k];
      }
      if(Object.keys(m).length) seq.cellVoice[r.id]=m;
    }
    const sn=s.cellNote && s.cellNote[r.id];
    if(sn && typeof sn==='object'){
      const m={};
      for(const k in sn){
        const i=+k;
        const f=+sn[k];
        if(i>=0 && i<n && isFinite(f) && f>0) m[i]=f;
      }
      if(Object.keys(m).length) seq.cellNote[r.id]=m;
    }
  });
  seqActiveCell=null;""",
"M load")

# ---------- N. new project reset ----------
rep(
"""  seq.pattern={};
  seq.velocity={};
  seq.rows.forEach(r=>{
    seq.pattern[r.id]=new Array(SEQ_STEPS).fill(false);
    seq.velocity[r.id]=new Array(SEQ_STEPS).fill(100);
  });
  seqSyncRuntime={};""",
"""  seq.pattern={};
  seq.velocity={};
  seq.cellVoice={};
  seq.cellNote={};
  seqActiveCell=null;
  seq.rows.forEach(r=>{
    seq.pattern[r.id]=new Array(SEQ_STEPS).fill(false);
    seq.velocity[r.id]=new Array(SEQ_STEPS).fill(100);
  });
  seqSyncRuntime={};""",
"N reset")

if fails:
    print("PATCH FAILURES:")
    for f in fails: print(" -", f)
    sys.exit(1)
open(p,'w').write(src)
print(f"OK: {orig_len} -> {len(src)} bytes")
