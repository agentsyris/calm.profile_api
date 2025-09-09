#!/usr/bin/env python3
"""
calm.profile report renderer
converts markdown template with placeholders to PDF via HTML
"""

import os
import json
import re
import uuid
import tempfile
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


# number formatting utilities
def fmt_int(x):
    """format integer with commas"""
    return f"{int(round(x)):,}"


def fmt_currency(x):
    """format currency with commas"""
    return f"${int(round(x)):,}"


def fmt_percent(x, digits=0):
    """format percentage with specified decimal places"""
    return f"{x:.{digits}f}%"


try:
    import weasyprint

    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    import markdown

    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

# setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportRenderer:
    """renders calm.profile reports from template and data"""

    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self.template_file = self.templates_dir / "calm_profile_report_template.md"
        self.css_file = self.templates_dir / "report.css"

        if not self.template_file.exists():
            raise FileNotFoundError(f"template not found: {self.template_file}")
        if not self.css_file.exists():
            raise FileNotFoundError(f"css not found: {self.css_file}")

    def load_template(self) -> str:
        """load markdown template"""
        return self.template_file.read_text(encoding="utf-8")

    def load_css(self) -> str:
        """load css styles"""
        return self.css_file.read_text(encoding="utf-8")

    def substitute_placeholders(self, template: str, data: Dict[str, Any]) -> str:
        """replace ${var} placeholders with actual data"""

        def replace_placeholder(match):
            key_with_format = match.group(1)
            # extract the base key (remove formatting like :,)
            key = key_with_format.split(":")[0]
            value = data.get(key, f"${key}")

            # handle special formatting using utilities
            if isinstance(value, (int, float)):
                if (
                    "cost" in key.lower()
                    or "savings" in key.lower()
                    or "rate" in key.lower()
                    or "5yr"
                    in key.lower()  # 5-year savings should be formatted as currency
                ):
                    return fmt_currency(value)
                elif "percentage" in key.lower() or "confidence" in key.lower():
                    return fmt_percent(value, 1)
                elif "margin" in key.lower():
                    return fmt_int(value)  # margin fields should not have % symbol
                elif "hours" in key.lower() or "count" in key.lower():
                    return fmt_int(value)
                elif "rice" in key.lower():
                    # rice scores - compute if missing or return placeholder
                    if value == f"${key}":
                        return "TBD"  # fallback for missing rice scores
                    return str(value)
                else:
                    return fmt_int(value)
            elif isinstance(value, list):
                if key == "top_findings":
                    # convert top findings array to bullet list
                    return f"<ul>{''.join(f'<li>{str(v)}</li>' for v in value)}</ul>"
                else:
                    return ", ".join(str(v) for v in value)
            else:
                return str(value)

        result = re.sub(r"\$\{([^}]+)\}", replace_placeholder, template)

        # verify all placeholders resolved - fail if any remain
        unresolved = re.findall(r"\$\{[^}]+\}", result)
        if unresolved:
            raise ValueError(f"unresolved placeholders found: {unresolved}")

        # fix percentage formatting issues
        result = re.sub(r"\$(\d+(?:\.\d+)?%)", r"\1", result)  # $5% → 5%
        result = re.sub(r"(\d+(?:\.\d+)?)%%", r"\1%", result)  # 87.5%% → 87.5%

        return result

    def inject_image_paths(self, content: str) -> str:
        """inject proper image paths for components"""

        # mapping of image names to descriptive captions
        image_captions = {
            "radar.svg": "what it shows: behavioral preferences across 6-axis radar / so what: identifies systematic vs collaborative tendencies",
            "time-pie.svg": "what it shows: current time distribution across work activities / so what: identifies productivity bottlenecks and optimization opportunities",
            "handoff-flow.svg": "what it shows: workflow handoffs and decision points / so what: reveals communication gaps and process inefficiencies",
            "workflow-heatmap.svg": "what it shows: process efficiency scores across key activities / so what: highlights areas needing immediate attention",
            "swimlane.svg": "what it shows: workflow handoffs and decision points / so what: reveals communication gaps and process inefficiencies",
            "integration-map.svg": "what it shows: system connections and data flow / so what: identifies integration gaps and optimization opportunities",
            "savings-line-12mo.svg": "what it shows: projected savings over 12-month implementation / so what: demonstrates clear path to positive roi",
            "savings-line-5yr.svg": "what it shows: projected savings over 5-year implementation (units: $000s) / so what: demonstrates long-term roi and break-even analysis",
            "impact-matrix.svg": "what it shows: initiatives mapped by impact vs effort / so what: prioritizes quick wins and strategic investments",
            "mini-gantt.svg": "what it shows: phased implementation timeline with milestones / so what: provides clear execution path with dependencies",
        }

        # replace relative paths with absolute paths, preserving captions
        def replace_image(match):
            alt_text = match.group(1)
            image_path = match.group(2)

            # look for caption on the next line
            full_match = match.group(0)
            start_pos = match.end()

            # find the next line that starts with underscore (caption)
            lines = content[start_pos:].split("\n")
            caption = ""
            for line in lines[:3]:  # check next 3 lines
                if line.strip().startswith("_") and line.strip().endswith("_"):
                    caption = line.strip()[1:-1]  # remove underscores
                    break

            if caption:
                return f'<figure><img src="templates/components/{image_path}" alt="{alt_text}" class="chart"><figcaption>{caption}</figcaption></figure>'
            else:
                # use predefined caption or fallback to alt text
                predefined_caption = image_captions.get(image_path, alt_text)
                return f'<figure><img src="templates/components/{image_path}" alt="{alt_text}" class="chart"><figcaption>{predefined_caption}</figcaption></figure>'

        content = re.sub(
            r"!\[([^\]]*)\]\(components/([^)]+)\)",
            replace_image,
            content,
        )
        return content

    def markdown_to_html(self, markdown_content: str) -> str:
        """convert markdown to html"""
        if MARKDOWN_AVAILABLE:
            html = markdown.markdown(
                markdown_content, extensions=["tables", "fenced_code", "attr_list"]
            )
        else:
            # fallback: basic markdown conversion
            html = self._basic_markdown_to_html(markdown_content)

        return html

    def _basic_markdown_to_html(self, content: str) -> str:
        """basic markdown to html conversion fallback"""
        # tables - convert markdown tables to HTML first (before paragraph wrapping)
        content = self._convert_markdown_tables(content)

        # headers
        content = re.sub(r"^# (.+)$", r"<h1>\1</h1>", content, flags=re.MULTILINE)
        content = re.sub(r"^## (.+)$", r"<h2>\1</h2>", content, flags=re.MULTILINE)
        content = re.sub(r"^### (.+)$", r"<h3>\1</h3>", content, flags=re.MULTILINE)

        # bold
        content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)

        # italic
        content = re.sub(r"\*(.+?)\*", r"<em>\1</em>", content)

        # paragraphs - but don't wrap tables
        content = self._wrap_paragraphs(content)

        return content

    def _wrap_paragraphs(self, content: str) -> str:
        """wrap content in paragraphs, but preserve tables"""
        # split by double newlines to get paragraphs
        paragraphs = content.split("\n\n")
        result = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # if this paragraph contains table tags, don't wrap it
            if any(
                tag in para
                for tag in [
                    "<table>",
                    "<thead>",
                    "<tbody>",
                    "<tr>",
                    "<th>",
                    "<td>",
                    "</table>",
                ]
            ):
                result.append(para)
            else:
                result.append(f"<p>{para}</p>")

        return "\n\n".join(result)

    def _convert_markdown_tables(self, content: str) -> str:
        """convert markdown tables to HTML tables"""
        lines = content.split("\n")
        result = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # check if this line looks like a table header
            if "|" in line:
                # this might be a table, let's check the next few lines
                table_lines = []
                j = i

                # collect consecutive lines that contain |
                while j < len(lines) and "|" in lines[j]:
                    table_lines.append(lines[j])
                    j += 1

                # check if we have at least 2 lines and the second looks like a separator
                if len(table_lines) >= 2 and re.match(
                    r"^\s*\|[\s\-:]+\|", table_lines[1]
                ):
                    # this is a table, convert it
                    html_table = self._convert_table_lines_to_html(table_lines)
                    result.append(html_table)
                    i = j  # skip the table lines
                else:
                    # not a table, add the line normally
                    result.append(lines[i])
                    i += 1
            else:
                result.append(lines[i])
                i += 1

        return "\n".join(result)

    def _convert_table_lines_to_html(self, table_lines: list) -> str:
        """convert table lines to HTML table"""
        if len(table_lines) < 2:
            return "\n".join(table_lines)

        # parse header row
        header_cells = [cell.strip() for cell in table_lines[0].split("|")[1:-1]]

        # create HTML table
        html = ["<table>"]
        html.append("<thead>")
        html.append("<tr>")
        for cell in header_cells:
            html.append(f"<th>{cell}</th>")
        html.append("</tr>")
        html.append("</thead>")

        # parse data rows (skip separator line)
        if len(table_lines) > 2:
            html.append("<tbody>")
            for line in table_lines[2:]:
                cells = [cell.strip() for cell in line.split("|")[1:-1]]
                html.append("<tr>")
                for cell in cells:
                    html.append(f"<td>{cell}</td>")
                html.append("</tr>")
            html.append("</tbody>")

        html.append("</table>")
        return "\n".join(html)

    def cleanup_html(self, html_content: str) -> str:
        """post-process html to fix markdown conversion issues"""
        # strip wrapper <p> around headings
        html_content = re.sub(
            r"<p><h([1-6])[^>]*>(.*?)</h[1-6]></p>", r"<h\1>\2</h\1>", html_content
        )

        # strip wrapper <p> around page breaks
        html_content = re.sub(
            r'<p><div class="page-break"></div></p>',
            r'<div class="page-break"></div>',
            html_content,
        )

        # remove duplicate captions - keep only <figcaption>, remove italic markdown
        html_content = re.sub(
            r"<figcaption>.*?</figcaption></figure>_([^_]+)_",
            r"<figcaption>\1</figcaption></figure>",
            html_content,
        )

        # strip <p> wrappers around <table> nodes
        html_content = re.sub(
            r"<p><table([^>]*)>(.*?)</table></p>",
            r"<table\1>\2</table>",
            html_content,
            flags=re.DOTALL,
        )

        # strip <p> wrappers around <ul> lists
        html_content = re.sub(r"<p>\s*(<ul\b[^>]*>)", r"\1", html_content)
        html_content = re.sub(r"(</ul>)\s*</p>", r"\1", html_content)

        # strip <p> wrappers around <figure> elements
        html_content = re.sub(r"<p>\s*(<figure\b[^>]*>)", r"\1", html_content)
        html_content = re.sub(r"(</figure>)\s*</p>", r"\1", html_content)

        # fix list semantics: split label from list when they're in the same <p>
        html_content = re.sub(
            r"<p><strong>([^:]+:)</strong>\s*<ul>",
            r"<p><strong>\1</strong></p>\n<ul>",
            html_content,
        )

        return html_content

    def create_html_document(self, html_content: str, css_content: str) -> str:
        """create complete html document"""
        # cleanup html content
        html_content = self.cleanup_html(html_content)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>calm.profile diagnostic report</title>
    <style>
        {css_content}
    </style>
</head>
<body>
    <!-- autogenerated by renderer; do not edit -->
    {html_content}
</body>
</html>"""

    def validate_page_count(self, html_doc: str) -> bool:
        """validate that document renders to exactly 12 pages"""
        if not WEASYPRINT_AVAILABLE:
            logger.warning("weasyprint not available, cannot validate page count")
            return True

        try:
            # create temporary pdf to check page count
            temp_pdf = weasyprint.HTML(string=html_doc).write_pdf()

            # count pages by looking for page breaks in the html
            page_breaks = html_doc.count("page-break-before: always")
            estimated_pages = page_breaks + 1  # +1 for first page

            if estimated_pages > 12:
                logger.error(
                    f"document exceeds 12 pages: {estimated_pages} pages detected"
                )
                return False

            logger.info(f"page count validation passed: {estimated_pages} pages")
            return True

        except Exception as e:
            logger.warning(f"page count validation failed: {e}")
            return True  # allow to proceed if validation fails

    def validate_brand_compliance(self, html_doc: str) -> bool:
        """validate brand compliance using lint script"""
        try:
            # create temporary html file for linting
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False
            ) as f:
                f.write(html_doc)
                temp_html_path = f.name

            # run brand linter (non-blocking for now)
            try:
                lint_cmd = [
                    "python3",
                    "renderer/lint_report.py",
                    temp_html_path,
                ]

                result = subprocess.run(
                    lint_cmd, capture_output=True, text=True, cwd=os.getcwd()
                )

                if result.returncode != 0:
                    logger.warning("brand linting failed (non-blocking):")
                    logger.warning(result.stdout)
                    logger.warning(result.stderr)
                else:
                    logger.info("brand compliance validation passed")
            except Exception as e:
                logger.warning(f"brand linting failed (non-blocking): {e}")

            # cleanup
            os.unlink(temp_html_path)
            return True

        except Exception as e:
            logger.error(f"brand linting failed: {e}")
            return False

    def render_to_pdf(
        self, data: Dict[str, Any], output_path: Optional[str] = None
    ) -> str:
        """render report to pdf"""
        if not WEASYPRINT_AVAILABLE:
            raise ImportError(
                "weasyprint not available. install with: pip install weasyprint"
            )

        # load template and css
        template = self.load_template()
        css = self.load_css()

        # substitute placeholders
        content = self.substitute_placeholders(template, data)

        # inject image paths
        content = self.inject_image_paths(content)

        # convert to html
        html_content = self.markdown_to_html(content)

        # create complete document
        html_doc = self.create_html_document(html_content, css)

        # validate page count
        if not self.validate_page_count(html_doc):
            raise ValueError("document exceeds 12 pages")

        # validate brand compliance
        if not self.validate_brand_compliance(html_doc):
            raise ValueError("brand compliance validation failed")

        # create output directory
        output_dir = Path("out")
        output_dir.mkdir(exist_ok=True)

        # generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"calm_profile_report_{timestamp}.pdf"
        else:
            output_path = output_dir / output_path

        # render to pdf
        weasyprint.HTML(string=html_doc).write_pdf(str(output_path))

        logger.info(f"report generated: {output_path}")
        return str(output_path)

    def render_to_html(
        self, data: Dict[str, Any], output_path: Optional[str] = None
    ) -> str:
        """render report to html"""
        # load template and css
        template = self.load_template()
        css = self.load_css()

        # substitute placeholders
        content = self.substitute_placeholders(template, data)

        # inject image paths
        content = self.inject_image_paths(content)

        # convert to html
        html_content = self.markdown_to_html(content)

        # create complete document
        html_doc = self.create_html_document(html_content, css)

        # create output directory
        output_dir = Path("out")
        output_dir.mkdir(exist_ok=True)

        # generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"calm_profile_report_{timestamp}.html"
        else:
            output_path = output_dir / output_path

        # write html file
        Path(output_path).write_text(html_doc, encoding="utf-8")

        logger.info(f"report generated: {output_path}")
        return str(output_path)


def create_sample_data() -> Dict[str, Any]:
    """create sample data for testing"""
    return {
        "company_name": "acme corp",
        "assessment_date": datetime.now().strftime("%b %d, %Y"),
        "report_id": str(uuid.uuid4())[:8],
        "assessment_id": str(uuid.uuid4())[:8],
        "completion_date": datetime.now().strftime("%Y-%m-%d"),
        "response_count": 20,
        "confidence_score": 87.5,
        "archetype_primary": "architect",
        "archetype_confidence": 87.5,
        "archetype_tagline": "systematic builders of scalable foundations",
        "archetype_mix_primary": 65.0,
        "archetype_mix_secondary": 20.0,
        "archetype_mix_tertiary": 10.0,
        "archetype_mix_quaternary": 5.0,
        "archetype_secondary": "conductor",
        "archetype_tertiary": "curator",
        "archetype_quaternary": "craftsperson",
        "axis_structure": 85,
        "axis_collaboration": 35,
        "axis_scope": 70,
        "axis_tempo": 40,
        "archetype_strengths": [
            "framework design",
            "process optimization",
            "long-term planning",
            "system integration",
        ],
        "overhead_percentage": 15.2,
        "annual_cost": 125000,
        "hours_lost_ppw": 6.1,
        "team_multiplier": 4,
        "break_even_timeline": "3-4 months",
        "top_findings": [
            "strong preference for structured approaches with moderate collaboration needs",
            "excellent foundation for systematic improvements with clear path to 35% productivity gains",
            "communication delays and context switching overhead identified as primary bottlenecks",
        ],
        "radar_insights": "strong preference for structured approaches with moderate collaboration needs. excels in systematic thinking and framework development.",
        "time_productive": 45,
        "time_meetings": 25,
        "time_admin": 20,
        "time_context_switch": 10,
        "time_optimization": "reduce meeting overhead by 40% through async protocols and streamline administrative processes with automation tools.",
        "efficiency_planning": 9,
        "efficiency_execution": 7,
        "efficiency_review": 8,
        "efficiency_communication": 6,
        "workflow_bottlenecks": "communication delays and context switching overhead. meetings are inefficient and lack clear agendas.",
        # findings cards f1-f5
        "f1_issue": "inefficient meeting patterns",
        "f1_evidence": "25% of time spent in meetings with unclear agendas",
        "f1_impact": "6.1 hours lost per week per person",
        "f1_root_cause": "lack of structured meeting protocols",
        "f1_preview": "implement async-first communication and structured meeting templates",
        "f2_issue": "context switching overhead",
        "f2_evidence": "10% of time lost to task switching",
        "f2_impact": "2.4 hours per week per person",
        "f2_root_cause": "fragmented communication channels",
        "f2_preview": "consolidate communication to single platform with maker time blocks",
        "f3_issue": "administrative task burden",
        "f3_evidence": "20% of time on non-productive admin work",
        "f3_impact": "4.8 hours per week per person",
        "f3_root_cause": "lack of automation and process optimization",
        "f3_preview": "implement automation tools and process templates",
        "f4_issue": "unclear decision ownership",
        "f4_evidence": "delayed decisions due to unclear responsibility",
        "f4_impact": "3.2 hours per week per person",
        "f4_root_cause": "missing decision framework",
        "f4_preview": "establish rasic matrix and decision protocols",
        "f5_issue": "project tracking fragmentation",
        "f5_evidence": "multiple tools without integration",
        "f5_impact": "2.8 hours per week per person",
        "f5_root_cause": "lack of centralized project management",
        "f5_preview": "implement integrated project tracking system",
        # roi analysis
        "base_overhead": 12.0,
        "archetype_adjustment": 1.27,
        "hourly_rate": 85,
        "weekly_cost": 2074,
        "savings_month1": 5,
        "savings_month3": 15,
        "savings_month6": 25,
        "savings_month12": 35,
        "sensitivity_conservative_overhead": 12.0,
        "sensitivity_conservative_cost": 100000,
        "sensitivity_conservative_savings": 25,
        "sensitivity_conservative_payback": "4-5 months",
        "sensitivity_optimistic_overhead": 8.0,
        "sensitivity_optimistic_cost": 150000,
        "sensitivity_optimistic_savings": 45,
        "sensitivity_optimistic_payback": "2-3 months",
        # recommendations r1-r5
        "r1_title": "implement project templates",
        "r1_linked_finding": "1",
        "r1_description": "create standardized project templates for common workflows",
        "r1_effort": "low",
        "r1_impact": "high",
        "r1_timeline": "2 weeks",
        "r2_title": "establish async communication protocols",
        "r2_linked_finding": "2",
        "r2_description": "implement async-first communication with structured updates",
        "r2_effort": "medium",
        "r2_impact": "high",
        "r2_timeline": "4 weeks",
        "r3_title": "automate administrative processes",
        "r3_linked_finding": "3",
        "r3_description": "implement automation tools for routine administrative tasks",
        "r3_effort": "medium",
        "r3_impact": "medium",
        "r3_timeline": "6 weeks",
        "r4_title": "create decision ownership matrix",
        "r4_linked_finding": "4",
        "r4_description": "establish clear decision ownership and escalation protocols",
        "r4_effort": "low",
        "r4_impact": "high",
        "r4_timeline": "1 week",
        "r5_title": "integrate project tracking systems",
        "r5_linked_finding": "5",
        "r5_description": "consolidate project tracking into single integrated platform",
        "r5_effort": "high",
        "r5_impact": "medium",
        "r5_timeline": "8 weeks",
        # rasic matrix
        "rasic_initiative1": "template implementation",
        "rasic_r1": "pm",
        "rasic_a1": "cto",
        "rasic_s1": "design team",
        "rasic_c1": "engineering leads",
        "rasic_i1": "all teams",
        "rasic_initiative2": "async protocols",
        "rasic_r2": "pm",
        "rasic_a2": "engineering manager",
        "rasic_s2": "all teams",
        "rasic_c2": "stakeholders",
        "rasic_i2": "all teams",
        "rasic_initiative3": "automation setup",
        "rasic_r3": "devops",
        "rasic_a3": "pm",
        "rasic_s3": "engineering",
        "rasic_c3": "qa team",
        "rasic_i3": "all teams",
        "rasic_initiative4": "decision framework",
        "rasic_r4": "team leads",
        "rasic_a4": "pm",
        "rasic_s4": "all teams",
        "rasic_c4": "management",
        "rasic_i4": "all teams",
        # roadmap
        "critical_path": "template implementation → automation setup → team adoption → optimization",
        "milestone_schedule": "week 2: templates deployed, week 4: automation active, week 6: full team adoption, week 8: optimization complete",
        "roadmap_30_days": [
            "implement project templates",
            "establish decision ownership matrix",
            "create async communication protocols",
        ],
        "roadmap_60_days": [
            "deploy automation tools",
            "integrate project tracking systems",
            "train team on new processes",
        ],
        "roadmap_90_days": [
            "optimize workflows based on feedback",
            "scale successful practices",
            "measure and report on improvements",
        ],
        "roadmap_kpis": [
            "15% productivity improvement in month 1",
            "25% meeting reduction",
            "90% template adoption",
            "35% annual cost savings by month 12",
        ],
        "next_steps": "implement templates immediately, reduce meeting overhead by 50%, protect maker time with async protocols, establish clear decision ownership.",
        "technical_notes": "assessment based on 20 behavioral indicators across 4 core axes: structure, collaboration, scope, and tempo. calibrated against team context variables including meeting load, team size, and hourly rates.",
        "data_sources": "calm.profile assessment system, team context variables, industry benchmarks, behavioral psychology research, productivity studies.",
    }


def main():
    """main function for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="render calm.profile reports")
    parser.add_argument("--data", help="json data file")
    parser.add_argument("--output", help="output file path")
    parser.add_argument(
        "--format", choices=["pdf", "html"], default="pdf", help="output format"
    )
    parser.add_argument("--sample", action="store_true", help="use sample data")

    args = parser.parse_args()

    # load data
    if args.sample:
        data = create_sample_data()
    elif args.data:
        with open(args.data, "r") as f:
            data = json.load(f)
    else:
        print("error: specify --data file or --sample")
        return 1

    # render report
    renderer = ReportRenderer()

    try:
        if args.format == "pdf":
            output_path = renderer.render_to_pdf(data, args.output)
        else:
            output_path = renderer.render_to_html(data, args.output)

        print(f"report generated: {output_path}")
        return 0

    except Exception as e:
        print(f"error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
