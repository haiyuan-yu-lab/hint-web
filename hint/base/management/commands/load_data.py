from django.core.management.base import BaseCommand
from base.models import (MITerm, Pubmed, Organism, Protein, Tissue,
                         Interaction, Evidence, DownloadFile)
from pathlib import Path
from goapfp.io.obo_parser import OboParser
from typing import Dict
import logging


log = logging.getLogger("main")

REPORT_EVERY_N_DEFAULT = 1000
REPORT_EVERY_N = {
    "protein": 5000,
    "evidence": 50000,
    "interaction": 10000,
}


def insert_mi_ontology(mi_ontology: Path) -> Dict:
    mi = OboParser(mi_ontology.open())
    insert_buffer = []
    for term in mi:
        insert_buffer.append(
            MITerm(mi_id=int(mi.tags["id"][0].value.split(":")[-1]),
                   name=mi.tags["name"][0].value,
                   description=mi.tags["def"][0].value)
        )
    log.info(f"inserting {len(insert_buffer)} PSI-MI terms...")
    miterms = MITerm.objects.bulk_create(insert_buffer)
    log.info("Done")
    log.info("Creating PSI-MO id -> term dictionary..")
    return {m.mi_id: m for m in miterms}


def insert_organisms(taxonomy_metadata: Path) -> Dict:
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
                Organism(tax_id=int(tax_id),
                         name=name,
                         scientific_name=sci_name)
            )
            c += 1
            if c % REPORT_EVERY_N.get("organim", REPORT_EVERY_N_DEFAULT) == 0:
                log.info(f"Loaded {c} organisms so far...")
    log.info(f"inserting {c} organisms...")
    organisms = Organism.objects.bulk_create(insert_buffer)
    log.info("Done")
    log.info("Creating tax id -> organism dictionary..")
    return {o.tax_id: o for o in organisms}


def insert_tissues(tissue_metadata: Path) -> Dict:
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
    tissues = Tissue.objects.bulk_create(insert_buffer)
    log.info("Done")
    log.info("Creating tissue name -> tissue dictionary...")
    return {t.name: t for t in tissues}


def insert_proteins(protein_metadata: Path, organisms: Dict) -> Dict:
    header_read = False
    insert_buffer = []
    c = 0
    with protein_metadata.open() as tm:
        for line in tm:
            if not header_read:
                header_read = True
                continue
            uid, gid, name, taxid, desc = line.strip().split("\t")
            insert_buffer.append(
                Protein(uniprot_accession=uid,
                        gene_accession=gid,
                        entry_name=name,
                        description=desc,
                        organism=organisms[taxid])
            )
            c += 1
            if c % REPORT_EVERY_N.get("protein", REPORT_EVERY_N_DEFAULT) == 0:
                log.info(f"Loaded {c} proteins so far...")
    log.info(f"inserting {c} proteins...")
    proteins = Protein.objects.bulk_create(insert_buffer)
    log.info("Done")
    log.info("Creating uniprot_accession -> protein dictionary...")
    return {p.uniprot_accession: p for p in proteins}


def insert_interactions(hint_output_dir: Path,
                        mi_terms: Dict,
                        proteins: Dict,
                        tissues: Dict) -> None:
    # TODO(mateo): Handle the tissue data once the format is agreed.
    pubmeds = {}
    in_files = sorted(hint_output_dir.glob("**/*.txt"))
    log.info(f"Loading interactions from {len(in_files)} files")
    c = 0
    for in_file in in_files:
        header_read = False
        evidence_buffer = []
        with in_file.open() as f:
            etype = None
            if "binary" in in_file.stem:
                etype = Evidence.EvidenceType.BINARY
            elif "cocomp" in in_file.stem:
                etype = Evidence.EvidenceType.CO_COMPLEX
            if etype is None:
                log.info(f"Skipping {in_file}, can't find evidence type")
            for line in f:
                if not header_read:
                    header_read = True
                    continue
                up_a, up_b, g_a, g_b, p_m_q = f.strip().split("\t")
                pmid, method, quality = p_m_q.split(":")
                pmid = int(pmid)
                method = int(method)
                if pmid not in pubmeds:
                    pubmeds[pmid] = Pubmed.objects.get_or_create(
                        pubmed_id=pmid, title="update_entry")
                i = Interaction.objects.get_or_create(p1=proteins[up_a],
                                                      p2=proteins[up_b])
                c += 1
                if c % REPORT_EVERY_N.get("interaction",
                                          REPORT_EVERY_N_DEFAULT) == 0:
                    log.info(f"Processed {c} interactions so far...")
                evidence_buffer.append(Evidence(interaction=i,
                                                pubmed=pubmeds[pmid],
                                                method=mi_terms[method],
                                                quality=quality,
                                                evidence_type=etype))
            Evidence.objects.bulk_create(evidence_buffer)
    log.info(f"Processed all files with a total of {c} interactions.")


def run(hint_oputput_dir: Path,
        mi_ontology: Path,
        protein_metadata: Path,
        taxonomy_metadata: Path,
        tissue_metadata: Path) -> None:
    mi_terms = insert_mi_ontology(mi_ontology)
    organisms = insert_organisms(taxonomy_metadata)
    proteins = insert_proteins(protein_metadata, organisms)
    tissues = insert_tissues(tissue_metadata)
    insert_interactions(hint_oputput_dir, mi_terms, proteins, tissues)


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
