#!/usr/bin/env python3
"""
Por Trás do Focinho — gerador do portal (site estático).

  python3 build.py            -> gera ./dist     (produção: URLs limpas /artigo/slug/)
  python3 build.py --preview  -> gera ./preview  (links relativos .../index.html, para prévia)

Conteúdo: content/articles/*.md e content/pages/*.md (front matter YAML + Markdown).
Dados:    data/*.yaml  ·  Configuração e credenciais: config.yaml
"""
import sys, re, json, shutil, hashlib, datetime, unicodedata, random
from pathlib import Path
from urllib.parse import quote_plus
from email.utils import format_datetime
import subprocess, shutil as _sh
import yaml, markdown
from markupsafe import Markup, escape
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent
MODE = "preview" if "--preview" in sys.argv else "prod"
OUT = ROOT / ("preview" if MODE == "preview" else "dist")
TODAY = datetime.date.today()

def load(p):
    d = yaml.safe_load((ROOT / p).read_text(encoding="utf-8")) or {}
    return d["items"] if isinstance(d, dict) and "items" in d else d

CFG = load("config.yaml")
CATS = load("data/categories.yaml")
CAT = {c["slug"]: c for c in CATS}
PRODUCTS = {p["id"]: p for p in load("data/products.yaml")}
VIDEOS = load("data/videos.yaml")
FORMATS = {f["id"]: f for f in load("data/formats.yaml")}
SITE_URL = CFG["site"]["url"].rstrip("/")

# ---------------------------------------------------------------- utilidades
def slugify(s, sep="-"):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", sep, s.lower()).strip(sep)

def toc_slug(value, separator):
    return slugify(value, separator)

CUR = {"root": ""}  # raiz relativa da página em renderização (modo prévia)

def url(path=""):
    path = path.strip("/")
    is_file = bool(re.search(r"\.[a-z0-9]{2,5}$", path))
    if MODE == "prod":
        return "/" + path + ("" if is_file or not path else "/")
    if is_file:
        return CUR["root"] + path
    return CUR["root"] + (path + "/" if path else "") + "index.html"

def abs_url(path=""):
    path = path.strip("/")
    return SITE_URL + "/" + (path + "/" if path and "." not in path.split("/")[-1] else path)

def parse_md(fp):
    raw = fp.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise SystemExit(f"Front matter ausente em {fp}")
    meta = yaml.safe_load(m.group(1)) or {}
    meta["body_md"] = m.group(2)
    meta.setdefault("slug", fp.stem)
    return meta

def as_date(v):
    if isinstance(v, datetime.date):
        return v
    return datetime.date.fromisoformat(str(v))

def date_br(d):
    meses = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto",
             "setembro","outubro","novembro","dezembro"]
    return f"{d.day} de {meses[d.month-1]} de {d.year}"

def shade(hex_, f):
    """f>0 clareia, f<0 escurece."""
    h = hex_.lstrip("#"); r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    if f >= 0:
        r, g, b = (int(c + (255 - c) * f) for c in (r, g, b))
    else:
        r, g, b = (int(c * (1 + f)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"

# ---------------------------------------------------------------- ilustrações
FUR = [("#E9A23B", "#F6D7A4"), ("#C27A3E", "#EFCFA8"), ("#F3E2C4", "#FFFFFF"),
       ("#6B4A3A", "#C9A88E"), ("#2F2724", "#7B6A62"), ("#FFFFFF", "#F2EDE6"),
       ("#9A9CA3", "#E3E3E6"), ("#D9893F", "#FFFFFF")]

def pet_svg(animal, seed, x, y, s, nose="#2A1D1B"):
    """Desenha a cabeça de um pet 'espiando' (centro x,y; escala s). Retorna SVG."""
    rnd = random.Random(seed)
    fur, light = FUR[rnd.randrange(len(FUR))]
    dark = shade(fur, -0.28) if fur not in ("#FFFFFF", "#F3E2C4") else "#D7C3A6"
    tilt = rnd.choice([-8, -4, 0, 5, 9])
    spot = rnd.random() < 0.35
    g = [f'<g transform="translate({x} {y}) rotate({tilt}) scale({s})">',
         '<ellipse cx="0" cy="170" rx="190" ry="40" fill="#000" opacity=".12"/>']
    if animal == "cat":
        g += [f'<path d="M-140,-40 L-120,-200 L-40,-110 Z" fill="{fur}"/>',
              f'<path d="M140,-40 L120,-200 L40,-110 Z" fill="{fur}"/>',
              '<path d="M-118,-70 L-108,-165 L-62,-112 Z" fill="#F4A3B4"/>',
              '<path d="M118,-70 L108,-165 L62,-112 Z" fill="#F4A3B4"/>',
              f'<ellipse cx="0" cy="10" rx="165" ry="150" fill="{fur}"/>',
              f'<ellipse cx="0" cy="70" rx="80" ry="58" fill="{light}"/>']
        if spot:
            g.append(f'<path d="M-30,-138 Q0,-60 30,-138 Z" fill="{dark}" opacity=".8"/>')
        for ex in (-62, 62):
            g += [f'<ellipse cx="{ex}" cy="-5" rx="30" ry="24" fill="#C9D86A"/>',
                  f'<ellipse cx="{ex}" cy="-5" rx="7" ry="21" fill="#1B1716"/>',
                  f'<circle cx="{ex+9}" cy="-14" r="5" fill="#fff"/>']
        g += ['<path d="M-16,42 L16,42 L0,60 Z" fill="#E8798F"/>',
              '<path d="M0,60 Q-14,82 -30,74 M0,60 Q14,82 30,74" stroke="#5A403A" stroke-width="5" fill="none" stroke-linecap="round"/>']
        for wy in (52, 72):
            g += [f'<path d="M-70,{wy} L-190,{wy-14}" stroke="{shade(light,-0.35)}" stroke-width="3" stroke-linecap="round"/>',
                  f'<path d="M70,{wy} L190,{wy-14}" stroke="{shade(light,-0.35)}" stroke-width="3" stroke-linecap="round"/>']
    else:
        floppy = rnd.random() < 0.6
        if floppy:
            g += [f'<ellipse cx="-150" cy="10" rx="55" ry="115" fill="{dark}" transform="rotate(18 -150 10)"/>',
                  f'<ellipse cx="150" cy="10" rx="55" ry="115" fill="{dark}" transform="rotate(-18 150 10)"/>']
        else:
            g += [f'<path d="M-150,-30 L-130,-215 L-45,-120 Z" fill="{dark}"/>',
                  f'<path d="M150,-30 L130,-215 L45,-120 Z" fill="{dark}"/>']
        g += [f'<ellipse cx="0" cy="0" rx="160" ry="155" fill="{fur}"/>']
        if spot:
            g.append(f'<ellipse cx="-62" cy="-20" rx="58" ry="52" fill="{dark}" opacity=".85"/>')
        g += [f'<ellipse cx="0" cy="85" rx="98" ry="74" fill="{light}"/>']
        for ex in (-62, 62):
            g += [f'<circle cx="{ex}" cy="-18" r="22" fill="#1B1716"/>',
                  f'<circle cx="{ex+8}" cy="-26" r="7" fill="#fff"/>']
        g += [f'<path d="M-44,42 Q0,22 44,42 Q40,80 0,92 Q-40,80 -44,42 Z" fill="{nose}"/>',
              '<ellipse cx="-14" cy="50" rx="12" ry="6" fill="#fff" opacity=".35"/>',
              f'<path d="M0,92 L0,112 M0,112 Q-24,134 -48,118 M0,112 Q24,134 48,118" stroke="{shade(fur,-0.5)}" stroke-width="6" fill="none" stroke-linecap="round"/>']
    g.append("</g>")
    return "".join(g)

def paw(x, y, s, col, op):
    return (f'<g transform="translate({x} {y}) scale({s})" fill="{col}" opacity="{op}">'
            '<ellipse cx="0" cy="18" rx="22" ry="18"/><circle cx="-24" cy="-8" r="9"/>'
            '<circle cx="-8" cy="-22" r="9"/><circle cx="10" cy="-22" r="9"/><circle cx="26" cy="-8" r="9"/></g>')

def cover_svg(seed, color, animal, w=1200, h=675):
    rnd = random.Random(seed + "bg")
    pale = shade(color, 0.18)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice" role="img">',
             f'<rect width="{w}" height="{h}" fill="{color}"/>',
             f'<circle cx="{rnd.randint(int(w*.55), int(w*.8))}" cy="{int(h*.62)}" r="{int(h*.62)}" fill="{pale}"/>']
    for _ in range(7):
        parts.append(paw(rnd.randint(30, w - 30), rnd.randint(30, int(h * .7)),
                         rnd.uniform(.5, 1.1), "#fff", .07))
    x = rnd.randint(int(w * .58), int(w * .74))
    parts.append(pet_svg(animal, seed, x, int(h * .80), h / 540))
    parts.append("</svg>")
    return "".join(parts)

# ---------------------------------------------------------------- afiliados
def aff_links(p):
    # Produto com link de afiliado próprio (ex.: meli.la) tem prioridade sobre a busca genérica.
    a = CFG["affiliates"]
    if p.get("links"):
        out = [(store, href) for store, href in p["links"].items() if href]
        # Com a tag da Amazon configurada, oferece também a busca na Amazon (com comissão).
        if a.get("amazon_tag") and p.get("search") and "Amazon" not in p["links"]:
            out.append(("Amazon", f"https://www.amazon.com.br/s?k={quote_plus(p['search'])}&tag={a['amazon_tag']}"))
        return out
    q = p["search"]
    amz = f"https://www.amazon.com.br/s?k={quote_plus(q)}" + (f"&tag={a['amazon_tag']}" if a.get("amazon_tag") else "")
    return [("Amazon", amz),
            ("Mercado Livre", "https://lista.mercadolivre.com.br/" + slugify(q)),
            ("Petlove", f"https://www.petlove.com.br/busca?q={quote_plus(q)}"),
            ("Cobasi", f"https://www.cobasi.com.br/pesquisa?terms={quote_plus(q)}")]

# ---------------------------------------------------------------- conteúdo
md = markdown.Markdown(extensions=["toc", "tables", "attr_list", "md_in_html", "sane_lists"],
                       extension_configs={"toc": {"slugify": toc_slug, "toc_depth": "2"}})

LINK = re.compile(r"\]\(@(page:)?([a-z0-9\-/]+)(#[a-z0-9\-]+)?\)")

def checklists(h):
    return re.sub(r"<li>\[ \]\s*", '<li class="chk">', h)

def render_md(text):
    text = LINK.sub(lambda m: "](" + url(("" if m.group(1) else "artigo/") + m.group(2)) + (m.group(3) or "") + ")", text)
    md.reset()
    html_ = checklists(md.convert(text))
    html_ = re.sub(r"<table>", '<div class="table-wrap"><table>', html_).replace("</table>", "</table></div>")
    return html_, md.toc_tokens

ARTICLES = []
for fp in sorted((ROOT / "content/articles").glob("*.md")):
    a = parse_md(fp)
    if a.get("draft"):
        continue
    a["date"] = as_date(a["date"])
    if a["date"] > TODAY and not a.get("force"):
        continue  # agendado: publica automaticamente no próximo build após a data
    a["updated"] = as_date(a.get("updated", a["date"]))
    a["cat"] = CAT[a["category"]]
    a["path"] = f"artigo/{a['slug']}"
    a["words"] = len(re.findall(r"\w+", a["body_md"]))
    a["minutes"] = max(2, round(a["words"] / 200))
    a["animal"] = a.get("animal", a["cat"]["animal"])
    a["format_obj"] = FORMATS.get(a.get("format"))
    a["video_obj"] = next((v for v in VIDEOS if v.get("article") == a["slug"]), None)
    ARTICLES.append(a)
ARTICLES.sort(key=lambda a: (a["date"], a.get("pillar", False)), reverse=True)
BY_SLUG = {a["slug"]: a for a in ARTICLES}

PAGES = [parse_md(fp) for fp in sorted((ROOT / "content/pages").glob("*.md"))]

# ---------------------------------------------------------------- jinja
env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True,
                  trim_blocks=True, lstrip_blocks=True)
env.globals.update(url=url, abs_url=abs_url, cfg=CFG, cats=CATS, CAT=CAT, MODE=MODE,
                   date_br=date_br, aff_links=aff_links, PRODUCTS=PRODUCTS, VIDEOS=VIDEOS,
                   FORMATS=FORMATS, articles=ARTICLES, BY_SLUG=BY_SLUG, shade=shade,
                   year=TODAY.year, json=lambda o: Markup(json.dumps(o, ensure_ascii=False).replace("</", "<\\/")))
M = None  # módulo de macros (carregado após o env)

def related(a, n=4):
    pool = [BY_SLUG[s] for s in a.get("related", []) if s in BY_SLUG]
    pool += [x for x in ARTICLES if x is not a and x not in pool and
             (x.get("cluster") and x.get("cluster") == a.get("cluster"))]
    pool += [x for x in ARTICLES if x is not a and x not in pool and x["category"] == a["category"]]
    pool += [x for x in ARTICLES if x is not a and x not in pool]
    return pool[:n]
env.globals["related"] = related
env.globals["prods"] = lambda ids: [PRODUCTS[i] for i in (ids or []) if i in PRODUCTS]

SHORT = re.compile(r"<p>\s*\[\[([a-z\-]+)(?::\s*([^\]]+))?\]\]\s*</p>")

def expand_shortcodes(html_, ctx):
    def rep(m):
        name, arg = m.group(1), (m.group(2) or "").strip()
        if name == "produtos":
            ids = [i.strip() for i in arg.split(",")] if arg else ctx.get("products", [])
            return str(M.products([PRODUCTS[i] for i in ids if i in PRODUCTS]))
        if name == "leia":
            if arg in BY_SLUG:
                return str(M.inline_read(BY_SLUG[arg]))
            print(f"  aviso: [[leia:{arg}]] aponta para artigo inexistente"); return ""
        if name == "video":
            return str(M.video(ctx.get("video_obj")))
        if name == "newsletter":
            return str(M.newsletter("inline"))
        if name == "campanha":
            return str(M.campaign())
        if name == "formatos":
            return str(M.formats())
        if name == "loja":
            return str(M.store())
        if name == "videos":
            return str(M.video_grid())
        if name == "anuncio":
            return str(M.ad("in_article"))
        if name == "cards":
            return str(M.card_row([BY_SLUG[s.strip()] for s in arg.split(",") if s.strip() in BY_SLUG]))
        print(f"  aviso: shortcode desconhecido [[{name}]]")
        return ""
    return SHORT.sub(rep, html_)

def insert_ads(html_):
    """Anúncio após o 2º parágrafo e antes do 4º H2 (quando o texto é longo)."""
    ad = str(M.ad("in_article"))
    parts = re.split(r"(</p>)", html_, maxsplit=2)
    if len(parts) >= 5:
        html_ = "".join(parts[:4]) + ad + "".join(parts[4:])
    h2 = [m.start() for m in re.finditer(r"<h2", html_)]
    if len(h2) >= 4 and html_.count("ad-in_article") < 2:
        html_ = html_[:h2[3]] + ad + html_[h2[3]:]
    return html_

def write(path, html_):
    out = OUT / (path + "/index.html" if path and not path.endswith(".html") else (path or "index.html"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_, encoding="utf-8")

def render(tpl, path, **ctx):
    CUR["root"] = "../" * (len([p for p in path.split("/") if p]) if path else 0)
    ctx.setdefault("canonical", abs_url(path))
    ctx.setdefault("page_path", path)
    write(path, env.get_template(tpl).render(**ctx))

# ---------------------------------------------------------------- build
def build():
    global M
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)
    M = env.get_template("_macros.html").module
    (OUT / "assets/covers").mkdir(parents=True, exist_ok=True)

    for a in ARTICLES:
        (OUT / f"assets/covers/{a['slug']}.svg").write_text(
            cover_svg(a["slug"], a["cat"]["color"], a["animal"]), encoding="utf-8")
    for c in CATS:
        (OUT / f"assets/covers/cat-{c['slug']}.svg").write_text(
            cover_svg("cat-" + c["slug"], c["color"], c["animal"], 1600, 600), encoding="utf-8")
    (OUT / "assets/covers/home.svg").write_text(
        cover_svg("home-hero-7", "#0E3B43", "dog", 1600, 900), encoding="utf-8")

    # PNG para redes sociais (og:image) — requer rsvg-convert
    if _sh.which("rsvg-convert"):
        cv = lambda src, dst, w, h: subprocess.run(["rsvg-convert", "-w", str(w), "-h", str(h), "-o", str(dst), str(src)], check=True)
        for a in ARTICLES:
            cv(OUT / f"assets/covers/{a['slug']}.svg", OUT / f"assets/covers/{a['slug']}.png", 1200, 675)
        cv(OUT / "assets/covers/home.svg", OUT / "assets/og-default.png", 1200, 675)
        cv(OUT / "assets/favicon.svg", OUT / "assets/logo.png", 512, 512)
    else:
        print("  aviso: rsvg-convert ausente — imagens PNG de compartilhamento não geradas")

    # artigos
    for a in ARTICLES:
        CUR["root"] = "../../"
        body, toc = render_md(a["body_md"])
        body = insert_ads(expand_shortcodes(body, a))
        a["toc"] = toc
        render("article.html", a["path"], a=a, body=Markup(body),
               title=a.get("seo_title", a["title"]), description=a["description"],
               og_type="article", og_image=abs_url(f"assets/covers/{a['slug']}.png"))

    # categorias
    for c in CATS:
        items = [a for a in ARTICLES if a["category"] == c["slug"]]
        items.sort(key=lambda a: (not a.get("pillar"), -a["date"].toordinal()))
        render("category.html", f"categoria/{c['slug']}", c=c, items=items,
               title=f"{c['name']}: artigos e guias", description=c["desc"])

    # páginas
    for p in PAGES:
        path = "" if p["slug"] == "index" else p["slug"]
        CUR["root"] = "../" * (len(path.split("/")) if path else 0)
        body, toc = render_md(p["body_md"])
        body = expand_shortcodes(body, p)
        render(p.get("template", "page.html"), path, p=p, body=Markup(body), toc=toc,
               title=p["title"], description=p.get("description", ""),
               noindex=p.get("noindex", False))

    render("home.html", "", title=CFG["site"]["name"] + " — comportamento, saúde e curiosidades de cães e gatos",
           description=CFG["site"]["tagline"], is_home=True)
    render("painel.html", "painel", title="Painel editorial e de receita", description="", noindex=True)
    render("404.html", "404", title="Página não encontrada", description="", noindex=True)
    if MODE == "prod":
        shutil.move(OUT / "404/index.html", OUT / "404.html"); (OUT / "404").rmdir()

    # busca, sitemap, robots, feed, ads.txt
    idx = [{"t": a["title"], "d": a["description"], "c": a["cat"]["short"],
            "u": a["path"], "k": " ".join(a.get("keywords", []))} for a in ARTICLES]
    (OUT / "search-index.json").write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")

    urls = [("", TODAY, "1.0")] + [(f"categoria/{c['slug']}", TODAY, "0.8") for c in CATS]
    urls += [(a["path"], a["updated"], "0.9" if a.get("pillar") else "0.7") for a in ARTICLES]
    urls += [(p["slug"], TODAY, "0.4") for p in PAGES if not p.get("noindex") and p["slug"] != "index"]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{abs_url(u)}</loc><lastmod>{d.isoformat()}</lastmod><priority>{p}</priority></url>"
           for u, d, p in urls]
    sm.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nDisallow: /painel/\nDisallow: /admin/\nDisallow: /guia-gratuito/\n\nSitemap: {SITE_URL}/sitemap.xml\n",
        encoding="utf-8")
    items = []
    for a in ARTICLES[:20]:
        dt = datetime.datetime.combine(a["date"], datetime.time(9), datetime.timezone(datetime.timedelta(hours=-3)))
        items.append(f"<item><title>{escape(a['title'])}</title><link>{abs_url(a['path'])}</link>"
                     f"<guid>{abs_url(a['path'])}</guid><pubDate>{format_datetime(dt)}</pubDate>"
                     f"<description>{escape(a['description'])}</description></item>")
    (OUT / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f"<title>{escape(CFG['site']['name'])}</title><link>{SITE_URL}/</link>"
        f"<description>{escape(CFG['site']['tagline'])}</description><language>pt-BR</language>"
        + "".join(items) + "</channel></rss>", encoding="utf-8")
    cid = CFG["adsense"].get("client_id", "")
    if cid:
        (OUT / "ads.txt").write_text(f"google.com, {cid.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n")

    print(f"[{MODE}] {len(ARTICLES)} artigos · {len(CATS)} categorias · {len(PAGES)} páginas -> {OUT}")

if __name__ == "__main__":
    build()
