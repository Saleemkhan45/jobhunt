"""Command-line interface (argparse + rich for nice terminal output)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone

from pydantic import ValidationError
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .aggregator import JobAggregator
from .config import Settings
from .models import ApplicationStatus, Job, JobType, SearchQuery
from .sources import ALL_SOURCES
from .storage import JsonStore
from .tracker import ApplicationTracker, TrackerError

console = Console()

STATUS_STYLE = {
    "saved": "cyan",
    "applied": "blue",
    "interview": "yellow",
    "offer": "magenta",
    "selected": "bold green",
    "rejected": "red",
}


def _age(job: Job) -> str:
    if not job.posted_at:
        return "-"
    days = (datetime.now(timezone.utc) - job.posted_at).days
    return "today" if days <= 0 else f"{days}d"


def _jobs_table(jobs: list[Job], title: str) -> Table:
    table = Table(title=title, show_lines=False, header_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Title", max_width=42)
    table.add_column("Company", max_width=22)
    table.add_column("Location", max_width=22)
    table.add_column("Type")
    table.add_column("Age", justify="right")
    table.add_column("Source", style="dim")
    for index, job in enumerate(jobs, start=1):
        title_text = job.title + (" [green](remote)[/]" if job.remote else "")
        table.add_row(
            str(index), title_text, job.company, job.location,
            job.job_type.value.replace("_", " "), _age(job), job.source,
        )
    return table


# ---- commands -----------------------------------------------------------------


def cmd_search(args: argparse.Namespace, settings: Settings, store: JsonStore) -> int:
    query = SearchQuery(
        keyword=args.keyword,
        location=args.location,
        remote_only=args.remote,
        job_type=JobType(args.type) if args.type else None,
        limit=args.limit,
        max_age_days=args.days,
    )
    sources = args.sources.split(",") if args.sources else None
    aggregator = JobAggregator(settings, sources)

    mode = "offline sample data" if settings.offline else "live APIs"
    with console.status(f"Searching {len(sources or ALL_SOURCES)} job boards ({mode})…"):
        result = asyncio.run(aggregator.search(query))

    for name, error in result.errors.items():
        console.print(f"[yellow]⚠ {name} unavailable:[/] {error}")
    if result.errors and not result.per_source:
        console.print("[red]All sources failed.[/] Check your internet, or try [bold]--offline[/].")
        return 1

    store.save_results(result.jobs)
    per_source = ", ".join(f"{k}: {v}" for k, v in result.per_source.items())
    console.print(_jobs_table(result.jobs, f"'{query.keyword}' — {len(result.jobs)} jobs"))
    console.print(
        f"[dim]Fetched per board → {per_source}. "
        f"{result.raw_total} keyword matches, {len(result.jobs)} shown after filters "
        f"and de-duplication. Saved to {store.results_path.name}.[/]"
    )
    console.print("[dim]Next: `jobhunt show 3` for details, `jobhunt save 3` to track it.[/]")
    return 0


def _pick(store: JsonStore, number: int) -> Job:
    jobs = store.load_results()
    if not jobs:
        raise TrackerError("no saved search yet, run `search` first")
    if not 1 <= number <= len(jobs):
        raise TrackerError(f"pick a number between 1 and {len(jobs)}")
    return jobs[number - 1]


def cmd_show(args: argparse.Namespace, settings: Settings, store: JsonStore) -> int:
    job = _pick(store, args.number)
    body = (
        f"[bold]{job.company}[/] · {job.location} · {job.job_type.value.replace('_', ' ')}"
        f"{' · remote' if job.remote else ''}\n"
    )
    body += f"Posted: {job.posted_at:%d %b %Y}\n" if job.posted_at else ""
    body += f"Salary: {job.salary}\n" if job.salary else ""
    summary = job.description[:600] + ("…" if len(job.description) > 600 else "")
    body += f"Tags: {', '.join(job.tags) or '-'}\n\n{summary or 'No description.'}\n\n"
    body += f"[link={job.url}]{job.url}[/link]\n[dim]id {job.fingerprint} · from {job.source}[/]"
    console.print(Panel(body, title=job.title, expand=False))
    return 0


def cmd_save(args: argparse.Namespace, settings: Settings, store: JsonStore) -> int:
    tracker = ApplicationTracker(store)
    job = _pick(store, args.number)
    tracker.add(job)
    console.print(f"[green]✓ Tracking[/] {job.title} at {job.company} (id [bold]{job.fingerprint[:6]}[/])")
    return 0


def cmd_list(args: argparse.Namespace, settings: Settings, store: JsonStore) -> int:
    tracker = ApplicationTracker(store)
    status = ApplicationStatus(args.status) if args.status else None
    table = Table(title="Tracked applications", header_style="bold")
    for column in ("ID", "Title", "Company", "Status", "Updated", "Source"):
        table.add_column(column)
    for app in tracker.iter_by_status(status):
        style = STATUS_STYLE[app.status.value]
        table.add_row(
            app.job.fingerprint[:6], app.job.title, app.job.company,
            f"[{style}]{app.status.value}[/]", f"{app.history[-1].at:%d %b %H:%M}", app.job.source,
        )
    if not table.row_count:
        console.print("Nothing tracked yet. Run `search`, then `save <number>`.")
        return 0
    console.print(table)
    return 0


def cmd_update(args: argparse.Namespace, settings: Settings, store: JsonStore) -> int:
    tracker = ApplicationTracker(store)
    app = tracker.update_status(args.id, ApplicationStatus(args.status), args.note)
    style = STATUS_STYLE[app.status.value]
    console.print(f"[green]✓[/] {app.job.title} → [{style}]{app.status.value}[/]")
    return 0


def cmd_remove(args: argparse.Namespace, settings: Settings, store: JsonStore) -> int:
    app = ApplicationTracker(store).remove(args.id)
    console.print(f"Removed {app.job.title} at {app.job.company}")
    return 0


def cmd_report(args: argparse.Namespace, settings: Settings, store: JsonStore) -> int:
    report = ApplicationTracker(store).report()
    table = Table(title="Job-search report", header_style="bold", show_header=False)
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Jobs tracked", str(report["total_tracked"]))
    for status, count in report["by_status"].items():  # type: ignore[union-attr]
        table.add_row(f"  {status}", str(count))
    table.add_row("Interview rate", f"{report['interview_rate']}%")
    for source, count in report["by_source"].items():  # type: ignore[union-attr]
        table.add_row(f"From {source}", str(count))
    console.print(table)
    if args.export:
        report["generated_at"] = datetime.now(timezone.utc).isoformat()
        path = store.export(report, "report.json")
        console.print(f"[dim]Report exported to {path}[/]")
    return 0


def cmd_sources(args: argparse.Namespace, settings: Settings, store: JsonStore) -> int:
    for name, cls in ALL_SOURCES.items():
        console.print(f"[bold]{name:<10}[/] {cls.base_url}")
    return 0


# ---- parser -------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jobhunt",
        description="Search several job boards at once, then track your applications.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="show timing/retry logs")
    parser.add_argument("--offline", action="store_true", help="use bundled sample data")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="search all job boards concurrently")
    search.add_argument("keyword", help='e.g. "python", "react", "intern"')
    search.add_argument("-l", "--location", help="city or country (remote jobs always included)")
    search.add_argument("-r", "--remote", action="store_true", help="remote jobs only")
    search.add_argument("-t", "--type", choices=[t.value for t in JobType])
    search.add_argument("-n", "--limit", type=int, default=20)
    search.add_argument("-d", "--days", type=int, help="only jobs posted in the last N days")
    search.add_argument("-s", "--sources", help=f"comma list from: {', '.join(ALL_SOURCES)}")
    search.set_defaults(func=cmd_search)

    show = sub.add_parser("show", help="details of result #N from the last search")
    show.add_argument("number", type=int)
    show.set_defaults(func=cmd_show)

    save = sub.add_parser("save", help="start tracking result #N")
    save.add_argument("number", type=int)
    save.set_defaults(func=cmd_save)

    lst = sub.add_parser("list", help="list tracked applications")
    lst.add_argument("--status", choices=[s.value for s in ApplicationStatus])
    lst.set_defaults(func=cmd_list)

    update = sub.add_parser("update", help="change an application's status")
    update.add_argument("id", help="first characters of the tracker id")
    update.add_argument("status", choices=[s.value for s in ApplicationStatus])
    update.add_argument("--note")
    update.set_defaults(func=cmd_update)

    remove = sub.add_parser("remove", help="stop tracking an application")
    remove.add_argument("id")
    remove.set_defaults(func=cmd_remove)

    report = sub.add_parser("report", help="summary of your job search")
    report.add_argument("--export", action="store_true", help="also write data/report.json")
    report.set_defaults(func=cmd_report)

    sources = sub.add_parser("sources", help="list supported job boards")
    sources.set_defaults(func=cmd_sources)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False, show_time=False)],
    )
    settings = Settings.from_env(offline=args.offline or None)
    store = JsonStore(settings.data_dir)
    try:
        return args.func(args, settings, store)
    except ValidationError as exc:
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"]) or "input"
            console.print(f"[red]Invalid {field}:[/] {error['msg']}")
        return 2
    except (TrackerError, ValueError) as exc:
        console.print(f"[red]Error:[/] {exc}")
        return 1
    except KeyboardInterrupt:
        console.print("\nCancelled.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
