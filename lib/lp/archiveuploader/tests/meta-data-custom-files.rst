Meta-Data Custom files
======================

Meta-data custom files are files that contain more information about the
source package they're being uploaded with, such as descriptions and
pricing.  This information is used by the Software Centre to display
better descriptions about packages than would normally be found in the
package itself.

When the CustomUploadFile object is created with the right section name,
its custom_type property returns the right DBEnum,
PackageUploadCustomFormat.META_DATA.

    >>> from lp.archiveuploader.nascentuploadfile import CustomUploadFile
    >>> custom_upload_file = CustomUploadFile(
    ...     filepath="", checksums={}, size=1, priority_name="", policy=None,
    ...     component_and_section="main/raw-meta-data", logger=None)

    >>> print(custom_upload_file.custom_type.name)
    META_DATA

