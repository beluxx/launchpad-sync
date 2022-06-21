Sprites
=======

Many small images in Launchpad are combined into a single image file,
so that browsers do not have to make as many requests when they first
view a page. An individual sprite is displayed as a background image
on an element by setting the background position.

A new image can be added to the combined image file and CSS template with
the command::

    make css_combine


CSS Template
------------

SpriteUtil takes a template css file that contains special comments
indicating that the background-image for a given rule should be
added to the combined image file and the rule should be updated.

For example::

    .add {
        background-image: url(/@@/edit.png); /* sprite-ref: group1 */
    }

would become
::

    .add {
        background-image: url(foo/combined_image.png);
        background-position: 0px 234px;
    }

The sprite-ref parameter specifies not only that the given image
should become a sprite but also that all the images with sprite-ref
value (in this case: "group1") will be combined to a single file.
A SpriteUtil object currently can only process a single group.

Loading the CSS Template
------------------------

Instatiating a new SpriteUtil object will parse the css template and
find all the css rules for the specified group. The url_prefix_substitutions
parameter allows you to convert url prefixes into file paths relative
to the directory passed into combineImages(). The space between sprites
in the file can be changed with the margin parameter.

    >>> import os, tempfile
    >>> from PIL import Image
    >>> from lp.services.spriteutils import SpriteUtil
    >>> root = os.path.abspath(os.path.join(__file__, '../../../../..'))
    >>> icing = os.path.join(root, 'lib/canonical/launchpad/icing')
    >>> new_png_file = tempfile.NamedTemporaryFile()
    >>> new_positioning_file = tempfile.NamedTemporaryFile()
    >>> new_css_file = tempfile.NamedTemporaryFile()
    >>> def get_sprite_util(margin=0):
    ...     return SpriteUtil(
    ...         os.path.join(
    ...             root, 'lib/lp/services/tests/testfiles/template.css'),
    ...         'group1',
    ...         url_prefix_substitutions={'/@@/': '../images/'},
    ...         margin=margin)
    >>> sprite_util = get_sprite_util()


Generate Image File
-------------------

The combined image will have a width equal to that of the widest image,
and the height will be the sum of all the image heights, since the margin
is currently zero.

    >>> sprite_util.combineImages(icing)
    >>> sprite_util.savePNG(new_png_file.name)
    >>> image = Image.open(new_png_file.name)
    >>> print(image.size)
    (14, 55)

The height will increase when the margin is increased.

    >>> sprite_util = get_sprite_util(margin=100)
    >>> sprite_util.combineImages(icing)
    >>> sprite_util.savePNG(new_png_file.name)
    >>> image = Image.open(new_png_file.name)
    >>> print(image.size)
    (14, 455)


Positioning File
----------------

The positioning file contains locations of each sprite in the combined
image file. This allows the css file to be regenerated when the template
changes without requiring the combined image file to be recreated.

    >>> sprite_util.savePositioning(new_positioning_file.name)
    >>> print(six.ensure_text(new_positioning_file.read()))
    /*...
    {
        "../images/add.png": [
            0,
            -114
        ],
        "../images/blue-bar.png": [
            0,
            -342
        ],
        "../images/edit.png": [
            0,
            -228
        ]
    }

The positions attribute can be cleared and loaded from the file.

    >>> print(pretty(sprite_util.positions))
    {'../images/add.png': (0, -114),
     '../images/blue-bar.png': (0, -342),
     '../images/edit.png': (0, -228)}
    >>> sprite_util.positions = None
    >>> sprite_util.loadPositioning(new_positioning_file.name)
    >>> print(pretty(sprite_util.positions))
    {'../images/add.png': [0, -114],
     '../images/blue-bar.png': [0, -342],
     '../images/edit.png': [0, -228]}


Generate CSS File
-----------------

When the css file is generated, the second parameter is the relative
path from the css file to the combined image file. The .add and .foo
classes have the same background-position, since they both originally
referenced /@@/add.png, which was only added once to the combined file.
.bar and .info do not have a background-position and the background-image
is not group1.png, since its sprite-ref is "group2".

    >>> sprite_util.saveConvertedCSS(new_css_file.name, 'group1.png')
    >>> print(six.ensure_text(new_css_file.read()))
    /*...
    .add {
        background-image: url(group1.png);
        /* sprite-ref: group1 */
        background-position: 0 -114px
        }
    .foo {
        background-image: url(group1.png);
        /* sprite-ref: group1 */
        background-position: 0 -114px
        }
    .bar {
        background-image: url(/@@/add.png);
        /* sprite-ref: group2 */
        }
    .edit {
        background-image: url(group1.png);
        /* sprite-ref: group1 */
        background-repeat: no-repeat;
        background-position: 0 -228px
        }
    .info {
        background-image: url(/@@/info.png);
        /* sprite-ref: group2 */
        background-repeat: no-repeat
        }
    .bluebar {
        background-image: url(group1.png);
        /* sprite-ref: group1 */
        background-repeat: repeat-x;
        background-position: 0 -342px
        }
