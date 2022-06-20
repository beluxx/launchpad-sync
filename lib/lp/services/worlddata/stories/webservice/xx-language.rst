Language related webservices
============================

Accessing a single language
---------------------------

The language information from Launchpad can be queried using
'/+languages/CC', where CC is the language code.

    >>> es = anon_webservice.get('/+languages/es').jsonBody()
    >>> print(es['resource_type_link'])
    http.../#language
    >>> print(es['text_direction'])
    Left to Right
    >>> print(es['code'])
    es
    >>> print(es['english_name'])
    Spanish
    >>> print(es['plural_expression'])
    n != 1
    >>> print(es['plural_forms'])
    2
    >>> print(es['translators_count'])
    1
    >>> print(es['visible'])
    True


Accesing all or visible languages through API
---------------------------------------------

The list of all languages visible by default in Launchpad can by obtained
at '/+languages'.


    >>> def get_languages_entries(languages):
    ...     list = ''
    ...     for language in languages['entries']:
    ...         if language['visible']:
    ...             list += language['english_name'] + "\n"
    ...         else:
    ...             list += language['english_name'] + '(hidden)' + "\n"
    ...     return list
    >>> default_languages = anon_webservice.get('/+languages').jsonBody()
    >>> print(default_languages['resource_type_link'])
    http.../#languages
    >>> languages = get_languages_entries(default_languages)
    >>> print(languages)
    Abkhazian
    ...
    >>> '(hidden)' in languages
    False

The list of all languages known by Launchpad can by obtained
from '/+languages' using 'getAllLanguages' operation.
It also contains languages like Afar (Djibouti), which are hidden by
default.

    >>> all_languages = anon_webservice.get(
    ...     '/+languages?'
    ...     'ws.op=getAllLanguages&ws.start=0&ws.size=10'
    ...     ).jsonBody()
    >>> print(get_languages_entries(all_languages))
    Abkhazian
    ...
    Afar (Djibouti)(hidden)
    ...
