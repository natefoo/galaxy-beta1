import urllib2
from galaxy.web.controllers.admin import *
from galaxy.util.json import from_json_string, to_json_string
from galaxy.util.shed_util import *
from galaxy.tool_shed.tool_dependencies.install_util import get_tool_dependency_install_dir
from galaxy.tool_shed.encoding_util import *
from galaxy import eggs, tools

eggs.require( 'mercurial' )
from mercurial import hg

log = logging.getLogger( __name__ )

MAX_CONTENT_SIZE = 32768

class RepositoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            if tool_shed_repository.update_available:
                return '<div class="count-box state-color-error">%s</div>' % tool_shed_repository.name
            return tool_shed_repository.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.description
    class OwnerColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.owner
    class RevisionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.changeset_revision
    class ToolShedColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.tool_shed
    # Grid definition
    title = "Installed tool shed repositories"
    model_class = model.ToolShedRepository
    template='/admin/tool_shed_repository/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="manage_repository", id=item.id, webapp="galaxy" ) ),
                    attach_popup=True ),
        DescriptionColumn( "Description" ),
        OwnerColumn( "Owner" ),
        RevisionColumn( "Revision" ),
        ToolShedColumn( "Tool shed" ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = []
    operations = [ grids.GridOperation( "Get updates",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ),
                   grids.GridOperation( "Deactivate or uninstall",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ),
                   grids.GridOperation( "Activate or reinstall",
                                        allow_multiple=False,
                                        condition=( lambda item: item.deleted ),
                                        async_compatible=False ) ]
    standard_filters = []
    default_filter = dict( deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class )

class ToolDependencyGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_dependency ):
            return tool_dependency.name
    class VersionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_dependency ):
            return tool_dependency.version
    class TypeColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_dependency ):
            return tool_dependency.type
    class StatusColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_dependency ):
            if tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLING ]:
                return tool_dependency.status
            else:
                if tool_dependency.status in [ trans.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                               trans.model.ToolDependency.installation_status.UNINSTALLED ]:
                    bgcolor = trans.model.ToolDependency.states.UNINSTALLED
                elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.ERROR ]:
                    bgcolor = trans.model.ToolDependency.states.ERROR
                elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLED ]:
                    bgcolor = trans.model.ToolDependency.states.OK
                rval = '<div class="count-box state-color-%s" id="ToolDependencyStatus-%s">' % ( bgcolor, trans.security.encode_id( tool_dependency.id ) )
                rval += '%s</div>' % tool_dependency.status
                return rval

    webapp = "galaxy"
    title = "Tool Dependencies"
    template = "admin/tool_shed_repository/tool_dependencies_grid.mako"
    model_class = model.ToolDependency
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = False
    columns = [
        NameColumn( "Name",
                    link=( lambda item: iff( item.status in \
                                             [ model.ToolDependency.installation_status.NEVER_INSTALLED,
                                               model.ToolDependency.installation_status.INSTALLING,
                                               model.ToolDependency.installation_status.UNINSTALLED ], \
                                             None, dict( action="manage_tool_dependencies", operation='browse', id=item.id ) ) ),
                    filterable="advanced" ),
        VersionColumn( "Version",
                       filterable="advanced" ),
        TypeColumn( "Type",
                    filterable="advanced" ),
        StatusColumn( "Installation Status",
                      filterable="advanced" ),
    ]
    operations = [
        grids.GridOperation( "Install",
                             allow_multiple=True,
                             condition=( lambda item: item.status in [ model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                                       model.ToolDependency.installation_status.UNINSTALLED ] ) ),
        grids.GridOperation( "Uninstall",
                             allow_multiple=True,
                             allow_popup=False,
                             condition=( lambda item: item.status in [ model.ToolDependency.installation_status.INSTALLED,
                                                                       model.ToolDependency.installation_status.ERROR ] ) )
    ]
    def build_initial_query( self, trans, **kwd ):
        tool_dependency_ids = kwd.get( 'tool_dependency_ids', None )
        if tool_dependency_ids:
            clause_list = []
            for tool_dependency_id in tool_dependency_ids:
                clause_list.append( self.model_class.table.c.id == trans.security.decode_id( tool_dependency_id ) )
            return trans.sa_session.query( self.model_class ) \
                                   .filter( or_( *clause_list ) )
        return trans.sa_session.query( self.model_class )
    def apply_query_filter( self, trans, query, **kwd ):
        tool_dependency_id = kwd.get( 'tool_dependency_id', None )
        if not tool_dependency_id:
            return query
        return query.filter_by( tool_dependency_id=trans.security.decode_id( tool_dependency_id ) )

class AdminToolshed( AdminGalaxy ):
    
    repository_list_grid = RepositoryListGrid()
    tool_dependency_grid = ToolDependencyGrid()

    @web.expose
    @web.require_admin
    def activate_repository( self, trans, **kwd ):
        """Activate a repository that was deactivated but not uninstalled."""
        repository = get_repository( trans, kwd[ 'id' ] )
        shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repository_clone_url = self.__generate_clone_url( trans, repository )
        repository.deleted = False
        trans.sa_session.add( repository )
        trans.sa_session.flush()
        if repository.includes_tools:
            metadata = repository.metadata
            repository_tools_tups = get_repository_tools_tups( trans.app, metadata )
            # Reload tools into the appropriate tool panel section.
            tool_panel_dict = repository.metadata[ 'tool_panel_section' ]
            add_to_tool_panel( trans.app,
                               repository.name,
                               repository_clone_url,
                               repository.changeset_revision,
                               repository_tools_tups,
                               repository.owner,
                               shed_tool_conf,
                               tool_panel_dict,
                               new_install=False )
        message = 'The <b>%s</b> repository has been activated.' % repository.name
        status = 'done'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='browse_repositories',
                                                          message=message,
                                                          status=status ) )
    @web.expose
    @web.require_admin
    def browse_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, kwd[ 'id' ] )
        return trans.fill_template( '/admin/tool_shed_repository/browse_repository.mako',
                                    repository=repository,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def browse_repositories( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd.pop( 'operation' ).lower()
            if operation == "manage_repository":
                return self.manage_repository( trans, **kwd )
            if operation == "get updates":
                return self.check_for_updates( trans, **kwd )
            if operation == "activate or reinstall":
                repository = get_repository( trans, kwd[ 'id' ] )
                if repository.uninstalled:
                    if repository.includes_tools:
                        # Only allow selecting a different section in the tool panel if the repository was uninstalled.
                        return self.reselect_tool_panel_section( trans, **kwd )
                    else:
                        return self.reinstall_repository( trans, **kwd )
                else:
                    return self.activate_repository( trans, **kwd )
            if operation == "deactivate or uninstall":
                return self.deactivate_or_uninstall_repository( trans, **kwd )
        if 'message' not in kwd or not kwd[ 'message' ]:
            kwd[ 'message' ] = 'Names of repositories for which updates are available are highlighted in red.'
        return self.repository_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def browse_tool_dependency( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_dependency = get_tool_dependency( trans, kwd[ 'id' ] )
        return trans.fill_template( '/admin/tool_shed_repository/browse_tool_dependency.mako',
                                    repository=tool_dependency.tool_shed_repository,
                                    tool_dependency=tool_dependency,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def browse_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = '%srepository/browse_valid_repositories?galaxy_url=%s&webapp=galaxy&no_reset=true' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def browse_tool_sheds( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/galaxy/admin/tool_sheds.mako',
                                    webapp='galaxy',
                                    message=message,
                                    status='error' )
    @web.expose
    @web.require_admin
    def check_for_updates( self, trans, **kwd ):
        # Send a request to the relevant tool shed to see if there are any updates.
        repository = get_repository( trans, kwd[ 'id' ] )
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        url = '%s/repository/check_for_updates?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s&webapp=galaxy&no_reset=true' % \
            ( tool_shed_url, url_for( '/', qualified=True ), repository.name, repository.owner, repository.changeset_revision )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def confirm_tool_dependency_install( self, trans, **kwd ):
        """Display a page enabling the Galaxy administrator to choose to install tool dependencies for a tool shed repository they are installing."""
        # This method is called from the tool shed (never Galaxy) when a tool shed repository that includes a file named tool_dependencies.xml
        # is being installed into a local Galaxy instance.
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        tool_shed_url = kwd[ 'tool_shed_url' ]
        repo_info_dict = kwd[ 'repo_info_dict' ]
        includes_tools = util.string_as_bool( kwd.get( 'includes_tools', False ) )
        # Decode the encoded repo_info_dict param value.
        dict_with_tool_dependencies = tool_shed_decode( repo_info_dict )
        # The repo_info_dict includes tool dependencies which we need to display so the user knows what will be installed.
        new_repo_info_dict = {}
        for name, repo_info_tuple in dict_with_tool_dependencies.items():
            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, tool_dependencies = repo_info_tuple
            # Create a new repo_info_dict by eliminating tool-dependencies from the repo_info_tuple.
            new_repo_info_dict[ name ] = ( description, repository_clone_url, changeset_revision, ctx_rev )
        repo_info_dict = tool_shed_encode( new_repo_info_dict )
        install_tool_dependencies_check_box = CheckboxField( 'install_tool_dependencies', checked=True )
        return trans.fill_template( '/admin/tool_shed_repository/confirm_tool_dependency_install.mako',
                                    tool_shed_url=tool_shed_url,
                                    repo_info_dict=repo_info_dict,
                                    dict_with_tool_dependencies=dict_with_tool_dependencies,
                                    includes_tools=includes_tools,
                                    install_tool_dependencies_check_box=install_tool_dependencies_check_box,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def deactivate_or_uninstall_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        remove_from_disk = params.get( 'remove_from_disk', '' )
        remove_from_disk_checked = CheckboxField.is_checked( remove_from_disk )
        repository = get_repository( trans, kwd[ 'id' ] )
        shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repository_install_dir = os.path.abspath ( relative_install_dir )
        errors = ''
        if params.get( 'deactivate_or_uninstall_repository_button', False ):
            if repository.includes_tools:
                # Handle tool panel alterations.
                remove_from_tool_panel( trans, repository, shed_tool_conf, uninstall=remove_from_disk_checked )
            if repository.includes_datatypes:
                # Deactivate proprietary datatypes.
                installed_repository_dict = load_installed_datatypes( trans.app, repository, repository_install_dir, deactivate=True )
                if installed_repository_dict[ 'converter_path' ]:
                    load_installed_datatype_converters( trans.app, installed_repository_dict, deactivate=True )
                if installed_repository_dict[ 'display_path' ]:
                    load_installed_display_applications( installed_repository_dict, deactivate=True )
            if remove_from_disk_checked:
                try:
                    # Remove the repository from disk.
                    shutil.rmtree( repository_install_dir )
                    log.debug( "Removed repository installation directory: %s" % str( repository_install_dir ) )
                    removed = True
                except Exception, e:
                    log.debug( "Error removing repository installation directory %s: %s" % ( str( repository_install_dir ), str( e ) ) )
                    removed = False
                if removed:
                    repository.uninstalled = True
                    # Remove all installed tool dependencies.
                    for tool_dependency in repository.installed_tool_dependencies:
                        uninstalled, error_message = remove_tool_dependency( trans, tool_dependency )
                        if error_message:
                            errors = '%s  %s' % ( errors, error_message )
            repository.deleted = True
            trans.sa_session.add( repository )
            trans.sa_session.flush()
            if remove_from_disk_checked:
                message = 'The repository named <b>%s</b> has been uninstalled.  ' % repository.name
                if errors:
                    message += 'Attempting to uninstall tool dependencies resulted in errors: %s' % errors
                    status = 'error'
                else:
                    status = 'done'
            else:
                message = 'The repository named <b>%s</b> has been deactivated.  ' % repository.name
                status = 'done'
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='browse_repositories',
                                                              message=message,
                                                              status=status ) )
        remove_from_disk_check_box = CheckboxField( 'remove_from_disk', checked=remove_from_disk_checked )
        return trans.fill_template( '/admin/tool_shed_repository/deactivate_or_uninstall_repository.mako',
                                    repository=repository,
                                    remove_from_disk_check_box=remove_from_disk_check_box,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def find_tools_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = '%srepository/find_tools?galaxy_url=%s&webapp=galaxy&no_reset=true' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def find_workflows_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = '%srepository/find_workflows?galaxy_url=%s&webapp=galaxy&no_reset=true' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.json
    @web.require_admin
    def get_file_contents( self, trans, file_path ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        return get_repository_file_contents( file_path )
    @web.expose
    @web.require_admin
    def initiate_tool_dependency_installation( self, trans, tool_dependencies ):
        """Install specified dependencies for repository tools."""
        # Get the tool_shed_repository from one of the tool_dependencies.
        message = ''
        tool_shed_repository = tool_dependencies[ 0 ].tool_shed_repository
        work_dir = make_tmp_directory()
        # Get the tool_dependencies.xml file from the repository.
        tool_dependencies_config = get_config_from_repository( trans.app,
                                                               'tool_dependencies.xml',
                                                               tool_shed_repository,
                                                               tool_shed_repository.changeset_revision,
                                                               work_dir )
        installed_tool_dependencies = handle_tool_dependencies( app=trans.app,
                                                                tool_shed_repository=tool_shed_repository,
                                                                tool_dependencies_config=tool_dependencies_config,
                                                                tool_dependencies=tool_dependencies )
        for installed_tool_dependency in installed_tool_dependencies:
            if installed_tool_dependency.status == trans.app.model.ToolDependency.installation_status.ERROR:
                message += '  %s' % installed_tool_dependency.error_message
        try:
            shutil.rmtree( work_dir )
        except:
            pass
        tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in tool_dependencies ]
        if message:
            status = 'error'
        else:
            message = "Installed tool dependencies: %s" % ','.join( td.name for td in installed_tool_dependencies )
            status = 'done'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='manage_tool_dependencies',
                                                          tool_dependency_ids=tool_dependency_ids,
                                                          message=message,
                                                          status=status ) )
    @web.expose
    @web.require_admin
    def install_repository( self, trans, **kwd ):
        if not trans.app.toolbox.shed_tool_confs:
            message = 'The <b>tool_config_file</b> setting in <b>universe_wsgi.ini</b> must include at least one shed tool configuration file name with a '
            message += '<b>&lt;toolbox&gt;</b> tag that includes a <b>tool_path</b> attribute value which is a directory relative to the Galaxy installation '
            message += 'directory in order to automatically install tools from a Galaxy tool shed (e.g., the file name <b>shed_tool_conf.xml</b> whose '
            message += '<b>&lt;toolbox&gt;</b> tag is <b>&lt;toolbox tool_path="../shed_tools"&gt;</b>).<p/>See the '
            message += '<a href="http://wiki.g2.bx.psu.edu/Tool%20Shed#Automatic_installation_of_Galaxy_tool_shed_repository_tools_into_a_local_Galaxy_instance" '
            message += 'target="_blank">Automatic installation of Galaxy tool shed repository tools into a local Galaxy instance</a> section of the '
            message += '<a href="http://wiki.g2.bx.psu.edu/Tool%20Shed" target="_blank">Galaxy tool shed wiki</a> for all of the details.'
            return trans.show_error_message( message )
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        tool_shed_url = kwd[ 'tool_shed_url' ]
        repo_info_dict = kwd[ 'repo_info_dict' ]
        new_tool_panel_section = kwd.get( 'new_tool_panel_section', '' )
        tool_panel_section = kwd.get( 'tool_panel_section', '' )
        includes_tools = util.string_as_bool( kwd.get( 'includes_tools', False ) )
        install_tool_dependencies = kwd.get( 'install_tool_dependencies', '' )
        if not includes_tools or ( includes_tools and kwd.get( 'select_tool_panel_section_button', False ) ):
            if includes_tools:
                install_tool_dependencies = CheckboxField.is_checked( install_tool_dependencies )
                shed_tool_conf = kwd[ 'shed_tool_conf' ]
            else:
                install_tool_dependencies = False
                # If installing a repository that includes no tools, get the relative tool_path from the file
                # to which the migrated_tools_config setting points.
                shed_tool_conf = trans.app.config.migrated_tools_config
            # Get the tool path by searching the list of shed_tool_confs for the dictionary
            # that contains the information about shed_tool_conf.
            for shed_tool_conf_dict in trans.app.toolbox.shed_tool_confs:
                config_filename = shed_tool_conf_dict[ 'config_filename' ]
                if config_filename == shed_tool_conf:
                    tool_path = shed_tool_conf_dict[ 'tool_path' ]
                    break
                else:
                    file_name = strip_path( config_filename )
                    if file_name == shed_tool_conf:
                        tool_path = shed_tool_conf_dict[ 'tool_path' ]
                        break
            if includes_tools and ( new_tool_panel_section or tool_panel_section ):
                if new_tool_panel_section:
                    section_id = new_tool_panel_section.lower().replace( ' ', '_' )
                    new_section_key = 'section_%s' % str( section_id )
                    if new_section_key in trans.app.toolbox.tool_panel:
                        # Appending a tool to an existing section in trans.app.toolbox.tool_panel
                        log.debug( "Appending to tool panel section: %s" % new_tool_panel_section )
                        tool_section = trans.app.toolbox.tool_panel[ new_section_key ]
                    else:
                        # Appending a new section to trans.app.toolbox.tool_panel
                        log.debug( "Loading new tool panel section: %s" % new_tool_panel_section )
                        elem = Element( 'section' )
                        elem.attrib[ 'name' ] = new_tool_panel_section
                        elem.attrib[ 'id' ] = section_id
                        elem.attrib[ 'version' ] = ''
                        tool_section = tools.ToolSection( elem )
                        trans.app.toolbox.tool_panel[ new_section_key ] = tool_section
                else:
                    section_key = 'section_%s' % tool_panel_section
                    tool_section = trans.app.toolbox.tool_panel[ section_key ]
            else:
                tool_section = None
            # Decode the encoded repo_info_dict param value.
            repo_info_dict = tool_shed_decode( repo_info_dict )
            # Clone the repository to the configured location.
            installed_repository_names = []
            for name, repo_info_tuple in repo_info_dict.items():
                description, repository_clone_url, changeset_revision, ctx_rev = repo_info_tuple
                clone_dir = os.path.join( tool_path, self.__generate_tool_path( repository_clone_url, changeset_revision ) )
                relative_install_dir = os.path.join( clone_dir, name )
                if os.path.exists( clone_dir ):
                    # Repository and revision has already been cloned.
                    message += 'Revision <b>%s</b> of repository <b>%s</b> was previously installed.<br/>' % ( changeset_revision, name )
                else:
                    clone_repository( repository_clone_url, os.path.abspath( relative_install_dir ), ctx_rev )
                    owner = get_repository_owner( clean_repository_clone_url( repository_clone_url ) )
                    tool_shed = clean_tool_shed_url( tool_shed_url )
                    tool_shed_repository, metadata_dict, = load_repository_contents( trans,
                                                                                     repository_name=name,
                                                                                     description=description,
                                                                                     owner=owner,
                                                                                     installed_changeset_revision=changeset_revision,
                                                                                     current_changeset_revision=changeset_revision,
                                                                                     ctx_rev=ctx_rev,
                                                                                     tool_path=tool_path,
                                                                                     repository_clone_url=repository_clone_url,
                                                                                     relative_install_dir=relative_install_dir,
                                                                                     tool_shed=tool_shed,
                                                                                     tool_section=tool_section,
                                                                                     shed_tool_conf=shed_tool_conf )
                    if 'tools' in metadata_dict:
                        # Get the tool_versions from the tool shed for each tool in the installed change set.
                        url = '%srepository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy&no_reset=true' % \
                            ( tool_shed_url, name, owner, changeset_revision )
                        response = urllib2.urlopen( url )
                        text = response.read()
                        response.close()
                        if text:
                            tool_version_dicts = from_json_string( text )
                            handle_tool_versions( trans.app, tool_version_dicts, tool_shed_repository )
                        else:
                            message += "Version information for the tools included in the <b>%s</b> repository is missing.  " % name
                            message += "Reset all of this repository's metadata in the tool shed, then set the installed tool versions "
                            message += "from the installed repository's <b>Repository Actions</b> menu.  "
                            status = 'error'
                    installed_repository_names.append( name )
            if installed_repository_names:                
                installed_repository_names.sort()
                num_repositories_installed = len( installed_repository_names )
                if tool_section:
                    message += 'Installed %d %s and all tools were loaded into tool panel section <b>%s</b>:<br/>Installed repositories: ' % \
                        ( num_repositories_installed,
                          inflector.cond_plural( num_repositories_installed, 'repository' ),
                          tool_section.name )
                else:
                    message += 'Installed %d %s and all tools were loaded into the tool panel outside of any sections.<br/>Installed repositories: ' % \
                        ( num_repositories_installed,
                          inflector.cond_plural( num_repositories_installed, 'repository' ) )
                for i, repo_name in enumerate( installed_repository_names ):
                    if i == len( installed_repository_names ) -1:
                        message += '%s.<br/>' % repo_name
                    else:
                        message += '%s, ' % repo_name
            if install_tool_dependencies:
                tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in tool_shed_repository.missing_tool_dependencies ]
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='manage_tool_dependencies',
                                                                  operation='install',
                                                                  tool_dependency_ids=tool_dependency_ids,
                                                                  status=status,
                                                                  message=message ) )
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='browse_repositories',
                                                              message=message,
                                                              status=status ) )
        if len( trans.app.toolbox.shed_tool_confs ) > 1:
            shed_tool_conf_select_field = build_shed_tool_conf_select_field( trans )
            shed_tool_conf = None
        else:
            shed_tool_conf_dict = trans.app.toolbox.shed_tool_confs[0]
            shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
            shed_tool_conf = shed_tool_conf.replace( './', '', 1 )
            shed_tool_conf_select_field = None
        tool_panel_section_select_field = build_tool_panel_section_select_field( trans )
        if includes_tools:
            # If we're installing a single repository that contains a readme file, get it's contents to display.
            decoded_repo_info_dict = tool_shed_decode( repo_info_dict )
            if len( decoded_repo_info_dict ) == 1:
                name = decoded_repo_info_dict.keys()[ 0 ]
                repo_info_tuple = decoded_repo_info_dict[ name ]
                description, repository_clone_url, changeset_revision, ctx_rev = repo_info_tuple
                owner = get_repository_owner( clean_repository_clone_url( repository_clone_url ) )
                url = '%srepository/get_readme?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy&no_reset=true' % ( tool_shed_url, name, owner, changeset_revision )
                response = urllib2.urlopen( url )
                raw_text = response.read()
                response.close()
                readme_text = ''
                for i, line in enumerate( raw_text ):
                    readme_text = '%s%s' % ( readme_text, to_html_str( line ) )
                    if len( readme_text ) > MAX_CONTENT_SIZE:
                        large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( MAX_CONTENT_SIZE )
                        readme_text = '%s%s' % ( readme_text, to_html_str( large_str ) )
                        break
            else:
                readme_text = '' 
        else:
            readme_text = ''
        return trans.fill_template( '/admin/tool_shed_repository/select_tool_panel_section.mako',
                                    tool_shed_url=tool_shed_url,
                                    repo_info_dict=repo_info_dict,
                                    shed_tool_conf=shed_tool_conf,
                                    includes_tools=includes_tools,
                                    install_tool_dependencies=install_tool_dependencies,
                                    shed_tool_conf_select_field=shed_tool_conf_select_field,
                                    tool_panel_section_select_field=tool_panel_section_select_field,
                                    new_tool_panel_section=new_tool_panel_section,
                                    readme_text=readme_text,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def install_tool_dependencies( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_dependency_ids = util.listify( params.get( 'tool_dependency_ids', None ) )
        if not tool_dependency_ids:
            tool_dependency_ids = util.listify( params.get( 'id', None ) )
        tool_dependencies = []
        for tool_dependency_id in tool_dependency_ids:
            tool_dependency = get_tool_dependency( trans, tool_dependency_id )
            tool_dependencies.append( tool_dependency )
        if kwd.get( 'install_tool_dependencies_button', False ):
            # Filter tool dependencies to only those that are installed.
            tool_dependencies_for_installation = []
            for tool_dependency in tool_dependencies:
                if tool_dependency.status in [ trans.model.ToolDependency.installation_status.UNINSTALLED,
                                               trans.model.ToolDependency.installation_status.ERROR ]:
                    tool_dependencies_for_installation.append( tool_dependency )
            if tool_dependencies_for_installation:
                # Redirect back to the ToolDependencyGrid before initiating installation.
                tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in tool_dependencies_for_installation ]
                new_kwd = dict( action='manage_tool_dependencies',
                                operation='initiate_tool_dependency_installation',
                                tool_dependency_ids=tool_dependency_ids,
                                message=message,
                                status=status )
                return self.tool_dependency_grid( trans, **new_kwd )
            else:
                message = 'All of the selected tool dependencies are already installed.'
                status = 'error'
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='manage_tool_dependencies',
                                                                  tool_dependency_ids=tool_dependency_ids,
                                                                  status=status,
                                                                  message=message ) )
        return trans.fill_template( '/admin/tool_shed_repository/install_tool_dependencies.mako',
                                    tool_dependencies=tool_dependencies,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def manage_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository_id = kwd[ 'id' ]
        repository = get_repository( trans, repository_id )
        description = util.restore_text( params.get( 'description', repository.description ) )
        shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        if params.get( 'edit_repository_button', False ):
            if description != repository.description:
                repository.description = description
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "The repository information has been updated."
        elif params.get( 'set_metadata_button', False ):
            repository_clone_url = generate_clone_url( trans, repository )
            metadata_dict = generate_metadata_using_disk_files( trans.app.toolbox, relative_install_dir, repository_clone_url )
            if metadata_dict:
                repository.metadata = metadata_dict
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "Repository metadata has been reset."
        return trans.fill_template( '/admin/tool_shed_repository/manage_repository.mako',
                                    repository=repository,
                                    description=description,
                                    repo_files_dir=repo_files_dir,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def manage_tool_dependencies( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_dependency_id = params.get( 'tool_dependency_id', None )
        tool_dependency_ids = util.listify( params.get( 'tool_dependency_ids', None ) )
        if not tool_dependency_ids:
            tool_dependency_ids = util.listify( params.get( 'id', None ) )
        if tool_dependency_id and tool_dependency_id not in tool_dependency_ids:
            tool_dependency_ids.append( tool_dependency_id )
        tool_dependencies = []
        # We need a tool_shed_repository, so get it from one of the tool_dependencies.
        tool_dependency = get_tool_dependency( trans, tool_dependency_ids[ 0 ] )
        tool_shed_repository = tool_dependency.tool_shed_repository
        self.tool_dependency_grid.title = "Tool shed repository '%s' tool dependencies"  % tool_shed_repository.name
        self.tool_dependency_grid.global_actions = \
            [ grids.GridAction( label='Browse repository', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='browse_repository', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ),
              grids.GridAction( label='Manage repository', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='manage_repository', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ),
              grids.GridAction( label='Get updates', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='check_for_updates', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ),
              grids.GridAction( label='Set tool versions', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='set_tool_versions', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ),
              grids.GridAction( label='Deactivate or uninstall repository', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='deactivate_or_uninstall_repository', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ) ]
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            if not tool_dependency_ids:
                message = 'Select at least 1 tool dependency to %s.' % operation
                kwd[ 'message' ] = message
                kwd[ 'status' ] = 'error'
                del kwd[ 'operation' ]
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='manage_tool_dependencies',
                                                                  **kwd ) )
            if operation == 'browse':
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='browse_tool_dependency',
                                                                  **kwd ) )
            elif operation == 'uninstall':
                tool_dependencies_for_uninstallation = []
                for tool_dependency_id in tool_dependency_ids:
                    tool_dependency = get_tool_dependency( trans, tool_dependency_id )
                    if tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLED,
                                                   trans.model.ToolDependency.installation_status.ERROR ]:
                        tool_dependencies_for_uninstallation.append( tool_dependency )
                if tool_dependencies_for_uninstallation:
                    return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                      action='uninstall_tool_dependencies',
                                                                      **kwd ) )
                else:
                    kwd[ 'message' ] = 'All selected tool dependencies are already uninstalled.'
                    kwd[ 'status' ] = 'error'
            elif operation == "install":
                tool_dependencies_for_installation = []
                for tool_dependency_id in tool_dependency_ids:
                    tool_dependency = get_tool_dependency( trans, tool_dependency_id )
                    if tool_dependency.status in [ trans.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                   trans.model.ToolDependency.installation_status.UNINSTALLED ]:
                        tool_dependencies_for_installation.append( tool_dependency )
                if tool_dependencies_for_installation:
                    self.initiate_tool_dependency_installation( trans, tool_dependencies_for_installation )
                else:
                    kwd[ 'message' ] = 'All selected tool dependencies are already installed.'
                    kwd[ 'status' ] = 'error'
        return self.tool_dependency_grid( trans, **kwd )
    @web.json
    @web.require_admin
    def open_folder( self, trans, folder_path ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        return open_repository_files_folder( trans, folder_path )
    @web.expose
    @web.require_admin
    def reinstall_repository( self, trans, **kwd ):
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        repository_id = kwd[ 'id' ]
        repository = get_repository( trans, repository_id )
        no_changes = kwd.get( 'no_changes', '' )
        no_changes_checked = CheckboxField.is_checked( no_changes )
        install_tool_dependencies = CheckboxField.is_checked( kwd.get( 'install_tool_dependencies', '' ) )
        shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repository_clone_url = generate_clone_url( trans, repository )
        clone_dir = os.path.join( tool_path, self.__generate_tool_path( repository_clone_url, repository.installed_changeset_revision ) )
        relative_install_dir = os.path.join( clone_dir, repository.name )
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        if not repository.ctx_rev:
            # The ctx_rev column was introduced late, so may be null for some installed ToolShedRepositories.
            ctx_rev = get_ctx_rev( tool_shed_url, repository.name, repository.owner, repository.installed_changeset_revision )
        else:
            ctx_rev = repository.ctx_rev
        clone_repository( repository_clone_url, os.path.abspath( relative_install_dir ), ctx_rev )
        # Since we're reinstalling the repository we need to find the latest changeset revision to which is can be updated.
        current_changeset_revision, current_ctx_rev = get_update_to_changeset_revision_and_ctx_rev( trans, repository )
        if current_ctx_rev != ctx_rev:
            repo = hg.repository( get_configured_ui(), path=os.path.abspath( relative_install_dir ) )
            pull_repository( repo, repository_clone_url, current_changeset_revision )
            update_repository( repo, ctx_rev=current_ctx_rev )
        tool_section = None
        if repository.includes_tools:
            # Get the location in the tool panel in which each tool was originally loaded.
            metadata = repository.metadata
            if 'tool_panel_section' in metadata:
                tool_panel_dict = metadata[ 'tool_panel_section' ]
                if not tool_panel_dict:
                    tool_panel_dict = generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
            else:
                tool_panel_dict = generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
            # TODO: Fix this to handle the case where the tools are distributed across in more than 1 ToolSection.  The
            # following assumes everything was loaded into 1 section (or no section) in the tool panel.
            tool_section_dicts = tool_panel_dict[ tool_panel_dict.keys()[ 0 ] ]
            tool_section_dict = tool_section_dicts[ 0 ]
            original_section_id = tool_section_dict[ 'id' ]
            original_section_name = tool_section_dict[ 'name' ]
            if no_changes_checked:
                if original_section_id in [ '' ]:
                    tool_section = None
                else:
                    section_key = 'section_%s' % str( original_section_id )
                    if section_key in trans.app.toolbox.tool_panel:
                        tool_section = trans.app.toolbox.tool_panel[ section_key ]
                    else:
                        # The section in which the tool was originally loaded used to be in the tool panel, but no longer is.
                        elem = Element( 'section' )
                        elem.attrib[ 'name' ] = original_section_name
                        elem.attrib[ 'id' ] = original_section_id
                        elem.attrib[ 'version' ] = ''
                        tool_section = tools.ToolSection( elem )
                        trans.app.toolbox.tool_panel[ section_key ] = tool_section
            else:
                # The user elected to change the tool panel section to contain the tools.
                new_tool_panel_section = kwd.get( 'new_tool_panel_section', '' )
                tool_panel_section = kwd.get( 'tool_panel_section', '' )
                if new_tool_panel_section:
                    section_id = new_tool_panel_section.lower().replace( ' ', '_' )
                    new_section_key = 'section_%s' % str( section_id )
                    if new_section_key in trans.app.toolbox.tool_panel:
                        # Appending a tool to an existing section in trans.app.toolbox.tool_panel
                        log.debug( "Appending to tool panel section: %s" % new_tool_panel_section )
                        tool_section = trans.app.toolbox.tool_panel[ new_section_key ]
                    else:
                        # Appending a new section to trans.app.toolbox.tool_panel
                        log.debug( "Loading new tool panel section: %s" % new_tool_panel_section )
                        elem = Element( 'section' )
                        elem.attrib[ 'name' ] = new_tool_panel_section
                        elem.attrib[ 'id' ] = section_id
                        elem.attrib[ 'version' ] = ''
                        tool_section = tools.ToolSection( elem )
                        trans.app.toolbox.tool_panel[ new_section_key ] = tool_section
                elif tool_panel_section:
                    section_key = 'section_%s' % tool_panel_section
                    tool_section = trans.app.toolbox.tool_panel[ section_key ]
                else:
                    tool_section = None
        tool_shed_repository, metadata_dict, load_repository_contents( trans,
                                                                       repository_name=repository.name,
                                                                       description=repository.description,
                                                                       owner=repository.owner,
                                                                       installed_changeset_revision=repository.installed_changeset_revision,
                                                                       current_changeset_revision=current_changeset_revision,
                                                                       ctx_rev=ctx_rev,
                                                                       tool_path=tool_path,
                                                                       repository_clone_url=repository_clone_url,
                                                                       relative_install_dir=relative_install_dir,
                                                                       tool_shed=repository.tool_shed,
                                                                       tool_section=tool_section,
                                                                       shed_tool_conf=shed_tool_conf )
        repository.uninstalled = False
        repository.deleted = False
        trans.sa_session.add( repository )
        trans.sa_session.flush()
        message += 'The <b>%s</b> repository has been reinstalled.  ' % repository.name
        if install_tool_dependencies:
            message += 'The following tool dependencies are now being installed, please wait...'
            tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in tool_shed_repository.missing_tool_dependencies ]
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='manage_tool_dependencies',
                                                              operation='install',
                                                              tool_dependency_ids=tool_dependency_ids,
                                                              status=status,
                                                              message=message ) )
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='browse_repositories',
                                                          message=message,
                                                          status=status ) )
    @web.json
    def repository_installation_status_updates( self, trans, id=None, status=None ):
        # Avoid caching
        trans.response.headers[ 'Pragma' ] = 'no-cache'
        trans.response.headers[ 'Expires' ] = '0'
        # Create new HTML for any that have changed
        rval = {}
        if id is not None and status is not None:
            repository = trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( id ) )
            if repository.status != status:
                repository.status = status
                rval[ id ] = { "status": repository.status,
                               "html_status": unicode( trans.fill_template( "admin/tool_shed_repository/repository_installation_status.mako",
                                                                            repository=repository ),
                                                                            'utf-8' ) }
    @web.expose
    @web.require_admin
    def reselect_tool_panel_section( self, trans, **kwd ):
        repository = get_repository( trans, kwd[ 'id' ] )
        # Get the location in the tool panel in which the tool was originally loaded.
        metadata = repository.metadata
        if 'tool_panel_section' in metadata:
            tool_panel_dict = metadata[ 'tool_panel_section' ]
            if tool_panel_dict:
                if panel_entry_per_tool( tool_panel_dict ):
                    # TODO: Fix this to handle the case where the tools are distributed across in more than 1 ToolSection.  The
                    # following assumes everything was loaded into 1 section (or no section) in the tool panel.
                    tool_section_dicts = tool_panel_dict[ tool_panel_dict.keys()[ 0 ] ]
                    tool_section_dict = tool_section_dicts[ 0 ]
                    original_section_name = tool_section_dict[ 'name' ]
                else:
                    original_section_name = tool_panel_dict[ 'name' ]
            else:
                original_section_name = ''
        else:
            original_section_name = ''
        tool_panel_section_select_field = build_tool_panel_section_select_field( trans )
        no_changes_check_box = CheckboxField( 'no_changes', checked=True )
        if original_section_name:
            message = "The tools contained in your <b>%s</b> repository were last loaded into the tool panel section <b>%s</b>.  " \
                % ( repository.name, original_section_name )
            message += "Uncheck the <b>No changes</b> check box and select a different tool panel section to load the tools in a "
            message += "different section in the tool panel."
        else:
            message = "The tools contained in your <b>%s</b> repository were last loaded into the tool panel outside of any sections.  " % repository.name
            message += "Uncheck the <b>No changes</b> check box and select a tool panel section to load the tools into that section."
        status = 'done'
        return trans.fill_template( '/admin/tool_shed_repository/reselect_tool_panel_section.mako',
                                    repository=repository,
                                    no_changes_check_box=no_changes_check_box,
                                    original_section_name=original_section_name,
                                    tool_panel_section_select_field=tool_panel_section_select_field,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def set_tool_versions( self, trans, **kwd ):
        # Get the tool_versions from the tool shed for each tool in the installed change set.
        repository = get_repository( trans, kwd[ 'id' ] )
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        url = '%s/repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy&no_reset=true' % \
            ( tool_shed_url, repository.name, repository.owner, repository.changeset_revision )
        response = urllib2.urlopen( url )
        text = response.read()
        response.close()
        if text:
            tool_version_dicts = from_json_string( text )
            handle_tool_versions( trans.app, tool_version_dicts, repository )
            message = "Tool versions have been set for all included tools."
            status = 'done'
        else:
            message = "Version information for the tools included in the <b>%s</b> repository is missing.  " % repository.name
            message += "Reset all of this reppository's metadata in the tool shed, then set the installed tool versions "
            message ++ "from the installed repository's <b>Repository Actions</b> menu.  "
            status = 'error'
        shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        return trans.fill_template( '/admin/tool_shed_repository/manage_repository.mako',
                                    repository=repository,
                                    description=repository.description,
                                    repo_files_dir=repo_files_dir,
                                    message=message,
                                    status=status )
    @web.json
    def tool_dependency_status_updates( self, trans, ids=None, status_list=None ):
        # Avoid caching
        trans.response.headers[ 'Pragma' ] = 'no-cache'
        trans.response.headers[ 'Expires' ] = '0'
        # Create new HTML for any that have changed
        rval = {}
        if ids is not None and status_list is not None:
            ids = ids.split( "," )
            status_list = status_list.split( "," )
            for id, status in zip( ids, status_list ):
                tool_dependency = trans.sa_session.query( trans.model.ToolDependency ).get( trans.security.decode_id( id ) )
                if tool_dependency.status != status:
                    rval[ id ] = { "status": tool_dependency.status,
                                   "html_status": unicode( trans.fill_template( "admin/tool_shed_repository/tool_dependency_installation_status.mako",
                                                                                tool_dependency=tool_dependency ),
                                                                                'utf-8' ) }
        return rval
    @web.expose
    @web.require_admin
    def uninstall_tool_dependencies( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_dependency_ids = util.listify( params.get( 'tool_dependency_ids', None ) )
        if not tool_dependency_ids:
            tool_dependency_ids = util.listify( params.get( 'id', None ) )
        tool_dependencies = []
        for tool_dependency_id in tool_dependency_ids:
            tool_dependency = get_tool_dependency( trans, tool_dependency_id )
            tool_dependencies.append( tool_dependency )
        if kwd.get( 'uninstall_tool_dependencies_button', False ):
            errors = False
            # Filter tool dependencies to only those that are installed.
            tool_dependencies_for_uninstallation = []
            for tool_dependency in tool_dependencies:
                if tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLED,
                                               trans.model.ToolDependency.installation_status.ERROR ]:
                    tool_dependencies_for_uninstallation.append( tool_dependency )
            for tool_dependency in tool_dependencies_for_uninstallation:
                uninstalled, error_message = remove_tool_dependency( trans, tool_dependency )
                if error_message:
                    errors = True
                    message = '%s  %s' % ( message, error_message )
            if errors:
                message = "Error attempting to uninstall tool dependencies: %s" % message
                status = 'error'
            else:
                message = "These tool dependencies have been uninstalled: %s" % ','.join( td.name for td in tool_dependencies_for_uninstallation )
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='manage_tool_dependencies',
                                                              tool_dependency_ids=tool_dependency_ids,
                                                              status=status,
                                                              message=message ) )
        return trans.fill_template( '/admin/tool_shed_repository/uninstall_tool_dependencies.mako',
                                    tool_dependencies=tool_dependencies,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def update_to_changeset_revision( self, trans, **kwd ):
        """Update a cloned repository to the latest revision possible."""
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_shed_url = kwd[ 'tool_shed_url' ]
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        latest_changeset_revision = params.get( 'latest_changeset_revision', None )
        latest_ctx_rev = params.get( 'latest_ctx_rev', None )
        repository = get_tool_shed_repository_by_shed_name_owner_changeset_revision( trans.app, tool_shed_url, name, owner, changeset_revision )
        if changeset_revision and latest_changeset_revision and latest_ctx_rev:
            if changeset_revision == latest_changeset_revision:
                message = "The installed repository named '%s' is current, there are no updates available.  " % name
            else:
                shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
                if relative_install_dir:
                    repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, name ) )
                    repo = hg.repository( get_configured_ui(), path=repo_files_dir )
                    repository_clone_url = os.path.join( tool_shed_url, 'repos', owner, name )
                    pull_repository( repo, repository_clone_url, latest_ctx_rev )
                    update_repository( repo, latest_ctx_rev )
                    # Update the repository metadata.
                    tool_shed = clean_tool_shed_url( tool_shed_url )
                    metadata_dict = generate_metadata_using_disk_files( trans.app.toolbox, relative_install_dir, repository_clone_url )
                    repository.metadata = metadata_dict
                    # Update the repository changeset_revision in the database.
                    repository.changeset_revision = latest_changeset_revision
                    repository.ctx_rev = latest_ctx_rev
                    repository.update_available = False
                    trans.sa_session.add( repository )
                    trans.sa_session.flush()
                    # Create tool_dependency records if necessary.
                    if 'tool_dependencies' in metadata_dict:
                        tool_dependencies = create_tool_dependency_objects( trans.app, repository, repository.changeset_revision )
                    message = "The installed repository named '%s' has been updated to change set revision '%s'.  " % ( name, latest_changeset_revision )
                    # See if any tool dependencies can be installed.
                    shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
                    if repository.missing_tool_dependencies:
                        message += "Click the name of one of the missing tool dependencies listed below to install tool dependencies."
                else:
                    message = "The directory containing the installed repository named '%s' cannot be found.  " % name
                    status = 'error'
        else:
            message = "The latest changeset revision could not be retrieved for the installed repository named '%s'.  " % name
            status = 'error'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='manage_repository',
                                                          id=trans.security.encode_id( repository.id ),
                                                          message=message,
                                                          status=status ) )
    @web.expose
    @web.require_admin
    def view_tool_metadata( self, trans, repository_id, tool_id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        webapp = params.get( 'webapp', 'community' )
        repository = get_repository( trans, repository_id )
        metadata = {}
        tool = None
        if 'tools' in repository.metadata:
            for tool_metadata_dict in repository.metadata[ 'tools' ]:
                if tool_metadata_dict[ 'id' ] == tool_id:
                    metadata = tool_metadata_dict
                    tool = trans.app.toolbox.load_tool( os.path.abspath( metadata[ 'tool_config' ] ), guid=metadata[ 'guid' ] )
                    break
        return trans.fill_template( "/admin/tool_shed_repository/view_tool_metadata.mako",
                                    repository=repository,
                                    tool=tool,
                                    metadata=metadata,
                                    message=message,
                                    status=status )
    def __generate_clone_url( self, trans, repository ):
        """Generate the URL for cloning a repository."""
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        return '%s/repos/%s/%s' % ( tool_shed_url, repository.owner, repository.name )
    def __generate_tool_path( self, repository_clone_url, changeset_revision ):
        """
        Generate a tool path that guarantees repositories with the same name will always be installed
        in different directories.  The tool path will be of the form:
        <tool shed url>/repos/<repository owner>/<repository name>/<installed changeset revision>
        http://test@bx.psu.edu:9009/repos/test/filter
        """
        tmp_url = clean_repository_clone_url( repository_clone_url )
        # Now tmp_url is something like: bx.psu.edu:9009/repos/some_username/column
        items = tmp_url.split( 'repos' )
        tool_shed_url = items[ 0 ]
        repo_path = items[ 1 ]
        tool_shed_url = clean_tool_shed_url( tool_shed_url )
        return '%s/repos%s/%s' % ( tool_shed_url, repo_path, changeset_revision )

## ---- Utility methods -------------------------------------------------------

def build_shed_tool_conf_select_field( trans ):
    """Build a SelectField whose options are the keys in trans.app.toolbox.shed_tool_confs."""
    options = []
    for shed_tool_conf_dict in trans.app.toolbox.shed_tool_confs:
        shed_tool_conf_filename = shed_tool_conf_dict[ 'config_filename' ]
        if shed_tool_conf_filename != trans.app.config.migrated_tools_config:
            if shed_tool_conf_filename.startswith( './' ):
                option_label = shed_tool_conf_filename.replace( './', '', 1 )
            else:
                option_label = shed_tool_conf_filename
            options.append( ( option_label, shed_tool_conf_filename ) )
    select_field = SelectField( name='shed_tool_conf' )
    for option_tup in options:
        select_field.add_option( option_tup[0], option_tup[1] )
    return select_field
def build_tool_panel_section_select_field( trans ):
    """Build a SelectField whose options are the sections of the current in-memory toolbox."""
    options = []
    for k, v in trans.app.toolbox.tool_panel.items():
        if isinstance( v, tools.ToolSection ):
            options.append( ( v.name, v.id ) )
    select_field = SelectField( name='tool_panel_section', display='radio' )
    for option_tup in options:
        select_field.add_option( option_tup[0], option_tup[1] )
    return select_field
def get_repository( trans, id ):
    """Get a tool_shed_repository from the database via id"""
    return trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( id ) )
def get_tool_dependency( trans, id ):
    """Get a tool_dependency from the database via id"""
    return trans.sa_session.query( trans.model.ToolDependency ).get( trans.security.decode_id( id ) )
