import logging

from django.http import HttpResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def index(request):
    logger.debug(f"index view accessed - method: {request.method}, path: {request.path}")
    return HttpResponse("Hello, world. You're at the polls index.")
