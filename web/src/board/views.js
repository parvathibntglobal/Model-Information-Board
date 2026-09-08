// Board + blogs view builders, ported verbatim from the SEO demo.
// They return HTML strings; BoardView renders them and wires clicks to the router.
import { DB } from './db'

const byS = (arr,s) => arr.find(x=>x.slug===s);
const ST = {v:['ev-v','verified'], c:['ev-c','contested'], s:['ev-n','single report'],
            n:['ev-n','not discussed']};
// A state we were not given renders as 'not discussed' rather than throwing:
// an unknown state is an absence, and absence is a real value on this board.
const stOf = (k) => ST[k] || ST.n;

function crumb(parts){
  return '<p class="crumb">'+parts.map(([t,h])=>h?`<a data-go="${h}">${t}</a>`:t).join('<i>/</i>')+'</p>';
}
function ranked(rows){
  if(!rows || !rows.length) return '';
  return '<div class="ranked">'+rows.map((r,i)=>{
    const [cls,lbl]=stOf(r.s);
    return `<div class="rank${r.dim?' dim':''}"><span class="n">${String(i+1).padStart(2,'0')}</span>
      <div><b>${r.m}</b><span class="vend">${r.v}</span><p>${r.d}</p></div>
      <div class="right"><span class="price">${r.p}</span><span class="st ${cls}">${r.e} · ${lbl}</span></div></div>`;
  }).join('')+'</div>';
}
function conds(list){
  if(!list || !list.length) return '';
  return '<ul class="conds">'+list.map(([a,b])=>`<li><b>${a}</b><span>${b}</span></li>`).join('')+'</ul>';
}
function quotes(qs){
  if(!qs || !qs.length) return '';
  return '<div class="quotes">'+qs.map(([q,who,src,c])=>
    `<div class="qb${c?' c':''}"><q>${q}</q><cite>${who} · ${src} · <u>open the source</u></cite></div>`).join('')+'</div>';
}
function related(list){
  if(!list || !list.length) return '';
  return '<div class="related">'+list.map(([h,t])=>`<a data-go="${h}">${t}</a>`).join('')+'</div>';
}
function sec(eyebrow,h2,intro,inner){
  // An empty `inner` means the pipeline produced nothing for this block. Render
  // NOTHING rather than a heading over a void: the demo's `pick`, `conds`,
  // `nots` and `lim` blocks were written by hand, and a classifier does not
  // produce them. A fabricated pick is the synthesised claim rule 3 forbids,
  // and an invented condition is worse than a missing one because it reads as
  // a finding. So the block waits for an editor instead of guessing.
  if(!inner || !String(inner).trim()) return '';
  return `<div class="shell sec"><div class="sec-h">${eyebrow?`<span class="eyebrow">${eyebrow}</span>`:''}
    ${h2?`<h2>${h2}</h2>`:''}${intro?`<p>${intro}</p>`:''}</div>${inner}</div>`;
}
function card(x, route){
  const [cls,lbl]=stOf(x.st);
  return `<div class="icard" data-go="${route}:${x.slug}"><b>${x.name}</b><p>${x.card}</p>
    <div class="meta"><span class="${cls}">${x.ev} · ${lbl}</span><span>${x.vol}</span></div></div>`;
}
function mcard(x){
  return `<div class="icard" data-go="metric:${x.slug}"><b>${x.name}</b><p>${x.card}</p>
    <div class="meta"><span>unit · ${x.unit}</span><span>${x.vol}</span></div></div>`;
}

/* ---------- views ---------- */
function vBoard(tab){
  tab = tab||'best';
  const empty = '<p class="muted" style="padding:8px 0">Nothing here yet.</p>';
  const panes = {
    best: {intro:'Jobs with enough reports to rank. Each opens a page that names the cheapest model engineers report doing it, the conditions that change the answer, and the criticisms that did not disqualify it.',
      grid: DB.jobs.length ? DB.jobs.map(j=>card(j,'job')).join('') : empty},
    cap: {intro:'A capability means one thing across every model page. These are the definitions the board rules by — written so an answer engine can quote them, and so two claims can be compared without arguing about words.',
      grid: DB.caps.length ? DB.caps.map(c=>card(c,'cap')).join('') : empty},
    met: {intro:'The axes recorded on every model. Each page states the unit, where the figure came from, and the thing the number cannot tell you — which is usually more useful than the number.',
      grid: DB.mets.length ? DB.mets.map(m=>mcard(m)).join('') : empty}
  };
  const p = panes[tab];
  return `<div class="shell phead">${crumb([['Board',null]])}
    <h1>The board</h1>
    <p class="sub">Three ways into the same evidence. <b>Best for</b> answers a job.
    <b>Capabilities</b> defines what a claim means, so a claim on one model page can be compared with a
    claim on another. <b>Metrics</b> are the axes, and what each one refuses to average.</p></div>
    <div class="shell">
      <div class="tabs" role="tablist">
        <button role="tab" aria-selected="${tab==='best'}" data-tab="best">Best for</button>
        <button role="tab" aria-selected="${tab==='cap'}" data-tab="cap">Capabilities</button>
        <button role="tab" aria-selected="${tab==='met'}" data-tab="met">Metrics</button>
      </div>
      <p class="muted" style="max-width:70ch;margin-bottom:20px;line-height:1.6">${p.intro}</p>
      <div class="igrid">${p.grid}</div>
    </div>`;
}

function vJob(slug){
  const j = byS(DB.jobs,slug); if(!j) return vBoard('best');
  // `pick` names ONE model the winner, and that is an editorial judgement no
  // classifier makes. Absent by default, so the block below is skipped rather
  // than filled with a guess.
  const [w,pr,ev,why] = j.pick || [];
  return `<div class="shell phead">${crumb([['Board','board'],['Best for','board:best'],[j.name,null]])}
    <h1>${j.h1}</h1><p class="sub">${j.sub}</p></div>
    ${j.pick ? sec('The pick','','',`<div class="defbox"><div class="l">${ev}</div>
      <p><b>${w}</b> at ${pr}.</p><p>${why}</p></div>`) : ''}
    ${sec('Every model with reports for this job','What engineers actually ran','',ranked(j.rows))}
    ${sec('Conditions that change the answer','Where the pick stops holding',
      'Most disagreements between engineers are condition mismatches rather than contradictions. These are the ones the reports keep naming.',conds(j.conds))}
    ${sec('The quotes behind the ranking','What they said, verbatim','',quotes(j.qs))}
    ${sec('Related','','',related(j.rel))}`;
}

function vCap(slug){
  const c = byS(DB.caps,slug); if(!c) return vBoard('cap');
  return `<div class="shell phead">${crumb([['Board','board'],['Capabilities','board:cap'],[c.name,null]])}
    <h1>${c.name}</h1><p class="sub">A capability the board found engineers discussing. This page is
    the definition every model page resolves against, so a report about one model can be compared with a
    report about another.</p></div>
    ${sec('','','',`<div class="defbox"><div class="l">definition</div><p>${c.d1}</p><p>${c.d2}</p></div>`)}
    ${sec('What this is not','Three things filed elsewhere',
      'Capability boundaries exist so a disagreement is a disagreement rather than two people using one word for two things.',conds(c.nots))}
    ${sec('Models with evidence','Who has been reported doing this','',ranked(c.rows))}
    ${sec('Reports','What breaks it','',quotes(c.qs))}
    ${sec('Related','','',related(c.rel))}`;
}

function vMet(slug){
  const m = byS(DB.mets,slug); if(!m) return vBoard('met');
  const head = m.cols.map((c,i)=>`<th${m.num[i]?' class="r"':''}>${c}</th>`).join('');
  const body = m.rows.map(r=>'<tr>'+r.map((v,i)=>`<td${m.num[i]?' class="r"':''}>${v}</td>`).join('')+'</tr>').join('');
  return `<div class="shell phead">${crumb([['Board','board'],['Metrics','board:met'],[m.name,null]])}
    <h1>${m.name}</h1><p class="sub">An axis the board found figures for. Every figure is shown as the
    text wrote it, with whether it was <b>stated</b> by the provider or <b>reported</b> by somebody who
    measured it — the two are never merged.</p></div>
    ${sec('','','',`<div class="defbox"><div class="l">unit · ${m.unit}</div><p>${m.d1}</p><p>${m.d2}</p></div>`)}
    ${sec('The number\u2019s limits','What this metric cannot tell you',
      'Four things that change the figure and never appear beside it.',conds(m.lim))}
    ${sec('Every model tracked','Recorded figures',
      'Each figure is copied verbatim from the evidence. A stated figure and a reported one are different facts from different sources, so they sit side by side rather than being averaged.',
      `<div class="tblwrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`)}
    ${sec('Related','','',related(m.rel))}`;
}

function vBlogs(){
  return `<div class="shell phead">${crumb([['Blogs',null]])}
    <h1>What we found while building the board</h1>
    <p class="sub">Not model reviews. Working notes from the engineers who built the pipeline — what broke,
    what the measurements said, and where our own assumptions turned out to be wrong. Every figure carries
    the population it was measured on, and every claim links to the evidence behind it.</p></div>
    <div class="shell sec"><div class="postlist">${DB.posts.length ? DB.posts.map(p=>
      `<div class="pcard${p.feat?' feat':''}" data-go="post:${p.slug}"><span class="tag">${p.tag}</span>
        <h3>${p.title}</h3><p>${p.dek}</p><p class="by">${p.by}</p></div>`).join('') : '<p class="muted" style="padding:8px 0">No posts yet.</p>'}</div>
      <p class="muted" style="margin-top:24px;max-width:70ch;line-height:1.6;font-size:.94rem">Posts are
      written against the board's own corpus. A post may cover one model, several, a job, a capability, or a
      change somebody noticed before a vendor announced it — and every figure in one is a bookmark into the
      evidence it came from.</p></div>`;
}

function vPost(slug){
  const p = byS(DB.posts,slug); if(!p) return vBlogs();
  const body = p.body.map(([t,v])=>{
    if(t==='h2') return `<h2>${v}</h2>`;
    if(t==='ul') return '<ul>'+v.map(li=>`<li>${li}</li>`).join('')+'</ul>';
    if(t==='quote') return `<blockquote>${v}</blockquote>`;
    return '<p>'+String(v).replace(/\{E(\d+)\}/g,(m,n)=>`<span class="bm" data-ev="${n}">E${n}</span>`)+'</p>';
  }).join('');
  const ev = p.ev.map(([n,q,src])=>`<div class="evrow" id="ev${n}"><span class="id">E${n}</span>
    <div><q>${q}</q><span class="src">${src}</span></div><u>open evidence →</u></div>`).join('');
  return `<div class="shell phead">${crumb([['Blogs','blogs'],[p.title.slice(0,42)+'…',null]])}
    <h1>${p.title}</h1></div>
    <div class="shell"><div class="artmeta">${p.meta.map(m=>`<span>${m}</span>`).join('')}</div>
      <article class="article"><p class="lead">${p.lead}</p>${body}</article>
      <div class="evpanel" id="evidence"><h3>Evidence behind this post</h3>
        <p class="n">Every figure above is a bookmark into one of these. Demo data in this build — in
        production each row opens the stored quote with its verified offset and a link to the source.</p>
        ${ev}</div>
      ${related(p.rel)}
    </div>`;
}
export { vBoard, vJob, vCap, vMet, vBlogs, vPost }
