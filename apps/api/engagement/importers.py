"""
Connecteurs d'import partenaire (CAT-02). Chaque connecteur transforme une source autorisée
(UiTdatabank, agenda.brussels, flux ICS d'un lieu partenaire…) en événements `source=IMPORT`,
dédoublonnés par (import_source, external_id). Aucun scraping non autorisé (§5.6).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import ImportSource


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    log: list[str] = field(default_factory=list)


class BaseImporter:
    def __init__(self, source: ImportSource):
        self.source = source
        self.result = ImportResult()

    def run(self) -> ImportResult:
        raise NotImplementedError


class NoopImporter(BaseImporter):
    """Connecteur de démonstration : vérifie la configuration sans écrire."""

    def run(self) -> ImportResult:
        self.result.log.append(
            f"Source {self.source.slug} ({self.source.kind}) : connecteur non implémenté."
        )
        return self.result


REGISTRY: dict[str, type[BaseImporter]] = {
    "noop": NoopImporter,
    # "uitdatabank": UiTdatabankImporter,   # à implémenter après accord publiq (§13)
    # "agenda_brussels": AgendaBrusselsImporter,
    # "ics": IcsFeedImporter,
}


def get_importer(source: ImportSource) -> BaseImporter:
    cls = REGISTRY.get(source.kind, NoopImporter)
    return cls(source)
