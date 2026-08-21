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

The homepage reads citations, h-index, and i10-index from
`_data/scholar.yml`. The `Update Scholar Metrics` GitHub Actions workflow runs
daily at 09:23 Hong Kong time. It validates the profile identity and all three
metrics before atomically replacing the data file, commits the verified data,
and explicitly requests a Pages rebuild.

The fetcher uses the public Scholar profile by default. For more reliable
hosted runs, add a repository Actions secret named `SERPAPI_KEY`; the direct
profile remains a fallback. A total failure, malformed response, wrong profile,
or unexpected metric decrease fails the workflow without changing the stored
values. The failure job opens and assigns a durable GitHub Issue, comments on
repeated failures, and the next successful run closes the alert.

Run the same checks locally with:

```sh
python3 -m unittest discover -s tests -p "test_*.py" -v
python3 scripts/update_scholar.py --check-only
```

If Scholar legitimately corrects a metric downward, run the workflow manually
with `allow_decrease` enabled after checking the public profile.
