The CheckBox Matrix Widget
==========================

A custom widget to display checkboxes in multiple columns.

    >>> from lp.app.widgets.itemswidgets import CheckBoxMatrixWidget

This widget is created to allow many options to be displayed in a single
page.

    >>> from lp.services.beautifulsoup import BeautifulSoup
    >>> from lp.services.webapp.servers import LaunchpadTestRequest
    >>> from lp.registry.interfaces.product import (
    ...     IProduct,
    ...     IProductSet,
    ...     License,
    ...     )
    >>> product = getUtility(IProductSet).get(1)
    >>> licenses_field = IProduct['licenses'].bind(product)
    >>> vtype = licenses_field.value_type
    >>> request = LaunchpadTestRequest()
    >>> matrix_widget = CheckBoxMatrixWidget(licenses_field, vtype, request)

Since we didn't provided a value in the request, the form value will be
empty:

    >>> matrix_widget._getFormValue()
    []

If we pass in a value via the request, we'll be able to get the licences
as a set from _getFormValue() or getInputValue():

    >>> request = LaunchpadTestRequest(
    ...     form={'field.licenses': ['GNU_LGPL_V2_1', 'GNU_GPL_V2']})
    >>> matrix_widget = CheckBoxMatrixWidget(licenses_field, vtype, request)
    >>> for item in sorted(matrix_widget._getFormValue()):
    ...     print(repr(item))
    <...License.GNU_GPL_V2...>
    <...License.GNU_LGPL_V2_1...>
    >>> for item in sorted(matrix_widget.getInputValue()):
    ...     print(repr(item))
    <...License.GNU_GPL_V2...>
    <...License.GNU_LGPL_V2_1...>

It should render as many rows as are specified by the column_count attribute.

    >>> import math
    >>> matrix_widget.column_count = 4
    >>> all_licenses = [token.value for token in License]
    >>> html = matrix_widget.renderValue(all_licenses)
    >>> soup = BeautifulSoup(html)
    >>> row_count = math.ceil(
    ...     len(License) / float(matrix_widget.column_count))
    >>> len(soup.table('tr')) == row_count
    True
    >>> len(soup.table.tr('td'))
    4

All the checkboxes should be checked since we passed in all the licences
to renderValue().

    >>> u'checked' in dict(soup.table.tr.td.input.attrs)
    True


All the checkboxes should be unchecked if we pass in zero licences
to renderValue().

    >>> html = matrix_widget.renderValue([])
    >>> soup = BeautifulSoup(html)
    >>> u'checked' in dict(soup.table.tr.td.input.attrs)
    False
