from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from base.models import Organism, Protein, Interaction


def home(request):
    context = {}
    context["active"] = "home"

    # organism information
    orgs = (Protein.objects
            .order_by().values_list("organism", flat=True).distinct())
    context["organisms"] = Organism.objects.filter(pk__in=orgs)
    print(len(orgs))
    return render(request, "home.html", context)


def download(request):
    context = {}
    context["active"] = "download"
    return render(request, "download.html", context)


def faq(request):
    context = {}
    context["active"] = "faq"
    return render(request, "faq.html", context)


def search_proteins(request):
    context = {}
    if request.method == "POST":
        query = request.POST.get("protein-name", "")
        if query:
            protein_qs = Protein.objects
            proteins = protein_qs.filter(
                Q(uniprot_accession__icontains=query)
            )
            if len(proteins) > 0:
                context["proteins"] = proteins
    return render(request, "components/protein-search.html", context)


def network_viewer(request):
    context = {}
    if request.method == "POST":
        query = request.POST.get("protein-accession", "")
        if query:
            protein = get_object_or_404(Protein, uniprot_accession=query)
            interactions = Interaction.objects.filter(
                Q(p1=protein) | Q(p2=protein)
            )
            context["main_interactions"] = interactions
            # collect all proteins in these interactions
            main_interactors = set()
            for interaction in interactions:
                main_interactors.add(interaction.p1)
                main_interactors.add(interaction.p2)
            # remove main protein to reduce redundant interactions
            main_interactors -= protein
            neighbors_interactions = Interaction.objects.filter(
                Q(p1__in=main_interactors) & Q(p2__in=main_interactors)
            )
            context["neighbors_interactions"] = neighbors_interactions
    return render(request, "network-viewer.html", context)
