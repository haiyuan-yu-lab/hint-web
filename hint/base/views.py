from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count
from base.models import Organism, Protein, Interaction, HintVersion, Evidence
from base.hint_downloads import get_downloadable_files
from typing import Dict
import logging


log = logging.getLogger("main")
NETWORK_NODE_LIMIT = 50
PAGINATION_STEP = 50


def home(request):
    context = {}
    context["active"] = "home"

    # organism information
    orgs = (Protein.objects
            .order_by().values_list("organism", flat=True).distinct())
    context["organisms"] = Organism.objects.filter(pk__in=orgs)
    return render(request, "home.html", context)


def download(request):
    context = {}
    context["active"] = "download"
    hint_version = HintVersion.get_latest_version()
    context["hint_version"] = hint_version
    context["raw_files"] = get_downloadable_files(hint_version.year,
                                                  hint_version.month)
    return render(request, "download.html", context)


def old_versions(request):
    context = {}
    context["active"] = "download"
    hint_version = HintVersion.get_latest_version()
    context["raw_files"] = get_downloadable_files(hint_version.year,
                                                  hint_version.month - 1,
                                                  include_previous=True)
    return render(request, "old-versions.html", context)


def faq(request):
    context = {}
    context["active"] = "faq"
    return render(request, "faq.html", context)


def search_proteins(request):
    context = {}
    if request.method == "POST":
        protein_query = request.POST.get("protein-name", "")
        # if there is no search term, no need to return anything
        if protein_query:
            protein_qs = Protein.objects
            if "organism" in request.POST:
                tax_id = int(request.POST["organism"])
                protein_qs = protein_qs.filter(organism__tax_id=tax_id)
            protein_qs = protein_qs.filter(
                Q(uniprot_accession__icontains=protein_query) |
                Q(gene_accession__icontains=protein_query)
            )
            context["proteins"] = protein_qs
    return render(request, "components/protein-search.html", context)


def build_cytoscape_dict(main_nodes, neighbors,
                         main_interactions, neighbors_interactions) -> Dict:

    def display_name(i, n):
        if i[f"p{n}__gene_accession"]:
            return i[f"p{n}__gene_accession"]
        return i[f"p{n}__uniprot_accession"]

    if len(main_nodes) + len(neighbors) > NETWORK_NODE_LIMIT:
        return {"message": "too-many-nodes"}
    colors = {"main": "#3175b0", "neighbor": "#b06831"}
    encoded_nodes = [
        {"data": {"id": p.display_name(network=True), "c": colors["main"]}}
        for p in main_nodes]
    encoded_nodes.extend(
        {"data": {"id": p.display_name(network=True), "c": colors["neighbor"]}}
        for p in neighbors)
    edges = [{
        "data": {
            "id": i["id"],
            "source": display_name(i, 1),
            "target": display_name(i, 2),
            "c": colors["neighbor"]
        }
    } for i in main_interactions]

    edges.extend({
        "data": {
            "id": i["id"],
            "source": display_name(i, 1),
            "target": display_name(i, 2),
            "c": colors["neighbor"]
        }
    } for i in neighbors_interactions)

    return {
        "nodes": encoded_nodes,
        "edges": edges
    }


def network_viewer(request):

    def make_filter(proteins, evidence_type, quality, main=True):
        if main:
            filters = (Q(p1__in=proteins) | Q(p2__in=proteins))
        else:
            filters = (Q(p1__in=proteins) & Q(p2__in=proteins))
        if evidence_type == "binary":
            filters &= Q(
                evidence__evidence_type=Evidence.EvidenceType.BINARY)
        elif evidence_type == "cocomp":
            filters &= Q(
                evidence__evidence_type=Evidence.EvidenceType.CO_COMPLEX)
        if quality == "high-quality":
            filters &= Q(
                evidence__quality=Evidence.Quality.LITERATURE_CURATED)
        return filters

    interaction_colums = [
        "id",
        "p1__gene_accession",
        "p1__uniprot_accession",
        "p2__gene_accession",
        "p2__uniprot_accession",
        "num_evidence",
    ]
    context = {}
    if request.method == "POST":
        protein_selection = set(request.POST.getlist("selected_proteins[]"))
        if len(protein_selection) > 0:
            evidence_type = request.POST.get("evidence-type")
            quality = request.POST.get("quality")
            log.info(f"protein selection has {len(protein_selection)} items")
            log.info(f"etype: {evidence_type}")
            log.info(f"quality: {quality}")
            # pass the search filters through
            context["evidence_type"] = evidence_type
            context["quality"] = quality
            proteins = Protein.objects.filter(
                uniprot_accession__in=protein_selection)
            log.debug("proteins selected")
            for prot in proteins:
                log.debug(f"protein = {prot.pk}")
            filters = make_filter(proteins, evidence_type, quality)
            interactions_qs = (
                Interaction.objects.filter(filters)
                .annotate(num_evidence=Count("evidence"))
                .order_by("-num_evidence", "id")
                .distinct())

            interaction_count = interactions_qs.count()
            context["main_load"] = interaction_count > PAGINATION_STEP
            if interaction_count > NETWORK_NODE_LIMIT:
                context["network_data"] = {"message": "too-many-nodes"}
                interactions = (
                    interactions_qs[:PAGINATION_STEP]
                    .values(*interaction_colums))
            else:
                interactions = interactions_qs.values(*interaction_colums)
                context["main_load"] = False
            # group interactions for display
            main_interactors = set()
            for it in interactions:
                main_interactors.add(it["p1__uniprot_accession"])
                main_interactors.add(it["p2__uniprot_accession"])
            context["main_interactions"] = interactions
            context["main_interactions_count"] = interaction_count
            log.debug(f"{interaction_count=}")
            main_interactors -= protein_selection
            main_interactors = Protein.objects.filter(
                uniprot_accession__in=main_interactors)
            filters = make_filter(main_interactors,
                                  evidence_type,
                                  quality,
                                  main=False)
            neighbors_interactions_qs = (
                Interaction.objects.filter(filters)
                .annotate(num_evidence=Count("evidence"))
                .order_by("-num_evidence", "id")
                .distinct())
            neighbors_ints_count = neighbors_interactions_qs.count()
            context["neigh_load"] = neighbors_ints_count > PAGINATION_STEP
            if interaction_count > NETWORK_NODE_LIMIT:
                neighbors_interactions = (
                    neighbors_interactions_qs[:PAGINATION_STEP]
                    .values(*interaction_colums))
            else:
                neighbors_interactions = (
                    neighbors_interactions_qs
                    .values(*interaction_colums))
                context["neigh_load"] = False
                context["network_data"] = build_cytoscape_dict(
                    proteins,
                    main_interactors,
                    interactions,
                    neighbors_interactions)
            context["neighbors_interactions"] = neighbors_interactions
            context["neighbors_interactions_count"] = neighbors_ints_count
            log.debug(f"{neighbors_ints_count=}")
            log.debug(f"{neighbors_interactions=}")

    return render(request, "network-viewer.html", context)


def interaction_evidence(request, interaction_id, ev_type, ev_quality):
    context = {}
    interaction = get_object_or_404(Interaction, pk=interaction_id)
    filters = Q(interaction=interaction)
    if ev_type == "binary":
        filters &= Q(evidence_type=Evidence.EvidenceType.BINARY)
    elif ev_type == "cocomp":
        filters &= Q(evidence_type=Evidence.EvidenceType.CO_COMPLEX)
    if ev_quality == "high-quality":
        filters &= Q(quality=Evidence.Quality.LITERATURE_CURATED)
    context["evidence_list"] = Evidence.objects.filter(filters)
    log.debug(f"{context=}")
    return render(request, "components/evidence-detail.html", context)
