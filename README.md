# Slow Centuries Study Guides

Free, classroom-ready study guides for the [Slow Centuries](VIDEO_CHANNEL_URL) YouTube series. Each guide has a summary, chapter list, timeline, key terms, a hands-on activity, discussion questions and links to primary sources in museums, libraries and archives.

**Read the guides:** https://GITHUB_USER.github.io/slow-centuries-study-guides/

| Episode | Guide | PDF |
|---|---|---|
| Timelapse of Algorithms | [docs/algorithms](docs/algorithms/index.md) | [PDF](docs/pdf/timelapse-of-algorithms.pdf) |
| Timelapse of Money | [docs/money](docs/money/index.md) | [PDF](docs/pdf/timelapse-of-money.pdf) |
| Timelapse of Encryption | [docs/encryption](docs/encryption/index.md) | [PDF](docs/pdf/timelapse-of-encryption.pdf) |

## Licence

Guide text: [CC BY 4.0](LICENSE.md). Linked objects and images belong to their institutions.

## Corrections

Open an [issue](../../issues) with the guide, the line and your source. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Adding a guide (for maintainers)

1. Copy `templates/study-guide-template.md` to `docs/<slug>/index.md` and fill it in.
2. Add the page to `mkdocs.yml` and `docs/index.md`, and the slug to `scripts/build_pdf.py`.
3. Check links: `python scripts/check_links.py --archive`
4. Preview: `pip install mkdocs-material && mkdocs serve`
5. Push to `main`. GitHub Actions rebuilds the PDFs and publishes the site.

## One-time setup

1. Create a public repo named `slow-centuries-study-guides` on GitHub and push this folder to it.
2. Fill in the links (replaces `GITHUB_USER` and each episode's `VIDEO_URL`, then rebuilds the PDFs with QR codes):
   `python scripts/set_links.py --user <your-github-name> --algorithms <youtube-link> --money <youtube-link> --encryption <youtube-link>`
   You can run it again as each video goes live.
3. In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. Push any change, or run the "Publish study guides" workflow from the **Actions** tab. The site appears at the URL above within a few minutes.
