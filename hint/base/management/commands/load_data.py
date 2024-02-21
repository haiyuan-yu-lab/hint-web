from django.core.management.base import BaseCommand
from base.models import (MITerm, Pubmed, Organism, Protein, Tissue,
                         Interaction, Evidence, DownloadFile)
from pathlib import Path
from goapfp.io.obo_parser import OboParser
import logging


log = logging.getLogger("main")

REPORT_EVERY_N_DEFAULT = 1000
REPORT_EVERY_N = {
    "protein": 5000,
    "evidence": 50000,
    "intraction": 10000,
}


def insert_mi_ontology(mi_ontology: Path) -> None:
    mi = OboParser(mi_ontology.open())
    insert_buffer = []
    for term in mi:
        insert_buffer.append(
            MITerm(mi_id=mi.tags["id"][0].value.split(":")[-1],
                   name=mi.tags["name"][0].value,
                   description=mi.tags["def"][0].value)
        )
    log.info(f"inserting {len(insert_buffer)} PSI-MI terms...")
    MITerm.objects.bulk_create(insert_buffer)
    log.info("Done")


def insert_organisms(taxonomy_metadata: Path) -> None:
    header_read = False
    insert_buffer = []
    c = 0
    with taxonomy_metadata.open() as tm:
        for line in tm:
            if not header_read:
                header_read = True
                continue
            tax_id, name, sci_name = line.strip().split("\t")
            insert_buffer.append(
                Organism(tax_id=tax_id,
                         name=name,
                         scientific_name=sci_name)
            )
            c += 1
            if c % REPORT_EVERY_N.get("organim", REPORT_EVERY_N_DEFAULT) == 0:
                log.info(f"Loaded {c} organisms so far...")
    log.info(f"inserting {c} organisms...")
    Organism.objects.bulk_create(insert_buffer)
    log.info("Done")


def insert_tissues(tissue_metadata: Path) -> None:
    header_read = False
    insert_buffer = []
    c = 0
    with tissue_metadata.open() as tm:
        for line in tm:
            if not header_read:
                header_read = True
                continue
            name, desc = line.strip().split("\t")
            insert_buffer.append(
                Tissue(name=name,
                       description=desc)
            )
            c += 1
            if c % REPORT_EVERY_N.get("tissue", REPORT_EVERY_N_DEFAULT) == 0:
                log.info(f"Loaded {c} tissues so far...")
    log.info(f"inserting {c} tissues...")
    Tissue.objects.bulk_create(insert_buffer)
    log.info("Done")


def run(hint_oputput_dir: Path,
        mi_ontology: Path,
        protein_metadata: Path,
        taxonomy_metadata: Path,
        tissue_metadata: Path) -> None:
    insert_mi_ontology(mi_ontology)
    insert_organisms(taxonomy_metadata)
    insert_tissues(tissue_metadata)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("hint_output_directory",
                            help="Directory containing the output files"
                                 " calculated using the HINT pipeline.")
        parser.add_argument("mi_ontology",
                            help="Path to the PSI-MI ontology definition file"
                                 " in obo format")
        parser.add_argument("protein_metadata",
                            help="Path to a TSV file with columns:"
                                 " `uniprot_id` `gene_id` `name` `tax_id`"
                                 " `description`. Please note that every"
                                 " protein in the HINT pipeline should exist.")
        parser.add_argument("taxonomy_metadata",
                            help="Path to a TSV file with columns:"
                                 " `tax_id` `organism_name` `scientific_name`."
                                 " Please note that every organisms in the"
                                 " HINT pipeline should exist.")
        parser.add_argument("tissue_metadata",
                            help="Path to a TSV file with columns:"
                                 " `tissue_name` `description`. Please note"
                                 " that every tissue in the HINT pipeline"
                                 " should exist.")

    def handle(self, *args, **options):
        hint_output_dir = Path(options["hint_output_dir"])
        mi_ontology = Path(options["mi_ontology"])
        protein_metadata = Path(options["protein_metadata"])
        taxonomy_metadata = Path(options["taxonomy_metadata"])
        tissue_metadata = Path(options["tissue_metadata"])
        assert hint_output_dir.is_dir(), "HINT directory doesn't exist."
        assert mi_ontology.is_file(), "PSI-MI ontology file doesn't exist."
        assert protein_metadata.is_file(), "Protein metadata doesn't exist."
        assert taxonomy_metadata.is_file(), "Taxonomy metadata doesn't exist."
        assert tissue_metadata.is_file(), "Tissue metadata doesn't exist."
        run(hint_output_dir,
            mi_ontology,
            protein_metadata,
            taxonomy_metadata,
            tissue_metadata)
