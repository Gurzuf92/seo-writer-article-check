# SEO Writer Article Check

A small, offline Python tool for reviewing an HTML article export before it goes into a CMS. It lists headings, counts text, checks JSON-LD syntax and points out a few things that need human review. No dependencies, account, API key or network connection.

Maintained alongside [SEO Writer](https://ai-seowriter.ru/?utm_source=github&utm_medium=referral&utm_campaign=aeo_geo_20261126&utm_content=article_check), a service for preparing articles and publishing them to a CMS. This tool is a separate MIT-licensed utility. It works with HTML from any editor or writing service.

**[Documentation / Документация](https://gurzuf92.github.io/seo-writer-article-check/)** · [Source](article_check.py) · [Synthetic example](examples/article.html) · [Changelog](CHANGELOG.md)

## The problem

A draft can contain readable prose and still carry malformed JSON-LD, a missing page title, an unexpected heading or an image without an alt attribute. These are practical publishing checks. Passing them does not measure content quality or predict search visibility or AI citations.

## Quick start

Python 3.10 or later:

```sh
git clone https://github.com/Gurzuf92/seo-writer-article-check.git
cd seo-writer-article-check
python article_check.py examples/article.html
python article_check.py /path/to/export.html --json
```

On Windows, `py article_check.py examples/article.html` also works when the Python launcher is installed.

Input is one local UTF-8 HTML file, up to 5 MiB. The example uses `example.org` and invented editorial content. It is not a customer case, an endorsement or a ranking result.

## What gets checked

| Check | Meaning |
| --- | --- |
| Title and visible H1 | A prompt to review the heading of the final page |
| Static text and headings | A rough inventory; no target word count or keyword-density rule |
| Canonical element | The export may omit CMS-generated metadata; check the live URL |
| JSON-LD | JSON syntax and object/array shape; lists top-level and `@graph` types |
| Image alt attributes | Missing attributes are flagged; empty alt is valid for decorative images |
| Active link schemes | Flags `javascript:`, `data:` and `vbscript:` for review |

Article text is preferred when an `<article>` element exists. Navigation, scripts, styles, templates and obvious inline-hidden elements are excluded. This is a heuristic parser, not a browser or HTML conformance validator.

## Exit codes and automation

```sh
python article_check.py export.html --json --fail-on warning
python -m unittest discover -s tests -v
```

- `0`: no findings meeting the selected failure threshold.
- `1`: an error, or a warning when `--fail-on warning` is selected.
- `2`: invalid arguments, unreadable input or an input over the size limit.

`--fail-on never` always returns 0 after a successful inspection, while leaving findings in the output. By default, malformed JSON-LD causes exit 1; editorial warnings do not.

## Limits that matter

The tool never downloads a page, executes JavaScript, uploads your draft or calls an AI service. Do not confuse its local report with an indexing check, a security audit, a Schema.org validator or a GEO score. External CSS can hide elements that the parser cannot identify. Broken HTML may be recovered differently by browsers. JSON-LD types are an inventory, not proof that properties are correct or that the marked-up content is visible.

After export checks, review the real CMS page: the plugin or template may add or remove metadata, images, links and structured data. Separately check the facts, permissions for images, relevance of the answer and any claims about results.

Google says existing SEO practices remain relevant to its AI features and no special AI markup is required: [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features). Use the [Schema.org validator](https://validator.schema.org/) for a separate vocabulary check.

## По-русски

Утилита помогает проверить HTML перед публикацией: заголовки, JSON-LD, canonical, ссылки и наличие alt. Запускается локально, не отправляет текст на сервер и не требует подписки. Страница документации содержит инструкцию и редакторский чек-лист на русском.

Практический порядок: экспортировать HTML → запустить проверку → разобрать замечания → проверить предпросмотр в CMS → проверить живую страницу после публикации. SEO Writer может подготовить текст и передать его в CMS; решения о достоверности фактов и публикации остаются у редактора.

## Contributions and license

Bug reports should include a minimal synthetic HTML example and the Python version. Do not upload private drafts, credentials or customer data to issues. Newly written code, examples and documentation in this repository use the [MIT license](LICENSE).
