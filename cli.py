#!/usr/bin/env python3
"""Command-Line Interface & Harness Runner for the Grad School Scholarship Finder Agent."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import shutil
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import yaml

from scholarship_agent.tools.eligibility_tools import (
    batch_score_scholarships,
    evaluate_scholarship_fit,
)
from scholarship_agent.tools.essay_tools import (
    get_essay_prompt_context,
    save_essay_draft,
)
from scholarship_agent.tools.profile_tools import (
    get_student_profile,
    update_profile_setting,
)
from scholarship_agent.tools.search_tools import (
    scrape_scholarship_page,
    search_scholarships_web,
)
from scholarship_agent.tools.tracker_tools import sync_and_export_tracker

console = Console()


def cmd_init(args: argparse.Namespace) -> None:
    """Create or customize a local, git-ignored profile.yaml from profile.example.yaml."""
    repo_root = Path(__file__).resolve().parent
    example_path = repo_root / "profile.example.yaml"
    target_path = Path(args.profile).expanduser().resolve() if args.profile else (repo_root / "profile.yaml")

    if not target_path.exists() or args.force:
        shutil.copyfile(example_path, target_path)

    with target_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if args.name:
        data.setdefault("student", {})["name"] = args.name
    if args.citizenship:
        data.setdefault("student", {})["citizenship_status"] = args.citizenship
    if args.state:
        data.setdefault("geographies", {})["current_state_or_province"] = args.state
    if args.country:
        data.setdefault("geographies", {})["current_country"] = args.country
    if args.degree:
        data.setdefault("academics", {})["target_degree"] = args.degree
    if args.field:
        data.setdefault("academics", {})["field_of_study"] = args.field
    if args.gpa is not None:
        data.setdefault("academics", {})["gpa"] = float(args.gpa)
    if args.min_award is not None:
        data.setdefault("filters", {})["min_award_amount_usd"] = int(args.min_award)

    with target_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    console.print(
        Panel.fit(
            f"Initialized local profile at [bold green]{target_path}[/bold green] (git-ignored).\n"
            f"• Name: {data.get('student', {}).get('name')}\n"
            f"• Degree & Field: {data.get('academics', {}).get('target_degree')} in {data.get('academics', {}).get('field_of_study')}\n"
            f"• Geography: {data.get('geographies', {}).get('current_state_or_province')}, {data.get('geographies', {}).get('current_country')}\n"
            f"• Min Award Filter: ${data.get('filters', {}).get('min_award_amount_usd', 0):,}",
            title="Profile Initialized",
        )
    )


def cmd_match(args: argparse.Namespace) -> None:
    """Score scholarships against profile.yaml (geographies & filters) and export SQLite/CSV/Markdown."""
    result = sync_and_export_tracker(profile_path=args.profile)
    scored = batch_score_scholarships(include_filtered_out=True, profile_path=args.profile)
    profile = get_student_profile(profile_path=args.profile).get("profile", {})

    geo = profile.get("geographies", {})
    flt = profile.get("filters", {})

    console.print(
        Panel.fit(
            f"[bold cyan]Student:[/bold cyan] {profile.get('student', {}).get('name')} "
            f"({profile.get('student', {}).get('citizenship_status')})\n"
            f"[bold cyan]Program:[/bold cyan] {profile.get('academics', {}).get('target_degree')} in "
            f"{profile.get('academics', {}).get('field_of_study')} (GPA {profile.get('academics', {}).get('gpa')})\n"
            f"[bold cyan]Geography:[/bold cyan] {geo.get('current_city_or_metro')}, {geo.get('current_state_or_province')} "
            f"-> Study in {', '.join(geo.get('study_destination_countries', []))}\n"
            f"[bold cyan]Filters:[/bold cyan] Min Award ${flt.get('min_award_amount_usd', 0):,} | "
            f"Min Fit Score {flt.get('min_fit_score_threshold', 0)} | "
            f"Matched: [bold green]{result['matched_count']}[/bold green] "
            f"(${result['total_potential_award_usd']:,} total) | "
            f"Filtered Out: [bold yellow]{result['filtered_out_count']}[/bold yellow]",
            title="Grad School Scholarship Finder — Harness Match Summary",
        )
    )

    table = Table(title="Top Recommended Graduate Scholarships (Passed Geography & Filter Rules)")
    table.add_column("Fit Score", justify="center", style="bold green")
    table.add_column("Status", style="cyan")
    table.add_column("Scholarship", style="bold")
    table.add_column("Scope / Region", style="magenta")
    table.add_column("Award", style="yellow")
    table.add_column("Deadline", justify="center")

    for rec in scored["scholarships"]:
        if not rec.get("filter_passed"):
            continue
        region_info = f"{rec['geography_scope']} ({', '.join(rec.get('eligible_states_or_regions', [])[:2])})"
        table.add_row(
            f"{rec['fit_score']}/100",
            rec["eligibility_status"],
            f"{rec['name']}\n[dim]{rec['scholarship_id']}[/dim]",
            region_info,
            rec["award_display"],
            rec["deadline"],
        )

    console.print(table)

    if scored["filtered_out_summary"]:
        rej_table = Table(title="Filtered-Out Scholarships (Blocked by Geography or Filter Config)")
        rej_table.add_column("Scholarship", style="dim")
        rej_table.add_column("Filter Rejection Reason(s)", style="red")
        for rej in scored["filtered_out_summary"]:
            rej_table.add_row(
                f"{rej['name']} ({rej['scholarship_id']})",
                "; ".join(rej["reasons"]),
            )
        console.print(rej_table)

    console.print(
        f"\n[bold green]Exported artifacts:[/bold green]\n"
        f"  • SQLite DB: [underline]{result['sqlite_db_path']}[/underline]\n"
        f"  • CSV Export: [underline]{result['csv_path']}[/underline]\n"
        f"  • Markdown Dashboard: [underline]{result['dashboard_markdown_path']}[/underline]"
    )


def cmd_search(args: argparse.Namespace) -> None:
    """Run live web + curated search for graduate scholarships."""
    res = search_scholarships_web(query=args.query, max_results=args.max_results)
    console.print(
        Panel.fit(
            f"Query: [bold]{args.query}[/bold]\n"
            f"Curated Matches: [green]{res['curated_matches_count']}[/green] | "
            f"Live Web Results: [cyan]{res['live_web_results_count']}[/cyan]",
            title="Scholarship Discovery Search",
        )
    )
    if res["curated_matches"]:
        console.print("[bold]Curated Fellowship Matches:[/bold]")
        for item in res["curated_matches"]:
            console.print(f"  • [bold]{item['name']}[/bold] ({item['award_display']}) — {item['source_url']}")
    if res["live_web_results"]:
        console.print("\n[bold]Live Web Search Results (Sanitized):[/bold]")
        for item in res["live_web_results"]:
            console.print(f"  • [bold]{item['title']}[/bold]\n    {item['url']}\n    [dim]{item['snippet']}[/dim]")


def cmd_scrape(args: argparse.Namespace) -> None:
    """Scrape and sanitize an external scholarship webpage."""
    res = scrape_scholarship_page(args.url)
    console.print_json(data=res)


def cmd_essay(args: argparse.Namespace) -> None:
    """Generate a structured essay outline & starter draft for a target scholarship."""
    ctx = get_essay_prompt_context(args.scholarship_id, profile_path=args.profile)
    if ctx.get("status") != "success":
        console.print(f"[bold red]Error:[/bold red] {ctx.get('error')}")
        sys.exit(1)

    eval_res = evaluate_scholarship_fit(args.scholarship_id, profile_path=args.profile).get("evaluation", {})
    student = ctx["student_summary"]
    prompts = ctx.get("essay_prompts", [])
    projects = student.get("projects", [])
    leadership = student.get("leadership", [])

    draft_lines = [
        "## Prompt & Fellowship Context",
        f"- **Fellowship**: {ctx['scholarship_name']} ({ctx['provider']})",
        f"- **Profile Fit Score**: {eval_res.get('fit_score', 'N/A')}/100 ({eval_res.get('eligibility_status', '')})",
        "- **Official Prompt(s)**:",
    ]
    for p in prompts:
        draft_lines.append(f"  - *{p}*")

    draft_lines.extend(["", "## Tailored Essay Outline"])
    for step in ctx.get("recommended_outline", []):
        draft_lines.append(f"- {step}")

    proj_title = projects[0]["title"] if projects else "Graduate AI Research"
    proj_summary = projects[0]["summary"] if projects else ""
    lead_role = leadership[0]["role"] if leadership else "Academic Mentor"
    lead_summary = leadership[0]["summary"] if leadership else ""
    geo = student.get("geography", {})

    draft_lines.extend(
        [
            "",
            "## Starter Personal Statement Draft",
            "",
            f"As an incoming {student.get('target_degree')} student in {student.get('field_of_study')}, "
            f"my research mission is to {student.get('career_goals', '').lower()} "
            f"Through my work on *{proj_title}*—where I {proj_summary[0].lower() + proj_summary[1:] if proj_summary else 'developed reliable AI systems'}—"
            f"I saw firsthand how rigorous engineering can transform experimental models into dependable tools.",
            "",
            f"In graduate school (targeting {', '.join(student.get('target_universities', [])[:2])}), I plan to focus on "
            f"{', '.join(student.get('research_interests', [])[:3])}. "
            f"Beyond technical research, I am committed to broadening participation in computing across "
            f"{geo.get('current_city_or_metro', 'my community')} and {geo.get('current_state_or_province', 'beyond')}. "
            f"As {lead_role} ({lead_summary}), I have seen how structured mentorship accelerates student confidence and research readiness.",
            "",
            f"The {ctx['scholarship_name']} will provide the intellectual community and support needed to advance this research agenda and translate these innovations into lasting public benefit.",
        ]
    )

    saved = save_essay_draft(
        scholarship_id=args.scholarship_id,
        essay_title=f"{ctx['scholarship_name']} — Tailored Application Essay",
        draft_markdown="\n".join(draft_lines),
    )
    console.print(
        Panel.fit(
            f"Saved tailored outline & starter draft for [bold]{ctx['scholarship_name']}[/bold] to:\n"
            f"[underline green]{saved['file_path']}[/underline green]",
            title="Essay Assistant",
        )
    )


async def _run_adk_prompt(prompt: str) -> None:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from scholarship_agent import get_root_agent

    session_service = InMemorySessionService()
    agent = get_root_agent()
    runner = Runner(
        agent=agent,
        app_name="scholarship_agent",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="scholarship_agent",
        user_id="grad_student",
    )
    content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    async for event in runner.run_async(
        user_id="grad_student",
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    console.print(Panel(part.text, title="Google ADK Scholarship Coordinator"))


def cmd_agent(args: argparse.Namespace) -> None:
    """Run a prompt through the full Google ADK multi-agent coordinator."""
    asyncio.run(_run_adk_prompt(args.prompt))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Grad School Scholarship Finder — Google ADK + Harness Engineering CLI"
    )
    parser.add_argument(
        "--profile",
        default="",
        help="Optional path to custom profile.yaml (defaults to ./profile.yaml)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser(
        "init",
        help="Initialize or customize your local git-ignored profile.yaml from profile.example.yaml",
    )
    p_init.add_argument("--force", action="store_true", help="Overwrite existing profile.yaml with template")
    p_init.add_argument("--name", help="Student name")
    p_init.add_argument("--citizenship", help="Citizenship status (e.g. 'US Citizen', 'International')")
    p_init.add_argument("--state", help="Current state or province (e.g. 'California', 'Washington')")
    p_init.add_argument("--country", help="Current country (e.g. 'United States', 'Canada')")
    p_init.add_argument("--degree", help="Target degree (e.g. \"Master's\", 'PhD', 'MBA')")
    p_init.add_argument("--field", help="Field of study (e.g. 'Computer Science', 'Bioengineering')")
    p_init.add_argument("--gpa", type=float, help="Current GPA (e.g. 3.85)")
    p_init.add_argument("--min-award", type=int, help="Minimum award filter in USD (e.g. 5000)")

    sub.add_parser(
        "match",
        help="Score scholarships using profile.yaml (geographies & filters) and export SQLite/CSV/Markdown dashboard",
    )

    p_search = sub.add_parser("search", help="Run curated + live web search for scholarships")
    p_search.add_argument("query", help="Search keywords (e.g. 'AI fellowship Washington')")
    p_search.add_argument("--max-results", type=int, default=6)

    p_scrape = sub.add_parser("scrape", help="Scrape and sanitize a scholarship webpage URL")
    p_scrape.add_argument("url", help="Official https:// URL to scrape")

    p_essay = sub.add_parser("essay", help="Generate a tailored essay outline and draft for a scholarship ID")
    p_essay.add_argument("scholarship_id", help="Scholarship ID (e.g., nsf-grfp-2027, uw-gsee-fellowship-2027)")

    p_agent = sub.add_parser("agent", help="Send a natural language prompt to the Google ADK root_agent")
    p_agent.add_argument("prompt", help="Prompt for the ADK agent")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {
        "init": cmd_init,
        "match": cmd_match,
        "search": cmd_search,
        "scrape": cmd_scrape,
        "essay": cmd_essay,
        "agent": cmd_agent,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
