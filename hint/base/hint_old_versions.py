from pathlib import Path
from typing import Dict, Tuple
from django.contrib.staticfiles.storage import staticfiles_storage
from base.models import Organism, Protein
import logging
from datetime import datetime


log = logging.getLogger("main")


def get_old_versions() -> Dict[int, Tuple[int, int, str]]:
    """
    Searches the current raw_hint_files directory and retrieves all valid 
    files to list as "old" versions. This includes all previous versions until
    the current year and last month. Every combination of year-month all the 
    way to the current year and month-1 will be included.

    Returns
    -------
    dict:
        A dictionary mapping organisms (year, month) -> Path
    """
    raw_files = Path(__file__).resolve().parent / "static" / "raw_hint_files"
    now = datetime.now()
    year = now.year
    month = now.month

    orgs = (Protein.objects
            .order_by().values_list("organism", flat=True).distinct())
    all_organisms = Organism.objects.filter(pk__in=orgs)
    prefixes_dict = {o: o.get_filename_prefix() for o in all_organisms}
    valid_suffixes = [
            ]


    for oldver_dir in raw_files.glob("*/"):
        log.info(f"found {oldver_dir} in the raw folder")
        try:
            dir_year, dir_month = [int(i) for i in oldver_dir.name.split("-")]
        except ValueError:
            log.info(f"{oldver_dir} does not match the naming convention")
            continue
        if dir_year > year:
            continue
        if (dir_year == year and dir_month >= month):
            continue
        log.info(f"{oldver_dir} is a valid directory, traversing...")
        for hint_file in oldver_dir.glob("*.txt"):
            pass 
