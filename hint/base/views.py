from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Count, Case, When, Value
from django.http import StreamingHttpResponse, Http404
from base.models import Organism, Protein, Interaction, HintVersion, Evidence
from base.hint_downloads import get_downloadable_files
from typing import Dict
from pathlib import Path
import logging


log = logging.getLogger("main")
NETWORK_NODE_LIMIT = 50
PAGINATION_STEP = 50
EVIDENCE_LOAD_TH = 20
COLORS = {"both": "#9933ff",
          "binary": "#3366ff",
          "co-complex": "#ff1a1a",
          "main": "#1b6abf",
          "neighbor": "#bf651b"}


def home(request):
    context = {}
    context["active"] = "home"

    # organism information
    orgs = (Protein.objects
            .order_by().values_list("organism", flat=True).distinct())
    order = Case(
        *[When(tax_id=tid, then=Value(i))
          for i, tid in enumerate(Organism.CUSTOM_ORGANISM_ORDER)]
    )
    context["organisms"] = (
        Organism.objects
        .filter(pk__in=orgs)
        .order_by(order))
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


def download_raw(request, hint_version, filename):
    def file_iterator(file, chunk_size=512):
        with file.open() as f:
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break
    raw_files = Path(__file__).resolve().parent / "static" / "raw_hint_files"
    file = raw_files / hint_version / filename
    if file.exists():
        response = StreamingHttpResponse(file_iterator(file))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment;filename="{filename}"'
    else:
        raise Http404("File does not exist")
    return response


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

    def edge_color(i):
        if i["binary"] and i["cocomplex"]:
            return COLORS["both"]
        if i["binary"]:
            return COLORS["binary"]
        return COLORS["co-complex"]

    if len(main_nodes) + len(neighbors) > NETWORK_NODE_LIMIT:
        return {"message": "too-many-nodes"}
    encoded_nodes = [
        {"data": {"id": p.display_name(network=True), "c": COLORS["main"]}}
        for p in main_nodes]
    encoded_nodes.extend(
        {"data": {"id": p.display_name(network=True), "c": COLORS["neighbor"]}}
        for p in neighbors)
    edges = [{
        "data": {
            "id": i["id"],
            "source": display_name(i, 1),
            "target": display_name(i, 2),
            "c": edge_color(i)
        }
    } for i in main_interactions]

    edges.extend({
        "data": {
            "id": i["id"],
            "source": display_name(i, 1),
            "target": display_name(i, 2),
            "c": edge_color(i)
        }
    } for i in neighbors_interactions)

    return {
        "nodes": encoded_nodes,
        "edges": edges,
    }


INTERACTION_COLUMS = [
    "id",
    "p1__gene_accession",
    "p1__uniprot_accession",
    "p2__gene_accession",
    "p2__uniprot_accession",
    "cocomplex",
    "cocomplex_hq",
    "binary",
    "binary_hq",
    "num_evidence",
]


def get_interactions_qs(protein_selection, evidence_type, quality):
    def make_filters(proteins, main=True):
        if main:
            filters = (Q(p1__in=proteins) | Q(p2__in=proteins))
        else:
            filters = (Q(p1__in=proteins) & Q(p2__in=proteins))
        if evidence_type == "binary":
            filters &= Q(binary=True)
            if quality == "high-quality":
                filters &= Q(binary_hq=True)
        elif evidence_type == "cocomp":
            filters &= Q(cocomplex=True)
            if quality == "high-quality":
                filters &= Q(cocomplex_hq=True)
        elif evidence_type == "both":
            if quality == "high-quality":
                filters &= (Q(binary_hq=True) | Q(cocomplex_hq=True))
        return filters

    proteins = Protein.objects
    q = None
    for p in protein_selection:
        if q is None:
            q = Q(uniprot_accession__startswith=p)
        else:
            q |= Q(uniprot_accession__startswith=p)
    proteins = Protein.objects.filter(q)
    filters = make_filters(proteins)
    interactions_qs = (
        Interaction.objects.filter(filters)
        .annotate(num_evidence=Count("evidence"))
        .order_by("-num_evidence", "id")
        .distinct())
    interactions = interactions_qs.values(
        "p1__uniprot_accession",
        "p2__uniprot_accession",
    )
    main_interactors = set()
    for it in interactions:
        main_interactors.add(it["p1__uniprot_accession"])
        main_interactors.add(it["p2__uniprot_accession"])
    main_interactors -= protein_selection
    main_interactors = Protein.objects.filter(
        uniprot_accession__in=main_interactors)
    filters = make_filters(main_interactors, main=False)
    neighbors_qs = (
        Interaction.objects.filter(filters)
        .annotate(num_evidence=Count("evidence"))
        .order_by("-num_evidence", "id")
        .distinct())
    return proteins, main_interactors, interactions_qs, neighbors_qs


def network_viewer(request):
    context = {}
    if request.method == "POST":
        protein_selection = set(request.POST.getlist("selected_proteins[]"))
        if len(protein_selection) > 0:
            evidence_type = request.POST.get("evidence-type")
            quality = request.POST.get("quality")
            # pass the search filters forward for pagination and lazy loading
            selection_data = {
                "evidence_type": evidence_type,
                "quality": quality,
                "selected_proteins": protein_selection,
            }
            context["selection_data"] = selection_data
            context["evidence_th"] = EVIDENCE_LOAD_TH
            log.info(f"protein selection has {len(protein_selection)} items")
            log.info(f"etype: {evidence_type}")
            log.info(f"quality: {quality}")

            proteins, neighbors, interactions_qs, neighbors_ints_qs =\
                get_interactions_qs(protein_selection, evidence_type, quality)

            interaction_count = interactions_qs.count()
            context["main_load"] = interaction_count > PAGINATION_STEP
            if interaction_count > NETWORK_NODE_LIMIT:
                context["network_data"] = {"message": "too-many-nodes"}
                interactions = (
                    interactions_qs[:PAGINATION_STEP]
                    .values(*INTERACTION_COLUMS))
            else:
                interactions = interactions_qs.values(*INTERACTION_COLUMS)
                context["main_load"] = False

            # group interactions for display
            context["main_interactions"] = interactions
            context["main_interactions_count"] = interaction_count
            log.debug(f"{interaction_count=}")
            neighbors_ints_count = neighbors_ints_qs.count()
            context["neigh_load"] = neighbors_ints_count > PAGINATION_STEP
            if interaction_count > NETWORK_NODE_LIMIT:
                neighbors_interactions = (
                    neighbors_ints_qs[:PAGINATION_STEP]
                    .values(*INTERACTION_COLUMS))
            else:
                neighbors_interactions = (
                    neighbors_ints_qs
                    .values(*INTERACTION_COLUMS))
                context["neigh_load"] = False
                context["network_data"] = build_cytoscape_dict(
                    proteins,
                    neighbors,
                    interactions,
                    neighbors_interactions)
            context["neighbors_interactions"] = neighbors_interactions
            context["neighbors_interactions_count"] = neighbors_ints_count
            context["color_reference"] = COLORS
            log.debug(f"{neighbors_ints_count=}")
            log.debug(f"{neighbors_interactions=}")

    return render(request, "network-viewer.html", context)


def interaction_load_more(request):
    context = {}
    if request.method == "POST":
        protein_selection = set(request.POST.getlist("selected_proteins[]"))
        if len(protein_selection) > 0:
            evidence_type = request.POST.get("evidence-type")
            quality = request.POST.get("quality")
            name = request.POST.get("name")
            offset = int(request.POST.get("offset"))
            count = int(request.POST.get("count"))
            log.debug(f"{offset=}")
            log.debug(f"{quality=}")
            log.debug(f"{evidence_type=}")
            log.debug(f"{name=}")
            proteins, neighbors, interactions_qs, neighbors_ints_qs =\
                get_interactions_qs(protein_selection, evidence_type, quality)
            # pass the search filters forward for pagination and lazy loading
            selection_data = {
                "evidence_type": evidence_type,
                "quality": quality,
                "selected_proteins": protein_selection,
            }
            context["name"] = name
            context["selection_data"] = selection_data
            context["evidence_th"] = EVIDENCE_LOAD_TH
            qs = interactions_qs if name == "main" else neighbors_ints_qs
            interactions = (
                qs[offset:offset+PAGINATION_STEP]
                .values(*INTERACTION_COLUMS))
            context["load_more"] = offset + len(interactions) < count
            context["count"] = count
            context["offset"] = offset + len(interactions)
            context["interactions"] = interactions
            context["color_reference"] = COLORS
            log.debug(context)
    return render(request, "components/interaction-row.html", context)


def interaction_evidence(request, interaction_id):
    context = {}
    interaction = get_object_or_404(Interaction, pk=interaction_id)
    filters = Q(interaction=interaction)
    context["evidence_list"] = Evidence.objects.filter(filters)
    return render(request, "components/evidence-detail.html", context)


def interaction_stream_download(request):

    def iterate_interactions(interactions_lists):
        for interactions in interactions_lists:
            for it in interactions:
                yield it.get_hint_format()

    if request.method == "POST":
        protein_selection = set(request.POST.getlist("selected_proteins[]"))
        if len(protein_selection) > 0:
            evidence_type = request.POST.get("evidence-type")
            quality = request.POST.get("quality")
            download_section = request.POST.get("download-section")
            proteins, neighbors, interactions_qs, neighbors_ints_qs =\
                get_interactions_qs(protein_selection, evidence_type, quality)
            # pass the search filters forward for pagination and lazy loading
            interactions_lists = []
            if download_section == "main":
                interactions_lists.append(interactions_qs)
            elif download_section == "neighbors":
                interactions_lists.append(neighbors_ints_qs)
            else:
                download_section = "all"
                interactions_lists.append(interactions_qs)
                interactions_lists.append(neighbors_ints_qs)
            response = StreamingHttpResponse(
                iterate_interactions(interactions_lists))
            response['Content-Type'] = 'application/octet-stream'
            fn = f"HINT-search-results-{download_section}.tsv"
            response['Content-Disposition'] = f'attachment;filename="{fn}"'
            return response
    raise Http404("Could not create a download file")
