from django.db import models
from django.utils.translation import gettext_lazy as _


# ============================================================================
#                             External Sources
# ============================================================================

class MITerm(models.Model):
    mi_id = models.CharField(max_length=7)
    name = models.TextField()
    description = models.TextField()


class Pubmed(models.Model):
    pubmed_id = models.PositiveIntegerField()
    title = models.TextField()
    authors = models.TextField()
    year = models.PositiveIntegerField()
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
    tax_id = models.PositiveIntegerField()
    name = models.TextField()
    scientific_name = models.TextField()


class Protein(models.Model):
    # we support UniProt and Gene Symbols, max_lengths are 25, which may be
    # too long for the present, but maybe not enough in the future!
    uniprot_accession = models.CharField(max_length=25)
    gene_accession = models.CharField(max_length=25)
    entry_name = models.CharField(max_length=50, default="")
    description = models.TextField()
    organism = models.ForeignKey(Organism,
                                 on_delete=models.CASCADE)


class Tissue(models.Model):
    name = models.TextField(unique=True)
    description = models.TextField()

    @classmethod
    def get_default_pk(cls):
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
    evidence_type = models.CharField(max_length=3, choices=EvidenceType)
    tissue = models.ForeignKey(Tissue,
                               on_delete=models.CASCADE,
                               default=Tissue.get_default_pk)
