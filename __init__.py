# -*- coding: utf-8 -*-

from . import settings


def classFactory(iface): 
    """ Load Plugin class from main plugin file.
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    settings.init_plugin()
    from .main import GWComposerPlugin
    return GWComposerPlugin(iface)

