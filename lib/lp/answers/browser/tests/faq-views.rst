Answer Tracker FAQ Pages
========================

    >>> from lp.registry.interfaces.product import IProductSet

    >>> firefox = getUtility(IProductSet).getByName('firefox')
    >>> ignored = login_person(firefox.owner)
    >>> firefox_faq = firefox.newFAQ(
    ...     firefox.owner, 'A FAQ', 'FAQ for test purpose')


Latest FAQs portlet
-------------------

The latest FAQs portlet allows an `IFAQTarget` to show the latest FAQs.
It's view provided latest_faqs to get the FAQs to display.

    >>> from lp.testing.pages import (
    ...     extract_text, find_tag_by_id)

    >>> view = create_initialized_view(
    ...     firefox, '+portlet-listfaqs', principal=firefox.owner)
    >>> for faq in view.latest_faqs:
    ...     print(faq.title)
    A FAQ
    What's the keyboard shortcut for [random feature]?
    How do I install plugins (Shockwave, QuickTime, etc.)?
    How do I troubleshoot problems with extensions/themes?
    How do I install Extensions?

    >>> content = find_tag_by_id(view.render(), 'portlet-latest-faqs')
    >>> print(content.h2)
    <h2>...FAQs for Mozilla Firefox </h2>

    >>> print(extract_text(content.ul))
    A FAQ
    What's the keyboard shortcut for [random feature]?...

Each FAQ is linked.

    >>> print(content.find('a', {'class': 'sprite faq'}))
    <a class="..." href="http://answers.../firefox/+faq/...">A FAQ</a>

The portlet has a form to search FAQs. The view provides the action URL so
that the form works from any page.

    >>> print(view.portlet_action)
    http://answers.launchpad.test/firefox/+faqs

    >>> print(content.form['action'])
    http://answers.launchpad.test/firefox/+faqs

The portlet provides a link to create a FAQ when the user that has append
permission, such as the project owner.

    >>> print(content.find('a', {'class': 'menu-link-create_faq sprite add'}))
    <a class="..." href=".../firefox/+createfaq">Create a new FAQ</a>

Other users do not see the link.

    >>> user = factory.makePerson(name='a-user')
    >>> ignored = login_person(user)
    >>> view = create_initialized_view(
    ...     firefox, '+portlet-listfaqs', principal=user)
    >>> content = find_tag_by_id(view.render(), 'portlet-latest-faqs')
    >>> print(content.find('a', {'class': 'menu-link-create_faq sprite add'}))
    None
