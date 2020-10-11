"""Python package emqxlwm2m"""

# Module metadata
__author__ = 'Daniel Andersson'
__maintainer__ = __author__
__email__ = 'daniel.4ndersson@gmail.com'
__contact__ = __email__
__copyright__ = 'Copyright (c) 2020 Daniel Andersson'
__license__ = 'MIT'
__url__ = 'https://github.com/Penlect/emqxlwm2m'
__version__ = '0.2.0'

# Package
from .core import LwM2MGateway

__all__ = ['LwM2MGateway']
