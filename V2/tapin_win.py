import sys
p='C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
src=open(p).read()
fails=[]
def rep(old,new,label):
    global src
    if src.count(old)!=1: fails.append(f"{label}: {src.count(old)} matches"); return
    src=src.replace(old,new)

# ---- CSS ----
rep(""".seq-grp-btn.active{border-color:#e9c46a;color:#e9c46a;}""",
""".seq-grp-btn.active{border-color:#e9c46a;color:#e9c46a;}
/* Tap-in recording: arm button + the big green tap pad. */
.tapin-wrap{display:flex;align-items:center;gap:8px;}
#tapinRow{
  background:var(--panel-2,#1c1c24); color:#eee;
  border:1px solid rgba(255,255,255,0.25);
  border-radius:6px; padding:4px 6px; font-size:12px;
  max-width:110px;
}
#tapinRecBtn.active{border-color:#ff5d5d;color:#ff5d5d;}
#tapinPad{
  width:52px;height:52px;
  border-radius:50%;
  border:2px solid rgba(120,220,150,0.8);
  background:radial-gradient(circle at 35% 30%, rgba(150,240,180,0.55), rgba(50,150,90,0.85) 70%);
  box-shadow:0 3px 10px rgba(0,0,0,0.5), inset 0 -4px 8px rgba(0,0,0,0.35);
  cursor:pointer;
  touch-action:none;
  user-select:none;
  padding:0;
  flex:none;
}
#tapinPad:disabled{opacity:0.35;cursor:default;}
#tapinPad.hit{
  transform:scale(0.92);
  box-shadow:0 1px 4px rgba(0,0,0,0.5), 0 0 16px rgba(120,240,160,0.7), inset 0 -2px 6px rgba(0,0,0,0.35);
}""",
"css")

# ---- toolbar: row select + Rec + green pad, after the group switcher ----
rep("""      <button id="seqPerfAB" class="seq-clear seq-perf-btn active" type="button" title="Play every row regardless of group. Shortcut: \\">AB</button>""",
"""      <button id="seqPerfAB" class="seq-clear seq-perf-btn active" type="button" title="Play every row regardless of group. Shortcut: \\">AB</button>
      <span class="tapin-wrap">
        <select id="tapinRow" title="Which row your taps record into"></select>
        <button id="tapinRecBtn" class="seq-clear" type="button" title="Arm tap-in recording (starts playback if stopped). While armed, every tap on the green pad writes a hit into the selected row at the nearest step.">&#9210; Rec</button>
        <button id="tapinPad" type="button" disabled title="Tap here (mouse or touch) while Rec is armed -- each tap lands on the nearest step of the selected row" aria-label="Tap pad"></button>
      </span>""",
"toolbar")

# ---- module ----
rep("""const seqKeysBtn=document.getElementById('seqKeysBtn');""",
"""/* ---------- tap-in pattern recording ---------- */
// Live finger-drumming into the grid: arm Rec (playback starts if it
// wasn't running), pick a target row, and every tap on the green pad is
// quantized to the NEAREST step of that row and written into the pattern.
// Nearest -- not next -- so a slightly-early or slightly-late tap lands on
// the step you meant. The current transport position is derived from the
// scheduler's own clock (seqMasterStep/seqMasterNextTime against
// ctx.currentTime), the same clock the voices are scheduled on, so taps
// line up with what you hear, not with a UI timer. If the chosen step was
// already scheduled (you tapped late), the hit is fired immediately as a
// monitor so you still hear it this pass; otherwise the scheduler plays it
// when the step arrives, avoiding a doubled flam.
let tapinArmed=false;
const tapinRecBtn=document.getElementById('tapinRecBtn');
const tapinPad=document.getElementById('tapinPad');
const tapinRowSel=document.getElementById('tapinRow');

function tapinFillRows(){
  const cur=tapinRowSel.value;
  tapinRowSel.innerHTML='';
  seq.rows.forEach(row=>{
    const v=VOICES.find(x=>x.id===row.voiceId);
    const o=document.createElement('option');
    o.value=row.id;
    o.textContent=v ? v.name : row.voiceId;
    tapinRowSel.appendChild(o);
  });
  if(cur && seq.rows.some(r=>r.id===cur)) tapinRowSel.value=cur;
  else if(seqActiveCell && seq.rows.some(r=>r.id===seqActiveCell.rowId)) tapinRowSel.value=seqActiveCell.rowId;
}
tapinRowSel.addEventListener('focus', tapinFillRows);
tapinFillRows();

function tapinSetArmed(on){
  tapinArmed=on;
  tapinRecBtn.classList.toggle('active', on);
  tapinPad.disabled=!on;
  tapinRecBtn.innerHTML=on ? '&#9209; Rec' : '&#9210; Rec';
}
tapinRecBtn.addEventListener('click', async ()=>{
  if(tapinArmed){ tapinSetArmed(false); return; }
  tapinFillRows();
  if(!(await labEnsureAudioRunning())){ showHint('Could not start the audio engine.'); return; }
  if(!seq.playing) seqStart(); // tap-in needs a moving playhead
  tapinSetArmed(true);
  showHint('Tap-in armed: hit the green pad in time -- taps write into "'+(tapinRowSel.selectedOptions[0]||{}).textContent+'".');
});

function tapinTap(){
  if(!tapinArmed || !seq.playing || !ctx) return;
  const row=seq.rows.find(r=>r.id===tapinRowSel.value) || seq.rows[0];
  if(!row) return;
  const sps=seqSecondsPerStep();
  // Where the transport actually IS right now, as a float step index:
  // seqMasterNextTime is the time of step seqMasterStep (the next one to
  // be scheduled), so now sits (gap/sps) steps before it.
  const posFloat=seqMasterStep - (seqMasterNextTime - ctx.currentTime)/sps;
  const n=rowSteps(row);
  let idx, alreadyScheduled;
  if(rowMode(row)==='sync'){
    // Sync rows subdivide the current bar into their own n steps.
    const barFloat=((posFloat % SEQ_STEPS)+SEQ_STEPS) % SEQ_STEPS;
    idx=Math.round(barFloat/SEQ_STEPS*n) % n;
    alreadyScheduled=true; // sync-lane scheduling is bar-local; monitor to be safe
  }else{
    const g=Math.round(posFloat);
    idx=((g % n)+n) % n;
    alreadyScheduled=g < seqMasterStep; // nearest step is behind the scheduler
  }
  seq.pattern[row.id][idx]=true;
  const btn=seqFindCellEl(row.id, idx);
  if(btn) btn.classList.add('on');
  if(alreadyScheduled) triggerRowStep(row, idx); // monitor: the loop plays it from next pass
  tapinPad.classList.add('hit');
  setTimeout(()=>tapinPad.classList.remove('hit'), 90);
}
tapinPad.addEventListener('pointerdown', (e)=>{ e.preventDefault(); tapinTap(); });

const seqKeysBtn=document.getElementById('seqKeysBtn');""",
"module")

if fails:
    print("FAILURES:", fails); sys.exit(1)
open(p,'w').write(src)
print("OK", len(src))
