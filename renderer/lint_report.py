#!/usr/bin/env python3
"""
calm.profile brand linter
enforces brand guidelines in generated reports
"""

import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrandLinter:
    """enforces brand guidelines in html reports"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.teal_accent_color = "#00c9a7"

    def lint_html_file(self, html_path: str) -> bool:
        """lint html file for brand compliance"""
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # run all lint checks
            self._check_unresolved_placeholders(html_content)
            self._check_double_percentages(html_content)
            self._check_page_count(html_content)
            self._check_teal_accent_per_page(html_content)
            self._check_rasci_references(html_content)
            self._check_figure_captions(html_content)
            self._check_rasic_matrix_schema(html_content)
            self._check_rice_tokens(html_content)
            self._check_raw_table_syntax(html_content)
            self._check_cost_calculations(html_content)

            # warnings
            self._check_table_headers(html_content)
            self._check_image_accessibility(html_content)

            # report results
            self._report_results()

            return len(self.errors) == 0

        except Exception as e:
            logger.error(f"linting failed: {e}")
            return False

    def _check_unresolved_placeholders(self, html_content: str) -> None:
        """fail on unresolved ${ anywhere"""
        unresolved = re.findall(r"\$\{[^}]+\}", html_content)
        if unresolved:
            self.errors.append(f"unresolved placeholders found: {unresolved}")

    def _check_double_percentages(self, html_content: str) -> None:
        """fail on any %%"""
        double_percentages = re.findall(r"\d+%%", html_content)
        if double_percentages:
            self.errors.append(f"double percentages found: {double_percentages}")

    def _check_page_count(self, html_content: str) -> None:
        """fail if page count != 12"""
        # count page breaks (primary method)
        page_breaks = len(re.findall(r'class="page-break"', html_content))
        page_count = page_breaks + 1  # +1 for first page

        # also check for page-break-before: always in CSS
        css_page_breaks = len(re.findall(r"page-break-before:\s*always", html_content))

        # use page breaks as primary method
        if page_breaks > 0:
            page_count = page_breaks + 1
        elif css_page_breaks > 0:
            page_count = css_page_breaks + 1
        else:
            # fallback to h2 count
            h1_count = len(re.findall(r"<h1[^>]*>", html_content))
            h2_count = len(re.findall(r"<h2[^>]*>", html_content))
            unique_h2_count = max(
                h2_count, len(re.findall(r"<p><h2[^>]*>", html_content))
            )
            page_count = unique_h2_count

        # enforce exactly 12 pages
        if page_count != 12:
            self.errors.append(
                f"page count is {page_count}, expected exactly 12 (page-breaks: {page_breaks})"
            )

    def _check_teal_accent_per_page(self, html_content: str) -> None:
        """fail if more than one teal accent per page"""
        # find all .teal-accent classes
        accent_classes = re.findall(r'class="[^"]*teal-accent[^"]*"', html_content)

        # count accents per page by looking for page boundaries
        page_sections = re.split(
            r"page-break-before:\s*always|<!--\s*p\d+\s*-->", html_content
        )

        for i, page_content in enumerate(page_sections):
            page_accents = len(
                re.findall(r'class="[^"]*teal-accent[^"]*"', page_content)
            )
            if page_accents > 1:
                self.errors.append(
                    f"page {i+1} has {page_accents} teal accents, max 1 allowed"
                )

    def _check_rasci_references(self, html_content: str) -> None:
        """fail on 'rasci' present"""
        if re.search(r"\brasci\b", html_content, re.IGNORECASE):
            self.errors.append(
                "'rasci' reference found - use 'responsibilities' instead"
            )

    def _check_figure_captions(self, html_content: str) -> None:
        """fail on <figure> without <figcaption> containing '— so what'"""
        figures = re.findall(r"<figure[^>]*>(.*?)</figure>", html_content, re.DOTALL)
        for i, figure in enumerate(figures):
            if "<figcaption>" not in figure:
                self.errors.append(f"figure {i+1} missing figcaption")
            else:
                figcaption_match = re.search(
                    r"<figcaption[^>]*>([^<]+)</figcaption>", figure
                )
                if figcaption_match:
                    caption_text = figcaption_match.group(1)
                    if "so what" not in caption_text.lower():
                        self.errors.append(
                            f"figure {i+1} caption missing 'so what' pattern"
                        )

    def _check_rasic_matrix_schema(self, html_content: str) -> None:
        """fail on RASIC matrix rows where A count != 1 or R count == 0"""
        # find table rows in the responsibilities table
        table_rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html_content, re.DOTALL)

        for i, row in enumerate(table_rows):
            # skip header row
            if "<th>" in row:
                continue

            # count R, A, S, C, I in this row
            cells = re.findall(r"<td[^>]*>([^<]+)</td>", row)
            if len(cells) >= 5:  # ensure we have all 5 columns
                r_content = cells[0].strip()
                a_content = cells[1].strip()

                # count roles (split by comma)
                r_count = len([r for r in r_content.split(",") if r.strip()])
                a_count = len([a for a in a_content.split(",") if a.strip()])

                if a_count != 1:
                    self.errors.append(
                        f"RASIC row {i+1}: accountable count is {a_count}, expected 1"
                    )
                if r_count == 0:
                    self.errors.append(
                        f"RASIC row {i+1}: responsible count is 0, expected at least 1"
                    )

    def _check_rice_tokens(self, html_content: str) -> None:
        """fail on unresolved rice tokens like $r1_rice"""
        rice_tokens = re.findall(r"\$r\d+_rice", html_content)
        if rice_tokens:
            self.errors.append(f"unresolved rice tokens found: {rice_tokens}")

    def _check_raw_table_syntax(self, html_content: str) -> None:
        """fail when html contains raw table syntax but no <table> tags"""
        # check for raw markdown table syntax: | header | header |
        #                                      |--------|--------|
        raw_table_pattern = r"\n\|\s*[-:]+\s*\|"
        raw_table_matches = re.findall(raw_table_pattern, html_content)

        if raw_table_matches:
            # check if there are any <table> tags on the page
            table_tags = re.findall(r"<table[^>]*>", html_content)
            if not table_tags:
                self.errors.append(
                    f"raw table syntax detected but no <table> tags found: {len(raw_table_matches)} instances"
                )

    def _check_cost_calculations(self, html_content: str) -> None:
        """validate cost calculations match the displayed formula"""
        # extract values from the specific cost formula lines
        weekly_formula_match = re.search(
            r"weekly cost: (\d+(?:\.\d+)?) hours × \$(\d+(?:\.\d+)?) × (\d+) people = \$(\d{1,3}(?:,\d{3})*)",
            html_content,
        )
        annual_formula_match = re.search(
            r"annual cost: \$(\d{1,3}(?:,\d{3})*) × 52 weeks = \$(\d{1,3}(?:,\d{3})*)",
            html_content,
        )

        if not weekly_formula_match or not annual_formula_match:
            self.errors.append(
                "cost calculation validation failed: could not find cost formula lines"
            )
            return

        # parse values from weekly formula
        hours_lost_ppw = float(weekly_formula_match.group(1))
        hourly_rate = float(weekly_formula_match.group(2))
        team_multiplier = int(weekly_formula_match.group(3))
        weekly_cost_display = int(weekly_formula_match.group(4).replace(",", ""))

        # parse values from annual formula
        weekly_cost_from_annual = int(annual_formula_match.group(1).replace(",", ""))
        annual_cost_display = int(annual_formula_match.group(2).replace(",", ""))

        # calculate expected values
        weekly_cost_calc = hours_lost_ppw * hourly_rate * team_multiplier
        annual_cost_calc = weekly_cost_calc * 52

        # validate weekly cost calculation
        if abs(weekly_cost_display - weekly_cost_calc) > 1:
            self.errors.append(
                f"weekly cost mismatch: displayed ${weekly_cost_display:,}, calculated ${weekly_cost_calc:,.0f}"
            )

        # validate annual cost calculation
        if abs(annual_cost_display - annual_cost_calc) > 52:
            self.errors.append(
                f"annual cost mismatch: displayed ${annual_cost_display:,}, calculated ${annual_cost_calc:,.0f}"
            )

        # validate weekly cost consistency between formulas
        if weekly_cost_display != weekly_cost_from_annual:
            self.errors.append(
                f"weekly cost inconsistency: ${weekly_cost_display:,} vs ${weekly_cost_from_annual:,}"
            )

    def _check_table_headers(self, html_content: str) -> None:
        """warn on tables missing header row or missing units in column headings"""
        tables = re.findall(r"<table[^>]*>(.*?)</table>", html_content, re.DOTALL)

        for i, table in enumerate(tables):
            # check for header row
            if "<th>" not in table and "<thead>" not in table:
                self.warnings.append(f"table {i+1} missing header row")

            # check for units in column headings
            headers = re.findall(r"<th[^>]*>([^<]+)</th>", table)
            for header in headers:
                header_lower = header.lower()
                if any(
                    unit in header_lower
                    for unit in ["$", "%", "hours", "days", "weeks", "months"]
                ):
                    continue
                if header.strip() and not any(
                    word in header_lower
                    for word in ["name", "title", "description", "scenario"]
                ):
                    self.warnings.append(
                        f"table {i+1} header '{header}' may be missing units"
                    )

    def _check_image_accessibility(self, html_content: str) -> None:
        """warn on images missing <title>/<desc>"""
        # check SVG elements for title/desc
        svgs = re.findall(r"<svg[^>]*>(.*?)</svg>", html_content, re.DOTALL)

        for i, svg_content in enumerate(svgs):
            has_title = "<title>" in svg_content
            has_desc = "<desc>" in svg_content

            if not has_title:
                self.warnings.append(f"SVG {i+1} missing <title> element")
            if not has_desc:
                self.warnings.append(f"SVG {i+1} missing <desc> element")

    def _report_results(self) -> None:
        """report linting results"""
        if self.errors:
            logger.error("brand linting errors:")
            for error in self.errors:
                logger.error(f"  ❌ {error}")

        if self.warnings:
            logger.warning("brand linting warnings:")
            for warning in self.warnings:
                logger.warning(f"  ⚠️  {warning}")

        if not self.errors and not self.warnings:
            logger.info("✅ brand linting passed - no issues found")
        elif not self.errors:
            logger.info("✅ brand linting passed with warnings")
        else:
            logger.error("❌ brand linting failed")


def main():
    """main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="lint calm.profile reports for brand compliance"
    )
    parser.add_argument("html_file", help="html file to lint")
    parser.add_argument(
        "--fail-on-warnings", action="store_true", help="fail on warnings"
    )

    args = parser.parse_args()

    if not Path(args.html_file).exists():
        logger.error(f"file not found: {args.html_file}")
        return 1

    linter = BrandLinter()
    success = linter.lint_html_file(args.html_file)

    if args.fail_on_warnings and linter.warnings:
        logger.error("failing due to warnings")
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
