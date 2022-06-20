Hosted files
============

In Launchpad, hosted file resources are managed by the Launchpad
library. This test illustrates the Launchpad-specific behaviour of
hosted file resources.


The librarian manages hosted files
----------------------------------

Firefox starts out with a link to branding images, but no actual images.

    >>> project = webservice.get('/firefox').jsonBody()
    >>> print(project['icon_link'])
    http://.../firefox/icon
    >>> print(project['logo_link'])
    http://.../firefox/logo
    >>> print(project['brand_link'])
    http://.../firefox/brand

    >>> print(webservice.get(project['icon_link']))
    HTTP/1.1 404 Not Found
    ...
    >>> print(webservice.get(project['logo_link']))
    HTTP/1.1 404 Not Found
    ...
    >>> print(webservice.get(project['brand_link']))
    HTTP/1.1 404 Not Found
    ...

We can upload branding images with PUT.

    >>> import os
    >>> import canonical.launchpad
    >>> def load_image(filename):
    ...     image_file = os.path.join(
    ...         os.path.dirname(canonical.launchpad.__file__),
    ...         'images', filename)
    ...     with open(image_file, 'rb') as f:
    ...         return f.read()

    >>> print(webservice.put(project['icon_link'], 'image/png',
    ...                      load_image('team.png')))
    HTTP/1.1 200 Ok
    ...
    >>> print(webservice.put(project['logo_link'], 'image/png',
    ...                      load_image('team-logo.png')))
    HTTP/1.1 200 Ok
    ...
    >>> print(webservice.put(project['brand_link'], 'image/png',
    ...                      load_image('team-mugshot.png')))
    HTTP/1.1 200 Ok
    ...

The project's branding links now redirects you to files maintained
by the librarian.

    >>> result = webservice.get(project['icon_link'])
    >>> print(result)
    HTTP/1.1 303 See Other
    ...
    Location: http://.../icon
    ...

    >>> result = webservice.get(project['logo_link'])
    >>> print(result)
    HTTP/1.1 303 See Other
    ...
    Location: http://.../logo
    ...

    >>> result = webservice.get(project['brand_link'])
    >>> print(result)
    HTTP/1.1 303 See Other
    ...
    Location: http://.../brand
    ...


Error handling
--------------

Launchpad's ImageUpload classes enforce restrictions on uploaded
images. You can't upload an image that's the wrong type.

    >>> print(webservice.put(
    ...     project['brand_link'], 'image/png', 'Not an image'))
    HTTP/1.1 400 Bad Request
    ...
    The file uploaded was not recognized as an image; please check it
    and retry.

You also can't upload an image that's the wrong size.

    >>> print(webservice.put(project['brand_link'], 'image/png',
    ...                      load_image('team-logo.png')))
    HTTP/1.1 400 Bad Request
    ...
    This image is not exactly 192x192 pixels in size.

