from django.db import models
from django.utils.translation import gettext_lazy as _
import string


# ============================================================================
#                             External Sources
# ============================================================================

class MITerm(models.Model):
    mi_id = models.CharField(max_length=7, unique=True)
    name = models.TextField()
    description = models.TextField()


class Pubmed(models.Model):
    pubmed_id = models.TextField(unique=True)
    title = models.TextField()
    authors = models.TextField()
    year = models.PositiveIntegerField(default=1900)
    source = models.TextField()

# ============================================================================
#                             HINT Sources
# ============================================================================


# TODO(mateo): For now a single database holds all the interactions across all
# organisms. This may be too slow if we are dealing with 10s of millions of
# interactions. A solution to this may be linking the Interaction table to the
# organism, and partitioning that table and the Protein table based on the
# organism ID. Since Django does not support table partitioning natively, the
# URL below explains how to do this
# https://pganalyze.com/blog/postgresql-partitioning-django
class Organism(models.Model):
    tax_id = models.PositiveIntegerField(unique=True)
    name = models.TextField()
    scientific_name = models.TextField()

    CUSTOM_ORGANISM_ORDER = [
        9606,
        4932,
        4896,
        10090,
        7227,
        6239,
        3702,
        562,
        10116,
        4530,
    ]

    def get_filename_prefix(self) -> str:
        """
        Makes the scientific name removing any character that's not a letter
        or digit.

        Useful for linking the filenames from older versions of HINT to an
        organism.

        Returns
        -------
        str
            The filename prefix
        """
        return "".join([c for c in self.scientific_name
                        if c in string.ascii_letters + string.digits])


class Protein(models.Model):
    # we support UniProt and Gene Symbols, max_lengths are 25, which may be
    # too long for the present, but maybe not enough in the future!
    uniprot_accession = models.CharField(max_length=25, unique=True)
    gene_accession = models.CharField(max_length=25)
    entry_name = models.CharField(max_length=250, default="")
    description = models.TextField()
    organism = models.ForeignKey(Organism,
                                 on_delete=models.CASCADE)

    def display_name(self, network: bool = False) -> str:
        if self.gene_accession:
            return self.gene_accession
        if network:
            return self.uniprot_accession.split("-")[0]
        return self.uniprot_accession


class Tissue(models.Model):
    name = models.TextField(unique=True)
    description = models.TextField()

    @classmethod
    def get_default_pk(cls):
        """
        Default tissue for the database. Applied to any interaction that does
        not have tissue information. If it doesn't exist yet, it gets created.

        Returns
        -------
        Tissue
            A tissue with name and description set to "Default Tissue"
        """
        tissue, created = cls.objects.get_or_create(
            name="Default Tissue",
            description="Default Tissue"
        )
        return tissue.pk


class Interaction(models.Model):
    p1 = models.ForeignKey(Protein,
                           related_name="prot1_set",
                           on_delete=models.CASCADE)
    p2 = models.ForeignKey(Protein,
                           related_name="prot2_set",
                           on_delete=models.CASCADE)


class Evidence(models.Model):
    class Quality(models.TextChoices):
        HIGH_THROUGHPUT = "HT", _("High Throughput")
        LITERATURE_CURATED = "LC", _("Literature Curated")

    class EvidenceType(models.IntegerChoices):
        BINARY = 0
        CO_COMPLEX = 1

    interaction = models.ForeignKey(Interaction,
                                    on_delete=models.CASCADE)
    pubmed = models.ForeignKey(Pubmed,
                               on_delete=models.CASCADE)
    # TODO(mateo): confirm that this field is actually PSI-MI ontology.
    method = models.ForeignKey(MITerm,
                               on_delete=models.CASCADE)
    quality = models.CharField(max_length=2, choices=Quality)
    evidence_type = models.IntegerField(choices=EvidenceType)
    tissue = models.ForeignKey(Tissue,
                               on_delete=models.CASCADE,
                               default=Tissue.get_default_pk)

# ============================================================================
#                             Versioning and rotation
# ============================================================================


class HintVersion(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()

    @classmethod
    def get_latest_version(cls):
        """
        Returns the latest version of the Hint interactions loaded for display.

        Each time the database is loaded, all previous interactions are cleaned
        and this value is recreated in the `load_data.py` script.

        Returns
        -------
        HintVersion
            Latest loaded HINT version
        """
        return cls.objects.latest("year", "month")


class DownloadFileMetadata(models.Model):
    full_path = models.TextField()
    interaction_count = models.IntegerField(default=0)
