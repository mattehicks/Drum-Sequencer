import sys
p='C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
src=open(p).read()
fails=[]
def rep(old,new,label):
    global src
    if src.count(old)!=1: fails.append(f"{label}: {src.count(old)} matches"); return
    src=src.replace(old,new)

# ---- CSS ----
rep(""".seq-row-block.seq-row-silenced{opacity:0.4;}""",
""".seq-row-block.seq-row-silenced{opacity:0.4;}
/* Performance groups: A/B row assignment + transport switcher. */
.seq-perf-btn{min-width:34px;}
.seq-perf-btn.active{border-color:var(--accent,#7ad0ff);color:var(--accent,#7ad0ff);}
.seq-grp-btn.active{border-color:#e9c46a;color:#e9c46a;}""",
"css")

# ---- toolbar buttons after Keys ----
rep("""      <button id="seqKeysBtn" class="seq-clear" type="button" title="Open the note keyboard: click a grid cell, then press a key to pin that pitch to the cell">Keys</button>""",
"""      <button id="seqKeysBtn" class="seq-clear" type="button" title="Open the note keyboard: click a grid cell, then press a key to pin that pitch to the cell">Keys</button>
      <button id="seqPerfA" class="seq-clear seq-perf-btn" type="button" title="Play only rows assigned to group A (plus unassigned rows). Shortcut: [">A</button>
      <button id="seqPerfB" class="seq-clear seq-perf-btn" type="button" title="Play only rows assigned to group B (plus unassigned rows). Shortcut: ]">B</button>
      <button id="seqPerfAB" class="seq-clear seq-perf-btn active" type="button" title="Play every row regardless of group. Shortcut: \\">AB</button>""",
"toolbar")

# ---- silencing: perf gate joins mute/solo ----
rep("""function rowIsSilenced(row){
  if(row.muted) return true;
  return seq.rows.some(r=>r.solo) && !row.solo;
}""",
"""function rowIsSilenced(row){
  if(row.muted) return true;
  if(seq.rows.some(r=>r.solo) && !row.solo) return true;
  // Performance groups: a row tagged A or B is silent while the other group
  // is selected; untagged rows (the default) play in every group, so a kit's
  // core can run underneath while A/B parts trade places.
  if(row.perf && seq.perfActive!=='AB' && row.perf!==seq.perfActive) return true;
  return false;
}""",
"gate")

# ---- row flags: group cycle button before Mute ----
rep("""    const muteBtn=document.createElement('button');
    muteBtn.type='button';
    muteBtn.className='seq-mute-btn'+(row.muted?' active':'');""",
"""    const grpBtn=document.createElement('button');
    grpBtn.type='button';
    grpBtn.className='seq-flag-btn seq-grp-btn'+(row.perf?' active':'');
    grpBtn.textContent=row.perf||'AB';
    grpBtn.title=row.perf
      ? 'This row plays only in group '+row.perf+'. Click to cycle (A / B / both).'
      : 'This row plays in every group. Click to assign it to group A.';
    grpBtn.addEventListener('click', (e)=>{
      e.stopPropagation();
      row.perf = row.perf==null ? 'A' : (row.perf==='A' ? 'B' : null);
      grpBtn.textContent=row.perf||'AB';
      grpBtn.classList.toggle('active', !!row.perf);
      grpBtn.title=row.perf
        ? 'This row plays only in group '+row.perf+'. Click to cycle (A / B / both).'
        : 'This row plays in every group. Click to assign it to group A.';
      seqPerfRefreshUI();
    });
    flags.appendChild(grpBtn);
    const muteBtn=document.createElement('button');
    muteBtn.type='button';
    muteBtn.className='seq-mute-btn'+(row.muted?' active':'');""",
"row btn")

# ---- switcher logic (insert before the Keys-panel block's neighbor: reuse seqKeysBtn anchor) ----
rep("""const seqKeysBtn=document.getElementById('seqKeysBtn');""",
"""/* ---------- performance group switcher ---------- */
// Live A/B arrangement switching: the transport keeps running and the
// playhead never resets -- selecting a group only changes which rows sound
// from the next scheduled step on, exactly like a mute scene. Rows carry an
// optional A/B tag (the AB button on each row's flag line); untagged rows
// play everywhere.
seq.perfActive='AB';
const seqPerfBtns={A:document.getElementById('seqPerfA'), B:document.getElementById('seqPerfB'), AB:document.getElementById('seqPerfAB')};
function seqPerfRefreshUI(){
  for(const k in seqPerfBtns) seqPerfBtns[k].classList.toggle('active', seq.perfActive===k);
  updateRowSilencedStyles(); // same cheap pass mute/solo already use
}
function seqPerfSet(which){
  if(seq.perfActive===which) return;
  seq.perfActive=which;
  seqPerfRefreshUI();
}
for(const k in seqPerfBtns) seqPerfBtns[k].addEventListener('click', ()=> seqPerfSet(k));
document.addEventListener('keydown', (e)=>{
  const t=e.target;
  if(t && (t.tagName==='INPUT' || t.tagName==='TEXTAREA' || t.isContentEditable)) return;
  if(e.ctrlKey||e.metaKey||e.altKey) return;
  if(e.key==='[') seqPerfSet('A');
  else if(e.key===']') seqPerfSet('B');
  else if(e.key==='\\\\') seqPerfSet('AB');
});

const seqKeysBtn=document.getElementById('seqKeysBtn');""",
"switcher")

# ---- save ----
rep("""        muted:r.muted ? true : undefined,
        solo:r.solo ? true : undefined
      })),""",
"""        muted:r.muted ? true : undefined,
        solo:r.solo ? true : undefined,
        perf:r.perf || undefined
      })),""",
"save rows")
rep("""      pattern:Object.fromEntries(rowIds.map(id=>[id, seq.pattern[id].slice()])),""",
"""      perfActive:(seq.perfActive && seq.perfActive!=='AB') ? seq.perfActive : undefined,
      pattern:Object.fromEntries(rowIds.map(id=>[id, seq.pattern[id].slice()])),""",
"save active")

# ---- load ----
rep("""    if(r.muted) row.muted=true;
    if(r.solo) row.solo=true;
    return row;""",
"""    if(r.muted) row.muted=true;
    if(r.solo) row.solo=true;
    if(r.perf==='A' || r.perf==='B') row.perf=r.perf;
    return row;""",
"load rows")
rep("""      if(Object.keys(m).length) seq.cellNote[r.id]=m;
    }
  });
  seqActiveCell=null;""",
"""      if(Object.keys(m).length) seq.cellNote[r.id]=m;
    }
  });
  seqActiveCell=null;
  seq.perfActive=(s.perfActive==='A' || s.perfActive==='B') ? s.perfActive : 'AB';
  if(typeof seqPerfRefreshUI==='function') setTimeout(seqPerfRefreshUI, 0);""",
"load active")

# ---- new project reset ----
rep("""  seq.cellVoice={};
  seq.cellNote={};
  seqActiveCell=null;""",
"""  seq.cellVoice={};
  seq.cellNote={};
  seqActiveCell=null;
  seq.perfActive='AB';
  if(typeof seqPerfRefreshUI==='function') setTimeout(seqPerfRefreshUI, 0);""",
"reset")

if fails:
    print("FAILURES:", fails); sys.exit(1)
open(p,'w').write(src)
print("OK", len(src))
