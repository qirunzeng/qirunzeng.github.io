# Qirun Zeng — Academic Website

A small, independent academic website built with Jekyll and hosted on GitHub Pages.

The site uses no external theme, UI framework, icon library, web font, analytics script, or JavaScript dependency. Its layouts, components, native CSS, and visual system are maintained directly in this repository. The Ruby dependencies are limited to the static-site build and local preview.

## Local preview

```sh
bundle install
bundle exec jekyll serve
```

Then open `http://127.0.0.1:4000`.

## Content

- Personal details: `_data/profile.yml`
- Homepage sections: `_data/home.yml`
- Publications: `_data/publications.yml`
- Teaching: `_data/teaching.yml`

To choose the papers shown on the homepage, edit `selected_publications` in
`_data/home.yml`. Each entry is a publication `id` from
`_data/publications.yml`, and the list order controls the display order.

## Google Scholar metrics

The Publications page reads citations, h-index, and i10-index from
`_data/scholar.yml`. The `Update Scholar Metrics` GitHub Actions workflow runs
daily at 09:23 Hong Kong time. It validates the profile identity and all three
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
manual dispatch. The schedule becomes active after the workflow is pushed.
Visitors make no API requests, and all statistics and charts work without JS.

```sh
python3 scripts/update_codeforces.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Solved problems are deduplicated by contest ID and problem index, including
practice and virtual participation. Topics count unique solved problems and
can overlap; languages count all accepted submissions, including repeated
solves. The fetcher paginates the complete submission history, respects API
request spacing, validates identity and rating consistency, and atomically
replaces the snapshot only on success. A decreasing solved count fails for
manual inspection. Network/API failure leaves the previous snapshot intact;
the date shown on the page identifies its age. GitHub Actions reports refresh
failures in its run status.

## Design and performance

The visual system uses system fonts, neutral surfaces, restrained wine accents,
thin dividers, and responsive spacing, with light/dark themes and reduced-motion
support. Topic comparisons use bars because overlapping categories are not
parts of a whole; languages use a static SVG ring with a text legend.
The bandit game script loads only on the homepage. Maintenance scripts and tests
are excluded from the published output. No additional runtime libraries were
introduced.
