from django.shortcuts import render


def privacy_policy(request):
    """View for Privacy Policy page"""
    return render(request, 'privacy.html')


def terms_of_service(request):
    """View for Terms of Service page"""
    return render(request, 'terms.html')
