Advanced structural subscriptions
---------------------------------

When a user visits the +subscriptions page of a product they are given the
option to subscribe to add a new subscription

    >>> from lp.services.webapp import canonical_url
    >>> from lp.testing.sampledata import USER_EMAIL
    >>> login(USER_EMAIL)
    >>> product = factory.makeProduct()
    >>> url = canonical_url(product, view_name='+subscriptions')
    >>> logout()
    >>> user_browser.open(url)
    >>> user_browser.getLink("Add a subscription")
    <Link text='Add a subscription' url='.../+subscriptions'>
