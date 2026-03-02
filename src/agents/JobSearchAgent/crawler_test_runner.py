import argparse
import json
from pathlib import Path
import sys
from typing import Any

try:
    from src.agents.JobSearchAgent.crawlerEngine import parse_keywords, run_crawler
except ModuleNotFoundError:
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.agents.JobSearchAgent.crawlerEngine import parse_keywords, run_crawler


def crawl_single_company(args: argparse.Namespace) -> dict[str, Any]:
    return run_crawler(
        company_name=args.company,
        endpoint=args.endpoint,
        keywords=parse_keywords(args.keywords),
        site_number=args.site_number,
        location_id=args.location_id,
        category_id=args.category_id,
        output_dir=args.output_dir,
    )


def crawl_multiple_companies(companies: list[dict[str, Any]], output_dir: str) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    for cfg in companies:
        result = run_crawler(
            company_name=cfg["company"],
            endpoint=cfg["endpoint"],
            keywords=parse_keywords(cfg.get("keywords")),
            site_number=cfg.get("site_number"),
            location_id=cfg.get("location_id"),
            category_id=cfg.get("category_id"),
            output_dir=cfg.get("output_dir", output_dir),
        )
        results.append(result)

    success_count = sum(1 for item in results if item.get("status") == "success")
    return {
        "status": "success",
        "total_companies": len(results),
        "successful_companies": success_count,
        "results": results,
    }


def load_companies_from_file(batch_file: str) -> list[dict[str, Any]]:
    path = Path(batch_file)
    if not path.exists():
        raise FileNotFoundError(f"Batch file not found: {batch_file}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Batch file must contain a list of company configs.")

    required = {"company", "endpoint"}
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid company config at index {idx}: expected object.")
        missing = required - set(item.keys())
        if missing:
            raise ValueError(
                f"Invalid company config at index {idx}: missing {sorted(missing)}"
            )

    return data


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Test runner for generic job crawler (single or multiple companies)."
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--batch-file",
        help="Path to JSON file with a list of company configs.",
    )
    mode.add_argument(
        "--company",
        help="Single company display name.",
    )

    parser.add_argument("--endpoint", help="Single company API endpoint URL.")
    parser.add_argument("--site-number", default=None, help="Site number (e.g., CX_1001).")
    parser.add_argument("--location-id", default=None, help="Optional location facet ID.")
    parser.add_argument("--category-id", default=None, help="Optional category facet ID.")
    parser.add_argument(
        "--keywords",
        default=None,
        help="Comma-separated keywords. Example: 'AI,LLM,Python'",
    )
    parser.add_argument("--output-dir", default="dataset", help="Output directory.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    if args.batch_file:
        companies = load_companies_from_file(args.batch_file)
        result = crawl_multiple_companies(companies, output_dir=args.output_dir)
        print(json.dumps(result, indent=2))
        return

    if not args.endpoint:
        raise SystemExit("--endpoint is required when using --company")

    result = crawl_single_company(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
