"""Build ignored print intermediates from synthetic instrument editorial data."""

import argparse
import base64
import hashlib
import html
import io
import json
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
CORPUS = Path(__file__).resolve().parents[1]
HTML = ROOT / ".workshop" / "instrument-corpus" / "html"
CACHE = ROOT / ".workshop" / "instrument-corpus" / "images"
SHARED = ROOT / "docs" / "assets" / "html-docs"


def paragraphs(text):
    return "".join(f"<p>{html.escape(part.strip())}</p>" for part in text.strip().split("\n\n"))


def chapters(x):
    name, model, factory = x["name"].lower(), x["flagship"], x["factory"]
    first, launch, company = x["first"], x["launch"], "Aster Vale Instruments"
    models = f"{x['code']}-100 Foundation, {x['code']}-200 Atelier and {model}"
    stage_story = " ".join(
        f"At {stage.lower()}, the technician must {detail}."
        for stage, detail in zip(x["stages"], x["stage_details"], strict=True)
    )
    return [
        ("history", "A workshop history, not a generic instrument",
         f"""
The {name} occupies a distinct place in the {company} catalogue. The company was founded in 1958 as a fictional repair workshop and gradually became a manufacturer. Its first model in this instrument family appeared in {first}, rather than at the company's founding. Today production belongs to {factory}, line {x['line']}. That assignment identifies the responsible workshop, not a retailer or a place where a famous performance happened. All names and records in this dossier belong to the synthetic Aster Vale setting.

The broader instrument tradition provides context rather than a claim of invention. Our design draws on {x['heritage']}. In the current instrument, {x['mechanism']}. Aster Vale did not invent that operating principle. Its contribution in this catalogue is a particular production and service approach: {x['innovation']}. A buyer comparing brands should distinguish an established acoustic principle from a model-specific construction detail.

{x['history']} These events explain why the current flagship looks and behaves as it does. They are internal milestones in the fictional company's history, not dates for the invention of the instrument itself. Earlier instruments remain eligible for assessment, but a modern replacement part is not assumed to fit an older production series merely because the family name is the same.

The current range consists of {models}. Foundation is the access model, Atelier adds individual fitting time, and the 300-series flagship receives the longest voicing and final assessment. None is a miniature or a different instrument family. The shared nominal {x['dimension'].lower()} is {x['base']} across these three standard configurations. A dealer must not infer a shorter scale or smaller cabinet from the lower price.

The design compromise is deliberate: {x['tradeoff']}. The company therefore avoids describing one material or one number as a universal quality score. An instrument can pass its dimensional specification and still require a setup suited to the player. Conversely, a player may prefer a lower-priced configuration because its response fits a particular room, technique or transport routine. The model ladder is a selection aid, not a ranking of musicians.

The history also explains our service policy. The documented repair emphasis is {x['service']}, supported by a serial-based parts record. Changes made in a later revision are not quietly attributed to an earlier model. A repairer records whether the instrument remains in its original configuration or has received an approved update. That distinction matters when a performer, dealer and workshop discuss the same instrument using different informal names.

"""),
        ("performers", "The player problem shapes the flagship",
         f"""
In the fictional Aster Vale music scene, {x['artist']} is the best-known advocate of {model}. The performer works with {x['ensemble']} and used the model for {x['event']}. This is an invented endorsement within the training setting, not a claim about a real artist. The useful part of the story is the playing requirement: {x['need']}. That requirement gives a concrete reason to discuss response rather than relying on a decorative celebrity name.

The session brief asked the workshop to preserve that musical outcome at both rehearsal and performance levels. The technician began with the standard instrument, documented the player's setup and changed only one variable at a time. The team did not turn an artist's preference into a new factory limit. The release specification remained the same; the performer record described the adjustments and accessories used for this particular engagement.

A second fictional performer, {x['second_artist']}, uses this family for {x['second_use']}. The two stories are intentionally different. A setting that supports the first brief may not be ideal for the second. A dealer should therefore ask about venue, ensemble, typical dynamics and maintenance access before recommending the flagship. The correct question is which response the player needs, not which performer has the most recognizable name.

Our comparison passage starts gently, reaches the player's normal performance level and returns to a quiet ending. The listener pays attention to onset, continuity and decay, not simply maximum loudness. The player repeats the passage on Foundation, Atelier and {model}, with rest between attempts. The sequence can be reversed to reduce the influence of fatigue or expectation. A higher list price is not revealed as a cue before the listening comparison.

The flagship's characteristic serviceable feature is {x['innovation']}. In the artist programme, the workshop explains what this feature does and what it does not do. It supports repeatable construction or service, but it does not replace musical technique. It also does not guarantee a particular recorded tone in an unknown room. The performer remains responsible for the artistic choice; the workshop remains responsible for the documented instrument condition.

An artist loan is checked before dispatch and again on return. The record includes the serial, model revision, accessories, visible condition and the agreed setup. Changes made on tour are recorded rather than silently reset. The celebrated performance establishes a narrative about use, while the return inspection establishes the physical condition of that instrument. Neither replaces the production acceptance checks described in the quality section of this dossier.
"""),
        ("manufacturing", f"{factory} owns the complete build route",
         f"""
Production of the {name} is assigned to {factory}, line {x['line']}. The current material specification uses {x['materials']}. Incoming material is identified before it reaches the bench. A supplier description alone is not an acceptance record: the workshop checks the features relevant to this family and records the batch that entered the instrument. Finish and cosmetic matching happen later, after the parts have passed their structural checks.

The route has six named stages, and their order is part of the manufacturing record. {stage_story} A later stage cannot erase a missing earlier inspection. When a technician finds a problem, the traveller records which operation needs correction and which downstream checks must be repeated. That makes the route useful for a repair conversation as well as for production planning.

At {x['stages'][4].lower()}, the workshop establishes the player's working setup rather than simply making the instrument look finished. The technician must {x['stage_details'][4]}. That operation is performed with the specified parts and accessories, not whatever happens to be available at the bench. A substitution is documented and evaluated as a substitution. It is not folded into the standard model record as though nothing changed.

The final route operation is {x['stages'][5].lower()}. Its purpose is to expose a functional problem before packing, after the earlier operations have established the correct geometry. The workshop must {x['stage_details'][5]}. A failure at this point returns the instrument to the relevant operation, followed by another complete final assessment. The route diagram later in this dossier shows that return path explicitly rather than hiding it behind a success-only production arrow.

The three current models use different direct bench-time allowances: {x['hours'][0]} hours for Foundation, {x['hours'][1]} for Atelier and {x['hours'][2]} for {model}. Those are synthetic planning figures for hands-on work, not calendar lead times. Conditioning, curing, settling, queueing and shipping can extend elapsed time substantially. A dealer cannot convert a forty-hour bench estimate into a promise of delivery within one working week.

The manufacturing record closes only when the serial, material batches, model revision and acceptance decision agree. The packing team receives a released instrument, not an open repair job. If a unit is held for rework, it remains physically separated from released stock and cannot be borrowed to fill a dealer order. That boundary preserves the meaning of the factory name and the quality claims attached to {model}.
"""),
        ("quality", "Acceptance measures function, not prestige",
         f"""
The most useful quality question for the {name} is whether it performs its intended function in a known condition. Aster Vale uses {x['test']}. The family-specific acceptance rule is: {x['limit']}. These are invented workshop criteria for the synthetic catalogue, not an industry standard or independent certification. A released instrument has passed the documented route with the recorded setup; it has not been guaranteed to satisfy every possible player.

The recurring fault to watch for is {x['defect']}. A cosmetic inspection can miss this problem, which is why the functional check is separate. When the defect is observed, the instrument is held for investigation. The technician records the symptom before adjusting parts, because an undocumented adjustment can remove evidence of the original cause and make a later recurrence harder to diagnose.

An instrument's response and its dimensional compliance are related but different. For this family, {x['tradeoff']}. The acceptance route controls the production condition; the player comparison controls suitability for a musical brief. That distinction helps explain why {x['artist']} selected {model} for {x['event']} without implying that every Foundation instrument is defective or every flagship is automatically the right choice.

The nominal mass of the current configurations is {x['weights'][0]} kg for Foundation, {x['weights'][1]} kg for Atelier and {x['weights'][2]} kg for {model}. These catalogue figures exclude the transport case and accessories. They are not the force applied in a test or the shipping weight billed by a carrier. Material variation can affect an individual unit, so lifting and transport decisions use the actual instrument and case rather than a rounded catalogue value alone.

In the synthetic 2025 service record, this family shipped {x['units'][-1]} units and logged {x['returns'][-1]} 90-day service returns from that shipment cohort. A service return means an instrument was presented for assessment within ninety days of dispatch. This observation window is closed for the full 2025 cohort by this edition. It does not mean every return was a manufacturing defect or include future repairs. Returns can include setup requests, transport damage or wear.

Do not use the rising shipment curve as proof that sound quality improved. Shipments reflect orders and capacity, while the return record reflects a defined service observation window. The chart and its definitions are separate from the acceptance criteria. To assess a particular instrument, request the serial-specific release record, repeat the family check and compare the observed symptom with the documented setup before making a repair or warranty decision.
"""),
        ("ownership", "Choose, maintain and service a known configuration",
         f"""
Choose a {name} by starting with the musical and practical brief. Ask whether the instrument must support {x['need']}, whether it will travel regularly and who will maintain it. The three current configurations are {models}. Their synthetic euro list prices are EUR {x['prices'][0]:,}, EUR {x['prices'][1]:,} and EUR {x['prices'][2]:,}, respectively. These prices exclude tax, transport, cases and optional accessories, and are not offers from a real seller.

Foundation provides the shared operating geometry with the shortest individual fitting allowance. Atelier adds time for matching and adjustment. The 300-series flagship receives the most extended final assessment and the documented flagship configuration. All three have the nominal {x['dimension'].lower()} of {x['base']}. The specification table should be read by model row: a price from one row must not be combined with the mass or bench hours from another.

Before taking delivery, compare the instrument identity with the release record and inspect it with the dealer. Look for {x['defect']}, while recognizing that some causes require the specialist checks described earlier. Ask the dealer to demonstrate the relevant functional test rather than assuming an unmarked exterior proves acceptance. Record the agreed setup so that a later service discussion begins from a known condition instead of an impression formed after transport.

The routine care instruction is specific: {x['care']} It supports stable use but does not authorize invasive repair. A player should stop when a part binds, a joint moves unexpectedly or a response changes abruptly. Continued force can turn an adjustable problem into structural damage. Contact the dealer or an appropriate instrument technician and describe the observed symptom, the recent conditions and any changes in accessories.

The principal supported service operations are {x['service']}. A service request includes the serial, model revision, date of observation and a concise account of the symptom. Mention whether the instrument has travelled, changed climate or received a different setup. Do not describe a presumed internal cause as an established diagnosis. The technician compares the symptom with the original acceptance condition before deciding which part of the production or service route to revisit.

The fictional standard warranty lasts 24 months from dealer handover and covers confirmed manufacturing defects. Wear items, routine regulation, accidental damage and unapproved modifications are excluded. A 90-day service return in the infographic is therefore not automatically a warranty claim. The dealer documents the assessment outcome and explains the proposed work before authorization. The instrument remains the owner's property during assessment; a workshop hold is not a transfer of ownership.

"""),
    ]


CSS = """
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font-sans)}
a{color:var(--accent)}a:focus-visible,button:focus-visible{outline:3px solid var(--focus);outline-offset:4px}
.controls{position:sticky;top:0;z-index:4;background:var(--surface);border-bottom:1px solid var(--border);padding:12px 24px;display:flex;gap:20px;align-items:center}
button{font:inherit;color:var(--text);background:var(--surface-2);border:1px solid var(--border-strong);border-radius:5px;padding:8px 14px;cursor:pointer}
.page{width:210mm;min-height:297mm;margin:24px auto;padding:16mm 17mm 14mm;background:var(--surface);box-shadow:var(--shadow-2);position:relative}
.running{font-size:9pt;color:var(--text-muted);display:flex;justify-content:space-between;gap:10px;border-bottom:1px solid var(--border);padding-bottom:10px;margin-bottom:22px}
.eyebrow{color:var(--accent);font-size:10pt;font-weight:700;letter-spacing:.12em;text-transform:uppercase}
h1{font-size:35pt;line-height:1.1;letter-spacing:-.035em;margin:16px 0}h2{font-size:24pt;line-height:1.14;letter-spacing:-.025em;margin:12px 0 24px;max-width:95%}
h3{font-size:13pt;line-height:1.25;margin:0 0 12px}.lead{font-size:15pt;line-height:1.5}.prose{column-count:2;column-gap:8mm;font-size:10.8pt;line-height:1.48;text-align:left}
.prose p{margin:0 0 12px;orphans:3;widows:3}.prose p:first-child{margin-top:0}.prose.single{column-count:1;font-size:11.1pt;line-height:1.52}
.footer{position:absolute;bottom:10mm;left:17mm;right:17mm;border-top:1px solid var(--border);padding-top:8px;display:flex;justify-content:space-between;font-size:8pt;color:var(--text-muted)}
.hero{width:100%;height:125mm;object-fit:contain;background:#fff;border-radius:8px}.caption{font-size:9pt;line-height:1.5;color:var(--text-muted);margin:10px 0}
.notice{font-size:10pt;line-height:1.5;border-left:3px solid var(--accent);padding:8px 14px;background:var(--accent-soft)}
.toc{display:grid;grid-template-columns:1fr 1fr;gap:8px 24px;font-size:10pt;margin:20px 0}.toc a{text-decoration:none}
.anatomy{width:100%;max-height:160mm;background:#fff}.facts{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:20px 0}
.fact{border-top:3px solid var(--accent);padding:15px;background:var(--surface-2)}.fact strong{display:block;font-size:24pt;font-weight:650}.fact span{font-size:10pt;line-height:1.4}
table{width:100%;border-collapse:collapse;font-size:10pt;margin:18px 0}caption{text-align:left;font-weight:700;margin-bottom:12px}
th,td{text-align:left;padding:11px 9px;border-bottom:1px solid var(--border);vertical-align:top}thead{background:var(--surface-2)}td:not(:first-child){font-variant-numeric:tabular-nums}
.chart{width:100%;height:74mm;object-fit:contain;background:#fff}.flow{width:100%;height:auto}.visual-text{font-size:11pt;line-height:1.6}
.index{max-width:1100px;margin:40px auto;padding:24px}.index h1{font-size:36px}.index li{margin:12px 0;line-height:1.5}.index table{font-size:14px}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media screen and (max-width:850px){.page{width:calc(100% - 24px);min-height:0;padding:24px 24px 70px}.prose,.prose.single{column-count:1;font-size:16px;line-height:1.65}.hero{height:auto}.running{font-size:12px;flex-wrap:wrap}.footer{left:24px;right:24px;bottom:16px;font-size:11px}h1{font-size:38px}h2{font-size:30px}.facts{grid-template-columns:1fr}.toc{grid-template-columns:1fr}.chart{height:auto}.controls{flex-wrap:wrap;padding:10px 16px;gap:10px}table{font-size:12px}th,td{padding:8px 5px}.index{margin:0;padding:20px}}
@media print{@page{size:A4;margin:0}:root,:root[data-theme]{color-scheme:light;--bg:#fafafa;--surface:#fff;--surface-2:#f2f2f2;--surface-3:#e8e8e8;--border:#dedede;--border-strong:#b8b8b8;--text:#161616;--text-muted:#565656;--text-faint:#686868;--accent:var(--accent-light)}body{background:#fff}.controls{display:none}.page{width:210mm;height:297mm;min-height:0;margin:0;box-shadow:none;break-after:page;overflow:visible}.page:last-child{break-after:auto}a{color:var(--text);text-decoration:none}.prose{column-fill:auto;height:213mm;font-size:10.2pt;line-height:1.42}.prose.single{height:auto}.hero{border-radius:0}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def head(title, slug):
    tokens = (SHARED / "tokens.css").read_text(encoding="utf-8")
    bootstrap = (SHARED / "appearance.js").read_text(encoding="utf-8")
    license_text = (SHARED / "LICENSE").read_text(encoding="utf-8")
    return f"""<!doctype html>
<!-- {license_text} -->
<html lang="en" data-default-accent="blue"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="doc-id" content="aster-vale-{slug}"><title>{html.escape(title)}</title>
<script data-doc-bootstrap>
{bootstrap.strip()}
</script><style data-doc-tokens>
{tokens.strip()}
</style>
<style>{CSS}</style></head><body>"""


def page(body, number, slug, section, title):
    return (
        f'<section class="page" id="{section}" aria-label="{html.escape(title)}">'
        f'<div class="running"><span>ASTER VALE / INSTRUMENT DOSSIER</span>'
        f'<span>{html.escape(slug.upper())} / SEPTEMBER 2026</span></div>{body}'
        f'<footer class="footer"><span>Synthetic company and records / illustrative imagery</span>'
        f'<span>{number:02d} / 09</span></footer></section>'
    )


def image_uri(path):
    if not path.is_file():
        raise RuntimeError(f"Missing generated image: {path.name}. Generate it before building HTML.")
    with Image.open(path) as source:
        source.verify()
    with Image.open(path) as source:
        output = io.BytesIO()
        source.convert("RGB").save(output, format="JPEG", quality=89, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode()


def chart_uri(x):
    image = Image.new("RGB", (1200, 560), "white")
    draw = ImageDraw.Draw(image)
    font_path = Path("C:\\Windows\\Fonts\\segoeui.ttf")
    font = ImageFont.truetype(str(font_path), 26) if font_path.is_file() else ImageFont.load_default(size=26)
    small = ImageFont.truetype(str(font_path), 22) if font_path.is_file() else ImageFont.load_default(size=22)
    left, top, width, height = 95, 90, 1010, 330
    max_value = (max(x["units"]) // 100 + 1) * 100
    draw.text((left, 20), "Annual shipments | units dispatched", fill="#161616", font=font)
    for i in range(5):
        y = top + height - i * height / 4
        value = int(max_value * i / 4)
        draw.line((left, y, left + width, y), fill="#dedede", width=2)
        draw.text((15, y - 13), str(value), fill="#565656", font=small)
    points = [(left + i * width / 5, top + height - value / max_value * height)
              for i, value in enumerate(x["units"])]
    draw.line(points, fill="#0078d4", width=5)
    for i, ((px, py), value) in enumerate(zip(points, x["units"], strict=True)):
        draw.ellipse((px - 7, py - 7, px + 7, py + 7), fill="#0078d4")
        draw.text((px - 20, py - 38), str(value), fill="#161616", font=small)
        draw.text((px - 27, top + height + 20), str(2020 + i), fill="#565656", font=small)
    draw.text((left, 505), "Synthetic series | calendar years 2020-2025 | not revenue or production capacity",
              fill="#565656", font=small)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()


def anatomy(x, uri):
    pieces = [
        '<svg class="anatomy" viewBox="0 0 1200 1050" role="img" '
        'aria-labelledby="anatomy-title anatomy-desc">',
        f'<title id="anatomy-title">External parts of the {html.escape(x["name"].lower())}</title>',
        '<desc id="anatomy-desc">Four leader arrows identify visible external parts. '
        'The photograph is a generated illustration, not a dimensional drawing.</desc>',
        '<defs><marker id="arrow-tip" viewBox="0 0 10 10" refX="8" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#0078d4"/>'
        '</marker></defs><rect width="1200" height="1050" fill="white"/>',
        f'<image href="{uri}" x="100" y="0" width="1000" height="1000"/>',
    ]
    for i, (label, tx, ty) in enumerate(x["parts"]):
        left = i % 2 == 0
        lx, ly = (18 if left else 935), 150 + i * 218
        start = 255 if left else 935
        pieces.append(
            f'<rect x="{lx - 5}" y="{ly - 30}" width="255" height="55" rx="6" fill="white" stroke="#dedede"/>'
            f'<text x="{lx + 8}" y="{ly + 5}" font-family="Segoe UI,Arial,sans-serif" font-size="21" '
            f'fill="#161616">{html.escape(label)}</text>'
            f'<path d="M{start} {ly} L{tx + 100} {ty}" fill="none" stroke="#0078d4" '
            f'stroke-width="3" marker-end="url(#arrow-tip)"/>'
        )
    pieces.append("</svg>")
    return "".join(pieces)


def flow(x):
    pieces = [
        '<svg class="flow" viewBox="0 0 1000 660" role="img" aria-labelledby="flow-title flow-desc">',
        '<title id="flow-title">Manufacturing route with a release decision</title>',
        '<desc id="flow-desc">Six operations lead to acceptance. A failed check holds the instrument '
        'for rework and a repeated final check. Only a passing instrument reaches packing.</desc>',
        '<defs><marker id="flow-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" '
        'markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="var(--accent)"/></marker></defs>',
    ]
    for i, stage in enumerate(x["stages"]):
        col = i % 3 if i < 3 else 2 - i % 3
        row = i // 3
        px, py = 35 + col * 325, 25 + row * 165
        pieces.append(
            f'<rect x="{px}" y="{py}" width="280" height="105" rx="9" '
            'fill="var(--surface-2)" stroke="var(--border-strong)"/>'
            f'<text x="{px + 18}" y="{py + 35}" font-size="20" fill="var(--accent)">0{i+1}</text>'
            f'<text x="{px + 18}" y="{py + 73}" font-size="20" fill="var(--text)">{html.escape(stage)}</text>'
        )
    arrows = ["M315 77H350", "M640 77H675", "M815 130V190", "M675 242H640", "M350 242H315",
              "M175 295V340H465V370", "M560 415H685", "M465 460V520H350", "M175 520V325H80V295"]
    for path in arrows:
        pieces.append(f'<path d="{path}" fill="none" stroke="var(--accent)" stroke-width="3" marker-end="url(#flow-arrow)"/>')
    pieces.extend([
        '<path d="M465 370L560 415L465 460L370 415Z" fill="var(--accent-soft)" stroke="var(--accent)"/>',
        '<text x="465" y="421" text-anchor="middle" font-size="19" fill="var(--text)">Accept?</text>',
        '<rect x="685" y="370" width="280" height="90" rx="8" fill="var(--surface-2)" stroke="var(--border-strong)"/>',
        '<text x="825" y="423" text-anchor="middle" font-size="21" fill="var(--text)">Release and pack</text>',
        '<text x="612" y="401" font-size="19" fill="var(--text)">Pass</text>',
        '<rect x="35" y="485" width="315" height="90" rx="8" fill="var(--surface-2)" stroke="var(--border-strong)"/>',
        '<text x="192" y="538" text-anchor="middle" font-size="20" fill="var(--text)">Hold / rework / recheck</text>',
        '<text x="478" y="493" font-size="19" fill="var(--text)">Fail</text>',
        '<text x="35" y="630" font-size="20" fill="var(--text-muted)">Rework repeats the affected operation and every downstream check.</text>',
        '</svg>',
    ])
    return "".join(pieces)


def model_table(x):
    labels = [f"{x['code']}-100 Foundation", f"{x['code']}-200 Atelier", x["flagship"]]
    rows = "".join(
        f'<tr><th scope="row">{html.escape(label)}</th><td>{x["base"]}</td>'
        f'<td>{x["weights"][i]:.2f}</td><td>{x["hours"][i]}</td><td>{x["prices"][i]:,}</td></tr>'
        for i, label in enumerate(labels)
    )
    return (
        '<table><caption>Current full-size model specifications / synthetic catalogue values</caption>'
        f'<thead><tr><th scope="col">Model</th><th scope="col">{html.escape(x["dimension"])}</th>'
        '<th scope="col">Mass (kg)</th><th scope="col">Bench hours</th><th scope="col">List EUR</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
    )


def dossier(x, notice):
    prose_chapters = chapters(x)
    hero = image_uri(CACHE / f'{x["slug"]}-hero.png')
    technical = image_uri(CACHE / f'{x["slug"]}-anatomy.png')
    toc = "".join(
        f'<a href="#{anchor}">{i + 2:02d} / {html.escape(title)}</a>'
        for i, (anchor, title, _) in enumerate(prose_chapters)
    )
    toc += '<a href="#anatomy">07 / External anatomy</a><a href="#models">08 / Models and shipments</a><a href="#route">09 / Production route</a>'
    body = head(f'{x["name"]} | Aster Vale Instruments', x["slug"]) + "<main>"
    body += page(
        f'<div class="eyebrow">{html.escape(x["family"])} / Product dossier</div>'
        f'<h1>{html.escape(x["name"])}</h1><p class="lead">{html.escape(x["flagship"])}<br>'
        f'{html.escape(x["factory"])} / line {html.escape(x["line"])}</p>'
        f'<img class="hero" src="{hero}" alt="Generated product illustration of a complete {html.escape(x["name"].lower())}">'
        f'<p class="caption">Figure 1. AI-generated illustration of the fictional flagship; not a specification photograph.</p>'
        f'<p class="notice">{html.escape(notice)}</p><nav class="toc" aria-label="Dossier contents">{toc}</nav>',
        1, x["code"], "cover", x["name"],
    )
    for i, (anchor, title, text) in enumerate(prose_chapters):
        if len(re.findall(r"\b[\w'-]+\b", text)) < 420:
            raise RuntimeError(f"Insufficient prose on {x['slug']}/{anchor}")
        body += page(
            f'<div class="eyebrow">0{i + 1} / {anchor}</div><h2>{html.escape(title)}</h2>'
            f'<div class="prose">{paragraphs(text)}</div>',
            i + 2, x["code"], anchor, title,
        )
    body += page(
        '<div class="eyebrow">06 / Visible construction</div><h2>Identify parts before discussing service</h2>'
        + anatomy(x, technical)
        + '<p class="caption">Figure 2. Generated external view with authored leader arrows. '
          'Labels identify visible parts; no internal structure, tolerances or scale should be inferred.</p>'
        + f'<div class="visual-text"><p>The external view complements the operating description: {html.escape(x["mechanism"])}. '
          f'The actual material specification is {html.escape(x["materials"])}.</p>'
          f'<p>For a service discussion, describe the observed symptom before proposing a diagnosis. '
          f'The recurring fault in this family is {html.escape(x["defect"])}. '
          f'The corresponding bench check is {html.escape(x["test"])}.</p></div>',
        7, x["code"], "anatomy", "External anatomy",
    )
    body += page(
        '<div class="eyebrow">07 / Commercial and technical records</div><h2>Read the model row, then the trend</h2>'
        + model_table(x)
        + '<p class="caption">Mass excludes case and accessories. Bench hours are direct labour, not elapsed delivery time. '
          'Prices are fictional euro list prices excluding tax, transport and accessories.</p>'
        + f'<img class="chart" src="{chart_uri(x)}" alt="Line chart of annual shipments for this instrument family, 2020 through 2025; numerical values appear inside the chart.">'
        + '<p class="caption">Figure 3. Raster chart for image-reading exercises. The horizontal axis is calendar year; '
          'the vertical axis is units dispatched, not euro revenue or factory capacity.</p>'
        + '<div class="facts">'
        + f'<div class="fact"><strong>{x["units"][-1]}</strong><span>Units dispatched in 2025<br>One instrument family</span></div>'
        + f'<div class="fact"><strong>{x["returns"][-1]}</strong><span>90-day service returns<br>2025 shipment cohort</span></div>'
        + f'<div class="fact"><strong>24</strong><span>Warranty months<br>Confirmed manufacturing defects</span></div></div>'
        + '<p class="notice">All figures are synthetic. A service return includes assessment requests and is not necessarily '
          'a manufacturing defect or an approved warranty claim. A rising shipment line does not prove better sound quality.</p>',
        8, x["code"], "models", "Models and shipments",
    )
    body += page(
        '<div class="eyebrow">08 / Manufacturing control</div><h2>A failed check never flows into dispatch</h2>'
        + flow(x)
        + '<p class="caption">Figure 4. Authored process diagram. Follow the numbered operations, then read both branches '
          'of the acceptance decision. A hold is not a release.</p>'
        + f'<div class="visual-text"><h3>Release criterion</h3><p>{html.escape(x["limit"])}. '
          f'The responsible location is {html.escape(x["factory"])}, line {html.escape(x["line"])}.</p>'
          '<h3>Repair the cause and repeat the checks</h3><p>Return to the affected operation, correct or replace the part, '
          'then repeat every downstream check including final acceptance. Record the serial, revision and decision. '
          'Keep held instruments apart from released stock.</p>'
          '<h3>Choose service over force</h3>'
          f'<p>{html.escape(x["care"])} Supported specialist work includes {html.escape(x["service"])}.</p></div>',
        9, x["code"], "route", "Production route",
    )
    return body + "</main></body></html>\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", nargs="+")
    args = parser.parse_args()
    data = json.loads((CORPUS / "catalog.json").read_text(encoding="utf-8"))
    all_items = data["instruments"]
    items = [x for x in all_items if not args.slug or x["slug"] in args.slug]
    if not items:
        parser.error("Unknown instrument slug")
    HTML.mkdir(parents=True, exist_ok=True)
    records = []
    for item in items:
        content = dossier(item, data["notice"])
        path = HTML / f'{item["slug"]}.html'
        path.write_text(content, encoding="utf-8")
        records.append({"slug": item["slug"], "html_sha256": hashlib.sha256(content.encode()).hexdigest(),
                        "text_words": [len(re.findall(r"\b[\w'-]+\b", text)) for _, _, text in chapters(item)]})
        print(f"Built {path.name}: five prose chapters, {sum(records[-1]['text_words'])} words")
    evidence = ROOT / "evidence" / "instrument-corpus"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "source-build.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
