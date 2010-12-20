from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy import model, util
from galaxy.web.form_builder import *
from galaxy.web.controllers.requests_common import invalid_id_redirect
import logging, os

log = logging.getLogger( __name__ )

class RequestTypeGrid( grids.Grid ):
    # Custom column types
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.desc
    class RequestFormColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.request_form.name
    class SampleFormColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            return request_type.sample_form.name
    class SequencerColumn( grids.TextColumn ):
        def get_value(self, trans, grid, request_type):
            if request_type.sequencer:
                return request_type.sequencer.name
            return 'No sequencer assigned'
        def get_link( self, trans, grid, request_type ):
            if request_type.sequencer:
                self.link = ( lambda item: iff( item.deleted, None, dict( operation="view_sequencer", id=item.sequencer.id ) ) )
                return self.link( request_type )
            return None
    # Grid definition
    webapp = "galaxy"
    title = "Request Types"
    template = "admin/request_type/grid.mako"
    model_class = model.RequestType
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = True
    default_filter = dict( deleted="False" )
    columns = [
        NameColumn( "Name", 
                    key="name",
                    link=( lambda item: iff( item.deleted, None, dict( operation="view_request_type", id=item.id ) ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='desc',
                           filterable="advanced" ),
        RequestFormColumn( "Request Form", 
                           link=( lambda item: iff( item.deleted, None, dict( operation="view_form_definition", id=item.request_form.id ) ) ) ),
        SampleFormColumn( "Sample Form", 
                           link=( lambda item: iff( item.deleted, None, dict( operation="view_form_definition", id=item.sample_form.id ) ) ) ),
        SequencerColumn( "Sequencer" ),
        grids.DeletedColumn( "Deleted", 
                             key="deleted", 
                             visible=False, 
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Edit request type", allow_multiple=False, condition=( lambda item: not item.deleted ) ),
        grids.GridOperation( "Edit permissions", allow_multiple=False, condition=( lambda item: not item.deleted ) ),
        grids.GridOperation( "Use run details template", allow_multiple=False, condition=( lambda item: not item.deleted and not item.run_details ) ),
        grids.GridOperation( "Delete", allow_multiple=True, condition=( lambda item: not item.deleted ) ),
        grids.GridOperation( "Undelete", condition=( lambda item: item.deleted ) ),    
    ]
    global_actions = [
        grids.GridAction( "Create new request type", dict( controller='request_type', action='create_request_type' ) )
    ]

class RequestType( BaseController, UsesFormDefinitions ):
    request_type_grid = RequestTypeGrid()

    @web.expose
    @web.require_admin
    def browse_request_types( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            obj_id = kwd.get( 'id', None )
            if operation == "view_form_definition":
                return self.view_form_definition( trans, **kwd )
            elif operation == "view_request_type":
                return self.view_request_type( trans, **kwd )
            elif operation == "use run details template":
                return trans.response.send_redirect( web.url_for( controller='requests_admin',
                                                                  action='add_template',
                                                                  cntrller='requests_admin',
                                                                  item_type='request_type',
                                                                  form_type=trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE,
                                                                  request_type_id=obj_id ) )
            elif operation == "edit request type":
                return self.edit_request_type( trans, **kwd )
            elif operation == "delete":
                return self.delete_request_type( trans, **kwd )
            elif operation == "undelete":
                return self.undelete_request_type( trans, **kwd )
            elif operation == "edit permissions":
                return self.request_type_permissions( trans, **kwd )
            elif operation == "view_sequencer":
                return trans.response.send_redirect( web.url_for( controller='sequencer',
                                                                  action='view_sequencer',
                                                                  **kwd ) )
        # Render the grid view
        return self.request_type_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def create_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        rt_info_widgets, rt_states_widgets = self.__get_populated_request_type_widgets( trans, **kwd )
        sequencer_select_field = self.__build_sequencer_select_field( trans )
        if params.get( 'add_state_button', False ):
            # Append a new tuple to the set of states which will result in
            # empty state name and description TextFields being displayed on
            # the form.
            rt_states_widgets.append( ( "", "" ) )
        elif params.get( 'remove_state_button', False ):
            index = int( params.get( 'remove_state_button', '' ).split( " " )[2] )
            del rt_states_widgets[ index-1 ]
        elif params.get( 'create_request_type_button', False ):
            self.__save_request_type( trans, action='create_request_type', **kwd )
            message = 'The request type has been created.'
            return trans.response.send_redirect( web.url_for( controller='request_type',
                                                              action='browse_request_types',
                                                              message=message,
                                                              status=status ) )
        return trans.fill_template( '/admin/request_type/create_request_type.mako',
                                    rt_info_widgets=rt_info_widgets,
                                    rt_states_widgets=rt_states_widgets,
                                    sequencer_select_field=sequencer_select_field,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def view_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_type_id = kwd.get( 'id', None )
        try:
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
        # See if we have any associated templates
        widgets = request_type.get_template_widgets( trans )
        widget_fields_have_contents = self.widget_fields_have_contents( widgets )
        return trans.fill_template( '/admin/request_type/view_request_type.mako', 
                                    request_type=request_type,
                                    widgets=widgets,
                                    widget_fields_have_contents=widget_fields_have_contents,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def edit_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_type_id = params.get( 'id', None )
        try:
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
        # See if we have any associated templates
        widgets = request_type.get_template_widgets( trans )
        widget_fields_have_contents = self.widget_fields_have_contents( widgets )
        if params.get( 'edit_request_type_button', False ):
            request_type = self.__save_request_type( trans, action='edit_request_type', **kwd )
            message = 'Changes made to request type (%s) have been saved' % request_type.name
        sequencer_select_field = self.__build_sequencer_select_field( trans, request_type.sequencer )
        return trans.fill_template( '/admin/request_type/edit_request_type.mako',
                                    request_type=request_type,
                                    widgets=widgets,
                                    widget_fields_have_contents=widget_fields_have_contents,
                                    sequencer_select_field=sequencer_select_field,
                                    message=message,
                                    status=status )
    def __save_request_type( self, trans, action, **kwd ):
        # Here we save a newly created request_type or save changed
        # attributes of an existing request_type.
        params = util.Params( kwd )
        request_type_id = params.get( 'id', None )
        name = util.restore_text( params.get( 'name', ''  ) )
        desc = util.restore_text( params.get( 'desc', '' ) )
        request_form_id = params.get( 'request_form_id', 'none' )
        sample_form_id = params.get( 'sample_form_id', 'none' )
        sequencer_id = params.get( 'sequencer_id', 'none' )
        # validate
        if not name or request_form_id == 'none' or sample_form_id == 'none':
            message = 'Enter the name, request form, and the sample form associated with this request type.'
            return trans.response.send_redirect( web.url_for( controller='request_type',
                                                              action=action,
                                                              message=message,
                                                              status='error' ) )
        try:
            request_form = trans.sa_session.query( trans.model.FormDefinition ).get( trans.security.decode_id( request_form_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'form definition', action='browse_request_types' )
        
        try:
            sample_form = trans.sa_session.query( trans.model.FormDefinition ).get( trans.security.decode_id( sample_form_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'form definition', action='browse_request_types' )
        try:
            sequencer = trans.sa_session.query( trans.model.Sequencer ).get( trans.security.decode_id( sequencer_id ) )
        except:
            sequencer = None
        if request_type_id:
            # We're saving changed attributes of an existing request_type.
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
            request_type.name = name
            request_type.desc = desc
            request_type.request_form = request_form
            request_type.sample_form = sample_form
            request_type.sequencer = sequencer
            for sample_state in request_type.states:
                sample_state_id = trans.security.encode_id( sample_state.id )
                name = util.restore_text( params.get( 'state_name_%s' % sample_state_id, '' ) )
                desc = util.restore_text( params.get( 'state_desc_%s' % sample_state_id, '' ) )
                sample_state.name = name
                sample_state.desc = desc
                trans.sa_session.add( sample_state )
                trans.sa_session.flush()
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
        else:
            # We're saving a newly created request_type
            request_type = trans.model.RequestType( name=name,
                                                    desc=desc,
                                                    request_form=request_form,
                                                    sample_form=sample_form,
                                                    sequencer=sequencer ) 
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
            i = 0
            while True:
                if kwd.has_key( 'state_name_%i' % i ):
                    name = util.restore_text( params.get( 'state_name_%i' % i, '' ) )
                    desc = util.restore_text( params.get( 'state_desc_%i' % i, '' ) )
                    sample_state = trans.model.SampleState( name, desc, request_type ) 
                    trans.sa_session.add( sample_state )
                    trans.sa_session.flush()
                    i += 1
                else:
                    break
        return request_type
    def __check_path( self, a_path ):
        # Return a valid folder_path
        if a_path and not a_path.endswith( os.sep ):
            a_path += os.sep
        return a_path
    def __get_populated_request_type_widgets( self, trans, **kwd ):
        request_form_definitions = self.get_all_forms( trans, 
                                                        filter=dict( deleted=False ),
                                                        form_type=trans.model.FormDefinition.types.REQUEST )
        sample_form_definitions = self.get_all_forms( trans, 
                                                      filter=dict( deleted=False ),
                                                      form_type=trans.model.FormDefinition.types.SAMPLE )
        if not request_form_definitions or not sample_form_definitions:
            return [],[]
        params = util.Params( kwd )
        request_form_id = params.get( 'request_form_id', 'none' )
        sample_form_id = params.get( 'sample_form_id', 'none' )
        request_form_id_select_field = build_select_field( trans,
                                                           objs=request_form_definitions,
                                                           label_attr='name',
                                                           select_field_name='request_form_id',
                                                           selected_value=request_form_id,
                                                           refresh_on_change=False )
        sample_form_id_select_field = build_select_field( trans,
                                                           objs=sample_form_definitions,
                                                           label_attr='name',
                                                           select_field_name='sample_form_id',
                                                           selected_value=sample_form_id,
                                                           refresh_on_change=False )
        rt_info_widgets = [ dict( label='Name', 
                                  widget=TextField( 'name', 40, util.restore_text( params.get( 'name', '' ) ) ) ),
                            dict( label='Description', 
                                  widget=TextField( 'desc', 40, util.restore_text( params.get( 'desc', '' ) ) ) ),
                            dict( label='Request form',
                                  widget=request_form_id_select_field ),
                            dict( label='Sample form',
                                  widget=sample_form_id_select_field ) ]
        # Unsaved sample states being defined for this request type
        rt_states = []
        i=0
        while True:
            if kwd.has_key( 'state_name_%i' % i ):
                rt_states.append( ( util.restore_text( params.get( 'state_name_%i' % i, ''  ) ), 
                                    util.restore_text( params.get( 'state_desc_%i' % i, ''  ) ) ) )
                i += 1
            else:
                break
        return rt_info_widgets, rt_states
    @web.expose
    @web.require_admin
    def delete_request_type( self, trans, **kwd ):
        request_type_id = kwd.get( 'id', '' )
        request_type_id_list = util.listify( request_type_id )
        for request_type_id in request_type_id_list:
            try:
                request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
            except:
                return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
            request_type.deleted = True
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
        status = 'done'
        message = '%i request types has been deleted' % len( request_type_id_list )
        return trans.response.send_redirect( web.url_for( controller='request_type',
                                                          action='browse_request_types',
                                                          message=message,
                                                          status='done' ) )
    @web.expose
    @web.require_admin
    def undelete_request_type( self, trans, **kwd ):
        request_type_id = kwd.get( 'id', '' )
        request_type_id_list = util.listify( request_type_id )
        for request_type_id in request_type_id_list:
            try:
                request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
            except:
                return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
            request_type.deleted = False
            trans.sa_session.add( request_type )
            trans.sa_session.flush()
        status = 'done'
        message = '%i request types have been undeleted' % len( request_type_id_list )
        return trans.response.send_redirect( web.url_for( controller='request_type',
                                                          action='browse_request_types',
                                                          message=message,
                                                          status=status ) )
    @web.expose
    @web.require_admin
    def request_type_permissions( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        request_type_id = kwd.get( 'id', '' )
        try:
            request_type = trans.sa_session.query( trans.model.RequestType ).get( trans.security.decode_id( request_type_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', request_type_id, 'request type', action='browse_request_types' )
        roles = trans.sa_session.query( trans.model.Role ) \
                                .filter( trans.model.Role.table.c.deleted==False ) \
                                .order_by( trans.model.Role.table.c.name )
        if params.get( 'update_roles_button', False ):
            permissions = {}
            for k, v in trans.model.RequestType.permitted_actions.items():
                in_roles = [ trans.sa_session.query( trans.model.Role ).get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
            trans.app.security_agent.set_request_type_permissions( request_type, permissions )
            trans.sa_session.refresh( request_type )
            message = "Permissions updated for request type '%s'" % request_type.name
        return trans.fill_template( '/admin/request_type/request_type_permissions.mako',
                                    request_type=request_type,
                                    roles=roles,
                                    status=status,
                                    message=message )
    @web.expose
    @web.require_admin
    def view_form_definition( self, trans, **kwd ):
        form_definition_id = kwd.get( 'id', None )
        try:
            form_definition = trans.sa_session.query( trans.model.FormDefinition ).get( trans.security.decode_id( form_definition_id ) )
        except:
            return invalid_id_redirect( trans, 'request_type', form_definition_id, 'form definition', action='browse_request_types' )
        return trans.fill_template( '/admin/forms/view_form_definition.mako',
                                    form_definition=form_definition )

    # ===== Methods for building SelectFields used on various admin_requests forms
    def __build_sequencer_select_field( self, trans, sequencer=None ):
        if sequencer:
            selected_value = trans.security.encode_id( sequencer.id ) 
        else:
            selected_value = 'none'
        all_sequencers = trans.sa_session.query( trans.model.Sequencer ).filter( trans.model.Sequencer.table.c.deleted==False ).all()
        return build_select_field( trans,
                                   objs=all_sequencers,
                                   label_attr='name',
                                   select_field_name='sequencer_id',
                                   selected_value=selected_value,
                                   refresh_on_change=False )
