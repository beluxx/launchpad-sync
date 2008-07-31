<?xml version="1.0" encoding="UTF-8"?>
<!--
  wadl-to-refhtml.xsl 

  Generate HTML documentation for a webservice described in a WADL file. 
  This is tailored to WADL generated by the LAZR web service framework.

  Based on wadl_documentaion.xsl from Mark Nottingham <mnot@yahoo-inc.com> 
  that can be found at http://www.mnot.net/webdesc/
  Copyright (c) 2006-2007 Yahoo! Inc.
  Copyright (c) 2008 Canonical Inc.

  This work is licensed under the Creative Commons Attribution-ShareAlike 2.5
  License. To view a copy of this license, visit
    http://creativecommons.org/licenses/by-sa/2.5/
  or send a letter to
    Creative Commons
    543 Howard Street, 5th Floor
    San Francisco, California, 94105, USA
-->

<xsl:stylesheet
 xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
 xmlns:wadl="http://research.sun.com/wadl/2006/10"
 xmlns:html="http://www.w3.org/1999/xhtml"
 xmlns:exsl="http://exslt.org/common"
 extension-element-prefixes="exsl"
 xmlns="http://www.w3.org/1999/xhtml"
 exclude-result-prefixes="xsl wadl html"
>
    <xsl:output
        method="xml"
        encoding="UTF-8"
        indent="yes"
        doctype-public="-//W3C//DTD XHTML 1.0 Transitional//EN"
        doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
    />


    <!-- Allow using key('id', 'people') to identify unique elements, since
    the document doesn't have a parsed DTD. 
    -->
    <xsl:key name="id" match="*[@id]" use="@id"/>

    <!-- main template -->
    <xsl:template name="css-stylesheet">
        <style type="text/css">
            body {
                font-family: sans-serif;
                font-size: 0.85em;
                margin: 2em 8em;
            }
            .methods {
                background-color: #eef;
                padding: 1em;
            }
            h1 {
                font-size: 2.5em;
            }
            h2 {
                border-bottom: 1px solid black;
                margin-top: 1em;
                margin-bottom: 0.5em;
                font-size: 2em;
               }
            h3 {
                color: orange;
                font-size: 1.75em;
                margin-top: 1.25em;
                margin-bottom: 0em;
            }
            h4 {
                margin: 0em;
                padding: 0em;
                border-bottom: 2px solid white;
            }
            h6 {
                font-size: 1.1em;
                color: #99a;
                margin: 0.5em 0em 0.25em 0em;
            }
            dd {
                margin-left: 1em;
            }
            tt {
                font-size: 1.2em;
            }
            table {
                margin-bottom: 0.5em;
            }
            th {
                text-align: left;
                font-weight: normal;
                color: black;
                border-bottom: 1px solid black;
                padding: 3px 6px;
            }
            td {
                padding: 3px 6px;
                vertical-align: top;
                background-color: f6f6ff;
                font-size: 0.85em;
            }
            td p {
                margin: 0px;
            }
            ul {
                padding-left: 1.75em;
            }
            p + ul, p + ol, p + dl {
                margin-top: 0em;
            }
            .optional {
                font-weight: normal;
                opacity: 0.75;
            }
        </style>
    </xsl:template>

    <xsl:template match="/wadl:application">
        <xsl:variable name="base">
            <!-- Contains the base URL for the webservice without a trailing
                 slash.  -->
            <xsl:variable name="uri" select="wadl:resources/@base"/>
            <xsl:choose>
                <xsl:when test="substring($uri, string-length($uri) , 1) = '/'">
                    <xsl:value-of
                        select="substring($uri, 1, string-length($uri) - 1)"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="$uri"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:variable name="title">
            <xsl:choose>
                <xsl:when test="wadl:doc[@title]">
                    <xsl:value-of select="wadl:doc[@title][1]/@title"/>
                </xsl:when>
                <xsl:otherwise>Launchpad Web Service API</xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <html>
            <head>
                <title><xsl:value-of select="$title" /></title>
                <xsl:call-template name="css-stylesheet"/>
            </head>
            <body>
                <h1><xsl:value-of select="$title" /></h1>
                <xsl:apply-templates select="wadl:doc"/>

                <xsl:call-template name="top-level-collections" />
                <xsl:call-template name="entry-types" />
            </body>
        </html>
    </xsl:template>

    <!-- Top level collections container -->
    <xsl:template name="top-level-collections">
        <div id="top-level-collections">
            <h2>Top-level collections</h2>

            <!-- 
                Top-level collections are found in the WADL by
                looking at the representation of the service-root resource
                and processing all the resource-type linked from it.
            -->
            <xsl:for-each
                select="key('id', 'service-root-json')/wadl:param/wadl:link">
                <xsl:sort select="../@name" />
                <xsl:variable name="collection_id" 
                    select="substring-after(@resource_type, '#')" />

                <xsl:apply-templates 
                    select="key('id', $collection_id)" 
                    mode="top-level-collections" />
            </xsl:for-each>
        </div>
    </xsl:template>


    <!-- Documentation for one top-level-collection -->
    <xsl:template match="wadl:resource_type" mode="top-level-collections">
        <div id="{@id}" class="top-level-collection">
            <h3><xsl:call-template name="get-title-or-id"/></h3>
            <xsl:apply-templates select="wadl:doc"/>

            <!-- All top-level colletions supports a GET without arguments
            iterating over all the resources. 
            The type of the resource is found by looking at the href attribute
            of the default representation. Link is in the form
            <resource>-page.
             -->
            <dl class="standard-methods">
                <h4>Standard method</h4>
                <xsl:variable name="default_get"
                    select="wadl:method[not(wadl:request)][1]" />
                <xsl:variable name="resource_type"
                    select="substring-after(
                        substring-before(
                            $default_get//wadl:representation[
                                not(@mediaType)]/@href, '-page'), 
                        '#')" />
                <dt>GET</dt>
                <dd>Response contains a <a href="#{$resource_type}"
                        ><xsl:call-template name="get-title-or-id">
                            <xsl:with-param name="element" 
                                select="key('id', $resource_type)" />
                         </xsl:call-template></a> 
                collection.</dd>
            </dl>

            <xsl:call-template name="custom-GETs" />
            <xsl:call-template name="custom-POSTs" />
        </div>
    </xsl:template>

    <!-- Documentation for the standard methods on an entry -->
    <xsl:template name="standard-methods">
        <dl class="standard-methods">
            <h4>Standard methods</h4>

            <!-- Standard methods are the ones without a ws.op param. -->
            <xsl:apply-templates 
                select="wadl:method[not(.//wadl:param[@name = 'ws.op'])]"
                mode="standard-method">
                <xsl:sort select="@name"/>
            </xsl:apply-templates>
        </dl>
    </xsl:template>

    <!-- Documentation for the standard GET on an entry -->
    <xsl:template match="wadl:method[@name='GET']" mode="standard-method">
        <dt><xsl:value-of select="@name" /></dt>
        <dd>Response contains the default 
            <xsl:call-template name="representation-type" /> representation 
            for this entry.
        </dd>
    </xsl:template>

    <!-- Documentation for the standard PUT on an entry -->
    <xsl:template match="wadl:method[@name='PUT']" mode="standard-method">
        <dt><xsl:value-of select="@name" /></dt>
        <dd>Entity body should contain a representation encoded using 
            <xsl:call-template name="representation-type" /> of the entry. 
            All fields of the default representation should be included. Only
            fields marked as writeable in the default representation should be
            modified.
        </dd>
    </xsl:template>

    <!-- Documentation for the standard PATCH on an entry -->
    <xsl:template match="wadl:method[@name='PATCH']" mode="standard-method">
        <dt><xsl:value-of select="@name" /></dt>
        <dd>Entity body should contain a represention encoded using 
            <xsl:call-template name="representation-type"/> of the entry
            fields to update. Any fields of the default representation marked
            as writeable can be included.
        </dd>
    </xsl:template>

    <!-- Documentation for the custom GET operations of the resource type -->
    <xsl:template name="custom-GETs">
        <xsl:variable name="operations" select="wadl:method[
                @name = 'GET'][.//wadl:param[@name = 'ws.op']]" />

        <xsl:if test="$operations">
            <div class="custom-GETs">
                <h4>Custom GET methods</h4>

                <xsl:apply-templates select="$operations">
                    <xsl:sort select=".//wadl:param[@name='ws.op']/@fixed"/>
                </xsl:apply-templates>
            </div>
        </xsl:if>
    </xsl:template>

    <!-- Documentation for the custom POST operations of the resource type -->
    <xsl:template name="custom-POSTs">
        <xsl:variable name="operations" select="wadl:method[
            @name = 'POST'][.//wadl:param[@name = 'ws.op']]" />

        <xsl:if test="$operations">
            <div class="custom-POSTs">
                <h4>Custom POST methods</h4>

                <xsl:apply-templates select="$operations">
                    <xsl:sort select=".//wadl:param[@name='ws.op']/@fixed"/>
                </xsl:apply-templates>
            </div>
        </xsl:if>
    </xsl:template>

    <!-- Container for all the entry types documentation -->
    <xsl:template name="entry-types">
        <h2 id="entry-types">Entry types</h2>

        <!-- Process all the resource_types, except the service-root ones,
          the type describing collections of that type,
          or any other ones, linked from within the service root.
          -->
        <xsl:for-each select="wadl:resource_type[
                @id != 'service-root' 
                and @id != 'HostedFile' 
                and not(contains(@id, 'page-resource'))
            ]">
            <xsl:sort select="@id" />
            <xsl:variable name="id" select="./@id"/>
            <xsl:variable name="top_level_collections" 
                select="key('id', 'service-root-json')//@resource_type[
                    substring-after(., '#') = $id]" />
            <xsl:if test="not($top_level_collections[contains(., $id)])">
                <xsl:apply-templates select="." mode="entry-types" />
            </xsl:if>
        </xsl:for-each>
    </xsl:template>

    <!-- Documentation for one entry-type -->
    <xsl:template match="wadl:resource_type" mode="entry-types">
        <h3 id="{@id}"><xsl:call-template name="get-title-or-id"/></h3>
        <xsl:apply-templates select="wadl:doc"/>

        <xsl:call-template name="default-representation" />
        <xsl:call-template name="standard-methods" />
        <xsl:call-template name="custom-GETs" />
        <xsl:call-template name="custom-POSTs" />
    </xsl:template>

    <!-- Documentation of the default representation for an entry -->
    <xsl:template name="default-representation">
        <xsl:variable name="default_get" select="wadl:method[
            @name = 'GET' and not(wadl:request)]" />
        <xsl:variable name="representation" select="key(
                'id', substring-after(
                    $default_get/wadl:response/wadl:representation[
                        not(@mediaType)]/@href, '#'))"/>

        <div class="representation">
            <h4>Default representation 
                (<xsl:value-of select="$representation/@mediaType"/>)</h4>

            <table>
                <th>Key</th>
                <th>Value</th>
                <th>Description</th>
                <xsl:apply-templates select="$representation/wadl:param"
                    mode="representation">
                    <xsl:sort select="@name"/>
                </xsl:apply-templates>
            </table>
        </div>
    </xsl:template>

    <!-- Row describing one field in the default representation -->
    <xsl:template match="wadl:param" mode="representation">
        <xsl:variable name="resource_type"
            select="substring-before(../@id, '-')" />
        <xsl:variable name="patch_representation_id"
            ><xsl:value-of select="$resource_type"/>-diff</xsl:variable>
        <xsl:variable name="patch_representation"
            select="key('id', $patch_representation_id)"/>
        <tr>
            <td>
                <p><strong><xsl:value-of select="@name"/></strong></p>
            </td>
            <td>
                <p>
                    <xsl:choose>
                        <xsl:when test="$patch_representation/wadl:param[@name
                            = current()/@name]">
                            <small>(writeable)</small>
                        </xsl:when>
                        <xsl:otherwise>
                            <small>(read-only)</small>
                        </xsl:otherwise>
                    </xsl:choose>
                </p>
                <xsl:choose>
                    <xsl:when test="wadl:option">
                        <p><em>One of:</em></p>
                        <ul>
                            <xsl:apply-templates select="wadl:option"/>
                        </ul>
                    </xsl:when>
                    <xsl:when test="wadl:link[@resource_type]">
                        <xsl:apply-templates select="wadl:link" 
                            mode="representation" />
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:if test="@default">
                            <p>
                                Default:
                                <var><xsl:value-of select="@default"/></var>
                            </p>
                        </xsl:if>
                        <xsl:if test="@fixed">
                            <p>
                                Fixed:
                                <var><xsl:value-of select="@fixed"/></var>
                            </p>
                        </xsl:if>
                    </xsl:otherwise>
                </xsl:choose>
            </td>
            <td>
                <xsl:apply-templates select="wadl:doc"/>
                <xsl:if test="wadl:option[wadl:doc]">
                    <dl>
                        <xsl:apply-templates
                            select="wadl:option" mode="option-doc"/>
                    </dl>
                </xsl:if>
            </td>
        </tr>
    </xsl:template>

    <!-- Output the description of a link type in param listing -->
    <xsl:template match="wadl:link[
        @resource_type and ../@name != 'self_link']" 
        mode="representation">
        <xsl:variable name="resource_type"
            select="substring-after(@resource_type, '#')"/>
        <xsl:choose>
            <xsl:when test="contains($resource_type, 'page-resource')">
                Link to a <a href="#{substring-before($resource_type, '-')}"
                    ><xsl:value-of 
                        select="substring-before($resource_type, '-')"
                        /></a> collection.
            </xsl:when>
            <xsl:when test="$resource_type = 'HostedFile'">
                Link to a file resource.
            </xsl:when>
            <xsl:otherwise>
                Link to a <a href="#{$resource_type}"
                    ><xsl:value-of select="$resource_type"/></a>.
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="wadl:method">
        <xsl:variable name="id"
            ><xsl:call-template name="get-id"/></xsl:variable>
        <div class="method">
            <h4 id="{@id}"><xsl:value-of select="@name"/></h4>
            <xsl:choose>
                <xsl:when test="wadl:doc|wadl:request|wadl:response">
                    <xsl:apply-templates select="wadl:doc"/>
                    <xsl:apply-templates select="wadl:request"/>
                    <xsl:apply-templates select="wadl:response"/>
                </xsl:when>
                <xsl:otherwise>
                    <p><em>Missing documentation.</em></p>
                </xsl:otherwise>
            </xsl:choose>
        </div>
    </xsl:template>

    <xsl:template match="wadl:request">
        <xsl:apply-templates select="." mode="param-group">
            <xsl:with-param name="prefix">request</xsl:with-param>
            <xsl:with-param name="style">query</xsl:with-param>
        </xsl:apply-templates>
        <xsl:apply-templates select="." mode="param-group">
            <xsl:with-param name="prefix">request</xsl:with-param>
            <xsl:with-param name="style">header</xsl:with-param>
        </xsl:apply-templates>
        <xsl:if test="wadl:representation[@href]">
            <p>
                <em>acceptable request representations:</em>
            </p>
            <ul>
                <xsl:apply-templates
                    select="wadl:representation"/>
            </ul>
        </xsl:if>
    </xsl:template>

    <xsl:template match="wadl:response">
        <xsl:apply-templates select="." mode="param-group">
            <xsl:with-param name="prefix">response</xsl:with-param>
            <xsl:with-param name="style">header</xsl:with-param>
        </xsl:apply-templates>
        <xsl:if test="wadl:representation">
            <p>
                <em>available response representations:</em>
            </p>
            <ul>
                <xsl:apply-templates
                    select="wadl:representation[not(@mediaType)]"/>
            </ul>
        </xsl:if>
        <xsl:if test="wadl:fault">
            <p><em>potential faults:</em></p>
            <ul>
                <xsl:apply-templates select="wadl:fault"/>
            </ul>
        </xsl:if>
    </xsl:template>

    <xsl:template match="wadl:representation|wadl:fault">
        <xsl:variable name="id">
            <xsl:choose>
                <xsl:when test="@id">
                    <xsl:value-of
                        select="@id"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of
                        select="substring-after(@href, '#')"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <li>
            <a href="#{$id}">
                <xsl:value-of select="$id"/>
                <xsl:if test="@mediaType">
                (<xsl:value-of select="@mediaType"/>)
                </xsl:if>
            </a>
        </li>
    </xsl:template>

    <xsl:template match="wadl:representation|wadl:fault" mode="list">
        <xsl:variable name="id"
            ><xsl:call-template name="get-id"/></xsl:variable>
        <xsl:variable name="href" select="@id"/>
        <xsl:choose>
            <xsl:when test="preceding::wadl:*[@id=$href]"/>
            <xsl:otherwise>
                <h3 id="{$id}">
                    <xsl:value-of select="@id"/> (<xsl:value-of select="@mediaType"/>)
                </h3>
                <xsl:if test="not(wadl:param)">
                    <p><em>Missing documentation.</em></p>
                </xsl:if>
                <xsl:apply-templates select="wadl:doc"/>
                <xsl:if test="wadl:param">
                    <div class="representation">
                        <xsl:apply-templates select="." mode="param-group">
                            <xsl:with-param name="style">plain</xsl:with-param>
                        </xsl:apply-templates>
                        <xsl:apply-templates select="." mode="param-group">
                            <xsl:with-param name="style">header</xsl:with-param>
                        </xsl:apply-templates>
                    </div>
                </xsl:if>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="wadl:*" mode="param-group">
        <xsl:param name="style"/>
        <xsl:param name="prefix"></xsl:param>
        <xsl:if test=".//wadl:param[@style=$style]">
        <h6>
            <xsl:value-of select="$prefix"/>
            <xsl:text> </xsl:text><xsl:value-of select="$style"/> parameters
        </h6>
        <table>
            <tr>
                <th>parameter</th>
                <th>value</th>
                <th>description</th>
           </tr>
            <xsl:apply-templates
                select=".//wadl:param[@style=$style]"/>
        </table>
        </xsl:if>
    </xsl:template>

    <xsl:template match="wadl:param">
        <tr>
            <td>
                <p><strong><xsl:value-of select="@name"/></strong></p>
            </td>
            <td>
                <p>
                    <xsl:if test="@required='true'">
                        <small>(required)</small>
                    </xsl:if>
                    <xsl:if test="@repeating='true'">
                        <small>(repeating)</small>
                    </xsl:if>
                </p>
                <xsl:choose>
                    <xsl:when test="wadl:option">
                        <p><em>One of:</em></p>
                        <ul>
                            <xsl:apply-templates select="wadl:option"/>
                        </ul>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:if test="@default">
                            <p>
                                Default:
                                <tt><xsl:value-of select="@default"/></tt>
                            </p>
                        </xsl:if>
                        <xsl:if test="@fixed">
                            <p>
                                Fixed:
                                <tt><xsl:value-of select="@fixed"/></tt>
                            </p>
                        </xsl:if>
                    </xsl:otherwise>
                </xsl:choose>
            </td>
            <td>
                <xsl:apply-templates select="wadl:doc"/>
                <xsl:if test="wadl:option[wadl:doc]">
                    <dl>
                        <xsl:apply-templates
                            select="wadl:option" mode="option-doc"/>
                    </dl>
                </xsl:if>
                <xsl:if test="@path">
                    <ul>
                        <li>
                            XPath to value:
                            <tt><xsl:value-of select="@path"/></tt>
                        </li>
                        <xsl:apply-templates select="wadl:link"/>
                    </ul>
                </xsl:if>
            </td>
        </tr>
    </xsl:template>

    <xsl:template match="wadl:link">
        <li>
            Link:
            <a href="#{@resource_type}"><xsl:value-of select="@rel"/></a>
        </li>
    </xsl:template>

    <xsl:template match="wadl:option">
        <li>
            <tt><xsl:value-of select="@value"/></tt>
            <xsl:if test="ancestor::wadl:param[1]/@default=@value">
                <small>(default)</small>
            </xsl:if>
        </li>
    </xsl:template>

    <xsl:template match="wadl:option" mode="option-doc">
            <dt>
                <tt><xsl:value-of select="@value"/></tt>
                <xsl:if test="ancestor::wadl:param[1]/@default=@value">
                    <small>(default)</small>
                </xsl:if>
            </dt>
            <dd>
                <xsl:apply-templates select="wadl:doc"/>
            </dd>
    </xsl:template>

    <xsl:template match="wadl:doc">
        <xsl:param name="inline">0</xsl:param>
        <!-- skip WADL elements -->
        <xsl:choose>
            <xsl:when test="node()[1]=text() and $inline=0">
                <p>
                    <xsl:apply-templates select="node()" mode="copy"/>
                </p>
            </xsl:when>
            <xsl:otherwise>
                <xsl:apply-templates select="node()" mode="copy"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- utilities -->

    <xsl:template name="get-id">
        <xsl:choose>
            <xsl:when test="@id">
                <xsl:value-of select="@id"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="generate-id()"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>


    <!-- Returns the title or id of an element.

    Look for the first wadl:doc title attribute content of the
    current node or fall back to the element id. 

    :param element: The element to return the title or id. Defaults to the
        current node.
    -->
    <xsl:template name="get-title-or-id">
        <xsl:param name="element" select="current()" />
        <xsl:choose>
            <xsl:when test="$element/wadl:doc[@title]">
                <xsl:value-of select="$element/wadl:doc[@title][1]/@title"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$element/@id"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- Output the mediaType attribute of the default representation.

    Should be call on an element that contain a wadl:representation element
    without a mediaType attribute.
    -->
    <xsl:template name="representation-type">
        <xsl:variable name="representation" 
            select="key('id',
                        substring-after(
                            .//wadl:representation[not(@mediaType)]/@href, 
                            '#'))" />
        <code><xsl:value-of select="$representation/@mediaType"/></code>
    </xsl:template>

</xsl:stylesheet>
