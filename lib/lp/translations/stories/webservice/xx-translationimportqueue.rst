Translation Import Queue
========================

The queue of uploaded translation files is quite large.  It contains not
just files waiting to be imported, but also blocked or failed uploads,
and for a brief while, ones that are already processed and are waiting
to be cleaned up.

    >>> entry_attributes = set([
    ...     'date_created',
    ...     'date_status_changed',
    ...     'distroseries_link',
    ...     'format',
    ...     'id',
    ...     'path',
    ...     'productseries_link',
    ...     'resource_type_link',
    ...     'self_link',
    ...     'sourcepackage_link',
    ...     'status',
    ...     'uploader_link',
    ...     ])

    >>> def print_dict_entries(a_dict, shown_keys=None):
    ...     """Print entries from a dict-like object.
    ...
    ...     :param a_dict: dictionary to print.
    ...     :param shown_keys: optional set of keys that should be
    ...         shown.  If omitted, all keys are shown.
    ...     """
    ...     print('Entry:')
    ...     for key in sorted(a_dict):
    ...         if shown_keys is None or key in shown_keys:
    ...             print('', key, a_dict[key])

    >>> def print_list_of_dicts(a_list, shown_keys=None):
    ...     """Print entries from a list of dicts."""
    ...     for entry in a_list:
    ...         print_dict_entries(entry, shown_keys=shown_keys)


Enumerating the queue
---------------------

    >>> queue = webservice.get("/+imports").jsonBody()
    >>> queue['total_size']
    2

    >>> print_list_of_dicts(queue['entries'], entry_attributes)
    Entry:
     date_created ...
     date_status_changed ...
     distroseries_link None
     format PO format
     id 1
     path po/evolution-2.2-test.pot
     productseries_link http://.../evolution/trunk
     resource_type_link http://.../#translation_import_queue_entry
     self_link http://.../+imports/1
     sourcepackage_link None
     status Imported
     uploader_link http://.../~name16
    Entry:
     date_created ...
     date_status_changed ...
     distroseries_link None
     format PO format
     id 2
     path po/pt_BR.po
     productseries_link http://.../evolution/trunk
     resource_type_link http://.../#translation_import_queue_entry
     self_link http://.../+imports/2
     sourcepackage_link None
     status Imported
     uploader_link http://.../~name16


Entry fields
------------

Most of the fields in a translation import queue entry are immutable
from the web service's point of view.

    >>> from simplejson import dumps


Path
....

An entry's file path can be changed by the entry's owner or an admin.

    >>> first_entry = queue['entries'][0]['self_link']
    >>> print(webservice.patch(
    ...     first_entry, 'application/json', dumps({'path': 'foo.pot'})))
    HTTP/1.1 209 Content Returned
    ...

    >>> print(webservice.get(first_entry).jsonBody()['path'])
    foo.pot

A regular user is not allowed to make this change.

    >>> first_entry = queue['entries'][0]['self_link']
    >>> print(user_webservice.patch(
    ...     first_entry, 'application/json', dumps({'path': 'bar.pot'})))
    HTTP... Unauthorized
    ...


Status
......

For now, it is not possible to set an entry's status through the API.

    >>> first_entry = queue['entries'][0]['self_link']
    >>> print(webservice.patch(
    ...     first_entry, 'application/json', dumps({'status': 'Approved'})))
    HTTP... Bad Request
    ...
    status: You tried to modify a read-only attribute.

But you can set the status using the setStatus method.

    >>> print(webservice.named_post(
    ...     first_entry, 'setStatus', {}, new_status='Approved'))
    HTTP/1.1 200 Ok
    ...

The entry's status is changed.

    >>> queue = webservice.get("/+imports").jsonBody()
    >>> print(queue['entries'][0]['status'])
    Approved

Unprivileged users cannot change the status.

    >>> print(user_webservice.named_post(
    ...     first_entry, 'setStatus', {}, new_status='Deleted'))
    HTTP/1.1 401 Unauthorized
    ...


Target-specific import queues
-----------------------------

Objects that implement IHasTranslationImports (also known as "translation
targets") expose their specific sub-sets of the import queue through
getTranslationImportQueueEntries.

In this example, a person:

    >>> login(ANONYMOUS)
    >>> target = factory.makePerson()
    >>> target_url = '/~%s' % target.name
    >>> matching_entry = factory.makeTranslationImportQueueEntry(
    ...     'matching-entry.pot', uploader=target)
    >>> other_entry = factory.makeTranslationImportQueueEntry(
    ...     'other-entry.pot')
    >>> logout()

    >>> target_queue = webservice.named_get(
    ...     target_url, 'getTranslationImportQueueEntries').jsonBody()
    >>> print(target_queue['total_size'])
    1

    >>> print(target_queue['entries'][0]['path'])
    matching-entry.pot
