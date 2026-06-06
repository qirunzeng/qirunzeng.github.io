# qirunzeng.github.io

Personal academic homepage for Qirun Zeng, built with Jekyll and hosted on GitHub Pages.

## Main Content

- `_pages/home.md`: homepage
- `_pages/about.md`: academic background and service
- `_pages/publications.md`: research and publications
- `_pages/teaching.md`: teaching
- `_pages/contact.md`: contact information
- `_data/publications.yml`: publication metadata
- `_data/teaching.yml`: teaching metadata
- `_includes/paper-card.html`: reusable publication entry
- `_includes/contact-links.html`: reusable contact links
- `_sass/_custom.scss`: custom shared styles
- `files/`: downloadable files such as PDFs and handouts
- `images/`: avatar and favicon assets

## Local Preview

Install dependencies:

```bash
bundle install
```

Run the site locally:

```bash
bundle exec jekyll serve -l -H localhost
```

Then open `http://localhost:4000`.
