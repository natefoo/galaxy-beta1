<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    is_new = repository.is_new
    can_browse_contents = not is_new
    can_browse_contents = not is_new
    can_rate = repository.user != trans.user
    can_manage = repository.user == trans.user
    can_view_change_log = not is_new
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>

<%inherit file="${inherit(context)}"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "jquery.rating", "dynatree_skin/ui.dynatree" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "ui.core", "jquery.cookie", "jquery.dynatree" )}
    ${common_javascripts(repository)}
    <script type="text/javascript">
    $( function() {
        $( "select[refresh_on_change='true']").change( function() {
            $( "#upload_form" ).submit();
        });
    });
    </script>
</%def>

%if message:
    ${render_msg( message, status )}
%endif

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        %if can_manage:
            <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ) )}">Manage repository</a>
        %else:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ) )}">View repository</a>
        %endif
        %if can_view_change_log:
            <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">View change log</a>
        %endif
        %if can_browse_contents:
            <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">Browse repository</a>
        %endif
    </div>
</ul>

<div class="toolForm">
    <div class="toolFormTitle">Upload a single file or a tarball</div>
    <div class="toolFormBody">
    ## TODO: nginx
    <form id="upload_form" name="upload_form" action="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ) )}" enctype="multipart/form-data" method="post">
    <div class="form-row">
        <label>File:</label>
        <div class="form-row-input">
            <input type="file" name="file_data"/>
        </div>
        <div style="clear: both"></div>
    </div>

    <div class="form-row">
        <%
            if uncompress_file:
                yes_selected = 'selected'
                no_selected = ''
            else:
                yes_selected = ''
                no_selected = 'selected'
        %>
        <label>Uncompress files?</label>
        <div class="form-row-input">
            <select name="uncompress_file">
                <option value="true" ${yes_selected}>Yes
                <option value="false" ${no_selected}>No
            </select>
        </div>
        <div class="toolParamHelp" style="clear: both;">
            Supported compression types are gz and bz2.  If <b>Yes</b> is selected, the uploaded file will be uncompressed.  However,
            if the uploaded file is an archive that contains compressed files, the contained files will not be uncompressed.  For
            example, if the uploaded compressed file is some_file.tar.gz, some_file.tar will be uncompressed and extracted, but if
            some_file.tar contains 4.bed.gz, the contained file 4.bed.gz will not be uncompressed.
        </div>
    </div>
    <div class="form-row">
        <label>Message:</label>
        <div class="form-row-input">
            %if commit_message:
                <textarea name="commit_message" rows="3" cols="35">${commit_message}</textarea>
            %else:
                <textarea name="commit_message" rows="3" cols="35"></textarea>
            %endif
        </div>
        <div class="toolParamHelp" style="clear: both;">
            This is the commit message for the mercurial change set that will be created by this upload
        </div>
        <div style="clear: both"></div>
    </div>
    %if not repository.is_new:
        <div class="form-row" >
            <label>Contents:</label>
            <div id="tree" >
                Loading...
            </div>
            <input type="hidden" id="upload_point" name="upload_point" value=""/>
            <div class="toolParamHelp" style="clear: both;">
                Select a location within the repository to upload your files by clicking a check box next to the location.  If a location is not selected, files will be uploaded to the repository root.
            </div>
            <div style="clear: both"></div>
        </div>
    %endif
    <div class="form-row">
        <input type="submit" class="primary-button" name="upload_button" value="Upload">
    </div>
    </form>
    </div>
</div>
