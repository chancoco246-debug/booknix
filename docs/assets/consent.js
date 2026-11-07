/* Плашка согласия на cookie. Сам тег Google стоит в <head> в режиме Consent Mode:
   до согласия — без cookie, после «Разрешить» — обычная аналитика. */
(function(){
"use strict";
var KEY="bx-cookies";
if(typeof window.gtag!=="function")return;
function get(){try{return localStorage.getItem(KEY);}catch(e){return null;}}
function set(v){try{localStorage.setItem(KEY,v);}catch(e){}}
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
  gtag("consent","update",{analytics_storage:v==="yes"?"granted":"denied"});
});
var c=get();if(c!=="yes"&&c!=="no")show();
})();
