# Por Trás do Focinho — portal

Site estático gerado em Python: rápido, seguro, sem banco de dados e com hospedagem gratuita.

## Estrutura

```
config.yaml            credenciais e integrações (GA4, AdSense, afiliados, newsletter, loja)
content/articles/*.md  artigos (front matter YAML + Markdown)
content/pages/*.md     páginas institucionais
data/*.yaml            categorias, formatos, produtos de afiliados, vídeos
templates/             layout (Jinja)
static/                CSS, JS, favicon e painel de administração (Decap CMS)
build.py               gerador -> dist/
```

## Gerar o site

```bash
pip install -r requirements.txt
python3 build.py            # produção -> dist/
python3 build.py --preview  # prévia com links relativos -> preview/
```

O build gera sozinho: páginas, sitemap.xml, robots.txt, feed.xml, índice de busca, capas ilustradas (SVG + PNG para redes, se `rsvg-convert` estiver instalado), schema.org (Article, Breadcrumb, FAQ, Organization, WebSite) e ads.txt (quando o AdSense é configurado).

Artigos com `date` no futuro ficam **agendados**: entram no ar no primeiro build depois da data. Para publicar todos os dias sem intervenção, agende um build diário na hospedagem (Deploy Hook + cron do GitHub Actions).

## Escrever artigos

Atalhos dentro do texto:

| Atalho | Resultado |
|---|---|
| `[[produtos]]` | bloco de afiliados com os produtos do front matter |
| `[[video]]` | vídeo do canal ligado ao artigo (data/videos.yaml) ou convite para o canal |
| `[[leia:slug]]` | caixa “Leia também” |
| `[[newsletter]]` | formulário de captura |
| `[[anuncio]]` | posição manual de anúncio |
| `[texto](@slug)` | link interno para artigo |
| `[texto](@page:sobre)` | link interno para página |

## Publicar (Cloudflare Pages, gratuito)

1. Crie um repositório no GitHub e envie esta pasta.
2. Cloudflare Pages → Create project → conecte o repositório.
   - Build command: `pip install -r requirements.txt && python3 build.py`
   - Output directory: `dist`
3. Adicione o domínio portrasdofocinho.com (registro.br) nas configurações do projeto.
4. Search Console: verifique o domínio e envie `https://portrasdofocinho.com/sitemap.xml`.

Netlify funciona igual (mesmo comando e pasta).

## Painel de administração (/admin)

Decap CMS: criar, editar, agendar e revisar artigos, produtos, vídeos e integrações, sem programar. Para ativar:
1. Troque `SEU-USUARIO/portrasdofocinho` em `static/admin/config.yml` pelo repositório real.
2. Configure o login com GitHub (OAuth): na Netlify é nativo; na Cloudflare, use um proxy OAuth para Decap (por exemplo, um Worker).
3. O fluxo editorial vem ligado: Rascunho → Em revisão → Pronto.

## Painel interno (/painel)

Projeção de receita com premissas editáveis, lançamento mensal de métricas, gerador de briefing para IA, clusters de conteúdo, pendências e plano de 30 dias. Fica fora do Google (noindex + robots.txt).

## Eventos enviados ao GA4

`affiliate_click`, `generate_lead`, `article_complete`, `share`, `search`, `video_start`. Medição e anúncios só ligam depois do consentimento (Consent Mode v2, LGPD).
