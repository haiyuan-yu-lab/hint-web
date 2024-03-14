from django.core.management.base import BaseCommand
from django.conf import settings
from base.models import (MITerm, Pubmed, Organism, Protein, Tissue,
                         Interaction, Evidence, HintVersion)
from pathlib import Path
from goapfp.io.obo_parser import OboParser
from typing import Dict, List, Tuple
import logging
import shutil

STATIC_ROOT = Path(settings.STATIC_ROOT)

log = logging.getLogger("main")

REPORT_EVERY_N_DEFAULT = 1000
REPORT_EVERY_N = {
    "protein": 5000,
    "evidence": 50000,
    "interaction": 10000,
}


def divide_evidence_by_quality(evidence: str) -> Tuple[List[str]]:
    evidences = evidence.split("|")
    ht = []
    lc = []
    for e in evidences:
        if e[-2:] == "HT":
            ht.append(e)
        elif e[-2:] == "LC":
            lc.append(e)
    return lc, ht


def create_downloadable_files(year: int,
                              month: int,
                              hint_directory: Path):
    raw_files = STATIC_ROOT / "raw_hint_files" / f"{year}-{month:02}"
    raw_files.mkdir()
    file_header = "Uniprot_A\tUniprot_B\tGene_A\tGene_B\tpmid:method:quality\n"
    in_files = sorted(hint_directory.glob("**/*.txt"))
    valid_suffixes = {
        "binary_all.txt": ("_lcb_all.txt", "_htb_all.txt"),
        "binary_hq.txt": ("_lcb_hq.txt", "_htb_all.txt"),
        "both_all.txt": (None, None),
        "both_hq.txt": (None, None),
        "cocomp_all.txt": ("_lcc_all.txt", "_htc_all.txt"),
        "cocomp_hq.txt": ("_lcc_all.txt", "_htc_all.txt"),
    }
    for infile in in_files:
        lc_suffix = None
        ht_suffix = None
        for suffix, (lc, ht) in valid_suffixes.items():
            if infile.match(f"*{suffix}"):
                lc_suffix = lc
                ht_suffix = ht
                break
            continue
        dest_file = raw_files / infile.name
        shutil.copy2(infile, dest_file)
        if lc_suffix is not None and ht_suffix is not None:
            base = infile.name.split("_")[0]
            lc_file = raw_files / f"{base}{lc_suffix}"
            ht_file = raw_files / f"{base}{ht_suffix}"
            with (infile.open() as f,
                  lc_file.open("w") as lc_f,
                  ht_file.open("w") as ht_f):
                header = True
                for line in f:
                    if header:
                        header = False
                        lc_f.write(file_header)
                        ht_f.write(file_header)
                        continue
                    parts = line.strip().split("\t")
                    lc_ev, ht_ev = divide_evidence_by_quality(parts[-1])
                    if lc_ev:
                        lc_f.write("\t".join(parts[:-1]))
                        lc_f.write(f"\t{'|'.join(lc_ev)}\n")
                    if ht_ev:
                        ht_f.write("\t".join(parts[:-1]))
                        ht_f.write(f"\t{'|'.join(ht_ev)}\n")


def insert_mi_ontology(mi_ontology: Path) -> Dict:
    mi = OboParser(mi_ontology.open())
    insert_buffer = []
    for term in mi:
        desc = "" if len(term.tags["def"]) == 0 else term.tags["def"][0].value
        insert_buffer.append(
            MITerm(mi_id=int(term.tags["id"][0].value.split(":")[-1]),
                   name=term.tags["name"][0].value,
                   description=desc)
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
            tax_id, code, kdom, sname, cname, syn = line.split("\t")
            syn = syn.strip()
            insert_buffer.append(
                Organism(tax_id=int(tax_id),
                         name=cname,
                         scientific_name=sname)
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
            taxid = int(taxid)
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
            if "all" not in in_file.name:
                continue
            etype = None
            if "binary" in in_file.stem:
                etype = Evidence.EvidenceType.BINARY
            elif "cocomp" in in_file.stem:
                etype = Evidence.EvidenceType.CO_COMPLEX
            if etype is None:
                log.info(f"Skipping {in_file}, can't find evidence type")
                continue
            log.info(f"Processing {in_file} ...")
            log.info(f"Evidence type {etype} ...")
            for line in f:
                if not header_read:
                    header_read = True
                    continue
                up_a, up_b, g_a, g_b, p_m_qs = line.strip().split("\t")
                i, _ = Interaction.objects.get_or_create(p1=proteins[up_a],
                                                         p2=proteins[up_b])
                c += 1
                if c % REPORT_EVERY_N.get("interaction",
                                          REPORT_EVERY_N_DEFAULT) == 0:
                    log.info(f"Processed {c} interactions so far...")
                for p_m_q in p_m_qs.split("|"):
                    pmid, method, quality = p_m_q.split(":")
                    pmid = pmid
                    method = int(method)
                    if pmid not in pubmeds:
                        pubmeds[pmid], _ = Pubmed.objects.get_or_create(
                                pubmed_id=pmid, title="update_entry")
                    evidence_buffer.append(Evidence(interaction=i,
                                                    pubmed=pubmeds[pmid],
                                                    method=mi_terms[method],
                                                    quality=quality,
                                                    evidence_type=etype))
            Evidence.objects.bulk_create(evidence_buffer)
    log.info(f"Processed all files with a total of {c} interactions.")


def valid_version(year: int, month: int) -> bool:
    raw_files = STATIC_ROOT / "raw_hint_files"
    log.info(f"{raw_files} exists asd: {raw_files.exists()}")
    for oldver_dir in raw_files.glob("*/"):
        log.info(f"found {oldver_dir} in the raw folder")
        try:
            dir_year, dir_month = [int(i) for i in oldver_dir.name.split("-")]
            if dir_year == year and dir_month == month:
                return False
        except ValueError:
            log.info(f"{oldver_dir} does not match the naming convention")
            continue
    return True


def run(year: int,
        month: int,
        hint_oputput_dir: Path,
        mi_ontology: Path,
        protein_metadata: Path,
        taxonomy_metadata: Path,
        tissue_metadata: Path) -> None:
    create_downloadable_files(year, month, hint_oputput_dir)
    HintVersion.objects.create(year=year, month=month)
    mi_terms = insert_mi_ontology(mi_ontology)
    organisms = insert_organisms(taxonomy_metadata)
    proteins = insert_proteins(protein_metadata, organisms)
    tissues = insert_tissues(tissue_metadata)
    insert_interactions(hint_oputput_dir, mi_terms, proteins, tissues)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("year",
                            type=int,
                            help="Year to use for this version of HINT")
        parser.add_argument("month",
                            type=int,
                            help="Month to use for this version of HINT")
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
                                 " `tax_id` `code` `kingdom` `scientific name`"
                                 " `common name`, and `synonym`."
                                 " Please note that every organisms in the"
                                 " HINT pipeline should exist.")
        parser.add_argument("tissue_metadata",
                            help="Path to a TSV file with columns:"
                                 " `tissue_name` `description`. Please note"
                                 " that every tissue in the HINT pipeline"
                                 " should exist.")

    def handle(self, *args, **options):
        hint_output_dir = Path(options["hint_output_directory"])
        mi_ontology = Path(options["mi_ontology"])
        protein_metadata = Path(options["protein_metadata"])
        taxonomy_metadata = Path(options["taxonomy_metadata"])
        tissue_metadata = Path(options["tissue_metadata"])
        year = options["year"]
        month = options["month"]
        assert hint_output_dir.is_dir(), "HINT directory doesn't exist."
        assert mi_ontology.is_file(), "PSI-MI ontology file doesn't exist."
        assert protein_metadata.is_file(), "Protein metadata doesn't exist."
        assert taxonomy_metadata.is_file(), "Taxonomy metadata doesn't exist."
        assert tissue_metadata.is_file(), "Tissue metadata doesn't exist."
        assert valid_version(year, month), f"HINT {year}-{month:02} exists"
        run(year,
            month,
            hint_output_dir,
            mi_ontology,
            protein_metadata,
            taxonomy_metadata,
            tissue_metadata)
