#!/usr/bin/env python3
"""
build_html_gallery.py — Emit templates/visuals-gallery/index.html, a single self-contained file.

Why generated
-------------
The gallery is the one artefact here that a human reads rather than a script. That is
exactly why its content must not live in the HTML: prose edited inside a 400 KB markup
file cannot be reviewed in a diff, cannot be checked by a validator, and will be lost the
next time anyone regenerates. So all content lives in
samples/visual-gallery-assets/{content.json,visual-catalog.json}, and this file is
disposable output - exactly as samples/pbip-visual-gallery/ is disposable output of
scripts/build_gallery_report.mjs.

Why a single file
-----------------
It is meant to be opened by double-clicking. A sibling data file fetched with fetch() is
blocked by CORS on file:// URLs - the constraint already documented in
templates/html-prototype/README.md - so the catalog is inlined as a JSON script block
rather than loaded. The one exception is the custom-visual PNGs, which are referenced
relatively: images are not CORS-restricted on file://, and inlining 169 KB of base64 to
save a path reference would make the file worse to read in review.

Native icons are inlined rather than referenced for a different reason: an <img src>
pointing at an SVG cannot inherit currentColor, so a referenced icon would be stuck on
black in a dark theme. Inlining them is what makes them theme.

Thumbnails, and what each tier claims
------------------------------------
    photo       a real image of the custom visual (DataChant AppSource export)
    icon        a generic chart-type glyph - a LABEL, not a depiction of a render
    schematic   a labelled diagram drawn by scripts/schematics.py, because no honest
                glyph exists. Marked as a schematic everywhere it appears.

The distinction is stated on the page, per card and in the legend, because a thumbnail a
reader cannot interpret as evidence is worse than no thumbnail.

Usage:
    python3 scripts/build_html_gallery.py
    python3 scripts/build_html_gallery.py --check     # fail if the output is stale
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schematics import CSS as SCHEMATIC_CSS  # noqa: E402
from schematics import svg_for  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CATALOG = REPO / "samples" / "visual-gallery-assets" / "visual-catalog.json"
ICONS = REPO / "samples" / "visual-gallery-assets" / "icons"
OUT = REPO / "templates" / "visuals-gallery" / "index.html"
EXCEPTIONS = REPO / "samples" / "visual-gallery-assets" / "EXCEPTIONS.md"

ASSET_ROOT = "../../samples/visual-gallery-assets"


class Fail(Exception):
    pass


def icon_markup(src: str) -> str:
    """Inline a vendored SVG, stripped of the upstream comment block and fixed sizing.

    The comment is dropped so the markup stays diffable; `currentColor` and the viewBox
    are kept so the glyph themes and scales. width/height are dropped so CSS controls
    the rendered size.
    """
    path = ICONS / Path(src).name
    if not path.is_file():
        raise Fail(f"catalog references a missing icon: {src}")
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()
    text = re.sub(r'\s(width|height)="\d+"', "", text, count=2)
    text = text.replace("<svg", '<svg class="thumb-icon" focusable="false" aria-hidden="true"', 1)
    return re.sub(r"\s+", " ", text)


def thumbnail(v: dict) -> tuple[str, str, str]:
    """Return (markup, tier, note) for one visual's thumbnail."""
    t = v["thumbnail"]
    tier = t["tier"]
    if tier == "photo":
        alt = f"Reference image of the {v['name']} custom visual"
        return f'<img class="thumb-photo" src="{ASSET_ROOT}/{escape(t["src"])}" alt="{escape(alt)}" loading="lazy">', tier, ""
    if tier == "schematic":
        art = svg_for(v["visualType"])
        if art:
            return art, tier, "Schematic, not a render"
    if t.get("src") and (ICONS / Path(t["src"]).name).is_file():
        return icon_markup(t["src"]), tier, ""
    return '<span class="thumb-none">no artwork</span>', "missing", "Missing"


TIER_BLURB = {
    "photo": "Reference image exported for this custom visual.",
    "icon": "Generic chart-type glyph. A label for the visual type, not a picture of a render.",
    "schematic": "Drawn here because no honest glyph exists. A diagram of what the visual encodes, not what it will look like.",
    "collision": "Shares a glyph with a related visual type; the reason is recorded on the card.",
    "missing": "No artwork resolved. This is a defect and fails verification.",
}

STYLE = """
:root{
  --bg:#ffffff; --panel:#f7f7f9; --line:#e3e3e8; --ink:#1b1b1f; --muted:#5f6368;
  --accent:#0b6bcb; --accent-soft:#e8f1fc; --warn:#8a5300; --warn-soft:#fdf3e2;
  --shadow:0 1px 2px rgba(0,0,0,.06),0 4px 14px rgba(0,0,0,.05);
}
@media (prefers-color-scheme:dark){
  :root{--bg:#141416; --panel:#1c1c20; --line:#2e2e35; --ink:#ececf1; --muted:#a0a2ab;
        --accent:#6ea8ff; --accent-soft:#16233a; --warn:#e8b465; --warn-soft:#2c2415;
        --shadow:0 1px 2px rgba(0,0,0,.4),0 4px 14px rgba(0,0,0,.3)}
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 "Segoe UI",system-ui,-apple-system,sans-serif}
code,.mono{font-family:"Cascadia Mono",Consolas,"SF Mono",monospace}
.wrap{max-width:1560px;margin:0 auto;padding:28px 24px 80px}

header.top{border-bottom:1px solid var(--line);padding-bottom:20px;margin-bottom:22px}
h1{font-size:26px;margin:0 0 6px;letter-spacing:-.01em}
.sub{color:var(--muted);max-width:78ch;margin:0 0 14px}
.counts{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px;padding:0;list-style:none}
.counts li{background:var(--panel);border:1px solid var(--line);border-radius:999px;
  padding:3px 11px;font-size:12.5px;color:var(--muted)}
.counts b{color:var(--ink);font-weight:600}

.legend{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:6px;padding:12px 15px;margin:0 0 20px}
.legend h2{font-size:13px;margin:0 0 7px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
.legend dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:0;font-size:13.5px}
.legend dt{font-weight:600}
.legend dd{margin:0;color:var(--muted)}
.legend .note{margin:10px 0 0;font-size:13px;color:var(--muted);border-top:1px solid var(--line);padding-top:9px}

.layout{display:grid;grid-template-columns:236px 1fr;gap:26px;align-items:start}
@media (max-width:900px){.layout{grid-template-columns:1fr}}
.rail{position:sticky;top:20px}
.rail h3{font-size:11.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);
  margin:0 0 7px;font-weight:600}
.rail fieldset{border:0;margin:0 0 18px;padding:0}
.rail label{display:flex;gap:8px;align-items:flex-start;padding:3px 0;font-size:13.5px;cursor:pointer}
.rail label:hover{color:var(--accent)}
.rail input{margin:2px 0 0}
.rail .n{color:var(--muted);margin-left:auto;font-size:12px;font-variant-numeric:tabular-nums}

.searchrow{display:flex;gap:12px;align-items:center;margin:0 0 16px;flex-wrap:wrap}
#q{flex:1;min-width:260px;padding:9px 12px;border:1px solid var(--line);border-radius:7px;
  background:var(--panel);color:var(--ink);font:inherit}
#q:focus{outline:2px solid var(--accent);outline-offset:-1px}
.hitcount{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;
  cursor:pointer;text-align:left;padding:0;color:inherit;font:inherit;display:flex;flex-direction:column;
  transition:border-color .12s,transform .12s}
.card:hover{border-color:var(--accent);transform:translateY(-1px)}
.card:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.card.is-hidden{display:none}

.thumb{height:132px;display:flex;align-items:center;justify-content:center;
  background:var(--bg);border-bottom:1px solid var(--line);position:relative;padding:14px}
.thumb-icon{width:62px;height:62px;color:var(--ink);opacity:.9}
.thumb-schem{width:96px;height:60px}
.thumb-photo{max-width:100%;max-height:104px;object-fit:contain}
.thumb-none{color:var(--muted);font-size:12.5px}
.tier{position:absolute;top:8px;right:8px;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
  padding:2px 7px;border-radius:4px;background:var(--bg);border:1px solid var(--line);color:var(--muted)}
.tier.schematic,.tier.collision{background:var(--warn-soft);border-color:transparent;color:var(--warn)}

.body{padding:13px 15px 15px;display:flex;flex-direction:column;gap:7px;flex:1}
.nm{font-size:15px;font-weight:600;margin:0;letter-spacing:-.005em}
.vt{font-size:11.5px;color:var(--muted);word-break:break-all;margin:0}
.badges{display:flex;gap:5px;flex-wrap:wrap}
.b{font-size:10.5px;padding:1.5px 6px;border-radius:4px;background:var(--accent-soft);color:var(--accent);white-space:nowrap}
.b.gray{background:var(--line);color:var(--muted)}
.b.warn{background:var(--warn-soft);color:var(--warn)}
.fld{font-size:13.5px;margin:0}
.fld .k{font-weight:600;display:block;font-size:11.5px;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);margin-bottom:2px}
.fld.notfor{color:var(--muted)}
.alt{margin-top:auto;padding-top:9px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--muted);display:flex;gap:6px;align-items:center;flex-wrap:wrap}

#drawer{position:fixed;inset:0;background:rgba(0,0,0,.42);display:none;padding:5vh 4vw;overflow:auto;z-index:9}
#drawer.on{display:block}
.sheet{background:var(--bg);border:1px solid var(--line);border-radius:12px;max-width:940px;
  margin:0 auto;padding:24px 26px 28px;box-shadow:var(--shadow)}
.sheet h2{margin:0 0 4px;font-size:21px}
.sheet .close{float:right;border:1px solid var(--line);background:var(--panel);color:var(--muted);
  border-radius:6px;padding:4px 10px;cursor:pointer;font:inherit;font-size:13px}
.sheet .close:hover{color:var(--accent);border-color:var(--accent)}
.kv{display:grid;grid-template-columns:150px 1fr;gap:6px 16px;margin:18px 0;font-size:13.5px}
.kv dt{color:var(--muted)}
.kv dd{margin:0;word-break:break-word}
.roles{width:100%;border-collapse:collapse;margin:8px 0 4px;font-size:13.5px}
.roles th,.roles td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line)}
.roles th{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.req{color:var(--warn)}
.bigthumb{display:flex;align-items:center;justify-content:center;background:var(--panel);
  border:1px solid var(--line);border-radius:8px;padding:18px;margin:14px 0}
.bigthumb .thumb-icon{width:88px;height:88px}
.bigthumb .thumb-schem{width:150px;height:94px}
.bigthumb .thumb-photo{max-height:220px}
.note{font-size:13px;color:var(--muted);border-left:3px solid var(--accent);padding:2px 0 2px 11px;margin:10px 0}
.note.warn{border-left-color:var(--warn);color:var(--warn)}
footer.top{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}
footer.top code{font-size:12px}
"""

APP = """
const C = window.PBI_VISUAL_CATALOG;
const $ = (s,r=document)=>r.querySelector(s);
const $$ = (s,r=document)=>[...r.querySelectorAll(s)];
const esc = s => String(s??"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

const FAMILIES = [...new Set(C.visuals.map(v=>v.family).filter(Boolean))].sort();
const ORIGINS  = [["native","Native / Power BI built-in"],["custom","Custom visual"],["excluded","Not authorable"]];

function originOf(v){ return v.kind === "custom" ? "custom" : v.kind === "excluded" ? "excluded" : "native"; }
function matches(v, st){
  if (st.origin.size && !st.origin.has(originOf(v))) return false;
  if (st.family.size && !st.family.has(v.family)) return false;
  if (st.tier.size && !st.tier.has(v.thumbnail.tier)) return false;
  if (st.authorable.size){
    const a = v.authorable ? "yes" : "no";
    if (!st.authorable.has(a)) return false;
  }
  if (st.q){
    const hay = [v.name,v.visualType,v.family,v.useWhen,v.notFor,
                 (v.roles||[]).map(r=>r.name).join(" ")].join(" ").toLowerCase();
    if (!hay.includes(st.q)) return false;
  }
  return true;
}

function rolesChips(v){
  const r = v.roles || [];
  if (!r.length) return "";
  return `<div class="badges">${r.map(x=>`<span class="b gray">${esc(x.name)}</span>`).join("")}</div>`;
}

function card(v){
  const t = v.thumbnail;
  const note = t.tier === "schematic" ? "Schematic, not a render"
             : t.tier === "collision" ? "Shared glyph"
             : t.tier === "missing" ? "No artwork" : "";
  const badges = [];
  if (v.kind === "custom"){
    badges.push(`<span class="b">Microsoft</span>`);
    if (v.certified) badges.push(`<span class="b">${esc(v.certified)}</span>`);
    if (v.version) badges.push(`<span class="b gray">v${esc(v.version)}</span>`);
  } else if (v.kind === "excluded"){
    badges.push(`<span class="b warn">Not authorable here</span>`);
  } else {
    badges.push(`<span class="b gray">Built in</span>`);
  }
  const alt = v.nativeAlternative
    ? `<div class="alt">Prefer native <code>${esc(v.nativeAlternative)}</code></div>` : "";
  return `<button class="card" data-vt="${esc(v.visualType)}" data-origin="${originOf(v)}"
     data-tier="${esc(t.tier)}" data-family="${esc(v.family)}" data-authorable="${v.authorable}"
     data-hay="${esc([v.name,v.visualType,v.family,v.useWhen,v.notFor,(v.roles||[]).map(r=>r.name).join(" ")].join(" ").toLowerCase())}">
    <div class="thumb">${t.markup}<span class="tier ${esc(t.tier)}">${esc(t.tier)}</span></div>
    <div class="body">
      <p class="nm">${esc(v.name)}</p>
      <p class="vt mono">${esc(v.visualType)}</p>
      <div class="badges">${badges.join("")}</div>
      ${rolesChips(v)}
      <p class="fld"><span class="k">Use when</span>${esc(v.useWhen)}</p>
      ${v.notFor ? `<p class="fld notfor"><span class="k">Not for</span>${esc(v.notFor)}</p>` : ""}
      ${alt}
    </div></button>`;
}

function drawer(v){
  const t = v.thumbnail;
  const roles = (v.roles||[]).length ? `<table class="roles"><thead><tr>
      <th>Role</th><th>Kind</th><th>Required</th></tr></thead><tbody>${
      v.roles.map(r=>`<tr><td class="mono">${esc(r.name)}</td><td>${esc(r.kind||"-")}</td>
        <td class="${r.required?"req":""}">${r.required?"yes":"no"}</td></tr>`).join("")}</tbody></table>`
    : `<p class="note">This visual takes no data roles. It renders chrome or a fixed layout rather than bound data.</p>`;
  const why = t.tier === "schematic"
    ? `<p class="note warn">This thumbnail is a <strong>schematic</strong>, not a rendered Power BI visual. It shows what the visual encodes, not what it will look like with your data.</p>`
    : t.tier === "collision"
    ? `<p class="note warn">This glyph is shared with a related visual type. ${esc(t.reason||"")}</p>`
    : t.tier === "icon"
    ? `<p class="note">This is a generic chart-type glyph. It labels the visual type; it is not a picture of a Power BI render.</p>` : "";
  const excl = v.kind === "excluded"
    ? `<p class="note warn"><strong>Not authorable here.</strong> ${esc(v.exclusionReason)}</p>` : "";
  return `<div class="sheet" role="dialog" aria-modal="true" aria-label="${esc(v.name)}">
    <button class="close" id="close">Close</button>
    <h2>${esc(v.name)}</h2>
    <p class="vt mono">${esc(v.visualType)}</p>
    <div class="bigthumb">${t.markup}</div>
    ${why}${excl}
    <dl class="kv">
      <dt>Origin</dt><dd>${v.kind === "custom" ? "Microsoft-published custom visual"
        : v.kind === "excluded" ? "Catalogued but withheld" : "Power BI built-in"}</dd>
      <dt>Family</dt><dd>${esc(v.family || "-")}</dd>
      ${v.publisher ? `<dt>Publisher</dt><dd>${esc(v.publisher)}</dd>` : ""}
      ${v.certified ? `<dt>Certified</dt><dd>${esc(v.certified)}</dd>` : ""}
      ${v.version ? `<dt>Package version</dt><dd class="mono">${esc(v.version)}</dd>` : ""}
      ${v.provenance?.sourceCommit ? `<dt>Source commit</dt><dd class="mono">${esc(v.provenance.sourceCommit.slice(0,12))}</dd>` : ""}
      <dt>Demonstrated on</dt><dd>${v.demoPage ? esc(v.demoPage)
        : v.galleryPages?.length ? `${v.galleryPages.length} pages` : "not in the gallery"}</dd>
    </dl>
    <p class="fld"><span class="k">Use when</span>${esc(v.useWhen)}</p>
    ${v.notFor ? `<p class="fld notfor"><span class="k">Not for</span>${esc(v.notFor)}</p>` : ""}
    ${v.nativeAlternative ? `<p class="fld"><span class="k">Native alternative</span><code>${esc(v.nativeAlternative)}</code></p>` : ""}
    <h3 style="font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:20px 0 0">Data roles</h3>
    ${roles}
  </div>`;
}

const state = {origin:new Set(), family:new Set(), tier:new Set(), authorable:new Set(), q:""};
const byType = Object.fromEntries(C.visuals.map(v=>[v.visualType,v]));

function apply(){
  let n = 0;
  $$(".card").forEach(el=>{
    const v = byType[el.dataset.vt];
    const ok = matches(v, state);
    el.classList.toggle("is-hidden", !ok);
    if (ok) n++;
  });
  $("#hitcount").textContent = n === C.visuals.length
    ? `${n} visuals` : `${n} of ${C.visuals.length} visuals`;
}

function buildRail(){
  const mk = (title, items, bucket) => {
    const box = document.createElement("fieldset");
    box.innerHTML = `<h3>${title}</h3>` + items.map(([val,label,n]) =>
      `<label><input type="checkbox" data-bucket="${bucket}" value="${esc(val)}">
        <span>${esc(label)}</span><span class="n">${n}</span></label>`).join("");
    $("#rail").appendChild(box);
  };
  mk("Origin", ORIGINS.map(([v,l])=>[v,l,C.visuals.filter(x=>originOf(x)===v).length]), "origin");
  mk("Authorable", [["yes","Can author",C.visuals.filter(v=>v.authorable).length],
                    ["no","Cannot",C.visuals.filter(v=>!v.authorable).length]], "authorable");
  mk("Family", FAMILIES.map(f=>[f,f,C.visuals.filter(v=>v.family===f).length]), "family");
  mk("Thumbnail", [...new Set(C.visuals.map(v=>v.thumbnail.tier))]
      .sort().map(t=>[t,t,C.visuals.filter(v=>v.thumbnail.tier===t).length]), "tier");

  $("#rail").addEventListener("change", e=>{
    const b = e.target.dataset.bucket;
    if (!b) return;
    e.target.checked ? state[b].add(e.target.value) : state[b].delete(e.target.value);
    apply();
  });
}

function wire(){
  $("#q").addEventListener("input", e=>{ state.q = e.target.value.trim().toLowerCase(); apply(); });
  $("#grid").addEventListener("click", e=>{
    const card = e.target.closest(".card");
    if (!card) return;
    const v = byType[card.dataset.vt];
    const d = $("#drawer");
    d.innerHTML = drawer(v);
    d.classList.add("on");
    d.onclick = ev => { if (ev.target === d || ev.target.id === "close") close(); };
    document.addEventListener("keydown", escClose);
  });
  const close = ()=>{
    const d = $("#drawer");
    d.classList.remove("on"); d.innerHTML = "";
    document.removeEventListener("keydown", escClose);
  };
  const escClose = ev => { if (ev.key === "Escape") close(); };
  $("#reset").addEventListener("click", ()=>{
    Object.values(state).forEach(v => v.clear?.());
    state.q = ""; $("#q").value = "";
    $$("#rail input").forEach(i => i.checked = false);
    apply();
  });
}

buildRail();
wire();
apply();
"""


def origin_of(v: dict) -> str:
    return "custom" if v["kind"] == "custom" else ("excluded" if v["kind"] == "excluded" else "native")


def card(v: dict) -> str:
    """Server-rendered card markup.

    The card is rendered here rather than in the browser so the page has real content
    with JavaScript disabled - the filter rail and drawer enhance it, they are not what
    makes it readable. The same fields the JS reads off data-* are used for the initial
    paint so the two cannot disagree.
    """
    badges = []
    if v["kind"] == "custom":
        badges.append('<span class="b">Microsoft</span>')
        if v.get("certified"):
            badges.append(f'<span class="b">{escape(v["certified"])}</span>')
        if v.get("version"):
            badges.append(f'<span class="b gray">v{escape(v["version"])}</span>')
    elif v["kind"] == "excluded":
        badges.append('<span class="b warn">Not authorable here</span>')
    else:
        badges.append('<span class="b gray">Built in</span>')

    roles = "".join(f'<span class="b gray">{escape(r["name"])}</span>' for r in (v.get("roles") or []))
    chips = f'<div class="badges">{roles}</div>' if roles else ""
    alt = (f'<div class="alt">Prefer native <code>{escape(v["nativeAlternative"])}</code></div>'
           if v.get("nativeAlternative") else "")
    notfor = (f'<p class="fld notfor"><span class="k">Not for</span>{escape(v["notFor"])}</p>'
              if v.get("notFor") else "")

    return f"""<button class="card" data-vt="{escape(v['visualType'])}" data-origin="{origin_of(v)}"
     data-tier="{escape(v['thumbnail']['tier'])}" data-family="{escape(v.get('family') or '')}"
     data-authorable="{'true' if v['authorable'] else 'false'}">
  <div class="thumb">{v['thumbnail']['markup']}<span class="tier {escape(v['thumbnail']['tier'])}">{escape(v['thumbnail']['tier'])}</span></div>
  <div class="body">
    <p class="nm">{escape(v['name'])}</p>
    <p class="vt mono">{escape(v['visualType'])}</p>
    <div class="badges">{''.join(badges)}</div>
    {chips}
    <p class="fld"><span class="k">Use when</span>{escape(v.get('useWhen') or '')}</p>
    {notfor}
    {alt}
  </div>
</button>"""


def build() -> str:
    if not CATALOG.is_file():
        raise Fail(f"catalog missing: {CATALOG.relative_to(REPO)}. Run scripts/build_visual_catalog.py")
    doc = json.loads(CATALOG.read_text(encoding="utf-8"))

    prepared = []
    for v in doc["visuals"]:
        markup, tier, _ = thumbnail(v)
        v = dict(v, thumbnail=dict(v["thumbnail"], markup=markup))
        prepared.append(v)

    c = doc["counts"]
    cards = "\n".join(card(v) for v in prepared)
    catalog_json = json.dumps({**doc, "visuals": prepared}, indent=1, ensure_ascii=False).replace("</", "<\\/")

    legend_rows = "\n".join(
        f"<dt>{t}</dt><dd>{escape(TIER_BLURB[t])}</dd>"
        for t in ("photo", "icon", "schematic", "collision") if any(v["thumbnail"]["tier"] == t for v in prepared)
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Power BI visual gallery &mdash; {c['native'] + c['custom']} visuals</title>
<style>{STYLE}{SCHEMATIC_CSS}</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <h1>Power BI visual gallery</h1>
  <p class="sub">Every visual this project can author, with the data roles it takes and the
  substitution rule that should stop you reaching for it. Filter by origin, family or
  thumbnail; the text boxes are searchable. Open a card for the full detail.</p>
  <ul class="counts">
    <li><b>{c['native']}</b> native</li>
    <li><b>{c['custom']}</b> custom, all Microsoft-published</li>
    <li><b>{c['excluded']}</b> catalogued but not authorable here</li>
    <li><b>{c['thumbPhoto']}</b> reference images</li>
    <li><b>{c['thumbSchematic']}</b> schematics</li>
  </ul>
  <div class="legend">
    <h2>What a thumbnail is, and is not</h2>
    <dl>
      {legend_rows}
    </dl>
    <p class="note">No thumbnail here is a screenshot of Power BI. Native visuals are labelled with
    generic chart-type glyphs from Tabler Icons (MIT); custom visuals carry a reference image
    exported from AppSource. Where a glyph would mislead, the thumbnail is a drawn schematic and
    says so. To see an actual render, open the sample gallery at
    <code>samples/pbip-visual-gallery/VisualGallery.pbip</code>.</p>
  </div>
</header>

<div class="layout">
  <aside class="rail"><div id="rail"></div>
    <button id="reset" class="b gray" style="border:1px solid var(--line);border-radius:6px;padding:5px 11px;cursor:pointer;font:inherit;font-size:13px;background:var(--panel);color:var(--muted)">Clear filters</button>
  </aside>
  <main>
    <div class="searchrow">
      <input id="q" type="search" placeholder="Search name, visualType, family, role&hellip;" aria-label="Search visuals">
      <span class="hitcount" id="hitcount"></span>
    </div>
    <div class="grid" id="grid">
{cards}
    </div>
  </main>
</div>

<footer class="top">
  Generated by <code>scripts/build_html_gallery.py</code> &mdash; do not edit. Content comes from
  <code>samples/visual-gallery-assets/content.json</code> (authored prose) and
  <code>visual-catalog.json</code> (derived). Regenerate with
  <code>python3 scripts/build_html_gallery.py</code>.
  Custom visuals additionally need <code>python3 scripts/fetch_gallery_assets.py</code> followed by
  <code>python3 scripts/extract_custom_visuals.py</code> before the sample report can render them.
</footer>
</div>

<div id="drawer"></div>
<script>window.PBI_VISUAL_CATALOG = {catalog_json};</script>
<script>{APP}</script>
</body>
</html>
"""


def write_exceptions(doc: dict) -> int:
    """List every visual whose representation is a stand-in, for human review.

    These are the entries a maintainer might want to replace with a real render: the
    schematic tier and the shared-glyph tier. Nothing here is a build failure - they are
    recorded decisions - but they are the honest TODO list.
    """
    flagged = [v for v in doc["visuals"] if v["thumbnail"]["tier"] in ("schematic", "collision", "missing")]
    lines = [
        "# Thumbnail exceptions",
        "",
        "Generated by `scripts/build_html_gallery.py`. Do not hand-edit.",
        "",
        "These visuals do not have an honest single-glyph stand-in, so their thumbnail is",
        "either a drawn schematic or a glyph shared with a sibling type. None of this is a",
        "build failure - each entry records a decision - but this is the list to work through",
        "if a real render is wanted. Each needs a `.pbix` opened in Desktop to capture from,",
        "or a decision that the stand-in is good enough.",
        "",
        f"{len(flagged)} of {len(doc['visuals'])} visuals: "
        f"{sum(1 for v in flagged if v['thumbnail']['tier'] == 'schematic')} schematic, "
        f"{sum(1 for v in flagged if v['thumbnail']['tier'] == 'collision')} shared glyph, "
        f"{sum(1 for v in flagged if v['thumbnail']['tier'] == 'missing')} missing.",
        "",
    ]
    for tier, heading in (("schematic", "Schematic - drawn because no honest glyph exists"),
                          ("collision", "Shared glyph - no distinct glyph exists"),
                          ("missing", "Missing - no artwork resolved, this is a defect")):
        rows = [v for v in flagged if v["thumbnail"]["tier"] == tier]
        if not rows:
            continue
        lines += [f"## {heading}", "", "| Visual | `visualType` | Thumbnail | Why |", "|---|---|---|---|"]
        for v in sorted(rows, key=lambda x: x["visualType"]):
            t = v["thumbnail"]
            src = f"`tabler:{t['icon']}`" if t.get("icon") else "-"
            lines.append(f"| {v['name']} | `{v['visualType']}` | {src} | {t.get('reason', '')} |")
        lines.append("")
    EXCEPTIONS.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return len(flagged)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed output is not what this script produces")
    args = ap.parse_args(argv)

    try:
        html = build()
    except Fail as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != html:
            print(f"[FAIL] {OUT.relative_to(REPO)} is stale. Run scripts/build_html_gallery.py")
            return 1
        print("[PASS] index.html is up to date.")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8", newline="\n")
    doc = json.loads(CATALOG.read_text(encoding="utf-8"))
    flagged = write_exceptions(doc)

    print(f"[PASS] {OUT.relative_to(REPO)}  ({OUT.stat().st_size:,} B)")
    print(f"       {len(doc['visuals'])} visuals, {flagged} recorded as thumbnail exceptions")
    print(f"       {EXCEPTIONS.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))