import html
import json
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CATEGORIES = [
    ("Bioinformatics", "Genomics, single-cell, sequencing, and molecular biology workflows."),
    ("Analysis & modeling", "Statistics, machine learning, simulation, and reproducible computation."),
    ("Research communication", "Literature, scientific writing, figures, posters, and presentations."),
    ("Lab & data systems", "Instrumentation, databases, imaging, and laboratory automation."),
]


def get_skills():
    skills_dir = ROOT / "skills"
    skills = []
    if skills_dir.exists():
        for folder in sorted(skills_dir.iterdir()):
            skill_file = folder / "SKILL.md"
            if folder.is_dir() and skill_file.exists():
                title = folder.name.replace("-", " ").title()
                text = skill_file.read_text(encoding="utf-8", errors="ignore")
                description = "Specialized guidance for reproducible scientific research workflows."
                for line in text.splitlines():
                    if line.lower().startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip('"')
                        break
                skills.append({"name": folder.name, "title": title, "description": description})
    return skills


def page():
    skills = get_skills()
    skill_json = json.dumps(skills).replace("</", "<\\/")
    cards = "".join(
        f'<a class="skill-card" href="https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/{html.escape(item["name"])}">'
        f'<span class="card-kicker">SKILL</span><h3>{html.escape(item["title"])}</h3><p>{html.escape(item["description"])}</p><span class="card-link">Explore workflow <b>↗</b></span></a>'
        for item in skills[:12]
    )
    category_cards = "".join(
        f'<button class="category" data-category="{html.escape(name.lower())}"><span class="category-dot"></span><strong>{html.escape(name)}</strong><small>{html.escape(desc)}</small></button>'
        for name, desc in CATEGORIES
    )
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scientific Agent Skills</title>
<style>
:root {{ --ink:#18221f; --muted:#68746f; --paper:#f5f7f3; --card:#ffffff; --line:#dce4de; --green:#176b52; --mint:#d9eee3; --amber:#e8a94e; }}
* {{ box-sizing:border-box }} body {{ margin:0; background:var(--paper); color:var(--ink); font-family:Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; }}
a {{ color:inherit; text-decoration:none }} button,input {{ font:inherit }}
.shell {{ max-width:1180px; margin:0 auto; padding:26px 28px 70px; }}
.nav {{ display:flex; align-items:center; justify-content:space-between; gap:24px; margin-bottom:76px; }}
.brand {{ display:flex; align-items:center; gap:12px; font-weight:800; letter-spacing:-.03em; }}
.mark {{ width:32px; height:32px; display:grid; place-items:center; border-radius:10px; background:var(--green); color:#fff; font-size:15px; }}
.nav-links {{ display:flex; gap:28px; color:var(--muted); font-size:14px; }}
.nav-links a:hover {{ color:var(--green) }} .github {{ border:1px solid var(--line); padding:10px 15px; border-radius:999px; color:var(--green); font-weight:700; font-size:14px; }}
.hero {{ max-width:870px; }} .eyebrow {{ color:var(--green); text-transform:uppercase; letter-spacing:.16em; font-weight:800; font-size:11px; margin-bottom:18px; }}
h1 {{ margin:0; font-size:clamp(44px, 7vw, 84px); line-height:.98; letter-spacing:-.075em; max-width:800px; }}
.hero-copy {{ margin:25px 0 34px; color:var(--muted); font-size:18px; line-height:1.6; max-width:650px; }}
.hero-actions {{ display:flex; flex-wrap:wrap; gap:12px; }} .primary {{ background:var(--green); color:#fff; border-radius:8px; padding:14px 18px; font-weight:800; }} .secondary {{ color:var(--green); border:1px solid var(--line); background:#fff; border-radius:8px; padding:14px 18px; font-weight:800; }}
.stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:1px; background:var(--line); border:1px solid var(--line); margin:76px 0 74px; }} .stat {{ background:var(--card); padding:22px 24px; }} .stat strong {{ display:block; font-size:28px; letter-spacing:-.05em; }} .stat span {{ color:var(--muted); font-size:13px; }}
.section-head {{ display:flex; justify-content:space-between; align-items:end; gap:24px; margin-bottom:22px; }} h2 {{ margin:0; font-size:30px; letter-spacing:-.05em; }} .section-head p {{ color:var(--muted); margin:0; font-size:14px; }}
.categories {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:74px; }} .category {{ text-align:left; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; color:var(--ink); cursor:pointer; min-height:142px; transition:.2s; }} .category:hover,.category.active {{ border-color:var(--green); transform:translateY(-2px); box-shadow:0 8px 20px #315e4812; }} .category-dot {{ display:block; width:9px; height:9px; border-radius:50%; background:var(--amber); margin-bottom:20px; }} .category:nth-child(2) .category-dot {{ background:#6a91c9 }} .category:nth-child(3) .category-dot {{ background:#a97ac2 }} .category:nth-child(4) .category-dot {{ background:#5aa69c }} .category strong {{ display:block; font-size:14px; margin-bottom:7px; }} .category small {{ display:block; color:var(--muted); font-size:12px; line-height:1.45; }}
.toolbar {{ display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:18px; }} .search {{ width:280px; padding:12px 14px; border:1px solid var(--line); border-radius:8px; background:#fff; outline:none; }} .search:focus {{ border-color:var(--green); box-shadow:0 0 0 3px var(--mint); }}
.grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }} .skill-card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:22px; min-height:204px; transition:.2s; }} .skill-card:hover {{ border-color:var(--green); transform:translateY(-2px); }} .card-kicker {{ color:var(--green); letter-spacing:.14em; font-size:10px; font-weight:800; }} h3 {{ margin:13px 0 8px; font-size:19px; letter-spacing:-.03em; }} .skill-card p {{ color:var(--muted); font-size:13px; line-height:1.5; margin:0 0 20px; }} .card-link {{ color:var(--green); font-size:12px; font-weight:800; }} .card-link b {{ margin-left:4px; }} .empty {{ grid-column:1/-1; color:var(--muted); padding:30px 0; }}
.footer {{ border-top:1px solid var(--line); margin-top:80px; padding-top:22px; display:flex; justify-content:space-between; color:var(--muted); font-size:12px; }}
@media(max-width:800px) {{ .shell {{ padding:20px 18px 48px }} .nav {{ margin-bottom:52px }} .nav-links {{ display:none }} .categories,.grid {{ grid-template-columns:repeat(2,1fr) }} .stats {{ margin:54px 0 }} }} @media(max-width:520px) {{ h1 {{ font-size:47px }} .categories,.grid,.stats {{ grid-template-columns:1fr }} .toolbar,.section-head {{ align-items:flex-start; flex-direction:column }} .search {{ width:100% }} .footer {{ flex-direction:column; gap:8px }} }}
</style></head>
<body><main class="shell">
<nav class="nav"><a class="brand" href="/"><span class="mark">✦</span> Scientific Agent Skills</a><div class="nav-links"><a href="#domains">Domains</a><a href="#skills">Skill library</a><a href="https://agentskills.io/">Standard</a></div><a class="github" href="https://github.com/K-Dense-AI/scientific-agent-skills">View on GitHub</a></nav>
<section class="hero"><div class="eyebrow">Procedural knowledge for research agents</div><h1>Make scientific work more reproducible.</h1><p class="hero-copy">A curated library of practical skills that helps AI agents use scientific packages, databases, and research workflows with the right conventions, caveats, and validation checks.</p><div class="hero-actions"><a class="primary" href="#skills">Browse the library</a><a class="secondary" href="https://github.com/K-Dense-AI/scientific-agent-skills#-getting-started">Get started →</a></div></section>
<section class="stats"><div class="stat"><strong>177</strong><span>research skills</span></div><div class="stat"><strong>100+</strong><span>scientific databases</span></div><div class="stat"><strong>1</strong><span>open standard for agents</span></div></section>
<section id="domains"><div class="section-head"><div><h2>Explore by domain</h2></div><p>Start from the kind of work you need to do.</p></div><div class="categories">{category_cards}</div></section>
<section id="skills"><div class="section-head"><h2>Featured skills</h2><p>Versioned guidance, examples, and checks.</p></div><div class="toolbar"><span id="result-count" style="color:var(--muted);font-size:13px">Showing 12 featured skills</span><input class="search" id="search" placeholder="Search the library" aria-label="Search skills"></div><div class="grid" id="skill-grid">{cards}</div></section>
<footer class="footer"><span>Scientific Agent Skills · v2.72.0</span><span>Built for compatible AI agents and researchers</span></footer>
</main><script>const skills={skill_json};const grid=document.querySelector('#skill-grid');const search=document.querySelector('#search');const count=document.querySelector('#result-count');function render(query=''){{const filtered=skills.filter(s=>(s.title+' '+s.description).toLowerCase().includes(query.toLowerCase()));count.textContent=`Showing ${{filtered.length}} ${{filtered.length === 1 ? 'skill' : 'skills'}}`;grid.innerHTML=filtered.slice(0,24).map(s=>`<a class="skill-card" href="https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/${{s.name}}"><span class="card-kicker">SKILL</span><h3>${{s.title}}</h3><p>${{s.description}}</p><span class="card-link">Explore workflow <b>↗</b></span></a>`).join('')||'<div class="empty">No skills match that search.</div>'}}search.addEventListener('input',e=>render(e.target.value));document.querySelectorAll('.category').forEach(button=>button.addEventListener('click',()=>{{search.value=button.querySelector('strong').textContent;render(search.value);document.querySelector('#skills').scrollIntoView({{behavior:'smooth'}})}}));</script></body></html>'''


class handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(encoded)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api" or path.startswith("/api/"):
            payload = {"status": "ok", "service": "app", "skill_count": len(get_skills())}
            self._send(200, json.dumps(payload), "application/json; charset=utf-8")
            return
        if path != "/" and path.endswith("/"):
            self._send(404, json.dumps({"error": "Not found"}), "application/json; charset=utf-8")
            return
        self._send(200, page(), "text/html; charset=utf-8")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET, HEAD, OPTIONS")
        self.end_headers()
