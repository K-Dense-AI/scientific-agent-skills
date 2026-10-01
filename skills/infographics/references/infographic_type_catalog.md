# Infographic Type Catalog

All ten types with their `--type` value, what each is for, the data shape it expects, and
worked prompts: statistical, timeline, process, comparison, list, geographic,
hierarchical, anatomical, resume, and social.

Commands below are illustrative and were not sent to paid APIs during review.
Replace sample numerical claims with verified, dated sources and units. Supply exact
charts/maps as references when scientific geometry matters.

## Infographic Types

### 1. Statistical/Data-Driven (`--type statistical`)

Best for: Presenting numbers, percentages, survey results, and quantitative data.

**Key Elements:** Charts (bar, pie, line, donut), large numerical callouts, data comparisons, trend indicators.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "Synthetic survey of 1000 respondents: 680 use the internet (68%), \
   respondent regions A 53%, B 15%, C 20%, D 12%; label all data synthetic" \
  -o figures/internet_stats.png --type statistical --style technology
```

---

### 2. Timeline (`--type timeline`)

Best for: Historical events, project milestones, company history, evolution of concepts.

**Key Elements:** Chronological flow, date markers, event nodes, connecting lines.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "History of AI: 1950 Turing Test, 1956 Dartmouth Conference, \
   1997 Deep Blue, 2016 AlphaGo, 2022 ChatGPT" \
  -o figures/ai_history.png --type timeline --style technology
```

---

### 3. Process/How-To (`--type process`)

Best for: Step-by-step instructions, workflows, procedures, tutorials.

**Key Elements:** Numbered steps, directional arrows, action icons, clear flow.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "How to start a podcast: 1. Choose your niche, 2. Plan content, \
   3. Set up equipment, 4. Record episodes, 5. Publish and promote" \
  -o figures/podcast_process.png --type process --style marketing
```

---

### 4. Comparison (`--type comparison`)

Best for: Product comparisons, pros/cons, before/after, option evaluation.

**Key Elements:** Side-by-side layout, matching categories, check/cross indicators.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "Electric vs Gas Cars: Fuel cost (lower vs higher), \
   Maintenance (less vs more), Range (improving vs established)" \
  -o figures/ev_comparison.png --type comparison --style nature
```

---

### 5. List/Informational (`--type list`)

Best for: Tips, facts, key points, summaries, quick reference guides.

**Key Elements:** Numbered or bulleted points, icons, clear hierarchy.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "7 Habits of Highly Effective People: Be Proactive, \
   Begin with End in Mind, Put First Things First, Think Win-Win, \
   Seek First to Understand, Synergize, Sharpen the Saw" \
  -o figures/habits.png --type list --style corporate
```

---

### 6. Geographic (`--type geographic`)

Best for: Regional data, demographics, location-based statistics, global trends.

**Key Elements:** Map visualization, color coding, data overlays, legend.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "Synthetic renewable electricity shares: fictional Region A 80%, Region B 60%, \
   Region C 40%, Region D 20%; percent of annual generation; label hypothetical" \
  -o figures/renewable_map.png --type geographic --style nature
```

---

### 7. Hierarchical/Pyramid (`--type hierarchical`)

Best for: Organizational structures, priority levels, importance ranking.

**Key Elements:** Pyramid or tree structure, distinct levels, size progression.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "Maslow's Hierarchy: Physiological, Safety, Love/Belonging, \
   Esteem, Self-Actualization" \
  -o figures/maslow.png --type hierarchical --style education
```

---

### 8. Anatomical/Visual Metaphor (`--type anatomical`)

Best for: Explaining complex systems using familiar visual metaphors.

**Key Elements:** Central metaphor image, labeled parts, connection lines.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "Business as a human body: Brain=Leadership, Heart=Culture, \
   Arms=Sales, Legs=Operations, Skeleton=Systems" \
  -o figures/business_body.png --type anatomical --style corporate
```

---

### 9. Resume/Professional (`--type resume`)

Best for: Personal branding, CVs, portfolio highlights, professional achievements.

**Key Elements:** Photo area, skills visualization, timeline, contact info.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "UX Designer resume: Skills - User Research 95%, Wireframing 90%, \
   Prototyping 85%. Experience - 2020-2022 Junior, 2022-2025 Senior" \
  -o figures/resume.png --type resume --style technology
```

---

### 10. Social Media (`--type social`)

Best for: Instagram, LinkedIn, Twitter/X posts, shareable graphics.

**Key Elements:** Bold headline, minimal text, maximum impact, vibrant colors.

```bash
python skills/infographics/scripts/generate_infographic.py \
  "Save Water: Fix leaks, monitor use, and follow local conservation guidance. \
   Tips: shorter showers, fix leaks, full loads only" \
  -o figures/water_social.png --type social --style marketing
```

---
