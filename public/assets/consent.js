/* Google Analytics только после согласия посетителя (правила ЕС). */
(function(){
"use strict";
var D=window.BOOKNIX||{},ID=(D.settings||{}).gaId,KEY="bx-cookies";
if(!ID)return;
function get(){try{return localStorage.getItem(KEY);}catch(e){return null;}}
function set(v){try{localStorage.setItem(KEY,v);}catch(e){}}
var loaded=false;
function loadGA(){
  if(loaded)return;loaded=true;
  window.dataLayer=window.dataLayer||[];
  window.gtag=function(){dataLayer.push(arguments);};
  gtag("js",new Date());gtag("config",ID,{anonymize_ip:true});
  var s=document.createElement("script");s.async=true;s.src="https://www.googletagmanager.com/gtag/js?id="+encodeURIComponent(ID);
  document.head.appendChild(s);
}
function hide(){var b=document.querySelector(".bx-cookie");if(b)b.remove();}
function show(){
  hide();var b=document.createElement("div");b.className="bx-cookie";b.setAttribute("role","dialog");b.setAttribute("aria-label","Cookie");
  b.innerHTML='<div><b>Можно мы посчитаем посещения?</b><br>Мы используем cookie Google Analytics, чтобы понимать, сколько людей заходит на сайт и какие книги смотрят. Никакой рекламы.</div>'
   +'<div class="acts"><button class="btn btn-amber btn-sm" data-ck="yes">Разрешить</button><button class="btn btn-ghost btn-sm" data-ck="no">Отказаться</button></div>';
  document.body.appendChild(b);
}
document.addEventListener("click",function(e){
  var t=e.target.closest("[data-ck],[data-cookies]");if(!t)return;
  if(t.dataset.cookies!==undefined){show();return;}
  var v=t.dataset.ck;set(v);hide();
  if(v==="yes")loadGA();
  else if(loaded){location.reload();}
});
var c=get();
if(c==="yes")loadGA();else if(c!=="no")show();
})();
