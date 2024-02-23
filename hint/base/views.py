from django.shortcuts import render
from django.db.models import Q
from base.models import Organism, Protein


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


def search_protein(request):
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
