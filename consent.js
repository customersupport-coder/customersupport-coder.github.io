/* ============================================================
   LACE — analytics consent
   Google Analytics is loaded only after the visitor accepts.
   Choice is stored in this browser for 180 days.
   Reopen the banner from anywhere with: laceConsent.open()
   ============================================================ */
(function(){
  var GA_ID = "G-B7Z8K7R6M2";
  var KEY = "lace_consent";
  var MAX_AGE = 180 * 864e5;

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function(){ dataLayer.push(arguments); };

  var T = {
    en: {
      text: "We use Google Analytics cookies to count visits and see which pages work. They load only if you accept.",
      more: "Privacy policy",
      yes: "Accept",
      no: "Decline",
      label: "Cookie choice"
    },
    it: {
      text: "Usiamo i cookie di Google Analytics per contare le visite e capire quali pagine funzionano. Si attivano solo se accetti.",
      more: "Informativa privacy",
      yes: "Accetta",
      no: "Rifiuta",
      label: "Scelta dei cookie"
    }
  };

  function read(){
    try{
      var v = JSON.parse(localStorage.getItem(KEY) || "null");
      if (v && (v.v === "granted" || v.v === "denied") && (Date.now() - v.t) < MAX_AGE) return v.v;
    }catch(e){}
    return null;
  }
  function write(v){
    try{ localStorage.setItem(KEY, JSON.stringify({v: v, t: Date.now()})); }catch(e){}
  }

  var loaded = false;
  function loadGA(){
    if (loaded) return;
    loaded = true;
    gtag("js", new Date());
    gtag("config", GA_ID);
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
    document.head.appendChild(s);
  }
  function dropGACookies(){
    try{
      document.cookie.split(";").forEach(function(c){
        var n = c.split("=")[0].trim();
        if (n.indexOf("_ga") !== 0) return;
        var host = location.hostname.replace(/^www\./, "");
        ["", "; domain=" + host, "; domain=." + host].forEach(function(d){
          document.cookie = n + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" + d;
        });
      });
    }catch(e){}
  }

  var bar = null;
  function lang(){ return (document.documentElement.lang || "en").toLowerCase().indexOf("it") === 0 ? "it" : "en"; }
  function fill(){
    if (!bar) return;
    var t = T[lang()];
    bar.setAttribute("aria-label", t.label);
    bar.querySelector(".lc-text").textContent = t.text + " ";
    var a = document.createElement("a");
    a.href = "/privacy.html"; a.textContent = t.more;
    bar.querySelector(".lc-text").appendChild(a);
    bar.querySelector(".lc-yes").textContent = t.yes;
    bar.querySelector(".lc-no").textContent = t.no;
  }
  function close(){
    if (bar){ bar.remove(); bar = null; }
  }
  function open(){
    if (bar) return;
    if (!document.getElementById("lc-style")){
      var st = document.createElement("style");
      st.id = "lc-style";
      st.textContent =
        ".lc-bar{position:fixed;left:0;right:0;bottom:0;z-index:400;background:#0d1017;color:#f5f3ee;border-top:1px solid rgba(245,243,238,.22);padding:14px 16px calc(14px + env(safe-area-inset-bottom));font-family:system-ui,-apple-system,'Segoe UI',sans-serif}" +
        ".lc-in{max-width:1200px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:14px 24px;flex-wrap:wrap}" +
        ".lc-text{margin:0;font-size:13.5px;line-height:1.5;flex:1 1 320px;color:rgba(245,243,238,.86)}" +
        ".lc-text a{color:#2aa9e0;text-decoration:underline;text-underline-offset:3px;white-space:nowrap}" +
        ".lc-btns{display:flex;gap:10px;flex:0 0 auto}" +
        ".lc-btn{min-height:44px;min-width:112px;padding:0 20px;border:1px solid #f5f3ee;background:none;color:#f5f3ee;font:600 12px/1 ui-monospace,'IBM Plex Mono',Menlo,monospace;letter-spacing:.1em;text-transform:uppercase;cursor:pointer}" +
        ".lc-btn:hover,.lc-btn:focus-visible{background:#f5f3ee;color:#0d1017}" +
        "@media(max-width:560px){.lc-btns{width:100%}.lc-btn{flex:1}}";
      document.head.appendChild(st);
    }
    bar = document.createElement("div");
    bar.className = "lc-bar";
    bar.setAttribute("role", "region");
    bar.innerHTML = '<div class="lc-in"><p class="lc-text"></p><div class="lc-btns">' +
      '<button type="button" class="lc-btn lc-no"></button><button type="button" class="lc-btn lc-yes"></button></div></div>';
    document.body.appendChild(bar);
    fill();
    bar.querySelector(".lc-yes").addEventListener("click", function(){ write("granted"); close(); loadGA(); });
    bar.querySelector(".lc-no").addEventListener("click", function(){
      var was = read();
      write("denied"); close(); dropGACookies();
      if (was === "granted") location.reload();
    });
  }

  window.laceConsent = { open: open, state: read };

  var choice = read();
  if (choice === "granted") loadGA();

  function ready(fn){ if (document.readyState !== "loading") fn(); else document.addEventListener("DOMContentLoaded", fn); }
  ready(function(){
    if (!choice) open();
    try{
      new MutationObserver(fill).observe(document.documentElement, {attributes: true, attributeFilter: ["lang"]});
    }catch(e){}
    document.addEventListener("click", function(e){
      var el = e.target.closest ? e.target.closest("[data-cookie-settings]") : null;
      if (el){ e.preventDefault(); open(); }
    });
  });
})();
