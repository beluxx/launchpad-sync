# Copyright 2015-2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""All the interfaces that are exposed through the webservice.

There is a declaration in ZCML somewhere that looks like:
  <webservice:register module="lp.snappy.interfaces.webservice" />

which tells `lazr.restful` that it should look for webservice exports here.
"""

__all__ = [
    'ISnap',
    'ISnapBase',
    'ISnapBaseSet',
    'ISnapBuild',
    'ISnapBuildRequest',
    'ISnappySeries',
    'ISnappySeriesSet',
    'ISnapSet',
    ]

from lp.services.webservice.apihelpers import (
    patch_collection_property,
    patch_collection_return_type,
    patch_entry_return_type,
    patch_reference_property,
    )
from lp.snappy.interfaces.snap import (
    ISnap,
    ISnapBuildRequest,
    ISnapEdit,
    ISnapSet,
    ISnapView,
    )
from lp.snappy.interfaces.snapbase import (
    ISnapBase,
    ISnapBaseSet,
    )
from lp.snappy.interfaces.snapbuild import (
    ISnapBuild,
    ISnapFile,
    )
from lp.snappy.interfaces.snappyseries import (
    ISnappySeries,
    ISnappySeriesSet,
    )


# ISnapFile
patch_reference_property(ISnapFile, 'snapbuild', ISnapBuild)

# ISnapBuildRequest
patch_reference_property(ISnapBuildRequest, 'snap', ISnap)
patch_collection_property(ISnapBuildRequest, 'builds', ISnapBuild)

# ISnapView
patch_entry_return_type(ISnapView, 'requestBuild', ISnapBuild)
patch_collection_property(ISnapView, 'builds', ISnapBuild)
patch_collection_property(ISnapView, 'completed_builds', ISnapBuild)
patch_collection_property(ISnapView, 'pending_builds', ISnapBuild)

# ISnapEdit
patch_collection_return_type(ISnapEdit, 'requestAutoBuilds', ISnapBuild)
