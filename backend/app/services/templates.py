"""Reusable project templates: standard epics and milestone skeletons per delivery type."""

from dataclasses import dataclass

from app.models.enums import Methodology, ProjectKind


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    description: str
    kind: ProjectKind
    methodology: Methodology
    epics: tuple[str, ...]
    # (milestone name, offset in days from project start)
    milestones: tuple[tuple[str, int], ...]


TEMPLATES: dict[str, Template] = {
    t.id: t
    for t in (
        Template(
            "saas-feature",
            "SaaS feature delivery",
            "Scrum delivery of a customer-facing feature: discovery through release.",
            ProjectKind.software,
            Methodology.scrum,
            ("Discovery & design", "Core implementation", "Quality & hardening", "Launch"),
            (("Design sign-off", 14), ("Beta release", 56), ("General availability", 84)),
        ),
        Template(
            "data-migration",
            "Cloud data platform migration",
            "Legacy databases to a cloud lakehouse with CDC, medallion layers and BI cut-over.",
            ProjectKind.data_platform,
            Methodology.hybrid,
            (
                "Source inventory & profiling",
                "CDC ingestion (Bronze)",
                "Conformed models (Silver)",
                "Business marts (Gold)",
                "Reconciliation & data quality",
                "BI cut-over",
            ),
            (
                ("Environments ready", 21),
                ("Bronze ingestion live", 56),
                ("Silver/Gold UAT", 105),
                ("Production cut-over", 140),
            ),
        ),
        Template(
            "ai-product",
            "AI / RAG product",
            "LLM application with evaluation gates, safety review and staged rollout.",
            ProjectKind.ai_product,
            Methodology.scrum,
            (
                "Use-case discovery",
                "Knowledge ingestion & indexing",
                "Prompt & retrieval design",
                "Evaluation & safety",
                "Pilot & rollout",
            ),
            (
                ("Eval baseline agreed", 28),
                ("Safety review passed", 70),
                ("Pilot launch", 84),
            ),
        ),
        Template(
            "waterfall-generic",
            "Phase-gated project",
            "Traditional phase-gated plan with formal gate reviews.",
            ProjectKind.general,
            Methodology.waterfall,
            ("Requirements", "Design", "Build", "Test", "Deploy"),
            (("Requirements gate", 21), ("Design gate", 42), ("Test exit", 98), ("Go-live", 112)),
        ),
    )
}
