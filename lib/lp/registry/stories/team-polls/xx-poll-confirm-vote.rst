  Logged in as 'jdub' (which voted in the director-2004 poll), let's see the
  results of the director-2004 poll.

    >>> import base64
    >>> jdub_auth = base64.b64encode(
    ...     b"jeff.waugh@ubuntulinux.com:test"
    ... ).decode("ASCII")
    >>> print(
    ...     http(
    ...         r"""
    ... GET /~ubuntu-team/+poll/director-2004 HTTP/1.1
    ... Authorization: Basic %s
    ... """
    ...         % jdub_auth
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...
    ...2004 Director's Elections...
    ...
    ...This was a secret poll: your vote is identified only by the key...
    ...you were given when you voted. To view your vote you must enter...
    ...your key:...
    ...Results...
    ...This is the pairwise matrix for this poll...
    ...


  Now let's see if jdub's vote was stored correctly, by entering the token he
  got when voting.

    >>> print(
    ...     http(
    ...         r"""
    ... POST /~ubuntu-team/+poll/director-2004 HTTP/1.1
    ... Authorization: Basic %s
    ... Referer: https://launchpad.test/
    ... Content-Type: application/x-www-form-urlencoded
    ...
    ... token=9WjxQq2V9p&showvote=Show+My+Vote"""
    ...         % jdub_auth
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...
                  <p>Your vote was as follows:</p>
                  <p>
    <BLANKLINE>
                      <b>1</b>.
                      D
    <BLANKLINE>
                  </p>
                  <p>
    <BLANKLINE>
                      <b>2</b>.
                      B
    <BLANKLINE>
                  </p>
                  <p>
    <BLANKLINE>
                      <b>3</b>.
                      A
    <BLANKLINE>
                  </p>
                  <p>
    <BLANKLINE>
                      <b>3</b>.
                      C
    <BLANKLINE>
                  </p>
    ...


  Now we'll see the results of the leader-2004 poll, in which jdub also
  voted.

    >>> print(
    ...     http(
    ...         r"""
    ... GET /~ubuntu-team/+poll/leader-2004 HTTP/1.1
    ... Authorization: Basic %s
    ... """
    ...         % jdub_auth
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...
    ...2004 Leader's Elections...
    ...
    ...This was a secret poll: your vote is identified only by the key...
    ...you were given when you voted. To view your vote you must enter...
    ...your key:...
    ...


  And now we confirm his vote on this poll too.

    >>> print(
    ...     http(
    ...         r"""
    ... POST /~ubuntu-team/+poll/leader-2004 HTTP/1.1
    ... Authorization: Basic %s
    ... Referer: https://launchpad.test/
    ... Content-Type: application/x-www-form-urlencoded
    ...
    ... token=W7gR5mjNrX&showvote=Show+My+Vote"""
    ...         % jdub_auth
    ...     )
    ... )
    HTTP/1.1 200 Ok
    ...
                <p>Your vote was for
    <BLANKLINE>
                  <b>Jack Crawford</b></p>
    ...
