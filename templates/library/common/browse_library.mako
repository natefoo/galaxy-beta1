<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/library/common/library_item_info.mako" import="render_library_item_info" />
<%namespace file="/library/common/common.mako" import="render_actions_on_multiple_items" />
<% 
    from galaxy import util
    from galaxy.web.controllers.library_common import active_folders, active_folders_and_lddas, activatable_folders_and_lddas
    from time import strftime
%>

<%def name="title()">Browse data library</%def>
<%def name="stylesheets()">
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
    <link href="${h.url_for('/static/style/library.css')}" rel="stylesheet" type="text/css" />
</%def>

<%
    if cntrller in [ 'library', 'requests' ]:
        can_add = trans.app.security_agent.can_add_library_item( current_user_roles, library )
        if can_add:
            info_association, inherited = library.get_info_association()
        can_modify = trans.app.security_agent.can_modify_library_item( current_user_roles, library )
        can_manage = trans.app.security_agent.can_manage_library_item( current_user_roles, library )
    elif cntrller in [ 'library_admin', 'requests_admin' ]:
        info_association, inherited = library.get_info_association()

    tracked_datasets = {}

    class RowCounter( object ):
        def __init__( self ):
            self.count = 0
        def increment( self ):
            self.count += 1
        def __str__( self ):
            return str( self.count )
%>

<script type="text/javascript">
    $( document ).ready( function () {
        $("#library-grid").each( function() {
           // Recursively fill in children and descendents of each row
           var process_row = function( q, parents ) {
                // Find my index
                var index = $(q).parent().children().index( $(q) );
                // Find my immediate children
                var children = $(q).siblings().filter( "[parent='" + index + "']" );
                // Recursively handle them
                var descendents = children;
                children.each( function() {
                    child_descendents = process_row( $(this), parents.add( q ) );
                    descendents = descendents.add( child_descendents );
                });
                // Set up expand / hide link
                // HACK: assume descendents are invisible. The caller actually
                //       ensures this for the root node. However, if we start
                //       remembering folder states, we'll need something
                //       more sophisticated here.
                var visible = false;
                $(q).find( "span.expandLink").click( function() {
                    if ( visible ) {
                        descendents.hide();
                        descendents.removeClass( "expanded" );
                        q.removeClass( "expanded" );
                        visible = false;
                    } else {
                        children.show();
                        q.addClass( "expanded" );
                        visible = true;
                    }
                });
                // Check/uncheck boxes in subfolders.
                q.children( "td" ).children( "input[type=checkbox]" ).click( function() {
                    if ( $(this).is(":checked") ) {
                        descendents.find( "input[type=checkbox]").attr( 'checked', true );
                    } else {
                        descendents.find( "input[type=checkbox]").attr( 'checked', false );
                        // If you uncheck a lower level checkbox, uncheck the boxes above it
                        // (since deselecting a child means the parent is not fully selected any
                        // more).
                        parents.children( "td" ).children( "input[type=checkbox]" ).attr( "checked", false );
                    }
                });
                // return descendents for use by parent
                return descendents;
           }
           $(this).find( "tbody tr" ).not( "[parent]").each( function() {
                descendents = process_row( $(this), $([]) );
                descendents.hide();
           });
        });
    });
    function checkForm() {
        if ( $("select#action_on_datasets_select option:selected").text() == "delete" ) {
            if ( confirm( "Click OK to delete these datasets?" ) ) {
                return true;
            } else {
                return false;
            }
        }
    }
    // Looks for changes in dataset state using an async request. Keeps
    // calling itself (via setTimeout) until all datasets are in a terminal
    // state.
    var updater = function ( tracked_datasets ) {
        // Check if there are any items left to track
        var empty = true;
        for ( i in tracked_datasets ) {
            empty = false;
            break;
        }
        if ( ! empty ) {
            setTimeout( function() { updater_callback( tracked_datasets ) }, 3000 );
        }
    };
    var updater_callback = function ( tracked_datasets ) {
        // Build request data
        var ids = []
        var states = []
        $.each( tracked_datasets, function ( id, state ) {
            ids.push( id );
            states.push( state );
        });
        // Make ajax call
        $.ajax( {
            type: "POST",
            url: "${h.url_for( controller='library_common', action='library_item_updates' )}",
            dataType: "json",
            data: { ids: ids.join( "," ), states: states.join( "," ) },
            success : function ( data ) {
                $.each( data, function( id, val ) {
                    // Replace HTML
                    var cell = $("#libraryItem-" + id).find("#libraryItemInfo");
                    cell.html( val.html );
                    // If new state was terminal, stop tracking
                    if (( val.state == "ok") || ( val.state == "error") || ( val.state == "empty") || ( val.state == "deleted" ) || ( val.state == "discarded" )) {
                        delete tracked_datasets[ parseInt(id) ];
                    } else {
                        tracked_datasets[ parseInt(id) ] = val.state;
                    }
                });
                updater( tracked_datasets ); 
            },
            error: function() {
                // Just retry, like the old method, should try to be smarter
                updater( tracked_datasets );
            }
        });
    };
</script>

<%def name="render_dataset( cntrller, ldda, library_dataset, selected, library, folder, pad, parent, row_conter, show_deleted=False )">
    <%
        ## The received data must always be a LibraryDatasetDatasetAssociation object.  The object id passed to methods
        ## from the drop down menu should be the ldda id to prevent id collision ( which could happen when displaying
        ## children, which are always lddas ).  We also need to make sure we're displaying the latest version of this
        ## library_dataset, so we display the attributes from the ldda.
        if ldda.user:
            uploaded_by = ldda.user.email
        else:
            uploaded_by = 'anonymous'
        if ldda == library_dataset.library_dataset_dataset_association:
            current_version = True
            if cntrller in [ 'library', 'requests' ]:
                can_modify_library_dataset = trans.app.security_agent.can_modify_library_item( current_user_roles, library_dataset )
                can_manage_library_dataset = trans.app.security_agent.can_manage_library_item( current_user_roles, library_dataset )
        else:
            current_version = False
        if current_version and ldda.state not in ( 'ok', 'error', 'empty', 'deleted', 'discarded' ):
            tracked_datasets[ldda.id] = ldda.state
    %>
    %if current_version:
        <tr class="datasetRow"
        %if parent is not None:
            parent="${parent}"
            style="display: none;"
        %endif
        id="libraryItem-${ldda.id}">
            <td style="padding-left: ${pad+20}px;">
                %if selected:
                    <input type="checkbox" name="ldda_ids" value="${trans.security.encode_id( ldda.id )}" checked/>
                %else:
                    <input type="checkbox" name="ldda_ids" value="${trans.security.encode_id( ldda.id )}"/>
                %endif
                <a href="${h.url_for( controller='library_common', action='ldda_display_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), id=trans.security.encode_id( ldda.id ) )}"><b>${ldda.name[:50]}</b></a>
                <a id="dataset-${ldda.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                <div popupmenu="dataset-${ldda.id}-popup">
                    %if cntrller in [ 'library_admin', 'requests_admin' ] or can_modify_library_dataset:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_edit_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), id=trans.security.encode_id( ldda.id ) )}">Edit this dataset's information</a>
                    %else:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_display_info', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), id=trans.security.encode_id( ldda.id ) )}">View this dataset's information</a>
                    %endif
                    %if cntrller in [ 'library_admin', 'requests_admin' ] or can_manage_library_dataset:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='ldda_permissions', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), id=trans.security.encode_id( ldda.id ) )}">Edit this dataset's permissions</a>
                    %endif
                    %if cntrller in [ 'library_admin', 'requests_admin' ] or can_modify_library_dataset:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( folder.id ), replace_id=trans.security.encode_id( library_dataset.id ) )}">Upload a new version of this dataset</a>
                    %endif
                    %if ldda.has_data:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='act_on_multiple_datasets', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), ldda_ids=trans.security.encode_id( ldda.id ), do_action='add' )}">Import this dataset into your current history</a>
                        <a class="action-button" href="${h.url_for( controller='library_common', action='download_dataset_from_folder', cntrller=cntrller, id=trans.security.encode_id( ldda.id ), library_id=trans.security.encode_id( library.id ) )}">Download this dataset</a>
                    %endif
                    %if cntrller in [ 'library_admin', 'requests_admin' ]:
                        %if not library.deleted and not folder.deleted and not library_dataset.deleted:
                            <a class="action-button" confirm="Click OK to delete dataset '${ldda.name}'." href="${h.url_for( controller='library_admin', action='delete_library_item', library_id=trans.security.encode_id( library.id ), library_item_id=trans.security.encode_id( library_dataset.id ), library_item_type='library_dataset' )}">Delete this dataset</a>
                        %elif not library.deleted and not folder.deleted and library_dataset.deleted:
                            <a class="action-button" href="${h.url_for( controller='library_admin', action='undelete_library_item', library_id=trans.security.encode_id( library.id ), library_item_id=trans.security.encode_id( library_dataset.id ), library_item_type='library_dataset' )}">Undelete this dataset</a>
                        %endif
                    %endif
                </div>
            </td>
            <td id="libraryItemInfo">${render_library_item_info( ldda )}</td>
            <td>${uploaded_by}</td>
            <td>${ldda.create_time.strftime( "%Y-%m-%d" )}</td>
        </tr>
        <%
            my_row = row_counter.count
            row_counter.increment()
        %>
    %endif
</%def>

<%def name="render_folder( cntrller, folder, folder_pad, created_ldda_ids, library_id, hidden_folder_ids, show_deleted=False, parent=None, row_counter=None, root_folder=False )">
    <%
        if root_folder:
            pad = folder_pad
            expander = "/static/images/silk/resultset_bottom.png"
            folder_img = "/static/images/silk/folder_page.png"
        else:
            pad = folder_pad + 20
            expander = "/static/images/silk/resultset_next.png"
            folder_img = "/static/images/silk/folder.png"
        if created_ldda_ids:
            created_ldda_ids = util.listify( created_ldda_ids )
        if str( folder.id ) in hidden_folder_ids:
            return ""
        my_row = None
        if cntrller in [ 'library', 'requests' ]:
            can_access, folder_ids = trans.app.security_agent.check_folder_contents( trans.user, current_user_roles, folder )
            if not can_access:
                can_show, folder_ids = \
                    trans.app.security_agent.show_library_item( trans.user,
                                                                current_user_roles,
                                                                folder,
                                                                [ trans.app.security_agent.permitted_actions.LIBRARY_ADD,
                                                                  trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                                                                  trans.app.security_agent.permitted_actions.LIBRARY_MANAGE ] )
                if not can_show:
                    return ""
            can_add = trans.app.security_agent.can_add_library_item( current_user_roles, folder )
            if can_add:
                info_association, inherited = folder.get_info_association( restrict=True )
            can_modify = trans.app.security_agent.can_modify_library_item( current_user_roles, folder )
            can_manage = trans.app.security_agent.can_manage_library_item( current_user_roles, folder )
        elif cntrller in [ 'library_admin', 'requests_admin' ]:
            info_association, inherited = folder.get_info_association( restrict=True )
    %>
    %if not root_folder:
        <tr class="folderRow libraryOrFolderRow"
            %if parent is not None:
                parent="${parent}"
                style="display: none;"
            %endif
            >
            <td style="padding-left: ${folder_pad}px;">
                <span class="expandLink"></span>
                <input type="checkbox" class="folderCheckbox"/>
                <span class="rowIcon"></span>
                ${folder.name}
                %if folder.description:
                    <i>- ${folder.description}</i>
                %endif
                <a id="folder_img-${folder.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                <div popupmenu="folder_img-${folder.id}-popup">
                    %if cntrller in [ 'library_admin', 'requests_admin' ] or can_add:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=library_id, folder_id=trans.security.encode_id( folder.id ) )}">Add datasets to this folder</a>
                        <a class="action-button" href="${h.url_for( controller='library_common', action='create_folder', cntrller=cntrller, parent_id=trans.security.encode_id( folder.id ), library_id=library_id )}">Create a new sub-folder in this folder</a>
                    %endif
                    %if cntrller in [ 'library_admin', 'requests_admin' ] or can_modify:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='folder_info', cntrller=cntrller, id=trans.security.encode_id( folder.id ), library_id=library_id )}">Edit this folder's information</a>
                    %else:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='folder_info', cntrller=cntrller, id=trans.security.encode_id( folder.id ), library_id=library_id )}">View this folder's information</a>
                    %endif
                    %if ( cntrller in [ 'library_admin', 'requests_admin' ] or can_add ) and not info_association:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='info_template', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), response_action='folder_info', folder_id=trans.security.encode_id( folder.id ) )}">Add an information template to this folder</a>
                    %endif
                    %if cntrller in [ 'library_admin', 'requests_admin' ] or can_manage:
                        <a class="action-button" href="${h.url_for( controller='library_common', action='folder_permissions', cntrller=cntrller, id=trans.security.encode_id( folder.id ), library_id=library_id )}">Edit this folder's permissions</a>
                    %endif
                    %if cntrller in [ 'library_admin', 'requests_admin' ]:
                        %if not folder.deleted:
                            <a class="action-button" confirm="Click OK to delete the folder '${folder.name}.'" href="${h.url_for( controller='library_admin', action='delete_library_item', library_id=library_id, library_item_id=trans.security.encode_id( folder.id ), library_item_type='folder' )}">Delete this folder and its contents</a>
                        %elif folder.deleted and not folder.purged:
                            <a class="action-button" href="${h.url_for( controller='library_admin', action='undelete_library_item', library_id=library_id, library_item_id=trans.security.encode_id( folder.id ), library_item_type='folder' )}">Undelete this folder</a>
                        %endif
                    %endif
                </div>
            </div>
            <td colspan="3"></td>
        </tr>
        <%
            my_row = row_counter.count
            row_counter.increment()
        %>
    %endif
    %if cntrller == 'library':
        <% sub_folders = active_folders( trans, folder ) %>
        %for sub_folder in sub_folders:
            ${render_folder( cntrller, sub_folder, pad, created_ldda_ids, library_id, hidden_folder_ids, parent=my_row, row_counter=row_counter )}
        %endfor
        %for library_dataset in folder.active_library_datasets:
            <%
                ldda = library_dataset.library_dataset_dataset_association
                can_access = trans.app.security_agent.can_access_dataset( current_user_roles, ldda.dataset )
                selected = created_ldda_ids and str( ldda.id ) in created_ldda_ids
            %>
            %if can_access:
                ${render_dataset( cntrller, ldda, library_dataset, selected, library, folder, pad, my_row, row_counter )}
            %endif
        %endfor
    %elif cntrller == 'library_admin':
        %if show_deleted:
            <% sub_folders, lddas = activatable_folders_and_lddas( trans, folder ) %>
        %else:
            <% sub_folders, lddas = active_folders_and_lddas( trans, folder ) %>
        %endif
        %for sub_folder in sub_folders:
            ${render_folder( cntrller, sub_folder, pad, created_ldda_ids, library_id, [], parent=my_row, row_counter=row_counter, show_deleted=show_deleted )}
        %endfor 
        %for ldda in lddas:
            <%
                library_dataset = ldda.library_dataset
                selected = created_ldda_ids and str( ldda.id ) in created_ldda_ids
            %>
            ${render_dataset( cntrller, ldda, library_dataset, selected, library, folder, pad, my_row, row_counter, show_deleted=show_deleted )}
        %endfor
    %endif
</%def>

<h2>Data Library &ldquo;${library.name}&rdquo;</h2>

<ul class="manage-table-actions">
    %if not library.deleted and ( cntrller in [ 'library_admin', 'requests_admin' ] or can_add ):
        <li><a class="action-button" href="${h.url_for( controller='library_common', action='upload_library_dataset', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), folder_id=trans.security.encode_id( library.root_folder.id ) )}"><span>Add datasets</span></a></li>
        <li><a class="action-button" href="${h.url_for( controller='library_common', action='create_folder', cntrller=cntrller, parent_id=trans.security.encode_id( library.root_folder.id ), library_id=trans.security.encode_id( library.id ) )}">Add folder</a></li>
    %endif
</ul>

%if msg:
    ${render_msg( msg, messagetype )}
%endif

<form name="act_on_multiple_datasets" action="${h.url_for( controller='library_common', action='act_on_multiple_datasets', cntrller=cntrller, library_id=trans.security.encode_id( library.id ) )}" onSubmit="javascript:return checkForm();" method="post">
    <table cellspacing="0" cellpadding="0" border="0" width="100%" class="grid" id="library-grid">
        <thead>
            <tr class="libraryTitle">
                %if cntrller == 'library_admin' or can_add or can_modify or can_manage:
                    <th style="padding-left: 42px;">
                        ${library.name}
                        <a id="library-${library.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                        <div popupmenu="library-${library.id}-popup">
                            %if not library.deleted:
                                %if cntrller == 'library_admin' or can_modify:
                                    <a class="action-button" href="${h.url_for( controller='library_common', action='library_info', cntrller=cntrller, id=trans.security.encode_id( library.id ) )}">Edit information</a>
                                    ## Editing templates disabled until we determine optimal approach to re-linking library item to new version of form definition
                                    ##%if library.info_association:
                                    ##    <% form_id = library.info_association[0].template.id %>
                                    ##    <a class="action-button" href="${h.url_for( controller='forms', action='edit', form_id=form_id, show_form=True )}">Edit information template</a>
                                %endif
                                %if cntrller == 'library_admin' or can_add:
                                    %if not library.info_association:
                                        <a class="action-button" href="${h.url_for( controller='library_common', action='info_template', cntrller=cntrller, library_id=trans.security.encode_id( library.id ), response_action='browse_library' )}">Add template</a>
                                    %endif
                                %endif
                                %if cntrller == 'library_admin' or can_manage:
                                    <a class="action-button" href="${h.url_for( controller='library_common', action='library_permissions', cntrller=cntrller, id=trans.security.encode_id( library.id ) )}">Edit permissions</a>
                                %endif
                                %if cntrller == 'library_admin':
                                    <a class="action-button" confirm="Click OK to delete the library named '${library.name}'." href="${h.url_for( controller='library_admin', action='delete_library_item', library_id=trans.security.encode_id( library.id ), library_item_id=trans.security.encode_id( library.id ), library_item_type='library' )}">Delete this data library and its contents</a>
                                %endif
                                %if show_deleted:
                                    <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=False )}">Hide deleted items</a>
                                %else:
                                    <a class="action-button" href="${h.url_for( controller='library_common', action='browse_library', cntrller=cntrller, id=trans.security.encode_id( library.id ), show_deleted=True )}">Show deleted items</a>
                                %endif
                            %elif cntrller == 'library_admin' and not library.purged:
                                <a class="action-button" href="${h.url_for( controller='library_admin', action='undelete_library_item', library_id=trans.security.encode_id( library.id ), library_item_id=trans.security.encode_id( library.id ), library_item_type='library' )}">Undelete this data library</a>
                            %endif
                        </div>
                    </th>
                %else:
                    <th style="padding-left: 42px;">${library.name}</th>
                %endif
                <th>Information</th>
                <th>Uploaded By</th>
                <th>Date</th>
            </thead>
        </tr>
        <% row_counter = RowCounter() %>
        %if cntrller in [ 'library', 'requests' ]:
            ${render_folder( 'library', library.root_folder, 0, created_ldda_ids, trans.security.encode_id( library.id ), hidden_folder_ids, parent=None, row_counter=row_counter, root_folder=True )}
            %if not library.deleted:
                ${render_actions_on_multiple_items( 'library', default_action=default_action )}
            %endif
        %elif cntrller in [ 'library_admin', 'requests_admin' ]:
            ${render_folder( 'library_admin', library.root_folder, 0, created_ldda_ids, trans.security.encode_id( library.id ), [], parent=None, row_counter=row_counter, root_folder=True, show_deleted=show_deleted )}
            %if not library.deleted and not show_deleted:
                ${render_actions_on_multiple_items( 'library_admin' )}
            %endif
        %endif
    </table>
</form>

%if tracked_datasets:
    <script type="text/javascript">
        // Updater
        updater({${ ",".join( [ '"%s" : "%s"' % ( k, v ) for k, v in tracked_datasets.iteritems() ] ) }});
    </script>
    <!-- running: do not change this comment, used by TwillTestCase.library_wait -->
%endif

## Help about compression types

%if len( comptypes ) > 1:
    <div>
        <p class="infomark">
            TIP: Multiple compression options are available for downloading library datasets:
        </p>
        <ul style="padding-left: 1em; list-style-type: disc;">
            %if 'bz2' in comptypes:
                <li>bzip2: Compression takes the most time but is better for slower network connections (that transfer slower than the rate of compression) since the resulting file size is smallest.</li>
            %endif
            %if 'gz' in comptypes:
                <li>gzip: Compression is faster and yields a larger file, making it more suitable for fast network connections.</li>
            %endif
            %if 'zip' in comptypes:
                <li>ZIP: Not recommended but is provided as an option for those on Windows without WinZip (since WinZip can read .bz2 and .gz files).</li>
            %endif
        </ul>
    </div>
%endif
