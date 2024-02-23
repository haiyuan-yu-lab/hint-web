from django.shortcuts import render


def home(request):
    context = {}
    context["active"] = "home"
    return render(request, "home.html", context)


def download(request):
    context = {}
    context["active"] = "download"
    return render(request, "download.html", context)


def faq(request):
    context = {}
    context["active"] = "faq"
    return render(request, "faq.html", context)
