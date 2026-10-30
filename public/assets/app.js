
(function(){
"use strict";
var state=window.BOOKNIX;
state.books.forEach(function(b){if(b.type==="progress")b.type="wait";normSeries(b);});
function normSeries(b){if(!b.series)return;var m=/^(.*?),\s*(?:том|книга|кн\.?)\s*(\d+)\s*$/i.exec(b.series);if(m&&!b.seriesNo){b.series=m[1].trim();b.seriesNo=m[2];}if(!b.seriesNo){var t=/(?:том|книга|часть)\s*(\d+)/i.exec(b.title||"");if(t)b.seriesNo=t[1];}}
function sKey(x){return String(x||"").toLowerCase().replace(/ё/g,"е").replace(/\s+/g," ").trim();}
function allSeries(){var o={};state.books.forEach(function(b){if(b.series&&!o[sKey(b.series)])o[sKey(b.series)]=b.series;});return Object.keys(o).map(function(k){return o[k];}).sort(function(a,b){return a.localeCompare(b,"ru");});}
function seriesLabel(b){return esc(b.series)+(b.seriesNo?', книга '+esc(b.seriesNo):'');}
function seriesBooks(b){if(!b.series)return [];var k=sKey(b.series);return state.books.filter(function(x){return sKey(x.series)===k;}).sort(function(a,c){return ((parseFloat(a.seriesNo)||999)-(parseFloat(c.seriesNo)||999))||((a.added||0)-(c.added||0));});}
function seriesOrigOf(b){if(b.seriesOrig)return b.seriesOrig;var k=sKey(b.series),f=state.books.filter(function(x){return x.series&&sKey(x.series)===k&&x.seriesOrig;})[0];return f?f.seriesOrig:'';}
function seriesBlock(b){var list=seriesBooks(b);if(list.length<2)return '';var so=seriesOrigOf(b);return '<div class="series"><h3>Книги цикла «'+esc(b.series)+'»'+(so?' <span class="so">'+esc(so)+'</span>':'')+'</h3><div class="series-list">'+list.map(function(x){var inner=cover(x,92)+'<span class="n">'+(x.seriesNo?'Книга '+esc(x.seriesNo):'Без номера')+'</span><span class="st">'+esc(x.title)+'</span>';return x.id===b.id?'<div class="si cur" aria-current="true">'+inner+'</div>':'<a class="si" href="'+bookUrl(x.id)+'" data-open="'+esc(x.id)+'">'+inner+'</a>';}).join('')+'</div></div>';}
var TYPES={translation:"Мой перевод",wait:"Лист ожидания",rec:"Рекомендации"};
var BADGE={translation:"Мой перевод",progress:"Перевожу сейчас",wait:"Лист ожидания",rec:"Рекомендация"};
var MONTHS=["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"];
function fmtDate(v){var m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v||""));return m?(+m[3])+" "+MONTHS[+m[2]-1]+" "+m[1]:esc(v);}
function hasEta(b){return !!b.eta&&(b.type==="wait"||b.type==="progress");}
function etaLine(b){return hasEta(b)?'<p class="eta-line">Выход перевода — примерно <b>'+fmtDate(b.eta)+'</b></p>':'';}
var PAL=[["#2b4a6b","#0e1a2a"],["#6b2f3a","#1d0c12"],["#3f5b3a","#111c10"],["#7a5a2a","#22170a"],["#4a3b6e","#140f24"],["#2f6466","#0b1d1e"],["#6e4a3a","#1f130d"],["#384a5e","#0d131b"]];
var GEN=window.BOOKNIX.genres||{},SEO=window.BOOKNIX.seo||{};
var ui={q:(function(){try{return new URLSearchParams(location.search).get("q")||"";}catch(x){return "";}})(),genre:genreFromPath()||"",hero:0,timer:null,openId:idFromPath()};
function genreFromPath(){var m=/^\/zhanr\/([^\/]+)\/?$/.exec(location.pathname);if(!m)return null;var sl=decodeURIComponent(m[1]);for(var g in GEN){if(GEN[g].slug===sl)return g;}return null;}
function genreUrl(g){return GEN[g]?"/zhanr/"+GEN[g].slug+"/":"/";}
function gLink(g){return GEN[g]?'<a href="'+genreUrl(g)+'" data-genre="'+esc(g)+'">'+esc(g)+'</a>':esc(g);}
function idFromPath(){var m=/^\/knigi\/([^\/]+)\/?$/.exec(location.pathname);return m?decodeURIComponent(m[1]):null;}
function bookUrl(id){return "/knigi/"+encodeURIComponent(id)+"/";}
var app=document.getElementById("app");
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c];});}
function hash(s){var h=0;for(var i=0;i<s.length;i++){h=(h*31+s.charCodeAt(i))|0;}return Math.abs(h);}
function safeUrl(u){u=String(u||"").trim();return /^https?:\/\//i.test(u)?u:"";}
function cover(b,w){
  if(b.cover&&/^(data:image\/|\/|https?:)/.test(b.cover)) return '<div class="cv"><img src="'+esc(b.cover)+'" alt="Обложка: '+esc(b.title)+'" width="360" height="540" loading="lazy" decoding="async"></div>';
  var h=hash(b.title+b.author),p=PAL[h%PAL.length];
  return '<div class="cv gen s'+(h%3)+'" style="--c1:'+p[0]+';--c2:'+p[1]+';--cw:'+(w||170)+'px" role="img" aria-label="Обложка: '+esc(b.title)+'"><div class="ct">'+esc(b.title)+'</div><div><div class="rule"></div><div class="ca">'+esc(b.author)+'</div></div></div>';
}
function badge(t){return '<span class="badge '+t+'">'+(BADGE[t]||TYPES[t])+'</span>';}
function link(b){return safeUrl(b.post)||safeUrl(state.settings.channelUrl);}
function origLine(b){var p=[b.origTitle,b.origAuthor,b.year].filter(function(x){return x&&String(x).trim();});if(b.seriesOrig&&String(b.seriesOrig).trim())p.push('цикл «'+b.seriesOrig+'»');return p.length?'<p class="orig"><b>Оригинал:</b> '+p.map(esc).join(' · ')+'</p>':'';}
function annHtml(b){var ps=String(b.annotation||"").split(/\n\s*\n/).map(function(x){return x.trim();}).filter(Boolean);if(ps.length<=1) return '<p class="ann">'+esc(ps[0]||"")+'</p>';var open=ui.annOpen===b.id;return '<p class="ann">'+esc(open?ps.join("\n\n"):ps[0])+'</p><button class="more" data-more="1" aria-expanded="'+open+'">'+(open?'Свернуть':'Читать дальше')+'</button>';}
function noteLabel(t){return t==="rec"?"Рекомендация — почему стоит прочесть (необязательно)":"От переводчика — ваш комментарий (необязательно)";}
function allGenres(d){var o={};state.books.forEach(function(b){(b.genres||[]).forEach(function(g){o[g]=1;});});((d&&d.genres)||[]).forEach(function(g){o[g]=1;});return Object.keys(o).sort(function(a,b){return a.localeCompare(b,"ru");});}
var TG='<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M21.9 4.3 18.7 19.5c-.2 1.1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.3-5 9.2-8.3c.4-.4-.1-.6-.6-.2L6.1 13.1 1.2 11.6c-1.1-.3-1.1-1 .2-1.5L20.5 2.8c.9-.3 1.7.2 1.4 1.5z"/></svg>';
function sorted(){return state.books.slice().sort(function(a,b){return (b.added||0)-(a.added||0);});}
function matches(b){
  if(ui.genre&&(b.type==="wait"||(b.genres||[]).indexOf(ui.genre)<0)) return false;
  if(ui.q){var q=ui.q.toLowerCase();return (b.title+" "+b.author+" "+(b.series||"")+" "+(b.genres||[]).join(" ")+" "+(b.origin||"")+" "+(b.origTitle||"")+" "+(b.origAuthor||"")+" "+(b.seriesOrig||"")).toLowerCase().indexOf(q)>=0;}
  return true;
}
function featured(){var f=sorted().filter(function(b){return b.featured;});return f.length?f:sorted().slice(0,1);}
function card(b){return '<a class="card" href="'+bookUrl(b.id)+'" data-open="'+esc(b.id)+'"><div class="cv-wrap">'+cover(b,170)+'</div><span class="t">'+esc(b.title)+'</span><span class="a">'+esc(b.author)+(b.year?' · '+esc(b.year):'')+'</span>'+(b.series?'<span class="sr">'+esc(b.series)+(b.seriesNo?' · кн. '+esc(b.seriesNo):'')+'</span>':'')+badge(b.type)+(hasEta(b)?'<span class="eta">≈ '+fmtDate(b.eta)+'</span>':'')+'</a>';}
function row(id,title,list){
  if(!list.length) return "";
  return '<section class="row" id="'+id+'"><div class="row-head"><h2>'+title+'</h2><span class="count">'+list.length+'</span><div class="nav"><button aria-label="Прокрутить назад" data-scroll="-1">‹</button><button aria-label="Прокрутить вперёд" data-scroll="1">›</button></div></div><div class="shelf">'+list.map(card).join("")+'</div></section>';
}
function heroHtml(){
  var f=featured();if(!f.length) return "";
  var b=f[ui.hero%f.length];
  var bg=b.cover?'style="background-image:url(&quot;'+esc(b.cover)+'&quot;)"':'style="background:linear-gradient(120deg,'+PAL[hash(b.title+b.author)%PAL.length][0]+',transparent)"';
  return '<header class="hero"><div class="hero-bg" '+bg+'></div><div class="hero-in"><div><div class="eyebrow">'+TYPES[b.type]+(b.origin?' · '+esc(b.origin):'')+'</div><h1>'+esc(b.title)+'</h1><p class="by">'+esc(b.author)+(b.series?' — '+seriesLabel(b):'')+'</p>'+origLine(b)+etaLine(b)+'<ul class="tags">'+(b.genres||[]).map(function(g){return '<li>'+esc(g)+'</li>';}).join("")+'</ul><p class="ann">'+esc(b.annotation)+'</p><div class="hero-actions"><a class="btn btn-amber" href="'+esc(link(b))+'" target="_blank" rel="noopener">'+TG+'Найти в Telegram</a><button class="btn btn-ghost" data-open="'+esc(b.id)+'">Подробнее</button></div>'+(f.length>1?'<div class="dots">'+f.map(function(x,i){return '<button aria-label="'+esc(x.title)+'" data-hero="'+i+'" aria-current="'+(i===ui.hero%f.length)+'"></button>';}).join("")+'</div>':'')+'</div><div class="hero-cover">'+cover(b,260)+'</div></div></header>';
}
function render(){
  var s=state.settings,all=sorted(),filtered=all.filter(matches);
  var genres={};all.forEach(function(b){if(b.type==="wait")return;(b.genres||[]).forEach(function(g){genres[g]=(genres[g]||0)+1;});});
  var gl=Object.keys(genres).filter(function(g){return genres[g]>=3;}).sort(function(a,b){return (genres[b]-genres[a])||a.localeCompare(b,"ru");});
  var GSHOW=10,gVis=(ui.gAll||gl.length<=GSHOW+1)?gl:gl.slice(0,GSHOW);if(ui.genre&&gVis.indexOf(ui.genre)<0&&gl.indexOf(ui.genre)>=0)gVis=gVis.concat([ui.genre]);
  var body;
  if(ui.q||ui.genre){
    body='<section class="row"><div class="row-head"><h2>'+(ui.q?'Поиск: «'+esc(ui.q)+'»':esc(ui.genre))+'</h2><span class="count">'+filtered.length+'</span></div>'+(filtered.length?'<div class="grid">'+filtered.map(card).join("")+'</div>':'<p class="empty">Ничего не нашлось. Попробуйте другое название или автора — или загляните в канал, там книг больше.</p>')+'</section>';
  } else {
    body=row("new","Новое на Booknix",all.filter(function(b){return b.type!=="wait";}).slice(0,12))+row("translations","Мои переводы",all.filter(function(b){return b.type==="translation";}))+row("wait","Лист ожидания",all.filter(function(b){return b.type==="wait";}).sort(function(a,b){return (a.eta||"9999")<(b.eta||"9999")?-1:1;}))+row("rec","Рекомендации",all.filter(function(b){return b.type==="rec";}))+gl.map(function(g,i){return row("g"+i,gLink(g),all.filter(function(b){return b.type!=="wait"&&(b.genres||[]).indexOf(g)>=0;}));}).join("");
  }
  var searchVal=ui.q;
  var keep={};['.sheet-card'].forEach(function(q){var el=app.querySelector(q);if(el)keep[q]=el.scrollTop;});
  app.innerHTML='<div class="bx-bar"><a class="bx-logo" href="/" data-home="1">BOOK<span>NIX</span></a><nav class="bx-nav"><a href="/#translations" data-anchor="translations">Переводы</a><a href="/#rec" data-anchor="rec">Рекомендации</a><a href="/#wait" data-anchor="wait">Лист ожидания</a><a href="/#about" data-anchor="about">О канале</a></nav><label class="bx-search"><svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><path d="m20 20-4-4" stroke="currentColor" stroke-width="2"/></svg><input id="bx-q" type="search" placeholder="Книга или автор" aria-label="Поиск по книгам" value="'+esc(searchVal)+'"></label><button class="bx-theme" data-theme-toggle="1" aria-label="Переключить светлую и тёмную тему" title="Светлая / тёмная тема"><svg class="i-moon" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M20.5 14.6A8.5 8.5 0 0 1 9.4 3.5a.6.6 0 0 0-.8-.7A9.7 9.7 0 1 0 21.2 15.4a.6.6 0 0 0-.7-.8z"/></svg><svg class="i-sun" width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.5" fill="currentColor"/><path stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/></svg></button><a class="btn btn-amber btn-sm bx-tg" href="'+esc(safeUrl(s.channelUrl))+'" target="_blank" rel="noopener">'+TG+'<span class="lbl">Канал</span></a></div>'
   +'<div id="top"></div>'+(ui.q||ui.genre?'':heroHtml())
   +'<div class="filters" role="toolbar" aria-label="Жанры"><a class="chip" href="/" data-genre=""'+(!ui.genre?' aria-current="page"':'')+'>Все жанры</a>'+gVis.map(function(g){return '<a class="chip" href="'+genreUrl(g)+'" data-genre="'+esc(g)+'"'+(ui.genre===g?' aria-current="page"':'')+'>'+esc(g)+'<span class="n">'+genres[g]+'</span></a>';}).join("")+(gl.length>GSHOW+1?'<button class="chip more-g" data-gmore="1" aria-expanded="'+(!!ui.gAll)+'">'+(ui.gAll?'Свернуть ▴':'Ещё '+(gl.length-GSHOW)+' ▾')+'</button>':'')+'</div>'
   +body
   +'<section class="about" id="about"><div><div class="eyebrow">Telegram-канал</div><h2>'+esc(s.channelName)+'</h2><p>'+esc(s.about)+'</p><p>Полные книги лежат на закрытой Книжной полке. Чтобы попасть туда, напишите «Хочу доступ» в комментариях к любому посту — приглашение придёт в личные сообщения.</p></div><a class="btn btn-amber" href="'+esc(safeUrl(s.channelUrl))+'" target="_blank" rel="noopener">'+TG+'Подписаться</a></section>'
   +'<footer><span>Booknix — витрина канала '+esc(s.channelName)+'</span><span>Связь: '+esc(s.contact)+'</span><button class="cookie-link" data-cookies="1">Настройки cookie</button></footer>'
   +(ui.openId?sheetHtml():'');
  if(ui.resetSheet){delete keep['.sheet-card'];ui.resetSheet=false;}Object.keys(keep).forEach(function(q){var el=app.querySelector(q);if(el)el.scrollTop=keep[q];});
  if(document.activeElement===null||ui.focusSearch){var i=document.getElementById("bx-q");if(ui.focusSearch&&i){i.focus();i.setSelectionRange(i.value.length,i.value.length);}}
  ui.focusSearch=false;
}
function find(id){for(var i=0;i<state.books.length;i++){if(state.books[i].id===id) return state.books[i];}return null;}
function sheetHtml(){
  var b=find(ui.openId);if(!b) return "";
  return '<div class="sheet" data-close="1"><div class="sheet-card" role="dialog" aria-modal="true" aria-label="'+esc(b.title)+'"><button class="x" data-close="1" aria-label="Закрыть">×</button><div class="sheet-top"><div>'+cover(b,200)+'</div><div>'+badge(b.type)+'<h2>'+esc(b.title)+'</h2><p class="by">'+esc(b.author)+(b.series?' — '+seriesLabel(b):'')+'</p>'+origLine(b)+'<p class="meta">'+[esc(b.origin)].concat((b.genres||[]).map(gLink)).filter(Boolean).join(' · ')+'</p>'+etaLine(b)+annHtml(b)+(b.note?'<p class="note'+(b.type==="rec"?' rec':'')+'"><b>'+(b.type==="rec"?'Рекомендация':'От переводчика')+'</b>'+esc(b.note)+'</p>':'')+'<a class="btn btn-amber" href="'+esc(link(b))+'" target="_blank" rel="noopener">'+TG+(b.type==="translation"?'Читать перевод в Telegram':(b.type==="progress"||b.type==="wait")?'Следить за переводом':'Найти в Telegram')+'</a></div></div>'+seriesBlock(b)+'<div class="access"><strong>Как получить книгу.</strong> Откройте пост в канале и напишите в комментариях «Хочу доступ» — пришлю приглашение на закрытую Книжную полку, где лежат все файлы.</div></div></div>';
}

/* ---------- events ---------- */
document.addEventListener("click",function(e){
  var t=e.target.closest("[data-open],[data-close],[data-scroll],[data-genre],[data-hero],[data-more],[data-gmore],[data-home],[data-anchor]");
  if(!t) return;
  var ds=t.dataset;
  if((ds.open!==undefined||ds.home!==undefined||ds.anchor!==undefined||ds.genre!==undefined)&&(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button>0))return;
  if(ds.close!==undefined){if(e.target===t||t.classList.contains("x")){closeSheet();}return;}
  if(ds.home!==undefined){e.preventDefault();ui.q="";ui.genre="";ui.openId=null;go("/");render();window.scrollTo(0,0);return;}
  if(ds.anchor!==undefined){e.preventDefault();var wasFiltered=ui.q||ui.genre||ui.openId;ui.q="";ui.genre="";ui.openId=null;go("/");if(wasFiltered)render();var el=document.getElementById(ds.anchor);if(el)el.scrollIntoView({behavior:"smooth"});return;}
  if(ds.gmore!==undefined){ui.gAll=!ui.gAll;render();return;}
  if(ds.more!==undefined){ui.annOpen=ui.annOpen===ui.openId?null:ui.openId;render();return;}
      if(ds.open!==undefined){e.preventDefault();openBook(ds.open);return;}
  if(ds.scroll!==undefined){var sh=t.closest(".row").querySelector(".shelf");sh.scrollBy({left:(+ds.scroll)*sh.clientWidth*.85,behavior:"smooth"});return;}
  if(ds.genre!==undefined){e.preventDefault();ui.genre=ds.genre;ui.q="";ui.openId=null;go(ds.genre?genreUrl(ds.genre):"/");render();window.scrollTo(0,0);return;}
  if(ds.hero!==undefined){ui.hero=+ds.hero;stopRotate();render();return;}
});
document.addEventListener("click",function(e){
  if(!e.target.closest("[data-theme-toggle]"))return;
  var r=document.documentElement,t=r.getAttribute("data-theme")==="light"?"dark":"light";
  r.setAttribute("data-theme",t);try{localStorage.setItem("bx-theme",t);}catch(x){}
  var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute("content",t==="light"?"#f5f0e6":"#0b0f15");
});
document.addEventListener("input",function(e){
  if(e.target.id==="bx-q"){ui.q=e.target.value.trim();ui.focusSearch=true;render();}
});
document.addEventListener("keydown",function(e){if(e.key==="Escape"&&ui.openId)closeSheet();});
var HOME_TITLE=window.BOOKNIX.homeTitle||"Booknix";
function setTitle(){var b=ui.openId&&find(ui.openId);document.title=b?(SEO[b.id]||b.title+" — "+b.author+" | Booknix"):(ui.genre&&GEN[ui.genre])?GEN[ui.genre].title:HOME_TITLE;}
function go(path){setTitle();if(location.pathname!==path)history.pushState(null,"",path);}
function openBook(id){if(!find(id))return;ui.resetSheet=!!ui.openId;ui.openId=id;ui.annOpen=null;go(bookUrl(id));render();}
function closeSheet(){ui.openId=null;go(ui.genre?genreUrl(ui.genre):"/");render();}
window.addEventListener("popstate",function(){ui.openId=idFromPath();if(!ui.openId)ui.genre=genreFromPath()||"";ui.annOpen=null;setTitle();render();});

function stopRotate(){if(ui.timer){clearInterval(ui.timer);ui.timer=null;}}
var reduce=window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if(!reduce){ui.timer=setInterval(function(){if(ui.openId||ui.q||ui.genre||document.hidden) return;var ae=document.activeElement;if(ae&&ae.id==="bx-q")return;ui.hero++;var h=document.querySelector(".hero");if(h){var tmp=document.createElement("div");tmp.innerHTML=heroHtml();h.replaceWith(tmp.firstChild);}},9000);}

if(ui.openId&&!find(ui.openId))ui.openId=null;
setTitle();render();
})();
