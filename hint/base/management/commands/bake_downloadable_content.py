from django.core.management.base import BaseCommand
from django.conf import settings
from base import hint_downloads
from pathlib import Path
import logging

STATIC_ROOT = Path(settings.STATIC_ROOT)

log = logging.getLogger("main")


def run():
    raw_files = STATIC_ROOT / "raw_hint_files"
    for download_dir in raw_files.glob("*/"):
        try:
            year, month = [int(i) for i in download_dir.name.split("-")]
        except ValueError:
            continue
        hint_dir = raw_files / f"{year}-{month:02}"
        log.info(f"Processing downloadable files in {hint_dir}")
        hint_downloads.divide_downloadable_files(hint_dir)


class Command(BaseCommand):

    def handle(self, *args, **options):
        run()
