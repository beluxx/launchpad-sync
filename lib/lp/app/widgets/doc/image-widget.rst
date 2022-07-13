ImageChange widget
==================

In Launchpad we have images associated with people, products,
distributions, etc, and we want to allow people to have full control
over their images. That is, they must be able to upload a new image and
delete (or keep) an existing one. For this we created this widget, which
can be embedded into any form we want, which doesn't require us to add
any submit buttons to indicate that the image should be kept, deleted or
changed.

The widget is composed by a RadioWidget and a FileWidget, where the
radio specifies the action that should be performed (keep the existing
image, change back to the default image or change it to an user-uploaded
one) and the FileWidget gives us the user-uploaded file, in case there
is one.

Whenever you have a form in which you want to use the image widget, you
have to explicitly say whether you want to use its ADD_STYLE or
EDIT_STYLE incarnation, by passing an extra argument to the widget's
constructor (or to CustomWidgetFactory(), if you're using it).

Our policy is not to ask people to upload images when creating a record,
but instead to expose this as an edit form after the object is created.

Let's use Salgado and the Launchpad Administrators team as an examples
here, since they haven't uploaded custom logos yet.

    >>> from lp.registry.interfaces.person import IPerson, IPersonSet
    >>> salgado = getUtility(IPersonSet).getByName('salgado')
    >>> salgado.logo is None
    True

    >>> admins_team = getUtility(IPersonSet).getByName('admins')
    >>> admins_team.logo is None
    True

    >>> admins_team.icon is None
    True


The ADD_STYLE/EDIT_STYLE incarnations
-------------------------------------

The only difference between them is that the ADD_STYLE has a different
set of labels for its options and never returns our special flag to
indicate that the image should be kept, since there's nothing to be
kept. For that reason I'll only demonstrate the EDIT_STYLE here.

Since Salgado has no logo, the widget will display the default person-
logo image and the 'Keep' radio button will be selected. The other radio
button allows the user to upload a new image.

    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.app.widgets.image import ImageChangeWidget
    >>> add_style = ImageChangeWidget.ADD_STYLE
    >>> edit_style = ImageChangeWidget.EDIT_STYLE
    >>> person_logo = IPerson['logo'].bind(salgado)
    >>> widget = ImageChangeWidget(
    ...     person_logo, LaunchpadTestRequest(), edit_style)

    >>> from lp.services.beautifulsoup import BeautifulSoup
    >>> html = widget()
    >>> print(BeautifulSoup(html).find('img').get('src'))
    /@@/person-logo

    >>> def print_radio_items(html):
    ...     soup = BeautifulSoup(html)
    ...     for input in soup('input', {'type': 'radio'}):
    ...         item = input.get('value')
    ...         if input.get('checked'):
    ...             item += ': SELECTED'
    ...         else:
    ...             item += ': NOT SELECTED'
    ...         print(item)
    >>> print_radio_items(html)
    keep: SELECTED
    change: NOT SELECTED

If we set any random file as salgado's logo, we'll see it there, as well
as an option to delete the image that was just uploaded.

    >>> from lp.services.librarian.interfaces import (
    ...     ILibraryFileAliasSet)
    >>> login('guilherme.salgado@canonical.com')
    >>> logo = getUtility(ILibraryFileAliasSet)[53]
    >>> salgado.logo = logo

    # Need to create a new widget instance since we changed our context
    # manually.

    >>> widget = ImageChangeWidget(
    ...     person_logo, LaunchpadTestRequest(), edit_style)

    >>> html = widget()
    >>> logo.getURL() == BeautifulSoup(html).find('img').get('src')
    True

    >>> print_radio_items(html)
    keep: SELECTED
    delete: NOT SELECTED
    change: NOT SELECTED

Now we'll stuff values in our request to simulate a user playing with
the widget. Let's see how it reacts.

First, let's tell it to keep the existing image.

    >>> from lp.services.fields import KEEP_SAME_IMAGE
    >>> form = {'field.logo.action': 'keep'}
    >>> widget = ImageChangeWidget(
    ...     person_logo, LaunchpadTestRequest(form=form), edit_style)
    >>> widget.getInputValue() == KEEP_SAME_IMAGE
    True

Then we tell it to delete the existing one.

    >>> form = {'field.logo.action': 'delete'}
    >>> widget = ImageChangeWidget(
    ...     person_logo, LaunchpadTestRequest(form=form), edit_style)
    >>> widget.getInputValue() is None
    True

And now we change it to a random image.

    >>> import canonical.launchpad
    >>> import io
    >>> import os
    >>> logo_file_name = os.path.join(
    ...     os.path.dirname(canonical.launchpad.__file__),
    ...     'images/team-logo.png')
    >>> with open(logo_file_name, 'rb') as logo_file:
    ...     logo = io.BytesIO(logo_file.read())
    >>> logo.filename = 'logo.png'
    >>> form = {'field.logo.action': 'change',
    ...         'field.logo.image': logo}
    >>> widget = ImageChangeWidget(
    ...     person_logo, LaunchpadTestRequest(form=form), edit_style)
    >>> fileupload = widget.getInputValue()
    >>> print(fileupload.filename)
    logo.png

    >>> fileupload.content.filesize == len(logo.getvalue())
    True

In order for this widget to work on add forms, we need to make sure it
works when its field is bounded to an object that doesn't have the
attribute that the field represents.

    >>> personset_logo = IPerson['logo'].bind(getUtility(IPersonSet))
    >>> form = {'field.logo.action': 'keep'}
    >>> widget = ImageChangeWidget(
    ...     personset_logo, LaunchpadTestRequest(form=form), add_style)

Note that in this case the KEEP_SAME_IMAGE flag doesn't make sense, so
we return None, which is a sensible value that can be fed to a method
which creates a new database object for us.

    >>> widget.getInputValue() == None
    True

    >>> print_radio_items(widget())
    keep: SELECTED
    change: NOT SELECTED

    >>> form = {'field.logo.action': 'change',
    ...         'field.logo.image': logo}
    >>> widget = ImageChangeWidget(
    ...     personset_logo, LaunchpadTestRequest(form=form), add_style)
    >>> print_radio_items(widget())
    keep: NOT SELECTED
    change: SELECTED

    >>> widget.getInputValue().content.filesize == len(logo.getvalue())
    True


The IconImageUpload, LogoImageUpload and MugshotImageUpload fields
------------------------------------------------------------------

There are three fields which are used for image uploads. They are all
subsclasses of the same BaseImageUpload class, and the only thing they
change in each case is the max_size exact dimensions. We will only test
the IconImageUpload and MugshotImageUpload widgets below.

Since this is a special widget which returns a special object
(KEEP_SAME_IMAGE) to indicate that the image should be kept, we need to
use a custom field (IconImageUpload) together with it. That field should
not be used directly, since it specifies some constraints and defaults
that are specific to each image, so you must subclass it before using.

    >>> from lp.services.fields import (
    ...     BaseImageUpload, IconImageUpload)

Note: the .bind method here is fetching the field from the IPerson
schema (which should be an IconImageUpload, a subclass of
BaseImageUpload) and binding it to Launchpad Administrators.

    >>> person_icon = IPerson['icon'].bind(admins_team)
    >>> isinstance(person_icon, BaseImageUpload)
    True

    >>> isinstance(person_icon, IconImageUpload)
    True

    >>> person_icon.max_size
    5120

    >>> person_icon.dimensions
    (14, 14)

If we pass that special object (KEEP_SAME_IMAGE) to IconImageUpload's
set() method, the current image will be kept.

    >>> admins_team.icon = getUtility(ILibraryFileAliasSet)[53]
    >>> existing_img = admins_team.icon
    >>> existing_img is None
    False

    >>> person_icon.set(admins_team, KEEP_SAME_IMAGE)
    >>> admins_team.icon == existing_img
    True

On the other hand, if we pass None, the current image will be removed.

    >>> person_icon.set(admins_team, None)
    >>> admins_team.icon is None
    True

Similarly, passing any file of the type expected (FileUpload) will
change the current image to the given file.

    >>> person_icon.set(admins_team, fileupload)
    >>> admins_team.icon is None
    False

    >>> admins_team.icon == existing_img
    False


Input validation
----------------

The BaseImageUpload field expects an image with the exact dimensions and
within the stated constraints, so it won't accept anything else.

We will try submit a logo to the mugshot image upload widget. Since we
have an image with a byte size smaller than person_mugshot.max_size BUT
dimensions smaller than person_mugshot.dimensions, it must be rejected.

    >>> import PIL.Image
    >>> person_mugshot = IPerson['mugshot'].bind(salgado)
    >>> logo_file_name = os.path.join(
    ...     os.path.dirname(canonical.launchpad.__file__),
    ...     'images/team-logo.png')
    >>> with open(logo_file_name, 'rb') as logo_file:
    ...     logo = io.BytesIO(logo_file.read())
    >>> logo.filename = 'logo.png'
    >>> len(logo.getvalue()) <= person_mugshot.max_size
    True

    >>> image = PIL.Image.open(logo)
    >>> image.size <= person_mugshot.dimensions
    True

    >>> form = {'field.mugshot.action': 'change', 'field.mugshot.image': logo}
    >>> widget = ImageChangeWidget(
    ...     person_mugshot, LaunchpadTestRequest(form=form), edit_style)
    >>> widget.getInputValue()
    Traceback (most recent call last):
    ...
    zope.formlib.interfaces.WidgetInputError: ('field.mugshot',
    ...'Mugshot', LaunchpadValidationError(...'\nThis image is not exactly
    192x192\npixels in size.'))

This is what we see when the image is the correct dimensions, and within
the max_size:

    >>> mugshot_file_name = os.path.join(
    ...     os.path.dirname(canonical.launchpad.__file__),
    ...     'images/team-mugshot.png')
    >>> with open(mugshot_file_name, 'rb') as mugshot_file:
    ...     mugshot = io.BytesIO(mugshot_file.read())
    >>> mugshot.filename = 'mugshot.png'

Image is a small enough file:

    >>> len(mugshot.getvalue()) <= person_mugshot.max_size
    True

Image is the correct dimensions:

    >>> image = PIL.Image.open(mugshot)
    >>> image.size == person_mugshot.dimensions
    True

    >>> form = {'field.mugshot.action': 'change',
    ...         'field.mugshot.image': mugshot}
    >>> widget = ImageChangeWidget(
    ...     person_mugshot, LaunchpadTestRequest(form=form), edit_style)
    >>> fileupload = widget.getInputValue()
    >>> print(fileupload.filename)
    mugshot.png

    >>> fileupload.content.filesize == len(mugshot.getvalue())
    True

If we change person_mugshot's max_size to be smaller than our test
image, we'll get a validation error.

    >>> person_mugshot.max_size = len(mugshot.getvalue()) - 1
    >>> _ = mugshot.seek(0)
    >>> widget = ImageChangeWidget(
    ...     person_mugshot, LaunchpadTestRequest(form=form), edit_style)
    >>> widget.getInputValue()
    Traceback (most recent call last):
    ...
    zope.formlib.interfaces.WidgetInputError: ('field.mugshot',
    ...'Mugshot', LaunchpadValidationError(...'\nThis image exceeds the
    maximum allowed size in bytes.'))

A similar error will be raised if the image's dimensions are bigger than
the maximum we allow.

    >>> person_mugshot.max_size = len(mugshot.getvalue())
    >>> person_mugshot.dimensions = (image.size[0] - 1, image.size[1] + 1)
    >>> _ = mugshot.seek(0)
    >>> widget = ImageChangeWidget(
    ...     person_mugshot, LaunchpadTestRequest(form=form), edit_style)
    >>> widget.getInputValue()
    Traceback (most recent call last):
    ...
    zope.formlib.interfaces.WidgetInputError: ('field.mugshot',
    ...'Mugshot', LaunchpadValidationError(...'\nThis image is not exactly
    191x193\npixels in size.'))

    >>> person_mugshot.dimensions = (image.size[0] + 1, image.size[1] - 1)
    >>> _ = mugshot.seek(0)
    >>> widget = ImageChangeWidget(
    ...     person_mugshot, LaunchpadTestRequest(form=form), edit_style)
    >>> widget.getInputValue()
    Traceback (most recent call last):
    ...
    zope.formlib.interfaces.WidgetInputError: ('field.mugshot',
    ...'Mugshot', LaunchpadValidationError(...'\nThis image is not exactly
    193x191\npixels in size.'))

Finally, if the user specifies the 'change' action they must also provide
a file to be uploaded.

    >>> form = {'field.mugshot.action': 'change', 'field.mugshot.image': ''}
    >>> widget = ImageChangeWidget(
    ...     person_mugshot, LaunchpadTestRequest(form=form), edit_style)
    >>> widget.getInputValue()
    Traceback (most recent call last):
    ...
    zope.formlib.interfaces.WidgetInputError: ('field.mugshot',
    ...'Mugshot', LaunchpadValidationError(...'Please specify the image you
    want to use.'))


Non-exact Image Dimensions
--------------------------

For some input fields, we don't require a particular size for an image,
but want to enforce a maximum size on the image.  This can be achieved
by setting the exact_dimensions attribute of the field to False:

    >>> person_mugshot.exact_dimensions = False
    >>> person_mugshot.dimensions = (64, 64)
    >>> with open(mugshot_file_name, 'rb') as mugshot_file:
    ...     mugshot = io.BytesIO(mugshot_file.read())
    >>> mugshot.filename = 'mugshot.png'
    >>> form = {'field.mugshot.action': 'change',
    ...         'field.mugshot.image': mugshot}
    >>> widget = ImageChangeWidget(
    ...     person_mugshot, LaunchpadTestRequest(form=form), edit_style)
    >>> widget.getInputValue()
    Traceback (most recent call last):
    ...
    zope.formlib.interfaces.WidgetInputError: ('field.mugshot',
    ...'Mugshot', LaunchpadValidationError(...'\nThis image is larger than
    64x64\npixels in size.'))

If the image is smaller than the dimensions, the input validates:

    >>> person_mugshot.dimensions = (256, 256)
    >>> _ = mugshot.seek(0)
    >>> widget = ImageChangeWidget(
    ...     person_mugshot, LaunchpadTestRequest(form=form), edit_style)
    >>> fileupload = widget.getInputValue()
    >>> print(fileupload.filename)
    mugshot.png

The same occurs if the image matches the specified dimensions:

    >>> person_mugshot.dimensions = (192, 192)
    >>> _ = mugshot.seek(0)
    >>> widget = ImageChangeWidget(
    ...     person_mugshot, LaunchpadTestRequest(form=form), edit_style)
    >>> fileupload = widget.getInputValue()
    >>> print(fileupload.filename)
    mugshot.png
