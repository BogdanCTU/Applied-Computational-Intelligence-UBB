"""Dataset discovery, validation, and preview service (read-only on original_repo/data/)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...evaluation.metrics import load_alignment_csv_pairs, load_reference_pairs
from ...ontology.entity_extractor import EntityExtractor
from ...ontology.parser import load_ontology
from ..paths import ProjectPaths, resolve_project_paths


@dataclass
class DatasetDescriptor:
    """Describes an OAEI benchmark ontology pair or user-supplied custom dataset."""

    dataset_id: str
    track: str
    pair_name: str
    source_path: Path
    target_path: Path
    reference_path: Optional[Path]
    context_hint: str
    o1_is_code_hint: bool = False
    o2_is_code_hint: bool = False


class DatasetService:
    """Discovers read-only OAEI datasets and inspects entity/triple/reference statistics."""

    TRACK_CONTEXTS = {
        "conference": ("conference", False, False),
        "anatomy": ("anatomy", True, True),
        "biodiv": ("biodiversity", True, True),
        "mse": ("materials science and engineering", False, False),
        "phenotype": ("disease and phenotype", True, True),
        "commonkg": ("general knowledge", False, False),
    }

    def __init__(self, paths: ProjectPaths | None = None):
        self.paths = paths or resolve_project_paths()

    def discover_datasets(self) -> List[DatasetDescriptor]:
        """Scan `original_repo/data/` read-only and prioritize `conference/cmt-confof`."""
        data_root = self.paths.original_repo_dir / "data"
        found: List[DatasetDescriptor] = []
        if not data_root.is_dir():
            return found

        for src_xml in sorted(data_root.rglob("source.xml")):
            parent = src_xml.parent
            tgt_xml = parent / "target.xml"
            if not tgt_xml.is_file():
                continue
            ref_xml = parent / "reference.xml"
            rel = parent.relative_to(data_root).parts
            track = rel[0] if len(rel) >= 1 else "custom"
            pair_name = rel[1] if len(rel) >= 2 else parent.name
            ctx, c1, c2 = self.TRACK_CONTEXTS.get(track.lower(), ("general", False, False))
            dataset_id = "/".join(rel)
            found.append(
                DatasetDescriptor(
                    dataset_id=dataset_id,
                    track=track,
                    pair_name=pair_name,
                    source_path=src_xml,
                    target_path=tgt_xml,
                    reference_path=ref_xml if ref_xml.is_file() else None,
                    context_hint=ctx,
                    o1_is_code_hint=c1,
                    o2_is_code_hint=c2,
                )
            )

        # Put conference/cmt-confof/component first as primary replication target
        found.sort(
            key=lambda d: (
                0 if "cmt-confof" in d.dataset_id.lower() else 1,
                d.track,
                d.pair_name,
            )
        )
        return found

    def build_custom_descriptor(
        self,
        source_path: str | Path,
        target_path: str | Path,
        reference_path: Optional[str | Path] = None,
        context: str = "conference",
        o1_is_code: bool = False,
        o2_is_code: bool = False,
    ) -> DatasetDescriptor:
        src = Path(source_path).resolve()
        tgt = Path(target_path).resolve()
        ref = Path(reference_path).resolve() if reference_path else None
        if not src.is_file():
            raise FileNotFoundError(f"Source ontology not found: {src}")
        if not tgt.is_file():
            raise FileNotFoundError(f"Target ontology not found: {tgt}")
        if ref is not None and not ref.is_file():
            raise FileNotFoundError(f"Reference alignment not found: {ref}")
        return DatasetDescriptor(
            dataset_id=f"custom/{src.stem}-{tgt.stem}",
            track="custom",
            pair_name=f"{src.stem}-{tgt.stem}",
            source_path=src,
            target_path=tgt,
            reference_path=ref,
            context_hint=context,
            o1_is_code_hint=o1_is_code,
            o2_is_code_hint=o2_is_code,
        )

    def preview_dataset(self, descriptor: DatasetDescriptor) -> Dict[str, Any]:
        """Parse source, target, and optional reference read-only to return entity/triple stats."""
        src_ont = load_ontology(descriptor.source_path)
        tgt_ont = load_ontology(descriptor.target_path)
        extractor = EntityExtractor(combine_properties_sort=True)
        src_ents, src_sum = extractor.extract_entities(
            src_ont, "Source", ontology_is_code=descriptor.o1_is_code_hint
        )
        tgt_ents, tgt_sum = extractor.extract_entities(
            tgt_ont, "Target", ontology_is_code=descriptor.o2_is_code_hint
        )

        ref_pairs = (
            load_reference_pairs(descriptor.reference_path)
            if descriptor.reference_path and descriptor.reference_path.is_file()
            else []
        )

        # Check committed upstream reference outputs if inside original_repo
        committed_gpt4o_csv = (
            self.paths.original_repo_dir / "alignment" / descriptor.dataset_id / "predict.csv"
        )
        committed_gpt4o_pairs = (
            sorted(load_alignment_csv_pairs(committed_gpt4o_csv))
            if committed_gpt4o_csv.is_file()
            else []
        )

        return {
            "dataset_id": descriptor.dataset_id,
            "track": descriptor.track,
            "pair_name": descriptor.pair_name,
            "context_hint": descriptor.context_hint,
            "o1_is_code_hint": descriptor.o1_is_code_hint,
            "o2_is_code_hint": descriptor.o2_is_code_hint,
            "source": {
                "path": str(descriptor.source_path),
                "triples": src_ont.triple_count,
                "classes": src_sum.total_classes,
                "object_properties": src_sum.total_object_properties,
                "datatype_properties": src_sum.total_datatype_properties,
                "total_entities": src_sum.total_entities,
                "sample_entities": [e.uri for e in src_ents[:10]],
            },
            "target": {
                "path": str(descriptor.target_path),
                "triples": tgt_ont.triple_count,
                "classes": tgt_sum.total_classes,
                "object_properties": tgt_sum.total_object_properties,
                "datatype_properties": tgt_sum.total_datatype_properties,
                "total_entities": tgt_sum.total_entities,
                "sample_entities": [e.uri for e in tgt_ents[:10]],
            },
            "reference_count": len(ref_pairs),
            "reference_pairs": ref_pairs,
            "committed_gpt4o_predict_present": committed_gpt4o_csv.is_file(),
            "committed_gpt4o_predict_count": len(committed_gpt4o_pairs),
        }

