# Qirun Zeng — Academic Website

A small, independent academic website built with Jekyll and hosted on GitHub Pages.

The site uses no external theme, UI framework, icon library, web font, analytics script, or JavaScript dependency. Its layouts, components, native CSS, and visual system are maintained directly in this repository. The Ruby dependencies are limited to the static-site build and local preview.

## Local preview

```sh
bundle install
bash scripts/preview.sh
```

Then open `http://127.0.0.1:4000`.

The preview command updates CSS/JS content versions before starting Jekyll.
After editing CSS or JS during a preview session, run
`python3 scripts/update_assets.py` again so the browser requests the new version.
Commit `_data/assets.json` alongside asset changes. The content check rejects a
stale manifest; ordinary content or metrics updates keep the asset URLs stable.

## Verification

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
bundle exec ruby scripts/check_site.rb
```

The `Check Site` workflow runs on pushes and pull requests. It checks publication
IDs and references, asset versions, and both Scholar states. Temporary builds
are inspected for local links/resources, anchors, accessibility labels, page
metadata, JSON-LD, sitemap entries, and disabled Scholar information. The checks
use no external APIs and leave tracked content unchanged.

The two snapshot workflows share a write concurrency group. A common commit
helper rebases onto the current remote branch and retries a racing push up to
three times. A conflicting edit fails without overwriting the remote; local Git
tests cover unchanged snapshots, concurrent content edits, a racing push, and
snapshot conflicts.

## Content

- Personal details: `_data/profile.yml`
- Homepage sections: `_data/home.yml`
- Publications: `_data/publications.yml`
- Teaching: `_data/teaching.yml`

To choose the papers shown on the homepage, edit `selected_publications` in
`_data/home.yml`. Each entry is a publication `id` from
`_data/publications.yml`, and the list order controls the display order.
Each research interest has a
`papers` list; the first ID is its representative link and all IDs are validated.
The homepage identity is read from `_data/profile.yml`.

Each paper's `url` in `_data/publications.yml` is its shared paper address.
The title uses it directly, and conference/arXiv badges use `paper: true`
instead of storing another URL:

```yaml
- id: "werewolf"
  url: "https://aclanthology.org/2026.findings-emnlp.2427"
  # Other publication fields…
  links:
    - label: "EMNLP'2026"
      paper: true
      type: "conference"
```

In News `text`, use Markdown references such as
`[WEREWOLF][paper:werewolf]` or
`[**Full paper title**][paper:werewolf]`. The News template resolves these
references from publication IDs; no URL definitions belong in `_data/home.yml`.
Changing the paper's `url` updates its title, paper badges, and News links on
the next build. Code links keep their own repository URLs, and DOI links are
generated from the paper's `doi` identifier.

## Google Scholar metrics

Quick switch: edit `_data/features.json` and set `"scholar_enabled": false` to
disable Scholar, or `true` to re-enable it (the default). This single switch hides
the profile link, citation/h-index/i10-index metrics, source/date, and each paper's
"Cited by" link. Publication counts and venue breakdowns remain visible.
The fetcher exits successfully before any network request or snapshot write when
disabled, including manual runs. The scheduled workflow skips refresh, data
commits, rebuild requests, and alert recovery; existing data and alerts are kept.
Commit and push the switch change for GitHub Actions to read it; the visibility
change takes effect on the next Pages build. Restart local `jekyll serve` if
needed. Use JSON booleans `true`/`false`, without quotes.

The Publications page reads citations, h-index, and i10-index from
`_data/scholar.yml`. The `Update Scholar Metrics` GitHub Actions workflow runs
daily at 09:23 Hong Kong time, with a recovery window at 21:23. Scheduled runs
skip network requests if a successful check is already recorded for that UTC
date; manual dispatch always attempts a refresh when enabled. It validates the profile identity and all three
metrics before atomically replacing the data file, commits the verified data,
and explicitly requests a Pages rebuild.

The fetcher prefers the public Scholar profile, then falls back to the
open-source BTH Google Scholar mirror because Google blocks GitHub-hosted runner
IPs. The mirror response must contain a configured known publication; h-index
and i10-index are independently derived from its publication citation counts.
For a more reliable primary source, add a repository Actions secret named
`SERPAPI_KEY` (the free quota is sufficient for a daily run). A total failure,
malformed response, wrong profile, truncated publication list, or unexpected
metric decrease fails the workflow without changing the stored values. The
failure job opens and assigns a durable GitHub Issue, comments on repeated
failures, and the next successful run closes the alert.

The switch does not change the provider URLs or parsing behavior. HTTP 403/429
immediately falls through to the next source. Actions allows up to three complete
provider rounds with a 60-second pause between failed rounds; local runs use one
round by default. Identity checks and metric-decrease checks are never bypassed.
These retries can recover transient outages but cannot guarantee access when all
providers remain blocked. A successful run from a trusted local connection can
also refresh the snapshots with `python3 scripts/update_scholar.py`; review and
push both data files afterward. Never update `last_checked_at` by hand.

Run the same checks locally with:

```sh
python3 -m unittest discover -s tests -p "test_*.py" -v
python3 scripts/update_scholar.py --check-only
```

If Scholar legitimately corrects a metric downward, run the workflow manually
with `allow_decrease` enabled after checking the public profile.

## Codeforces statistics

The homepage uses `_data/codeforces.json`, a snapshot of the official
`user.info`, `user.status`, and `user.rating` API responses for `rewinery`.
The update workflow refreshes it every Monday at 10:47 Hong Kong time, or on
manual dispatch. The schedule runs from the default branch.
Visitors make no API requests, and all statistics and charts work without JS.

```sh
python3 scripts/update_codeforces.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Solved problems are deduplicated by contest ID and problem index, including
practice and virtual participation. Topics count unique solved problems and
can overlap; languages count all accepted submissions, including repeated
solves. Language versions are grouped into C++ and Python families; PyPy counts
as Python. Other language names remain distinct. The fetcher paginates the
complete submission history, respects API request spacing, validates identity and rating consistency, and atomically
replaces the snapshot only on success. A decreasing solved count fails for
manual inspection. Network/API failure leaves the previous snapshot intact;
the date shown on the page identifies its age. GitHub Actions reports refresh
failures in its run status.

## Design and performance

The site follows Apple HIG principles of hierarchy, alignment, consistent
spacing, and progressive disclosure while retaining its warm neutral and
Chengheng ink-blue palette. It uses system fonts, native HTML disclosures,
static SVG charts, and no external fonts, frameworks, or runtime dependencies.
Light and dark themes share semantic color tokens, visible keyboard focus,
and reduced-motion support. The header is a solid surface, without glass,
card shadows, or entrance animations.

The homepage order is introduction, Selected Publications, Recent News,
Service, and Programming. The introduction combines research and the current
advisor in one paragraph, followed by academic background in another.
`_data/home.yml` retains the research-interest descriptions and paper mappings
for maintenance; these are not rendered as a separate homepage section.
The three selected paper IDs and their order are maintained there as well.
No one-line paper summaries or repeated Publications/Email buttons are shown.
Teaching remains a separate page.

News entries use required `text` for the full archive and optional `home_text`
for the latest three homepage updates. The current entries use their full
paper titles and complete news text on both pages. A missing or empty
`home_text` falls back to `text`. Both support `[label][paper:publication-id]` references and
are validated by the content check. The archive always retains complete news.
Service displays one Reviewer label and a year/venue list. Programming is
entirely collapsed by default, including the handle, metrics, and update date;
its charts remain a nested native disclosure. All data remains in the built
HTML and works without JavaScript.

All pages share a 1120px maximum shell, a 200px desktop profile column,
and a 48px column gap. Below 900px they use one column, with profile links
following the main content. Horizontal gutters are 24px, or 16px on phones.
The desktop profile remains fixed and scrolls independently in short windows.
The mobile header uses two rows to keep navigation and theme controls visible.
The footer aligns with the main column and has one top separator.

CSS tokens define spacing (4/8/12/16/24/32/48px), type, weights (400/500/600),
radii, and separators. Page titles use 32px on desktop and 28px on phones;
section headings use 20px/18px, paper and course titles 17px, body text 16px,
secondary information 13px, and tags 12px. Section gaps are 48px/32px;
heading-to-content spacing is 16px. Dividers appear only below the header,
between adjacent publications or courses, and above the footer; adjacent
entries have 16px padding on each side of their divider. Section headings,
news, service, and programming use alignment and whitespace instead.

Paper, Code, and course-material tags share transparent backgrounds, muted
borders, and a 24px minimum height on every screen. Abstract sits below the
paper tags, with identical text and spacing on desktop and mobile; opening
it does not move its summary. Paper titles, full author lists, venue details,
DOIs, and citation links remain intact. Publication statistics use a compact
metric strip, with venue details expanded on demand. Scholar visibility still
uses the shared feature switch. Decorative number circles and timeline
markers are removed.

Email is available in the profile links as a Gmail web compose link, using
the single `email` field in `_data/profile.yml`. It opens a new tab with the
recipient prefilled and requires Gmail sign-in; visitors review and send the
message themselves. The WeChat dialog retains native modal and keyboard
behavior, with an ordinary image link as its no-JavaScript fallback.

Codeforces topics and languages use static SVG rings with text legends.
Topic segments represent shares of tag occurrences across unique solved
problems, not mutually exclusive shares of solved problems. The Other segment
sums tags beyond the top six. Social metadata uses the existing portrait;
the sitemap contains content pages only. Maintenance scripts and tests are
excluded from the published output.
