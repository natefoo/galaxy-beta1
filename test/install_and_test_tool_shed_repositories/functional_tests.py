#!/usr/bin/env python

# NOTE: This script cannot be run directly, because it needs to have test/functional/test_toolbox.py in sys.argv in 
#       order to run functional tests on repository tools after installation. The install_and_test_tool_shed_repositories.sh
#       will execute this script with the appropriate parameters.

import os, sys, shutil, tempfile, re, string, urllib, platform
from time import strftime
from ConfigParser import SafeConfigParser

# Assume we are run from the galaxy root directory, add lib to the python path
cwd = os.getcwd()
sys.path.append( cwd )

test_home_directory = os.path.join( cwd, 'test', 'install_and_test_tool_shed_repositories' )
default_test_file_dir = os.path.join( test_home_directory, 'test_data' )

# Here's the directory where everything happens.  Temporary directories are created within this directory to contain
# the database, new repositories, etc.
galaxy_test_tmp_dir = os.path.join( test_home_directory, 'tmp' )
default_galaxy_locales = 'en'
default_galaxy_test_file_dir = "test-data"
os.environ[ 'GALAXY_INSTALL_TEST_TMP_DIR' ] = galaxy_test_tmp_dir
new_path = [ os.path.join( cwd, "lib" ), os.path.join( cwd, 'test' ), os.path.join( cwd, 'scripts', 'api' ) ]
new_path.extend( sys.path )
sys.path = new_path

from galaxy import eggs

eggs.require( "nose" )
eggs.require( "NoseHTML" )
eggs.require( "NoseTestDiff" )
eggs.require( "twill==0.9" )
eggs.require( "Paste" )
eggs.require( "PasteDeploy" )
eggs.require( "Cheetah" )
eggs.require( "simplejson" )

# This should not be required, but it is under certain conditions, thanks to this bug: http://code.google.com/p/python-nose/issues/detail?id=284
eggs.require( "pysqlite" )

import install_and_test_tool_shed_repositories.functional.test_install_repositories as test_install_repositories
import install_and_test_tool_shed_repositories.base.test_db_util as test_db_util
import functional.test_toolbox as test_toolbox

import atexit, logging, os, os.path, sys, tempfile, simplejson
import twill, unittest, time
import sys, threading, random
import httplib, socket
from paste import httpserver

# This is for the galaxy application.
import galaxy.app
from galaxy.app import UniverseApplication
from galaxy.web import buildapp
from galaxy.util import parse_xml
from galaxy.util.json import from_json_string, to_json_string

from tool_shed.util.shed_util_common import url_join

import nose.core
import nose.config
import nose.loader
import nose.plugins.manager
from nose.plugins import Plugin

from base.util import parse_tool_panel_config, get_database_version, get_test_environment, get_repository_current_revision

from common import update

log = logging.getLogger( 'install_and_test_repositories' )

default_galaxy_test_port_min = 10000
default_galaxy_test_port_max = 10999
default_galaxy_test_host = '127.0.0.1'

# should this serve static resources (scripts, images, styles, etc.)
STATIC_ENABLED = True

def get_static_settings():
    """Returns dictionary of the settings necessary for a galaxy App
    to be wrapped in the static middleware.

    This mainly consists of the filesystem locations of url-mapped
    static resources.
    """
    cwd = os.getcwd()
    static_dir = os.path.join( cwd, 'static' )
    #TODO: these should be copied from universe_wsgi.ini
    return dict(
        #TODO: static_enabled needed here?
        static_enabled      = True,
        static_cache_time   = 360,
        static_dir          = static_dir,
        static_images_dir   = os.path.join( static_dir, 'images', '' ),
        static_favicon_dir  = os.path.join( static_dir, 'favicon.ico' ),
        static_scripts_dir  = os.path.join( static_dir, 'scripts', '' ),
        static_style_dir    = os.path.join( static_dir, 'june_2007_style', 'blue' ),
        static_robots_txt   = os.path.join( static_dir, 'robots.txt' ),
    )

def get_webapp_global_conf():
    """Get the global_conf dictionary sent as the first argument to app_factory.
    """
    # (was originally sent 'dict()') - nothing here for now except static settings
    global_conf = dict()
    if STATIC_ENABLED:
        global_conf.update( get_static_settings() )
    return global_conf

# Optionally, set the environment variable GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF
# to the location of a tool sheds configuration file that includes the tool shed
# that repositories will be installed from.

tool_sheds_conf_xml = '''<?xml version="1.0"?>
<tool_sheds>
    <tool_shed name="Galaxy main tool shed" url="http://toolshed.g2.bx.psu.edu/"/>
    <tool_shed name="Galaxy test tool shed" url="http://testtoolshed.g2.bx.psu.edu/"/>
</tool_sheds>
'''

# Create a blank shed_tool_conf.xml to hold the installed repositories.
shed_tool_conf_xml_template = '''<?xml version="1.0"?>
<toolbox tool_path="${shed_tool_path}">
</toolbox>
'''

# Since we will be running functional tests, we'll need the upload tool, but the rest can be omitted.
tool_conf_xml = '''<?xml version="1.0"?>
<toolbox>
    <section name="Get Data" id="getext">
        <tool file="data_source/upload.xml"/>
    </section>
</toolbox>
'''

# If we have a tool_data_table_conf.test.xml, set it up to be loaded when the UniverseApplication is started.
# This allows one to specify a set of tool data that is used exclusively for testing, and not loaded into any
# Galaxy instance. By default, this will be in the test-data-repo/location directory generated by buildbot_setup.sh.
if os.path.exists( 'tool_data_table_conf.test.xml' ):
    additional_tool_data_tables = 'tool_data_table_conf.test.xml'
    additional_tool_data_path = os.environ.get( 'GALAXY_INSTALL_TEST_EXTRA_TOOL_DATA_PATH', os.path.join( 'test-data-repo', 'location' ) )
else:
    additional_tool_data_tables = None
    additional_tool_data_path = None

# Also set up default tool data tables.
if os.path.exists( 'tool_data_table_conf.xml' ):
    tool_data_table_conf = 'tool_data_table_conf.xml'
elif os.path.exists( 'tool_data_table_conf.xml.sample' ):
    tool_data_table_conf = 'tool_data_table_conf.xml.sample'
else:
    tool_data_table_conf = None

# And set up a blank shed_tool_data_table_conf.xml.
tool_data_table_conf_xml_template = '''<?xml version="1.0"?>
<tables>
</tables>
'''
    
# The tool shed url and api key must be set for this script to work correctly. Additionally, if the tool shed url does not
# point to one of the defaults, the GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF needs to point to a tool sheds configuration file
# that contains a definition for that tool shed.

galaxy_tool_shed_url = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_SHED_URL', None )
tool_shed_api_key = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY', None )
exclude_list_file = os.environ.get( 'GALAXY_INSTALL_TEST_EXCLUDE_REPOSITORIES', 'install_test_exclude.xml' )

if tool_shed_api_key is None:
    print "This script requires the GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY environment variable to be set and non-empty."
    exit( 1 )
    
if galaxy_tool_shed_url is None:
    print "This script requires the GALAXY_INSTALL_TEST_TOOL_SHED_URL environment variable to be set and non-empty."
    exit( 1 )

if 'GALAXY_INSTALL_TEST_SECRET' not in os.environ:
    galaxy_encode_secret = 'changethisinproductiontoo'
    os.environ[ 'GALAXY_INSTALL_TEST_SECRET' ] = galaxy_encode_secret
else:
    galaxy_encode_secret = os.environ[ 'GALAXY_INSTALL_TEST_SECRET' ]

testing_single_repository = {}
if 'repository_name' in os.environ and 'repository_owner' in os.environ:
    testing_single_repository[ 'name' ] = os.environ[ 'repository_name' ]
    testing_single_repository[ 'owner' ] = os.environ[ 'repository_owner' ]
    if 'repository_revision' in os.environ:
        testing_single_repository[ 'changeset_revision' ] = os.environ[ 'repository_revision' ]
    else:
        testing_single_repository[ 'changeset_revision' ] = None
        
class ReportResults( Plugin ):
    '''Simple Nose plugin to record the IDs of all tests run, regardless of success.'''
    name = "reportresults"
    passed = dict()
    
    def options( self, parser, env=os.environ ):
        super( ReportResults, self ).options( parser, env=env )

    def configure(self, options, conf):
        super( ReportResults, self ).configure( options, conf )
        if not self.enabled:
            return

    def addSuccess( self, test ):
        '''Only record test IDs that correspond to tool functional tests.'''
        if 'TestForTool' in test.id():
            test_id = test.id()
            # Rearrange the test ID to match the format that is produced in test_results.failures
            test_id_parts = test_id.split( '.' )
            fixed_test_id = '%s (%s)' % ( test_id_parts[ -1 ], '.'.join( test_id_parts[ :-1 ] ) )
            test_parts = fixed_test_id.split( '/' )
            owner = test_parts[ -4 ]
            name = test_parts[ -3 ]
            test_identifier = '%s/%s' % ( owner, name )
            if test_identifier not in self.passed:
                self.passed[ test_identifier ] = []
            self.passed[ test_identifier ].append( fixed_test_id )

    def getTestStatus( self, test_identifier ):
        if test_identifier in self.passed:
            passed_tests = self.passed[ test_identifier ]
            del self.passed[ test_identifier ]
            return passed_tests
        return []

def execute_uninstall_method( app ):
    # Clean out any generated tests.
    remove_generated_tests( app )
    sa_session = app.model.context.current
    repositories_to_uninstall = sa_session.query( app.model.ToolShedRepository ).all()
    for repository in repositories_to_uninstall:
        if repository.status == app.model.ToolShedRepository.installation_status.UNINSTALLED:
            continue
        if repository.status not in [ app.model.ToolShedRepository.installation_status.UNINSTALLED,
                                      app.model.ToolShedRepository.installation_status.ERROR,
                                      app.model.ToolShedRepository.installation_status.INSTALLED ]:
            repository.status = app.model.ToolShedRepository.installation_status.ERROR
            sa_session.add( repository )
            sa_session.flush()
        name = str( repository.name )
        owner = str( repository.owner )
        changeset_revision = str( repository.installed_changeset_revision )
        log.debug( 'Changeset revision %s of repository %s queued for uninstallation.', changeset_revision, name )
        repository_dict = dict( name=name, owner=owner, changeset_revision=changeset_revision )
        # Generate a test method to uninstall this repository through the embedded Galaxy application's web interface.
        test_install_repositories.generate_uninstall_method( repository_dict )
    # Set up nose to run the generated uninstall method as a functional test.
    test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
    test_config.configure( sys.argv )
    # Run the uninstall method. This method uses the Galaxy web interface to uninstall the previously installed 
    # repository and delete it from disk.
    result, _ = run_tests( test_config )
    success = result.wasSuccessful()
    return success

def generate_config_file( input_filename, output_filename, config_items ):
    '''
    Generate a config file with the configuration that has been defined for the embedded web application.
    This is mostly relevant when setting metadata externally, since the script for doing that does not
    have access to app.config.
    ''' 
    cp = SafeConfigParser()
    cp.read( input_filename )
    config_items_by_section = []
    for label, value in config_items:
        found = False
        # Attempt to determine the correct section for this configuration option.
        for section in cp.sections():
            if cp.has_option( section, label ):
                config_tuple = section, label, value
                config_items_by_section.append( config_tuple )
                found = True
                continue
        # Default to app:main if no section was found.
        if not found:
            config_tuple = 'app:main', label, value
            config_items_by_section.append( config_tuple )
    # Replace the default values with the provided configuration.
    for section, label, value in config_items_by_section:
        cp.remove_option( section, label )
        cp.set( section, label, str( value ) )
    fh = open( output_filename, 'w' )
    cp.write( fh )
    fh.close()

def get_api_url( base, parts=[], params=None, key=None ):
    if 'api' in parts and parts.index( 'api' ) != 0:
        parts.pop( parts.index( 'api' ) )
        parts.insert( 0, 'api' )
    elif 'api' not in parts: 
        parts.insert( 0, 'api' )
    url = url_join( base, *parts )
    if key:
        url += '?%s' % urllib.urlencode( dict( key=key ) )
    else:
        url += '?%s' % urllib.urlencode( dict( key=tool_shed_api_key ) )
    if params:
        url += '&%s' % params
    return url

def get_latest_downloadable_changeset_revision( url, name, owner ):
    api_url_parts = [ 'api', 'repositories', 'get_ordered_installable_revisions' ]
    params = urllib.urlencode( dict( name=name, owner=owner ) )
    api_url = get_api_url( url, api_url_parts, params )
    changeset_revisions = json_from_url( api_url )
    if changeset_revisions:
        return changeset_revisions[ -1 ]
    else:
        return '000000000000'

def get_repository_info_from_api( url, repository_info_dict ):
    parts = [ 'api', 'repositories', repository_info_dict[ 'repository_id' ] ]
    api_url = get_api_url( base=url, parts=parts )
    extended_dict = json_from_url( api_url )
    latest_changeset_revision = get_latest_downloadable_changeset_revision( url, extended_dict[ 'name' ], extended_dict[ 'owner' ] )
    extended_dict[ 'latest_revision' ] = str( latest_changeset_revision )
    return extended_dict

def get_repository_tuple_from_elem( elem ):
    attributes = elem.attrib
    name = attributes.get( 'name', None )
    owner = attributes.get( 'owner', None )
    changeset_revision = attributes.get( 'changeset_revision', None )
    return ( name, owner, changeset_revision )

def get_repositories_to_install( tool_shed_url, latest_revision_only=True ):
    '''
    Get a list of repository info dicts to install. This method expects a json list of dicts with the following structure:
    [
      {
        "changeset_revision": <revision>,
        "encoded_repository_id": <encoded repository id from the tool shed>,
        "name": <name>,
        "owner": <owner>,
        "tool_shed_url": <url>
      },
      ...
    ]
    NOTE: If the tool shed URL specified in any dict is not present in the tool_sheds_conf.xml, the installation will fail.
    '''
    assert tool_shed_api_key is not None, 'Cannot proceed without tool shed API key.'
    params = urllib.urlencode( dict( do_not_test='false', 
                                     downloadable='true', 
                                     malicious='false',
                                     includes_tools='true',
                                     skip_tool_test='false' ) )
    api_url = get_api_url( base=tool_shed_url, parts=[ 'repository_revisions' ], params=params )
    base_repository_list = json_from_url( api_url )
    log.info( 'The api returned %d metadata revisions.', len( base_repository_list ) )
    known_repository_ids = {}
    detailed_repository_list = []
    for repository_to_install_dict in base_repository_list:
        # We need to get some details from the tool shed API, such as repository name and owner, to pass on to the
        # module that will generate the install methods.
        repository_info_dict = get_repository_info_from_api( galaxy_tool_shed_url, repository_to_install_dict )
        if repository_info_dict[ 'latest_revision' ] == '000000000000':
            continue
        owner = repository_info_dict[ 'owner' ] 
        name = repository_info_dict[ 'name' ]
        changeset_revision = repository_to_install_dict[ 'changeset_revision' ]
        repository_id = repository_to_install_dict[ 'repository_id' ]
        # We are testing deprecated repositories, because it is possible that a deprecated repository contains valid
        # and functionally correct tools that someone has previously installed. Deleted repositories have never been installed,
        # and therefore do not need to be checked. If they are undeleted, this script will then test them the next time it runs.
        if repository_info_dict[ 'deleted' ]:
            log.info( "Skipping revision %s of repository id %s (%s/%s) since the repository is deleted...",
                      changeset_revision, 
                      repository_id, 
                      name, 
                      owner )
            continue
        # Now merge the dict returned from /api/repository_revisions with the detailed dict we just retrieved.
        if latest_revision_only:
            if changeset_revision == repository_info_dict[ 'latest_revision' ]:
                detailed_repository_list.append( dict( repository_info_dict.items() + repository_to_install_dict.items() ) )
        else:
            detailed_repository_list.append( dict( repository_info_dict.items() + repository_to_install_dict.items() ) )
    repositories_tested = len( detailed_repository_list )
    if latest_revision_only:
        skipped_previous = ' and metadata revisions that are not the most recent'
    else:
        skipped_previous = ''
    if testing_single_repository:
        log.info( 'Testing single repository with name %s and owner %s.', 
                  testing_single_repository[ 'name' ], 
                  testing_single_repository[ 'owner' ])
        for repository_to_install in detailed_repository_list:
            if repository_to_install[ 'name' ] == testing_single_repository[ 'name' ] \
            and repository_to_install[ 'owner' ] == testing_single_repository[ 'owner' ]:
                if testing_single_repository[ 'changeset_revision' ] is None:
                    return [ repository_to_install ]
                else:
                    if testing_single_repository[ 'changeset_revision' ] == repository_to_install[ 'changeset_revision' ]:
                        return [ repository_to_install ]
        return []
    log.info( 'After removing deleted repositories%s from the list, %d remain to be tested.', skipped_previous, repositories_tested )
    return detailed_repository_list

def get_tool_info_from_test_id( test_id ):
    '''
    Test IDs come in the form test_tool_number (functional.test_toolbox.TestForTool_toolshed_url/repos/owner/repository_name/tool_id/tool_version)
    We want the tool ID and tool version.
    '''
    parts = test_id.replace( ')', '' ).split( '/' )
    tool_version = parts[ -1 ]
    tool_id = parts[ -2 ]
    return tool_id, tool_version

def get_tool_test_results_from_api( tool_shed_url, metadata_revision_id ):
    api_path = [ 'api', 'repository_revisions', metadata_revision_id ]
    api_url = get_api_url( base=tool_shed_url, parts=api_path )
    repository_metadata = json_from_url( api_url )
    tool_test_results = repository_metadata.get( 'tool_test_results', {} )
    # If, for some reason, the script that checks for functional tests has not run, tool_test_results will be None.
    if tool_test_results is None:
        return dict()
    return tool_test_results

def is_latest_downloadable_revision( url, repository_info_dict ):
    latest_revision = get_latest_downloadable_changeset_revision( url, name=repository_info_dict[ 'name' ], owner=repository_info_dict[ 'owner' ] )
    return str( repository_info_dict[ 'changeset_revision' ] ) == str( latest_revision )

def json_from_url( url ):
    url_handle = urllib.urlopen( url )
    url_contents = url_handle.read()
    try:
        parsed_json = from_json_string( url_contents )
    except:
        log.exception( 'Error parsing JSON data.' )
        raise
    return parsed_json

def parse_exclude_list( xml_filename ):
    '''
    This method should return a list with the following structure:
    [
        {
            'reason': The default reason or the reason specified in this section,
            'repositories': 
                [
                    ( name, owner, changeset revision if changeset revision else None ),
                    ( name, owner, changeset revision if changeset revision else None )
                ]
        },
        {
            'reason': The default reason or the reason specified in this section,
            'repositories': 
                [
                    ( name, owner, changeset revision if changeset revision else None ),
                    ( name, owner, changeset revision if changeset revision else None )
                ]
        },
    ]
    '''
    exclude_list = []
    exclude_verbose = []
    xml_tree = parse_xml( xml_filename )
    tool_sheds = xml_tree.findall( 'repositories' )
    xml_element = []
    exclude_count = 0
    for tool_shed in tool_sheds:
        if galaxy_tool_shed_url != tool_shed.attrib[ 'tool_shed' ]:
            continue
        else:
            xml_element = tool_shed
    for reason_section in xml_element:
        reason_text = reason_section.find( 'text' ).text
        repositories = reason_section.findall( 'repository' )
        exclude_dict = dict( reason=reason_text, repositories=[] )
        for repository in repositories:
            repository_tuple = get_repository_tuple_from_elem( repository )
            if repository_tuple not in exclude_dict[ 'repositories' ]:
                exclude_verbose.append( repository_tuple )
                exclude_count += 1
                exclude_dict[ 'repositories' ].append( repository_tuple )
        exclude_list.append( exclude_dict )
    log.debug( '%d repositories excluded from testing...', exclude_count )
    if '-list_repositories' in sys.argv:
        for name, owner, changeset_revision in exclude_verbose:
            if changeset_revision:
                log.debug( 'Repository %s owned by %s, changeset revision %s.', name, owner, changeset_revision )
            else:
                log.debug( 'Repository %s owned by %s, all revisions.', name, owner )
    return exclude_list

def register_test_result( url, metadata_id, test_results_dict, repository_info_dict, params ):
    '''
    Update the repository metadata tool_test_results and appropriate flags using the API.
    '''
    params[ 'tool_test_results' ] = test_results_dict
    if '-info_only' in sys.argv:
        return {}
    else:
        return update( tool_shed_api_key, '%s' % ( url_join( galaxy_tool_shed_url, 'api', 'repository_revisions', metadata_id ) ), params, return_formatted=False )

def remove_generated_tests( app ):
    # Delete any configured tool functional tests from the test_toolbox.__dict__, otherwise nose will find them 
    # and try to re-run the tests after uninstalling the repository, which will cause false failure reports, 
    # since the test data has been deleted from disk by now.
    tests_to_delete = []
    tools_to_delete = []
    global test_toolbox
    for key in test_toolbox.__dict__:
        if key.startswith( 'TestForTool_' ):
            log.info( 'Tool test found in test_toolbox, deleting: %s', key )
            # We can't delete this test just yet, we're still iterating over __dict__.
            tests_to_delete.append( key )
            tool_id = key.replace( 'TestForTool_', '' )
            for tool in app.toolbox.tools_by_id:
                if tool.replace( '_', ' ' ) == tool_id.replace( '_', ' ' ):
                    tools_to_delete.append( tool )
    for key in tests_to_delete:
        # Now delete the tests found in the previous loop.
        del test_toolbox.__dict__[ key ]
    for tool in tools_to_delete:
        del app.toolbox.tools_by_id[ tool ]

def run_tests( test_config ):
    loader = nose.loader.TestLoader( config=test_config )
    test_config.plugins.addPlugin( ReportResults() )
    plug_loader = test_config.plugins.prepareTestLoader( loader )
    if plug_loader is not None:
        loader = plug_loader
    tests = loader.loadTestsFromNames( test_config.testNames )
    test_runner = nose.core.TextTestRunner( stream=test_config.stream,
                                            verbosity=test_config.verbosity,
                                            config=test_config )
    plug_runner = test_config.plugins.prepareTestRunner( test_runner )
    if plug_runner is not None:
        test_runner = plug_runner
    result = test_runner.run( tests )
    return result, test_config.plugins._plugins

def show_summary_output( repository_info_dicts ):
    repositories_by_owner = dict()
    for repository in repository_info_dicts:
        if repository[ 'owner' ] not in repositories_by_owner:
            repositories_by_owner[ repository[ 'owner' ] ] = []
        repositories_by_owner[ repository[ 'owner' ] ].append( repository )
    for owner in repositories_by_owner:
        print "# "
        for repository in repositories_by_owner[ owner ]:
            print "# %s owned by %s, changeset revision %s" % ( repository[ 'name' ], repository[ 'owner' ], repository[ 'changeset_revision' ] )

def main():
    # ---- Configuration ------------------------------------------------------
    galaxy_test_host = os.environ.get( 'GALAXY_INSTALL_TEST_HOST', default_galaxy_test_host )
    galaxy_test_port = os.environ.get( 'GALAXY_INSTALL_TEST_PORT', str( default_galaxy_test_port_max ) )
    
    tool_path = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_PATH', 'tools' )
    if 'HTTP_ACCEPT_LANGUAGE' not in os.environ:
        os.environ[ 'HTTP_ACCEPT_LANGUAGE' ] = default_galaxy_locales
    galaxy_test_file_dir = os.environ.get( 'GALAXY_INSTALL_TEST_FILE_DIR', default_galaxy_test_file_dir )
    if not os.path.isabs( galaxy_test_file_dir ):
        galaxy_test_file_dir = os.path.abspath( galaxy_test_file_dir )
    use_distributed_object_store = os.environ.get( 'GALAXY_INSTALL_TEST_USE_DISTRIBUTED_OBJECT_STORE', False )
    if not os.path.isdir( galaxy_test_tmp_dir ):
        os.mkdir( galaxy_test_tmp_dir )
    galaxy_test_proxy_port = None
    # Set up the configuration files for the Galaxy instance.
    shed_tool_data_table_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DATA_TABLE_CONF', os.path.join( galaxy_test_tmp_dir, 'test_shed_tool_data_table_conf.xml' ) )
    galaxy_tool_data_table_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DATA_TABLE_CONF', tool_data_table_conf )
    galaxy_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_CONF', os.path.join( galaxy_test_tmp_dir, 'test_tool_conf.xml' ) )
    galaxy_shed_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_CONF', os.path.join( galaxy_test_tmp_dir, 'test_shed_tool_conf.xml' ) )
    galaxy_migrated_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_MIGRATED_TOOL_CONF', os.path.join( galaxy_test_tmp_dir, 'test_migrated_tool_conf.xml' ) )
    galaxy_tool_sheds_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF', os.path.join( galaxy_test_tmp_dir, 'test_tool_sheds_conf.xml' ) )
    galaxy_shed_tools_dict = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DICT_FILE', os.path.join( galaxy_test_tmp_dir, 'shed_tool_dict' ) )
    file( galaxy_shed_tools_dict, 'w' ).write( to_json_string( dict() ) )
    if 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' in os.environ:
        tool_data_path = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' )
    else:
        tool_data_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        os.environ[ 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' ] = tool_data_path
    # Configure the database connection and path.
    if 'GALAXY_INSTALL_TEST_DBPATH' in os.environ:
        galaxy_db_path = os.environ[ 'GALAXY_INSTALL_TEST_DBPATH' ]
    else: 
        tempdir = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        galaxy_db_path = os.path.join( tempdir, 'database' )
    # Configure the paths Galaxy needs to install and test tools.
    galaxy_file_path = os.path.join( galaxy_db_path, 'files' )
    new_repos_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
    galaxy_tempfiles = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
    galaxy_shed_tool_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir, prefix='shed_tools' ) 
    galaxy_migrated_tool_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
    # Set up the tool dependency path for the Galaxy instance.
    tool_dependency_dir = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR', None )
    if tool_dependency_dir is None:
        tool_dependency_dir = tempfile.mkdtemp( dir=galaxy_test_tmp_dir ) 
        os.environ[ 'GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR' ] = tool_dependency_dir
    if 'GALAXY_INSTALL_TEST_DBURI' in os.environ:
        database_connection = os.environ[ 'GALAXY_INSTALL_TEST_DBURI' ]
    else:
        database_connection = 'sqlite:///' + os.path.join( galaxy_db_path, 'install_and_test_repositories.sqlite' )
    kwargs = {}
    for dir in [ galaxy_test_tmp_dir ]:
        try:
            os.makedirs( dir )
        except OSError:
            pass

    print "Database connection: ", database_connection

    # Generate the shed_tool_data_table_conf.xml file.
    file( shed_tool_data_table_conf_file, 'w' ).write( tool_data_table_conf_xml_template )
    os.environ[ 'GALAXY_INSTALL_TEST_SHED_TOOL_DATA_TABLE_CONF' ] = shed_tool_data_table_conf_file
    # ---- Start up a Galaxy instance ------------------------------------------------------
    # Generate the tool_conf.xml file.
    file( galaxy_tool_conf_file, 'w' ).write( tool_conf_xml )
    # Generate the tool_sheds_conf.xml file, but only if a the user has not specified an existing one in the environment.
    if 'GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF' not in os.environ:
        file( galaxy_tool_sheds_conf_file, 'w' ).write( tool_sheds_conf_xml )
    # Generate the shed_tool_conf.xml file.
    tool_conf_template_parser = string.Template( shed_tool_conf_xml_template )
    shed_tool_conf_xml = tool_conf_template_parser.safe_substitute( shed_tool_path=galaxy_shed_tool_path )
    file( galaxy_shed_tool_conf_file, 'w' ).write( shed_tool_conf_xml )
    os.environ[ 'GALAXY_INSTALL_TEST_SHED_TOOL_CONF' ] = galaxy_shed_tool_conf_file
    # Generate the migrated_tool_conf.xml file.
    migrated_tool_conf_xml = tool_conf_template_parser.safe_substitute( shed_tool_path=galaxy_migrated_tool_path )
    file( galaxy_migrated_tool_conf_file, 'w' ).write( migrated_tool_conf_xml )
    # Write the embedded web application's specific configuration to a temporary file. This is necessary in order for
    # the external metadata script to find the right datasets.
    kwargs = dict( admin_users = 'test@bx.psu.edu',
                   allow_user_creation = True,
                   allow_user_deletion = True,
                   allow_library_path_paste = True,
                   database_connection = database_connection,
                   datatype_converters_config_file = "datatype_converters_conf.xml.sample",
                   file_path = galaxy_file_path,
                   id_secret = galaxy_encode_secret,
                   job_queue_workers = 5,
                   log_destination = "stdout",
                   migrated_tools_config = galaxy_migrated_tool_conf_file,
                   new_file_path = galaxy_tempfiles,
                   running_functional_tests = True,
                   shed_tool_data_table_config = shed_tool_data_table_conf_file,
                   shed_tool_path = galaxy_shed_tool_path,
                   template_path = "templates",
                   tool_config_file = ','.join( [ galaxy_tool_conf_file, galaxy_shed_tool_conf_file ] ),
                   tool_data_path = tool_data_path,
                   tool_data_table_config_path = galaxy_tool_data_table_conf_file,
                   tool_dependency_dir = tool_dependency_dir,
                   tool_path = tool_path,
                   tool_parse_help = False,
                   tool_sheds_config_file = galaxy_tool_sheds_conf_file,
                   update_integrated_tool_panel = False,
                   use_heartbeat = False )
    galaxy_config_file = os.environ.get( 'GALAXY_INSTALL_TEST_INI_FILE', None )
    # If the user has passed in a path for the .ini file, do not overwrite it.
    if not galaxy_config_file:
        galaxy_config_file = os.path.join( galaxy_test_tmp_dir, 'install_test_tool_shed_repositories_wsgi.ini' )
        config_items = []
        for label in kwargs:
            config_tuple = label, kwargs[ label ]
            config_items.append( config_tuple )
        # Write a temporary file, based on universe_wsgi.ini.sample, using the configuration options defined above.
        generate_config_file( 'universe_wsgi.ini.sample', galaxy_config_file, config_items )
    kwargs[ 'tool_config_file' ] = [ galaxy_tool_conf_file, galaxy_shed_tool_conf_file ]
    # Set the global_conf[ '__file__' ] option to the location of the temporary .ini file, which gets passed to set_metadata.sh.
    kwargs[ 'global_conf' ] = get_webapp_global_conf()
    kwargs[ 'global_conf' ][ '__file__' ] = galaxy_config_file
    # ---- Build Galaxy Application -------------------------------------------------- 
    if not database_connection.startswith( 'sqlite://' ):
        kwargs[ 'database_engine_option_max_overflow' ] = '20'
        kwargs[ 'database_engine_option_pool_size' ] = '10'
    kwargs[ 'config_file' ] = galaxy_config_file
    app = UniverseApplication( **kwargs )
    
    log.info( "Embedded Galaxy application started" )

    # ---- Run galaxy webserver ------------------------------------------------------
    server = None
    global_conf = get_webapp_global_conf()
    global_conf[ 'database_file' ] = database_connection
    webapp = buildapp.app_factory( global_conf,
                                   use_translogger=False,
                                   static_enabled=STATIC_ENABLED,
                                   app=app )

    # Serve the app on a specified or random port.
    if galaxy_test_port is not None:
        server = httpserver.serve( webapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
    else:
        random.seed()
        for i in range( 0, 9 ):
            try:
                galaxy_test_port = str( random.randint( default_galaxy_test_port_min, default_galaxy_test_port_max ) )
                log.debug( "Attempting to serve app on randomly chosen port: %s", galaxy_test_port )
                server = httpserver.serve( webapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
                break
            except socket.error, e:
                if e[0] == 98:
                    continue
                raise
        else:
            raise Exception( "Unable to open a port between %s and %s to start Galaxy server" % \
                             ( default_galaxy_test_port_min, default_galaxy_test_port_max ) )
    if galaxy_test_proxy_port:
        os.environ[ 'GALAXY_INSTALL_TEST_PORT' ] = galaxy_test_proxy_port
    else:
        os.environ[ 'GALAXY_INSTALL_TEST_PORT' ] = galaxy_test_port
    # Start the server.
    t = threading.Thread( target=server.serve_forever )
    t.start()
    # Test if the server is up.
    for i in range( 10 ):
        # Directly test the app, not the proxy.
        conn = httplib.HTTPConnection( galaxy_test_host, galaxy_test_port )
        conn.request( "GET", "/" )
        if conn.getresponse().status == 200:
            break
        time.sleep( 0.1 )
    else:
        raise Exception( "Test HTTP server did not return '200 OK' after 10 tries" )
    log.info( "Embedded galaxy web server started" )
    if galaxy_test_proxy_port:
        log.info( "The embedded Galaxy application is running on %s:%s", galaxy_test_host, galaxy_test_proxy_port )
    else:
        log.info( "The embedded Galaxy application is running on %s:%s", galaxy_test_host, galaxy_test_port )
    log.info( "Repositories will be installed from the tool shed at %s", galaxy_tool_shed_url )
    success = False
    # If a tool_data_table_conf.test.xml file was found, add the entries from it into the app's tool data tables.
    if additional_tool_data_tables:
        app.tool_data_tables.add_new_entries_from_config_file( config_filename=additional_tool_data_tables,
                                                               tool_data_path=additional_tool_data_path,
                                                               shed_tool_data_table_config=None, 
                                                               persist=False )
    # Initialize some variables for the summary that will be printed to stdout.
    repositories_passed = []
    repositories_failed = []
    repositories_failed_install = []
    exclude_list = []
    if os.path.exists( exclude_list_file ):
        log.info( 'Loading the list of repositories excluded from testing from the file %s...', exclude_list_file )
        exclude_list = parse_exclude_list( exclude_list_file )
    try:
        # Get a list of repositories to test from the tool shed specified in the GALAXY_INSTALL_TEST_TOOL_SHED_URL environment variable.
        log.info( "Retrieving repositories to install from the URL:\n%s\n", str( galaxy_tool_shed_url ) )
        if '-check_all_revisions' not in sys.argv:
            repositories_to_install = get_repositories_to_install( galaxy_tool_shed_url, latest_revision_only=True )
        else:
            repositories_to_install = get_repositories_to_install( galaxy_tool_shed_url, latest_revision_only=False )
        log.info( "Retrieved %d repositories from the API.", len( repositories_to_install ) )
        if '-list_repositories' in sys.argv:
            log.info( "The API returned the following repositories, not counting deleted:" )
            for repository_info_dict in repositories_to_install:
                log.info( "%s owned by %s changeset revision %s",
                          repository_info_dict.get( 'name', None ),
                          repository_info_dict.get( 'owner', None ),
                          repository_info_dict.get( 'changeset_revision', None ) )
        repositories_tested = len( repositories_to_install )
        # This loop will iterate through the list of repositories generated by the above code, having already filtered out any
        # that were marked as deleted. For each repository, it will generate a test method that will use Twill to install that
        # repository into the embedded Galaxy application that was started up, selecting to install repository and tool
        # dependencies if they are defined. If the installation completes successfully, it will then generate a test case for
        # each functional test defined for each tool in the repository, and execute the generated test cases. When this completes,
        # it will record the result of the tests, and if any failed, the traceback and captured output of the tool that was run.
        # After all tests have completed, the repository is uninstalled, so that the previous test cases don't interfere with
        # the next repository's functional tests.
        for repository_info_dict in repositories_to_install:
            """
            Each repository_info_dict looks something like:
            {
              "changeset_revision": "13fa22a258b5",
              "contents_url": "/api/repositories/529fd61ab1c6cc36/contents",
              "deleted": false,
              "deprecated": false,
              "description": "Convert column case.",
              "downloadable": true,
              "id": "529fd61ab1c6cc36",
              "long_description": "This tool takes the specified columns and converts them to uppercase or lowercase.",
              "malicious": false,
              "name": "change_case",
              "owner": "test",
              "private": false,
              "repository_id": "529fd61ab1c6cc36",
              "times_downloaded": 0,
              "tool_shed_url": "http://toolshed.local:10001",
              "url": "/api/repository_revisions/529fd61ab1c6cc36",
              "user_id": "529fd61ab1c6cc36"
            }
            """
            repository_status = dict()
            params = dict()
            repository_id = str( repository_info_dict.get( 'repository_id', None ) )
            changeset_revision = str( repository_info_dict.get( 'changeset_revision', None ) )
            metadata_revision_id = repository_info_dict.get( 'id', None )
            # Add the URL for the tool shed we're installing from, so the automated installation methods go to the right place.
            repository_info_dict[ 'tool_shed_url' ] = galaxy_tool_shed_url
            # Get the name and owner out of the repository info dict.
            name = str( repository_info_dict[ 'name' ] )
            owner = str( repository_info_dict[ 'owner' ] )
            # Populate the repository_status dict now.
            repository_status = get_tool_test_results_from_api( galaxy_tool_shed_url, metadata_revision_id )
            if 'test_environment' not in repository_status:
                repository_status[ 'test_environment' ] = {}
            test_environment = get_test_environment( repository_status[ 'test_environment' ] )
            test_environment[ 'galaxy_database_version' ] = get_database_version( app )
            test_environment[ 'galaxy_revision'] = get_repository_current_revision( os.getcwd() )
            repository_status[ 'test_environment' ] = test_environment
            repository_status[ 'passed_tests' ] = []
            repository_status[ 'failed_tests' ] = []
            repository_status[ 'skip_reason' ] = None
            # Iterate through the list of repositories defined not to be installed. This should be a list of dicts in the following format:
            # {
            #     'reason': The default reason or the reason specified in this section,
            #     'repositories': 
            #         [
            #             ( name, owner, changeset revision if changeset revision else None ),
            #             ( name, owner, changeset revision if changeset revision else None )
            #         ]
            # },
            # If changeset revision is None, that means the entire repository is excluded from testing, otherwise only the specified
            # revision should be skipped. 
            # TODO: When a repository is selected to be skipped, use the API to update the tool shed with the defined skip reason.
            skip_this_repository = False
            skip_because = None
            for exclude_by_reason in exclude_list:
                reason = exclude_by_reason[ 'reason' ]
                exclude_repositories = exclude_by_reason[ 'repositories' ]
                if ( name, owner, changeset_revision ) in exclude_repositories or ( name, owner, None ) in exclude_repositories:
                    skip_this_repository = True
                    skip_because = reason
                    break
            if skip_this_repository:
                repository_status[ 'not_tested' ] = dict( reason=skip_because )
                params[ 'tools_functionally_correct' ] = False
                params[ 'do_not_test' ] = False
                register_test_result( galaxy_tool_shed_url, metadata_revision_id, repository_status, repository_info_dict, params )
                log.info( "Not testing revision %s of repository %s owned by %s.", changeset_revision, name, owner )
                continue
            else:
                log.info( "Installing and testing revision %s of repository %s owned by %s...", changeset_revision, name, owner )
            # Explicitly clear tests from twill's test environment.
            remove_generated_tests( app )
            # Use the repository information dict to generate an install method that will install the repository into the embedded
            # Galaxy application, with tool dependencies and repository dependencies, if any.
            test_install_repositories.generate_install_method( repository_info_dict )
            os.environ[ 'GALAXY_INSTALL_TEST_HOST' ] = galaxy_test_host
            # Configure nose to run the install method as a test.
            test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
            test_config.configure( sys.argv )
            # Run the configured install method as a test. This method uses the embedded Galaxy application's web interface to install the specified
            # repository, with tool and repository dependencies also selected for installation.
            result, _ = run_tests( test_config )
            success = result.wasSuccessful()
            repository_status[ 'installation_errors' ] = dict( current_repository=[], repository_dependencies=[], tool_dependencies=[] )
            try:
                repository = test_db_util.get_installed_repository_by_name_owner_changeset_revision( name, owner, changeset_revision )
            except:
                log.exception( 'Error getting installed repository.' )
                success = False
                pass
            # If the installation succeeds, configure and run functional tests for this repository. This is equivalent to 
            # sh run_functional_tests.sh -installed
            if success:
                log.debug( 'Installation of %s succeeded, running all defined functional tests.', name )
                # Generate the shed_tools_dict that specifies the location of test data contained within this repository. If the repository 
                # does not have a test-data directory, this will return has_test_data = False, and we will set the do_not_test flag to True,
                # and the tools_functionally_correct flag to False, as well as updating tool_test_results.
                file( galaxy_shed_tools_dict, 'w' ).write( to_json_string( dict() ) )
                has_test_data, shed_tools_dict = parse_tool_panel_config( galaxy_shed_tool_conf_file, from_json_string( file( galaxy_shed_tools_dict, 'r' ).read() ) )
                # The repository_status dict should always have the following structure:
                # {
                #     "test_environment":
                #         {
                #              "galaxy_revision": "9001:abcd1234",
                #              "galaxy_database_version": "114",
                #              "tool_shed_revision": "9001:abcd1234",
                #              "tool_shed_mercurial_version": "2.3.1",
                #              "tool_shed_database_version": "17",
                #              "python_version": "2.7.2",
                #              "architecture": "x86_64",
                #              "system": "Darwin 12.2.0"
                #         },
                #      "passed_tests":
                #         [
                #             {
                #                 "test_id": "The test ID, generated by twill",
                #                 "tool_id": "The tool ID that was tested",
                #                 "tool_version": "The tool version that was tested",
                #             },
                #         ]
                #     "failed_tests":
                #         [
                #             {
                #                 "test_id": "The test ID, generated by twill",
                #                 "tool_id": "The tool ID that was tested",
                #                 "tool_version": "The tool version that was tested",
                #                 "stderr": "The output of the test, or a more detailed description of what was tested and what the outcome was."
                #                 "traceback": "The captured traceback."
                #             },
                #         ]
                #     "installation_errors":
                #         {
                #              'tool_dependencies':
                #                  [
                #                      {
                #                         'type': 'Type of tool dependency, e.g. package, set_environment, etc.', 
                #                         'name': 'Name of the tool dependency.', 
                #                         'version': 'Version if this is a package, otherwise blank.',
                #                         'error_message': 'The error message returned when installation was attempted.',
                #                      },
                #                  ],
                #              'repository_dependencies':
                #                  [
                #                      {
                #                         'tool_shed': 'The tool shed that this repository was installed from.', 
                #                         'name': 'The name of the repository that failed to install.', 
                #                         'owner': 'Owner of the failed repository.',
                #                         'changeset_revision': 'Changeset revision of the failed repository.',
                #                         'error_message': 'The error message that was returned when the repository failed to install.',
                #                      },
                #                  ],
                #              'current_repository':
                #                  [
                #                      {
                #                         'tool_shed': 'The tool shed that this repository was installed from.', 
                #                         'name': 'The name of the repository that failed to install.', 
                #                         'owner': 'Owner of the failed repository.',
                #                         'changeset_revision': 'Changeset revision of the failed repository.',
                #                         'error_message': 'The error message that was returned when the repository failed to install.',
                #                      },
                #                  ],
                #             {
                #                 "name": "The name of the repository.",
                #                 "owner": "The owner of the repository.",
                #                 "changeset_revision": "The changeset revision of the repository.",
                #                 "error_message": "The message stored in tool_dependency.error_message."
                #             },
                #         }
                #      "missing_test_components":
                #         [
                #             {
                #                 "tool_id": "The tool ID that missing components.",
                #                 "tool_version": "The version of the tool."
                #                 "tool_guid": "The guid of the tool."
                #                 "missing_components": "Which components are missing, e.g. the test data filename, or the test-data directory."
                #             },
                #         ]
                #      "not_tested":
                #         { 
                #             "reason": "The Galaxy development team has determined that this repository should not be installed and tested by the automated framework."
                #         }
                # }
                failed_tool_dependencies = repository.includes_tool_dependencies and repository.tool_dependencies_with_installation_errors
                failed_repository_dependencies = repository.repository_dependencies_with_installation_errors
                if 'missing_test_components' not in repository_status:
                    repository_status[ 'missing_test_components' ] = []
                if not has_test_data:
                    # If the repository does not have a test-data directory, any functional tests in the tool configuration will
                    # fail. Mark the repository as failed and skip installation.
                    log.error( 'Test data is missing for this repository. Updating repository and skipping functional tests.' )
                    # Record the lack of test data if the repository metadata defines tools.
                    if 'tools' in repository.metadata:
                        for tool in repository.metadata[ 'tools' ]:
                            tool_id = tool[ 'id' ]
                            tool_version = tool[ 'version' ]
                            tool_guid = tool[ 'guid' ]
                            # In keeping with the standard display layout, add the error message to the dict for each tool individually.
                            missing_components = dict( tool_id=tool_id, tool_version=tool_version, tool_guid=tool_guid,
                                                       missing_components="Repository %s is missing a test-data directory." % name )
                            if missing_components not in repository_status[ 'missing_test_components' ]:
                                repository_status[ 'missing_test_components' ].append( missing_components )
                    else:
                        continue
                    # Record the status of this repository in the tool shed.
                    set_do_not_test = not is_latest_downloadable_revision( galaxy_tool_shed_url, repository_info_dict )
                    params[ 'tools_functionally_correct' ] = False
                    params[ 'missing_test_components' ] = True
                    params[ 'do_not_test' ] = str( set_do_not_test )
                    register_test_result( galaxy_tool_shed_url, 
                                          metadata_revision_id, 
                                          repository_status, 
                                          repository_info_dict, 
                                          params )
                    # Run the cleanup method. This removes tool functional test methods from the test_toolbox module and uninstalls the
                    # repository using Twill.
                    execute_uninstall_method( app )
                    # Set the test_toolbox.toolbox module-level variable to the new app.toolbox.
                    test_toolbox.toolbox = app.toolbox
                    repositories_failed.append( dict( name=name, owner=owner, changeset_revision=changeset_revision ) )
                elif failed_tool_dependencies or failed_repository_dependencies:
                    # If a tool dependency fails to install correctly, this should be considered an installation error,
                    # and functional tests should be skipped, since the tool dependency needs to be correctly installed
                    # for the test to be considered reliable.
                    log.error( 'One or more tool dependencies of this repository are marked as missing.' )
                    log.error( 'Updating repository and skipping functional tests.' )
                    # In keeping with the standard display layout, add the error message to the dict for each tool individually.
                    for dependency in repository.tool_dependencies_with_installation_errors:
                        test_result = dict( type=dependency.type, 
                                            name=dependency.name, 
                                            version=dependency.version,
                                            error_message=dependency.error_message )
                        repository_status[ 'installation_errors' ][ 'tool_dependencies' ].append( test_result )
                    for dependency in repository.repository_dependencies_with_installation_errors:
                        test_result = dict( tool_shed=dependency.tool_shed, 
                                            name=dependency.name, 
                                            owner=dependency.owner, 
                                            changeset_revision=dependency.changeset_revision,
                                            error_message=dependency.error_message )
                        repository_status[ 'installation_errors' ][ 'repository_dependencies' ].append( test_result )
                    # Record the status of this repository in the tool shed.
                    params[ 'tools_functionally_correct' ] = False
                    params[ 'do_not_test' ] = False
                    params[ 'test_install_error' ] = True
                    register_test_result( galaxy_tool_shed_url, 
                                          metadata_revision_id, 
                                          repository_status, 
                                          repository_info_dict, 
                                          params )
                    # Run the cleanup method. This removes tool functional test methods from the test_toolbox module and uninstalls the
                    # repository using Twill.
                    execute_uninstall_method( app )
                    # Set the test_toolbox.toolbox module-level variable to the new app.toolbox.
                    test_toolbox.toolbox = app.toolbox
                    repositories_failed_install.append( dict( name=name, owner=owner, changeset_revision=changeset_revision ) )
                else:
                    # If the repository does have a test-data directory, we write the generated shed_tools_dict to a file, so the functional
                    # test framework can find it.
                    file( galaxy_shed_tools_dict, 'w' ).write( to_json_string( shed_tools_dict ) )
                    log.info( 'Saved generated shed_tools_dict to %s\nContents: %s', galaxy_shed_tools_dict, str( shed_tools_dict ) )
                    # Set the GALAXY_TOOL_SHED_TEST_FILE environment variable to the path of the shed_tools_dict file, so that test.base.twilltestcase.setUp
                    # will find and parse it properly.
                    os.environ[ 'GALAXY_TOOL_SHED_TEST_FILE' ] = galaxy_shed_tools_dict
                    os.environ[ 'GALAXY_TEST_HOST' ] = galaxy_test_host
                    os.environ[ 'GALAXY_TEST_PORT' ] = galaxy_test_port
                    # Set the module-level variable 'toolbox', so that test.functional.test_toolbox will generate the appropriate test methods.
                    test_toolbox.toolbox = app.toolbox
                    # Generate the test methods for this installed repository. We need to pass in True here, or it will look 
                    # in $GALAXY_HOME/test-data for test data, which may result in missing or invalid test files.
                    test_toolbox.build_tests( testing_shed_tools=True )
                    # Set up nose to run the generated functional tests.
                    test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
                    test_config.configure( sys.argv )
                    # Run the configured tests.
                    result, test_plugins = run_tests( test_config )
                    success = result.wasSuccessful()
                    # Use the ReportResults nose plugin to get a list of tests that passed.
                    for plugin in test_plugins:
                        if hasattr( plugin, 'getTestStatus' ):
                            test_identifier = '%s/%s' % ( owner, name )
                            passed_tests = plugin.getTestStatus( test_identifier )
                            break
                    repository_status[ 'passed_tests' ] = []
                    for test_id in passed_tests:
                        # Normalize the tool ID and version display.
                        tool_id, tool_version = get_tool_info_from_test_id( test_id )
                        test_result = dict( test_id=test_id, tool_id=tool_id, tool_version=tool_version )
                        repository_status[ 'passed_tests' ].append( test_result )
                    if success:
                        # This repository's tools passed all functional tests. Update the repository_metadata table in the tool shed's database
                        # to reflect that. Call the register_test_result method, which executes a PUT request to the repository_revisions API
                        # controller with the status of the test. This also sets the do_not_test and tools_functionally correct flags, and
                        # updates the time_last_tested field to today's date.
                        repositories_passed.append( dict( name=name, owner=owner, changeset_revision=changeset_revision ) )
                        params[ 'tools_functionally_correct' ] = True
                        params[ 'do_not_test' ] = False
                        register_test_result( galaxy_tool_shed_url, 
                                              metadata_revision_id, 
                                              repository_status, 
                                              repository_info_dict, 
                                              params )
                        log.debug( 'Revision %s of repository %s installed and passed functional tests.', changeset_revision, name )
                    else:
                        # If the functional tests fail, log the output and update the failed changeset revision's metadata record in the tool shed via the API.
                        for failure in result.failures + result.errors:
                            # Record the twill test identifier and information about the tool, so the repository owner can discover which test is failing.
                            test_id = str( failure[0] )
                            tool_id, tool_version = get_tool_info_from_test_id( test_id )
                            test_status = dict( test_id=test_id, tool_id=tool_id, tool_version=tool_version )
                            log_output = failure[1].replace( '\\n', '\n' )
                            # Remove debug output that the reviewer or owner doesn't need.
                            log_output = re.sub( r'control \d+:.+', r'', log_output )
                            log_output = re.sub( r'\n+', r'\n', log_output )
                            appending_to = 'output'
                            tmp_output = {}
                            output = {}
                            # Iterate through the functional test output and extract only the important data. Captured logging and stdout are not recorded.
                            for line in log_output.split( '\n' ):
                                if line.startswith( 'Traceback' ):
                                    appending_to = 'traceback'
                                elif '>> end captured' in line or '>> end tool' in line:
                                    continue
                                elif 'request returned None from get_history' in line:
                                    continue
                                elif '>> begin captured logging <<' in line:
                                    appending_to = 'logging'
                                    continue
                                elif '>> begin captured stdout <<' in line:
                                    appending_to = 'stdout'
                                    continue
                                elif '>> begin captured stderr <<' in line or '>> begin tool stderr <<' in line:
                                    appending_to = 'stderr'
                                    continue
                                if appending_to not in tmp_output:
                                    tmp_output[ appending_to ] = []
                                tmp_output[ appending_to ].append( line )
                            for output_type in [ 'stderr', 'traceback' ]:
                                if output_type in tmp_output:
                                    test_status[ output_type ] = '\n'.join( tmp_output[ output_type ] )
                            repository_status[ 'failed_tests' ].append( test_status )
                        # Call the register_test_result method, which executes a PUT request to the repository_revisions API controller with the outcome 
                        # of the tests, and updates tool_test_results with the relevant log data.
                        # This also sets the do_not_test and tools_functionally correct flags to the appropriate values, and updates the time_last_tested
                        # field to today's date.
                        repositories_failed.append( dict( name=name, owner=owner, changeset_revision=changeset_revision ) )
                        set_do_not_test = not is_latest_downloadable_revision( galaxy_tool_shed_url, repository_info_dict )
                        params[ 'tools_functionally_correct' ] = False
                        params[ 'do_not_test' ] = str( set_do_not_test )
                        register_test_result( galaxy_tool_shed_url, 
                                              metadata_revision_id, 
                                              repository_status, 
                                              repository_info_dict, 
                                              params )
                        log.debug( 'Revision %s of repository %s installed successfully, but did not pass functional tests.',
                                   changeset_revision, name ) 
                    # Run the uninstall method. This removes tool functional test methods from the test_toolbox module and uninstalls the
                    # repository using Twill.
                    log.debug( 'Uninstalling changeset revision %s of repository %s',
                               repository_info_dict[ 'changeset_revision' ], 
                               repository_info_dict[ 'name' ] )
                    success = execute_uninstall_method( app )
                    if not success:
                        log.error( 'Repository %s failed to uninstall.', repository_info_dict[ 'name' ] )
                    # Set the test_toolbox.toolbox module-level variable to the new app.toolbox.
                    test_toolbox.toolbox = app.toolbox
            else:
                # Even if the repository failed to install, execute the uninstall method, in case a dependency did succeed.
                log.debug( 'Uninstalling repository %s', repository_info_dict[ 'name' ] )
                try:
                    repository = test_db_util.get_installed_repository_by_name_owner_changeset_revision( name, owner, changeset_revision )
                except:
                    log.exception( 'Unable to uninstall, no installed repository found.' )
                    continue
                test_result = dict( tool_shed=repository.tool_shed, 
                                    name=repository.name, 
                                    owner=repository.owner, 
                                    changeset_revision=repository.changeset_revision,
                                    error_message=repository.error_message )
                repository_status[ 'installation_errors' ][ 'repository_dependencies' ].append( test_result )
                params[ 'tools_functionally_correct' ] = False
                params[ 'test_install_error' ] = True
                params[ 'do_not_test' ] = False
                register_test_result( galaxy_tool_shed_url, 
                                      metadata_revision_id, 
                                      repository_status, 
                                      repository_info_dict, 
                                      params )
                success = execute_uninstall_method( app  )
                if not success:
                    log.error( 'Repository %s failed to uninstall.', repository_info_dict[ 'name' ] )
                repositories_failed_install.append( dict( name=name, owner=owner, changeset_revision=changeset_revision ) )
                log.debug( 'Repository %s failed to install correctly.', repository_info_dict[ 'name' ] )
    except:
        log.exception( "Failure running tests" )
        
    log.info( "Shutting down" )
    # ---- Tear down -----------------------------------------------------------
    # Gracefully shut down the embedded web server and UniverseApplication.
    if server:
        log.info( "Shutting down embedded galaxy web server" )
        server.server_close()
        server = None
        log.info( "Embedded galaxy server stopped" )
    if app:
        log.info( "Shutting down galaxy application" )
        app.shutdown()
        app = None
        log.info( "Embedded galaxy application stopped" )
    # Clean up test files unless otherwise specified.
    if 'GALAXY_INSTALL_TEST_NO_CLEANUP' not in os.environ:
        try:
            for dir in [ galaxy_test_tmp_dir ]:
                if os.path.exists( dir ):
                    log.info( "Cleaning up temporary files in %s", dir )
                    shutil.rmtree( dir )
        except:
            pass
    else:
        log.debug( 'GALAXY_INSTALL_TEST_NO_CLEANUP set, not cleaning up.' )

    now = strftime( "%Y-%m-%d %H:%M:%S" )
    print "####################################################################################"
    print "# %s - repository installation and testing script completed." % now
    print "# Repository revisions tested: %d" % repositories_tested
    if '-info_only' in sys.argv:
        print "# -info_only set, not updating the tool shed."
    if repositories_tested > 0:
        if repositories_passed:
            print '# ----------------------------------------------------------------------------------'
            print "# %d repositories passed all tests:" % len( repositories_passed )
            show_summary_output( repositories_passed )
        if repositories_failed:
            print '# ----------------------------------------------------------------------------------'
            print "# %d repositories failed one or more tests:" % len( repositories_failed )
            show_summary_output( repositories_failed )
        if repositories_failed_install:
            # Set success to False so that the return code will not be 0.
            success = False
            print '# ----------------------------------------------------------------------------------'
            print "# %d repositories with installation errors:" % len( repositories_failed_install )
            show_summary_output( repositories_failed_install )
        else:
            success = True
    else:
        success = True
    print "####################################################################################"
    # Normally, the value of 'success' would determine whether this test suite is marked as passed or failed
    # in the automated buildbot framework. However, due to the procedure used here, we only want to report
    # failure if a repository fails to install correctly. Therefore, we have overriden the value of 'success'
    # here based on what actions the script has executed. 
    if success:
        return 0
    else:
        return 1

if __name__ == "__main__":
    now = strftime( "%Y-%m-%d %H:%M:%S" )
    print "####################################################################################"
    print "# %s - running repository installation and testing script." % now
    print "####################################################################################"
    sys.exit( main() )
