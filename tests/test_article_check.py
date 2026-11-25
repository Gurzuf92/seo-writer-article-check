import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from article_check import inspect_html, main


class WorkflowChecks(unittest.TestCase):
    def test_example_can_be_used_as_an_offline_export(self):
        sample = Path(__file__).parents[1] / "examples/article.html"
        result = inspect_html(sample.read_text(encoding="utf-8"))
        self.assertEqual(result["counts"].get("error", 0), 0)
        self.assertEqual(result["h1_count"], 1)
        self.assertEqual(result["json_ld"]["types"], ["Article"])
        self.assertEqual(result["text_scope"], "article")

    def test_broken_schema_fails_cli_and_produces_usable_json(self):
        with tempfile.TemporaryDirectory() as folder:
            sample = Path(folder) / "broken.html"
            sample.write_text('<article><h1>Draft</h1><script type="application/ld+json">{"@type":</script></article>', encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main([str(sample), "--json"])
            self.assertEqual(code, 1)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["json_ld"]["invalid"][0]["block"], 1)

    def test_hidden_navigation_and_decorative_images_do_not_inflate_article(self):
        result = inspect_html('<title>Draft</title><nav><h1>Navigation</h1></nav><article><h1>Useful answer</h1><div hidden><h1>Hidden heading</h1>hidden words</div><p>Visible words.</p><img src="divider.svg" alt=""><img src="chart.svg"></article>')
        self.assertEqual(result["h1_count"], 1)
        self.assertEqual(result["words"], 4)
        alt = [f for f in result["findings"] if f["code"] == "missing_alt"]
        self.assertEqual(len(alt), 1)
        self.assertTrue(alt[0]["message"].startswith("1 images"))

    def test_schema_graph_and_inline_headings_are_read(self):
        result = inspect_html('<article><h1>A <em>useful</em> answer</h1><script type="application/ld+json">{"@graph":[{"@type":["Article","TechArticle"]}]}</script></article>')
        self.assertEqual(result["headings"][0]["text"], "A useful answer")
        self.assertEqual(result["json_ld"]["types"], ["Article", "TechArticle"])

    def test_javascript_links_and_non_json_numbers_are_flagged(self):
        result = inspect_html('<article><h1>Draft</h1><a href="javascript:alert(1)">Bad link</a><script type="application/ld+json">{"number":NaN}</script></article>')
        codes = {f["code"] for f in result["findings"]}
        self.assertIn("active_link", codes)
        self.assertIn("invalid_json_ld", codes)


if __name__ == "__main__":
    unittest.main()
