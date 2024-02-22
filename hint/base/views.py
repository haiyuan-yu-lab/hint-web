from django.shortcuts import render


def home(request):
    context = {}
    return render(request, "home.html", context)


def downloads(request):
    context = {}
    return render(request, "downloads.html", context)


def faq(request):
    context = {}
    return render(request, "faq.html", context)
