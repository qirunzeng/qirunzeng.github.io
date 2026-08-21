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
