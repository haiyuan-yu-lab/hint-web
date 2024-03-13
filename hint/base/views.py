from django.shortcuts import render
from django.db.models import Q
from base.models import Organism, Protein, Interaction
from base.hint_old_versions import get_old_versions
import logging


log = logging.getLogger("main")


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
    return render(request, "download.html", context)


def old_versions(request):
    context = {}
    context["active"] = "download"
    get_old_versions()
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
                Q(uniprot_accession__icontains=protein_query)
            )
            context["proteins"] = protein_qs
    return render(request, "components/protein-search.html", context)


def network_viewer(request):
    context = {}
    if request.method == "POST":
        protein_selection = request.POST.getlist("selected_proteins[]")
        if len(protein_selection) > 0:
            log.info(f"protein selection has {len(protein_selection)} items")
            proteins = Protein.objects.filter(
                uniprot_accession__in=protein_selection)
            interactions = Interaction.objects.filter(
                Q(p1__in=proteins) | Q(p2__in=proteins)
            )
            context["main_interactions"] = interactions
            # collect all proteins in these interactions
            main_interactors = set()
            for interaction in interactions:
                main_interactors.add(interaction.p1)
                main_interactors.add(interaction.p2)
            # remove selected proteins to reduce redundant interactions
            main_interactors -= set(p for p in proteins)
            neighbors_interactions = Interaction.objects.filter(
                Q(p1__in=main_interactors) & Q(p2__in=main_interactors)
            )
            context["neighbors_interactions"] = neighbors_interactions
            # TODO: filter based on `evidence-type` and `quality`. It should
            # apply to `interactions`, and `neighbors_interactions` above.
            # First filter the `interactions` by their supporting evidence
            # metadata, and then retrieve the `neighbors_interactions` also
            # with the same filter.
    return render(request, "network-viewer.html", context)
