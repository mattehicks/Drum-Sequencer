import sys
p='C:/Users/matte/Documents/GitHub/d20-synth-tools/V2/index.html'
src=open(p).read()
fails=[]
def rep(old,new,label):
    global src
    if src.count(old)!=1: fails.append(f"{label}: {src.count(old)} matches"); return
    src=src.replace(old,new)

# ---- rack grid: narrower columns so collapsed cards sit ~2 in the old footprint ----
rep("""  grid-template-columns:repeat(auto-fill, minmax(260px,1fr));""",
"""  grid-template-columns:repeat(auto-fill, minmax(180px,1fr));""",
"grid")

# ---- card states + the colored header strip ----
rep(""".voice-head{display:flex; align-items:center; gap:10px;}""",
""".voice-head{display:flex; align-items:center; gap:10px;}
/* Collapsible instrument cards. Every card starts collapsed: just the green
   header strip plus a slim trigger pad, at roughly half the old footprint.
   Clicking the strip expands that card to the rack's full width with its
   sliders laid out in columns; clicking again collapses it back. */
.voice-strip{
  display:flex; align-items:center; gap:8px;
  margin:-14px -14px 0;
  padding:8px 12px;
  border-radius:10px 10px 0 0;
  background:linear-gradient(90deg, rgba(88,190,130,0.30), rgba(88,190,130,0.08));
  border-bottom:1px solid rgba(88,190,130,0.45);
  cursor:pointer;
  user-select:none;
}
.voice-strip:hover{background:linear-gradient(90deg, rgba(88,190,130,0.42), rgba(88,190,130,0.14));}
.voice-strip h3{margin:0; font-size:13px; flex:1; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.voice-chevron{font-size:10px; color:rgba(160,230,190,0.9); width:10px; flex:none;}
.voice.collapsed{gap:8px;}
.voice.collapsed .voice-params, .voice.collapsed .theory{display:none;}
.voice.collapsed .pad{padding:6px 0; font-size:10px; letter-spacing:0.08em;}
.voice.expanded{grid-column:1 / -1;}
.voice.expanded .voice-params{
  display:grid;
  grid-template-columns:repeat(auto-fill, minmax(240px,1fr));
  column-gap:18px; row-gap:6px;
}""",
"css")

# ---- expansion state survives renderVoices() rebuilds ----
rep("""function buildVoiceCard(voice){
  const card=document.createElement('article');
  card.className='voice';
  card.id='voiceCard-'+voice.id;

  const head=document.createElement('div');
  head.className='voice-head';
  head.title='Right-click for options';
  const keyEl=document.createElement('span');
  keyEl.className='voice-key'; keyEl.textContent=voice.key||'\u2022';
  const h3=document.createElement('h3'); h3.textContent=voice.name;
  head.appendChild(keyEl); head.appendChild(h3);
  head.addEventListener('contextmenu', (e)=>{""",
"""const voiceCardExpanded=new Set(); // by voice id; session-only, survives rack rebuilds

function buildVoiceCard(voice){
  const card=document.createElement('article');
  card.className='voice '+(voiceCardExpanded.has(voice.id)?'expanded':'collapsed');
  card.id='voiceCard-'+voice.id;

  // The strip is the whole collapse/expand control: click toggles, and the
  // right-click options menu lives here too since the strip replaced the
  // old always-open header.
  const head=document.createElement('div');
  head.className='voice-strip';
  head.title='Click to expand/collapse \u00b7 right-click for options';
  const chev=document.createElement('span');
  chev.className='voice-chevron';
  chev.textContent=voiceCardExpanded.has(voice.id)?'\u25be':'\u25b8';
  const keyEl=document.createElement('span');
  keyEl.className='voice-key'; keyEl.textContent=voice.key||'\u2022';
  const h3=document.createElement('h3'); h3.textContent=voice.name;
  head.appendChild(chev); head.appendChild(keyEl); head.appendChild(h3);
  head.addEventListener('click', ()=>{
    const nowOpen=!voiceCardExpanded.has(voice.id);
    if(nowOpen) voiceCardExpanded.add(voice.id); else voiceCardExpanded.delete(voice.id);
    card.classList.toggle('expanded', nowOpen);
    card.classList.toggle('collapsed', !nowOpen);
    chev.textContent=nowOpen?'\u25be':'\u25b8';
  });
  head.addEventListener('contextmenu', (e)=>{""",
"builder")

if fails:
    print("FAILURES:", fails); sys.exit(1)
open(p,'w').write(src)
print("OK", len(src))
