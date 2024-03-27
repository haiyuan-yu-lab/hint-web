from pathlib import Path
from typing import Dict, Tuple, List
from django.contrib.staticfiles.storage import staticfiles_storage
from base.models import Organism, Protein, DownloadFileMetadata
import logging
import pprint


log = logging.getLogger("main")
VALID_SUFFIXES = {
    "binary_all.txt": ("_lcb_all.txt", "_htb_all.txt"),
    "binary_hq.txt": ("_lcb_hq.txt", "_htb_hq.txt"),
    "both_all.txt": (None, None),
    "both_hq.txt": (None, None),
    "cocomp_all.txt": ("_lcc_all.txt", "_htc_all.txt"),
    "cocomp_hq.txt": ("_lcc_hq.txt", "_htc_hq.txt"),
}


# from https://stackoverflow.com/a/68385697
def buf_count_newlines_gen(fname):
    def _make_gen(reader):
        while True:
            b = reader(2 ** 16)
            if not b:
                break
            yield b

    with open(fname, "rb") as f:
        count = sum(buf.count(b"\n") for buf in _make_gen(f.raw.read))
    return count


def add_metadata(downloads: Dict,
                 org: int,
                 year: int,
                 month: int,
                 url: str,
                 metadata: DownloadFileMetadata,
                 evidence_type: str,
                 group: str,
                 quality: str) -> None:
    quality_map = {
        "all": "",
        "literature curated": "Literature curated",
        "high throughput": "High-throughput"
    }
    display_label = f"{quality_map[quality]} {evidence_type}"

    if org not in downloads:
        downloads[org] = {}

    if (year, month) not in downloads[org]:
        downloads[org][(year, month)] = {}
    date_dict = downloads[org][(year, month)]

    if group not in date_dict:
        date_dict[group] = {}
    g_dict = date_dict[group]

    if quality not in g_dict:
        g_dict[quality] = {}
    q_dict = g_dict[quality]

    q_dict[evidence_type] = (url, metadata.interaction_count, display_label)
    # if evidence_type not in q_dict:
    #     e_dict = q_dict[evidence_type]
    # e_dict[quality] = (url, metadata.interaction_count)


def in_range(year: int,
             month: int,
             upper_year: int,
             upper_month: int,
             include_previous: bool) -> bool:
    if year > upper_year:
        return False
    if year == upper_year:
        if month > upper_month:
            return False
        if month < upper_month and not include_previous:
            return False
    if year < upper_year and not include_previous:
        return False
    return True


def get_downloadable_files(
        year: int,
        month: int,
        include_previous=False) -> Dict[int, Tuple[int, int, str]]:
    """
    Searches the current raw_hint_files directory and retrieves all valid
    files to list as "old" versions. This includes all previous versions until
    the current year and last month. Every combination of year-month all the
    way to the current year and month-1 will be included.

    Parameters
    ----------
    year : int
        The upper year of versions of HINT to include in the results.
    month : int
        The upper month of versions of HINT to include in the results.
    include_previous : bool, default False
        If true, include all available year-month versions up to the provided
        `year` and `month`.

    Returns
    -------
    dowloads : dict
        A dictionary with the following structure:
        organism_id: {
            (year, month): {
                group: {
                    quality: {
                        evidence_type: (URL, num_interactions)
                    }
                }
            },
        }
    """
    raw_files = Path(__file__).resolve().parent / "static" / "raw_hint_files"
    static_prefix = "raw_hint_files"
    orgs = (Protein.objects
            .order_by().values_list("organism", flat=True).distinct())
    all_organisms = Organism.objects.filter(pk__in=orgs)
    prefixes_dict = {o: o.get_filename_prefix() for o in all_organisms}
    # file name suffix -> (evidence type, group, quality)
    valid_suffixes = {
        "binary_all.txt": ("binary", "all qualities", "all"),
        "binary_hq.txt": ("binary", "high quality", "all"),
        "both_all.txt": ("both", "all qualities", "all"),
        "both_hq.txt": ("both", "high quality", "all"),
        "cocomp_all.txt": ("co-complex", "all qualities", "all"),
        "cocomp_hq.txt": ("co-complex", "high quality", "all"),
        "lcb_hq.txt": ("binary", "high quality", "literature curated"),
        "lcc_hq.txt": ("co-complex", "high quality", "literature curated"),
        "htb_hq.txt": ("binary", "", "high throughput"),
        "htc_hq.txt": ("co-complex", "", "high throughput"),
    }

    downloads = {}

    for download_dir in raw_files.glob("*/"):
        try:
            dir_y, dir_m = [int(i) for i in download_dir.name.split("-")]
        except ValueError:
            continue
        if not in_range(dir_y, dir_m, year, month, include_previous):
            continue
        for hint_file in download_dir.glob("*.txt"):
            for org, prefix in prefixes_dict.items():
                if hint_file.match(f"{prefix}*", case_sensitive=False):
                    mdata, new = DownloadFileMetadata.objects.get_or_create(
                        full_path=f"{hint_file}",
                    )
                    if new:
                        qty_lines = buf_count_newlines_gen(f"{hint_file}")
                        mdata.interaction_count = qty_lines - 1
                        mdata.save()
                    for suffix, (e_type, gr, qual) in valid_suffixes.items():
                        if hint_file.match(f"*{suffix}"):
                            hintdir = f"{static_prefix}/{dir_y}-{dir_m:02}"
                            url = staticfiles_storage.url(
                                f"{hintdir}/{hint_file.name}"
                            )
                            add_metadata(downloads,
                                         org,
                                         dir_y,
                                         dir_m,
                                         url,
                                         mdata,
                                         e_type,
                                         gr,
                                         qual)
    pprint.pprint(downloads)
    log.info(pprint.pformat(downloads))
    return downloads


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


def divide_downloadable_files(hint_directory: Path):
    file_header = "Uniprot_A\tUniprot_B\tGene_A\tGene_B\tpmid:method:quality\n"
    in_files = sorted(hint_directory.glob("**/*.txt"))
    for infile in in_files:
        lc_suffix = None
        ht_suffix = None
        for suffix, (lc, ht) in VALID_SUFFIXES.items():
            if infile.match(f"*{suffix}"):
                lc_suffix = lc
                ht_suffix = ht
                break
            continue
        if lc_suffix is not None and ht_suffix is not None:
            base = infile.name.split("_")[0]
            lc_file = hint_directory / f"{base}{lc_suffix}"
            ht_file = hint_directory / f"{base}{ht_suffix}"
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
