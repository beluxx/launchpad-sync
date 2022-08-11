Page Tests Helpers
==================

Page tests are used to test common use-cases about Launchpad. We use the
zope.testbrowser component to write most of these tests. The pagetest
doctest environement comes loaded with a bunch of predefined names that
makes writing page test easy.

    >>> from lp.testing.pages import setUpGlobs
    >>> class MockTest:
    ...     def __init__(self):
    ...         self.globs = {}

    >>> test = MockTest()
    >>> setUpGlobs(test)


Preset Browsers
---------------

We have a bunch of zope.testbrowser instances set-up with predefined
authenticated user:

A browser with an anonymous user is available under 'anon_browser'. This
one should be use for all anonymous browsing tests.

  # Shortcut to fetch the Authorization header from the testbrowser

    >>> def getAuthorizationHeader(browser):
    ...   return browser._req_headers.get('Authorization', '')

    >>> anon_browser = test.globs['anon_browser']
    >>> print(getAuthorizationHeader(anon_browser))
    <BLANKLINE>

A browser with a logged in user without any privileges is available
under 'user_browser'. This one should be use all workflows involving
logged in users, when it shouldn't require any special privileges.

    >>> user_browser = test.globs['user_browser']
    >>> print(getAuthorizationHeader(user_browser))
    Basic no-priv@canonical.com:test

A browser with a logged in user with administrative privileges is
available under 'admin_browser'. This one should be used for testing
administrative workflows.

    >>> admin_browser = test.globs['admin_browser']
    >>> print(getAuthorizationHeader(admin_browser))
    Basic foo.bar@canonical.com:test

Finally, here is a 'browser' instance that simply contain a pre-
initialized Browser instance. It doesn't have any authentication
configured. It can be used when you need to configure another user.

    >>> browser = test.globs['browser']
    >>> print(getAuthorizationHeader(browser))
    <BLANKLINE>

All these browser instances are configured with handleErrors set to
False. This means that exception are raised instead of returning the
standard error page.

    >>> browser.handleErrors
    False


Using Raw HTTP Requests
-----------------------

Altough testbrowser is very convenient, sometimes more control over the
request is needed. For these cases, there is a function available under
'http' that can be used to send raw HTTP request.

    >>> test.globs['http']
    <function http ...>


Helper Routines for Testing Page Content
----------------------------------------

When analysing the page content in a page test, it is often desirable to
check for certain content in a subsection of the page.

To help with this, a number of helper functions are made available to
page tests in the starting namespace.

Each of these functions returns a BeautifulSoup "Tag" instance (or a
list of such instances in the case of find_tags_by_class).  Printing the
result will give the corresponding HTML.  The return value can be
further disected with the find() or findall() methods.

In page tests it is recommended that you print return value and match
the result (possibly with sections elided) rather than doing True/False
style tests.  These produce better errors in the case of test failures.


find_tag_by_id()
----------------

This routine will return the tag with the given id:

    >>> find_tag_by_id = test.globs['find_tag_by_id']
    >>> content = '''
    ... <html id="root">
    ...   <head><title>Foo</title></head>
    ...   <body>
    ...     <p id="para-1">Paragraph 1</p>
    ...     <p id="para-2">Paragraph <B>2</B></p>
    ...   </body>
    ... </html>
    ... '''

    >>> print(find_tag_by_id(content, 'para-1'))
    <p id="para-1">Paragraph 1</p>

    >>> print(find_tag_by_id(content, 'para-2'))
    <p id="para-2">Paragraph <b>2</b></p>

If an unknown ID is used, None is returned:

    >>> print(find_tag_by_id(content, 'para-3'))
    None

If more than one element has the requested id, raise a DuplicateIdError
exception.

    >>> duplicate_id_content = '''
    ... <body>
    ...   <p id="duplicate">Lorem ipsum</p>
    ...   <p id="duplicate">dolor sit amet</p>
    ... </body>
    ... '''
    >>> find_tag_by_id(duplicate_id_content, 'duplicate')
    Traceback (most recent call last):
    ...
    lp.testing.pages.DuplicateIdError: Found 2 elements with id 'duplicate'

A BeautifulSoup PageElement can be passed instead of a string so that
content can be retrieved without reparsing the entire page.

    >>> parsed_content = find_tag_by_id(content, 'root')
    >>> print(parsed_content.name)
    html

    >>> print(find_tag_by_id(parsed_content, 'para-1'))
    <p id="para-1">Paragraph 1</p>


find_tags_by_class()
--------------------

Sometimes it we want to find tags that match a particular class.  The
find_tags_by_class() returns a list of Tag objects matching the given
class:

    >>> find_tags_by_class = test.globs['find_tags_by_class']
    >>> content = '''
    ... <html>
    ...   <head><title>Foo</title</head>
    ...   <body>
    ...     <p class="message">Message</p>
    ...     <p class="error message">Error message</p>
    ...     <p class="warning message">Warning message</p>
    ...     <p class="error">Error</p>
    ...     <p class="warning">
    ...       Warning (outer)
    ...       <em class="warning">Warning (inner)</em>
    ...     </p>
    ...   </body>
    ... </html>
    ... '''

    >>> for tag in find_tags_by_class(content, 'message'):
    ...     print(tag)
    <p class="message">Message</p>
    <p class="error message">Error message</p>
    <p class="warning message">Warning message</p>

    >>> for tag in find_tags_by_class(content, 'error'):
    ...     print(tag)
    <p class="error message">Error message</p>
    <p class="error">Error</p>

    >>> for tag in find_tags_by_class(content, 'warning'):
    ...     print(tag)
    <p class="warning message">Warning message</p>
    <p class="warning">
      Warning (outer)
      <em class="warning">Warning (inner)</em>
    </p>
    <em class="warning">Warning (inner)</em>

If no tags have the given class, then an empty list is returned:

    >>> find_tags_by_class(content, 'no-such-class')
    []


first_tag_by_class()
--------------------

At other times we're only interested in finding the first tag to match a
given class. The first_tag_by_class() behaves like the
find_tags_by_class() function, except that it returns only the first
matching Tag object, if one exists:

    >>> first_tag_by_class = test.globs['first_tag_by_class']
    >>> content = '''
    ... <html>
    ...   <head><title>Foo</title</head>
    ...   <body>
    ...     <p class="heavy">Message</p>
    ...     <p class="light">Error message</p>
    ...     <p class="heavy">Warning message</p>
    ...     <p class="light">Error</p>
    ...   </body>
    ... </html>
    ... '''

    >>> print(first_tag_by_class(content, 'light'))
    <p class="light">Error message</p>

If no tags have the given class, then "None" is returned.

    >>> content = '''
    ... <html>
    ...   <head><title>Foo</title</head>
    ...   <body>
    ...     <p class="medium">Message</p>
    ...     <p class="medium">Error message</p>
    ...     <p class="medium">Warning message</p>
    ...     <p class="medium">Error</p>
    ...   </body>
    ... </html>
    ... '''

    >>> print(first_tag_by_class(content, 'light'))
    None


find_portlet()
--------------

Many pages on Launchpad make use of portlets, so it is useful to be able
to examine the contents of a portlet.  The find_portlet() function can
find a portlet by its title and return it:

    >>> find_portlet = test.globs['find_portlet']
    >>> content = '''
    ... <html>
    ...   <head><title>Foo</title</head>
    ...   <body>
    ...     <div class="portlet">
    ...       <h2>Portlet 1</h2>
    ...       Contents of portlet 1
    ...     </div>
    ...     <div class="portlet">
    ...       <h2>Portlet 2</h2>
    ...       Contents of portlet 2
    ...     </div>
    ...     <div class="portlet">
    ...       <h2>Portlet 3</h2>
    ...       Contents of portlet 3
    ...     </div>
    ...     <div class="portlet">
    ...       <h2> Portlet
    ...           with title broken
    ...           on multiple lines </h2>
    ...       Contents of the portlet.
    ...     </div>
    ...     <div id="maincontent">
    ...       Main content area
    ...     </div>
    ...   </body>
    ... </html>
    ... '''

    >>> print(find_portlet(content, 'Portlet 1'))
    <div...
    ...Contents of portlet 1...

    >>> print(find_portlet(content, 'Portlet 2'))
    <div class="portlet">
      <h2>Portlet 2</h2>
      Contents of portlet 2
    </div>

When looking for a portlet to match, any two sequences of whitespace are
considered equivalent. Whitespace at the beginning or end of the title
is also ignored.

    >>> print(find_portlet(
    ...     content, 'Portlet with  title broken on multiple lines  '))
      <div class="portlet">
        <h2> Portlet with title...

If the portlet doesn't exist, then None is returned:

    >>> print(find_portlet(content, 'No such portlet'))
    None


find_main_content
-----------------

Sometimes we want to check that a particular piece of content appears in
the main content of the page.  The find_main_content() method can be
used to do this:

    >>> find_main_content = test.globs['find_main_content']
    >>> print(find_main_content(content))
    <...
    Main content area
    ...


extract_text
------------

Sometimes we are just interested in a portion of text that is displayed
to the end user, and we don't want necessarily to check how the text is
displayed (ie. bold, italics, coloured et al).

    >>> extract_text = test.globs['extract_text']
    >>> print(extract_text(
    ...     '<p>A paragraph with <b>inline</b> <i>style</i>.</p>'))
    A paragraph with inline style.

The function also takes care of inserting proper white space for block
level and other elements introducing a visual separation:

    >>> print(extract_text( # doctest: -NORMALIZE_WHITESPACE
    ...     '<p>Para 1</p><p>Para 2<br>Line 2</p><ul><li>Item 1</li>'
    ...     '<li>Item 2</li></ul><div>Div 1</div><h1>A heading</h1>'))
    Para 1
    Para 2
    Line 2
    Item 1
    Item 2
    Div 1
    A heading

Of course, the function ignores processing instructions, declaration,
comments and render CDATA section has plain text.

    >>> print(extract_text(
    ...     '<?php echo("Hello world!")?><!-- A comment -->'
    ...     '<?A declaration.><![CDATA[Some << characters >>]]>'))
    Some << characters >>

The function also does some white space normalization, since formatted
HTML usually contains a lot of white space and that pagetests are run
using NORMALIZE_WHITESPACE, diff output in the case of failure often
contains lot of white space noise. So whitespace is stripped from the
beginning and end of the result, runs of space and tabs is replaced by a
single space. Runs of newlines is replaced by one newline. (Note also
that non-breaking space entities are also transformed into regular
space.)

    >>> print(extract_text( # doctest: -NORMALIZE_WHITESPACE
    ...     '   <p>Some  \t  white space    <br /></p>   '
    ...     '<p>Another&nbsp; &#160;  paragraph.</p><p><p>'
    ...     '<p>A final one</p>   '))
    Some white space
    Another paragraph.
    A final one

The function also knows about the sortkey class used in many tables. The
sortkey is not displayed but is used for the javascript table sorting.

    >>> print(extract_text(
    ...    '<table><tr><td><span class="sortkey">1</span>First</td></tr>'
    ...    '<tr><td><span class="sortkey">2</span>Second</td></tr>'
    ...    '<tr><td><span class="sortkey">3</span>Third</td></tr></table>'))
    First Second Third

The extract_text method is often used in conjunction with the other
find_xxx helper methods to identify the text to display.  Because of
this the function also accepts BeautifulSoup instance as a parameter
rather than a plain string.

    >>> print(extract_text(find_portlet(content, 'Portlet 2')))
    Portlet 2
    Contents of portlet 2


parse_relationship_section
--------------------------

Since the code to render Package Relationship is consolidated in one
place, a method to parse this section and check built-in features was
also created.

This method is able to parse a rendered relationship_section and print a
list of isolated attributes for each mentioned item.

    >>> parse_relationship_section = test.globs['parse_relationship_section']
    >>> content = '''
    ... <html>
    ...   <ul>
    ...     <li>
    ...        <a href="somewhere">
    ...          linked_item
    ...        </a>
    ...     </li>
    ...     <li>
    ...          not_linked_item
    ...     </li>
    ...     <li>
    ...        <a href="somewhereelse">
    ...          linked with spaces
    ...        </a>
    ...     </li>
    ...     <li>
    ...          text with spaces
    ...     </li>
    ... '''

    >>> parse_relationship_section(content)
    LINK: "linked_item" -> somewhere
    TEXT: "not_linked_item"
    LINK: "linked with spaces" -> somewhereelse
    TEXT: "text with spaces"


print_feedback_messages
---------------------

When testing an error condition or a notification we often are only
interested in the feedback messages.  This helper will get informational
messages and error messages, based on the CSS class.

    >>> print_feedback_messages = test.globs['print_feedback_messages']
    >>> class FakeBrowser:
    ...     pass
    >>> browser = FakeBrowser()
    >>> browser.contents = '''
    ... <html>
    ...   <div class="informational message">1 file has been deleted.</div>
    ...   <p>blah blah</p>
    ...   <div class="error message">Red Alert!</div>
    ... </html>'''

    >>> print_feedback_messages(browser.contents)
    1 file has been deleted.
    Red Alert!

The helper extracts the text of the messages, which makes a difference
if the messages contain html elements.

    >>> browser = FakeBrowser()
    >>> browser.contents = '''
    ... <html>
    ...   <div class="informational message">1 file has been deleted.</div>
    ...   <p>blah blah</p>
    ...   <div class="error message">
    ...     Red Alert!  There are <a href="+more-details">more details</a>.
    ...   </div>
    ... </html>'''

    >>> print_feedback_messages(browser.contents)
    1 file has been deleted.
    Red Alert!  There are more details.


print_radio_button_field
------------------------

Prints out the radio buttons in an easy to understand way. The checked
radio button is indicated with (*), and unchecked with ( ).

    >>> print_radio_button_field = test.globs['print_radio_button_field']
    >>> contents = '''
    ... <label>
    ...   <input type="radio" name="field.foo" id="field.foo.1" value="ONE">
    ...   One
    ... </label>
    ... <label>
    ...   <input type="radio" name="field.foo" id="field.foo.1"
    ...          value="TWO" checked="checked">
    ...   Two
    ... </label>
    ... <label>
    ...   <input type="radio" name="field.foo" id="field.foo.1" value="THREE">
    ...   Three
    ... </label>
    ... '''
    >>> print_radio_button_field(contents, 'foo')
    ( ) One
    (*) Two
    ( ) Three

Sometimes the label isn't directly above the radio button.

    >>> contents = '''
    ... <table>
    ...   <tr>
    ...     <td rowspan="2"><input class="radioType" id="field.branch_type.0"
    ...       name="field.branch_type" type="radio" value="HOSTED" /></td>
    ...     <td><label for="field.branch_type.0">Hosted</label></td>
    ...   </tr>
    ...   <tr>
    ...     <td>Launchpad is the primary location of this branch.</td>
    ...   </tr>
    ...   <tr>
    ...     <td rowspan="2"><input class="radioType" checked="checked"
    ...       id="field.branch_type.1" name="field.branch_type" type="radio"
    ...       value="MIRRORED" /></td>
    ...     <td><label for="field.branch_type.1">Mirrored</label></td>
    ...   </tr>
    ...   <tr>
    ...     <td>Primarily hosted elsewhere and is periodically mirrored
    ...      from the remote location into Launchpad.</td>
    ...   </tr>
    ...   <tr>
    ...     <td rowspan="2"><input class="radioType" id="field.branch_type.2"
    ...       name="field.branch_type" type="radio" value="REMOTE" /></td>
    ...     <td><label for="field.branch_type.2">Remote</label></td>
    ...   </tr>
    ...   <tr>
    ...     <td>Registered in Launchpad with an external location,
    ...     but is not to be mirrored, nor available through Launchpad.</td>
    ...   </tr>
    ... </table>
    ... '''
    >>> print_radio_button_field(contents, 'branch_type')
    ( ) Hosted
    (*) Mirrored
    ( ) Remote

