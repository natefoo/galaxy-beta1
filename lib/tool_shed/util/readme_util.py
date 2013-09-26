import logging
import os
from galaxy import eggs
from galaxy.util import json
from galaxy.util import unicodify
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util

eggs.require( 'mercurial' )

from mercurial import hg

log = logging.getLogger( __name__ )

def build_readme_files_dict( trans, repository, changeset_revision, metadata, tool_path=None ):
    """
    Return a dictionary of valid readme file name <-> readme file content pairs for all readme files defined in the received metadata.  Since the
    received changeset_revision (which is associated with the received metadata) may not be the latest installable changeset revision, the README
    file contents may not be available on disk.  This method is used by both Galaxy and the Tool Shed.
    """
    if trans.webapp.name == 'galaxy':
        can_use_disk_files = True
    else:
        repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
        latest_downloadable_changeset_revision = suc.get_latest_downloadable_changeset_revision( trans, repository, repo )
        can_use_disk_files = changeset_revision == latest_downloadable_changeset_revision
    readme_files_dict = {}
    if metadata:
        if 'readme_files' in metadata:
            for relative_path_to_readme_file in metadata[ 'readme_files' ]:
                readme_file_name = os.path.split( relative_path_to_readme_file )[ 1 ]
                if can_use_disk_files:
                    if tool_path:
                        full_path_to_readme_file = os.path.abspath( os.path.join( tool_path, relative_path_to_readme_file ) )
                    else:
                        full_path_to_readme_file = os.path.abspath( relative_path_to_readme_file )
                    try:
                        f = open( full_path_to_readme_file, 'r' )
                        text = unicodify( f.read() )
                        f.close()
                        readme_files_dict[ readme_file_name ] = suc.size_string( text )
                    except Exception, e:
                        log.exception( "Error reading README file '%s' from disk: %s" % ( str( relative_path_to_readme_file ), str( e ) ) )
                else:
                    # We must be in the tool shed and have an old changeset_revision, so we need to retrieve the file contents from the repository manifest.
                    ctx = suc.get_changectx_for_changeset( repo, changeset_revision )
                    if ctx:
                        fctx = suc.get_file_context_from_ctx( ctx, readme_file_name )
                        if fctx and fctx not in [ 'DELETED' ]:
                            try:
                                text = unicodify( fctx.data() )
                                readme_files_dict[ readme_file_name ] = suc.size_string( text )
                            except Exception, e:
                                log.exception( "Error reading README file '%s' from repository manifest: %s" % \
                                               ( str( relative_path_to_readme_file ), str( e ) ) )
    return readme_files_dict

def get_readme_files_dict_for_display( trans, tool_shed_url, repo_info_dict ):
    """
    Return a dictionary of README files contained in the single repository being installed so they can be displayed on the tool panel section
    selection page.
    """
    name = repo_info_dict.keys()[ 0 ]
    repo_info_tuple = repo_info_dict[ name ]
    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, installed_td = \
        suc.get_repo_info_tuple_contents( repo_info_tuple )
    # Handle README files.
    url = suc.url_join( tool_shed_url,
                       'repository/get_readme_files?name=%s&owner=%s&changeset_revision=%s' % ( name, repository_owner, changeset_revision ) )
    raw_text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
    readme_files_dict = json.from_json_string( raw_text )
    return readme_files_dict

def get_readme_file_names( repository_name ):
    """Return a list of file names that will be categorized as README files for the received repository_name."""
    readme_files = [ 'readme', 'read_me', 'install' ]
    valid_filenames = map( lambda f: '%s.txt' % f, readme_files )
    valid_filenames.extend( map( lambda f: '%s.rst' % f, readme_files ) )
    valid_filenames.extend( readme_files )
    valid_filenames.append( '%s.txt' % repository_name )
    valid_filenames.append( '%s.rst' % repository_name )
    return valid_filenames
