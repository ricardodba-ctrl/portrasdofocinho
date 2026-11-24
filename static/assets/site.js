/* Por Trás do Focinho — interações do portal (sem dependências) */
{
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const P = window.PTF || { root: "/", mode: "prod" };
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
                  set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
  const track = (name, params) => { if (typeof gtag === "function") gtag("event", name, params || {}); };
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const link = p => P.mode === "prod" ? "/" + p + "/" : P.root + p + "/index.html";

  /* menu mobile */
  const tog = $(".nav-toggle"), menu = $("#menu");
  if (tog) tog.addEventListener("click", () => { const o = menu.classList.toggle("open"); tog.setAttribute("aria-expanded", o); });

  /* busca instantânea */
  const dlg = $("#search"), q = $("#q"), res = $(".search-res");
  let idx = null;
  const norm = s => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  async function loadIdx() {
    if (idx) return idx;
    try { idx = await (await fetch(P.idx)).json(); } catch (e) { idx = []; }
    idx.forEach(i => i.n = norm(i.t + " " + i.d + " " + i.c + " " + i.k));
    return idx;
  }
  function draw() {
    const terms = norm(q.value.trim()).split(/\s+/).filter(t => t.length > 1);
    if (!terms.length) { res.innerHTML = '<li class="small" style="padding:12px">Digite um comportamento, sintoma ou raça.</li>'; return; }
    const hits = (idx || []).map(i => ({ i, s: terms.reduce((a, t) => a + (i.n.includes(t) ? (norm(i.t).includes(t) ? 3 : 1) : 0), 0) }))
      .filter(h => h.s > 0).sort((a, b) => b.s - a.s).slice(0, 8);
    res.innerHTML = hits.length ? hits.map(h => `<li><a href="${esc(link(h.i.u))}"><b>${esc(h.i.t)}</b><span>${esc(h.i.c)} · ${esc(h.i.d)}</span></a></li>`).join("")
      : '<li class="small" style="padding:12px">Nada encontrado ainda. Tente outra palavra, ou sugira o tema pelo contato.</li>';
    track("search", { search_term: q.value.trim() });
  }
  let t;
  function openSearch(initial) {
    dlg.hidden = false; document.body.style.overflow = "hidden";
    loadIdx().then(() => { if (initial) q.value = initial; draw(); });
    q.focus();
  }
  function closeSearch() { dlg.hidden = true; document.body.style.overflow = ""; }
  $$(".search-btn,[data-open-search]").forEach(b => b.addEventListener(b.tagName === "INPUT" ? "focus" : "click", e => {
    const hs = $("#hs"); openSearch(hs && hs.value); if (b.tagName === "INPUT") b.blur();
  }));
  if (q) q.addEventListener("input", () => { clearTimeout(t); t = setTimeout(draw, 120); });
  if (dlg) {
    $(".search-close").addEventListener("click", closeSearch);
    dlg.addEventListener("click", e => { if (e.target === dlg) closeSearch(); });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && !dlg.hidden) closeSearch();
      if (e.key === "/" && dlg.hidden && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) { e.preventDefault(); openSearch(); }
    });
    const sp = new URLSearchParams(location.search).get("q");
    if (sp) openSearch(sp);
  }

  /* newsletter: envia ao provedor configurado (Brevo/MailerLite) */
  $$(".nl-form").forEach(f => f.addEventListener("submit", async e => {
    e.preventDefault();
    const msg = $(".nl-msg", f), email = $("input[type=email]", f), ok = $("input[type=checkbox]", f);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.value)) { msg.textContent = "Confira o e-mail: falta algo como nome@provedor.com."; email.focus(); return; }
    if (!ok.checked) { msg.textContent = "Marque a caixa de consentimento para receber o guia."; ok.focus(); return; }
    const action = f.dataset.action;
    if (!action) { msg.textContent = "Inscrição ainda não conectada: o provedor de e-mail será configurado no lançamento."; return; }
    const body = new FormData(); body.append(f.dataset.field || "EMAIL", email.value); body.append("email_address_check", ""); body.append("locale", "pt"); body.append("html_type", "simple");
    try {
      await fetch(action, { method: "POST", body, mode: "no-cors" });
      msg.innerHTML = 'Pronto! Você está na lista. <a href="' + P.guide + '">Abra o guia aqui</a>.';
      track("generate_lead", { method: "newsletter" }); f.reset();
    } catch (err) { msg.textContent = "Não conseguimos enviar agora. Verifique sua conexão e tente de novo."; }
  }));

  /* cliques em afiliados e compartilhamento -> GA4 */
  document.addEventListener("click", e => {
    const a = e.target.closest("[data-aff]");
    if (a) { const [item, store_] = a.dataset.aff.split("|"); track("affiliate_click", { item_id: item, store: store_, page: location.pathname }); }
    const s = e.target.closest("[data-share]"); if (s) track("share", { method: s.dataset.share });
  });
  $$(".copy").forEach(b => b.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(b.dataset.link); b.textContent = "Link copiado"; }
    catch (e) { b.textContent = b.dataset.link; }
    track("share", { method: "copy" });
  }));

  /* YouTube leve: só carrega o player ao clicar */
  $$(".yt").forEach(b => b.addEventListener("click", () => {
    const f = document.createElement("iframe");
    f.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(b.dataset.id) + "?autoplay=1&rel=0";
    f.allow = "autoplay; encrypted-media; picture-in-picture"; f.allowFullscreen = true; f.title = b.getAttribute("aria-label") || "Vídeo";
    b.replaceChildren(f); track("video_start", { video_id: b.dataset.id });
  }, { once: true }));

  /* consentimento LGPD */
  const ck = $("#cookie");
  function setConsent(v) {
    store.set("ptf-consent", v); ck.hidden = true;
    if (typeof gtag === "function") {
      const g = v === "all" ? "granted" : "denied";
      gtag("consent", "update", { ad_storage: g, ad_user_data: g, ad_personalization: g, analytics_storage: g });
    }
  }
  if (ck) {
    if (!store.get("ptf-consent")) ck.hidden = false;
    $$("[data-consent]").forEach(b => b.addEventListener("click", () => setConsent(b.dataset.consent)));
    $$("[data-cookie-open]").forEach(b => b.addEventListener("click", () => { ck.hidden = false; }));
  }

  /* tempo de leitura: evento quando o leitor chega ao fim do artigo */
  const end = $(".share");
  if (end && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(es => { if (es[0].isIntersecting) { track("article_complete", { page: location.pathname }); io.disconnect(); } });
    io.observe(end);
  }
}
