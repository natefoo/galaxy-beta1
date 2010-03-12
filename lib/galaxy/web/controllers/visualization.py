from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, grids, iff
from galaxy.util.sanitize_html import sanitize_html


class VisualizationListGrid( grids.Grid ):
    # Grid definition
    title = "Saved Visualizations"
    model_class = model.Visualization
    default_sort_key = "-update_time"
    default_filter = dict( title="All", deleted="False", tags="All", sharing="All" )
    columns = [
        grids.TextColumn( "Title", key="title", model_class=model.Visualization, attach_popup=True,
                         link=( lambda item: dict( controller="tracks", action="browser", id=item.id ) ) ),
        grids.TextColumn( "Type", key="type", model_class=model.Visualization ),
        grids.IndividualTagsColumn( "Tags", "tags", model.Visualization, model.VisualizationTagAssociation, filterable="advanced", grid_name="VisualizationListGrid" ),
        grids.SharingStatusColumn( "Sharing", key="sharing", model_class=model.Visualization, filterable="advanced", sortable=False ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
    ]    
    columns.append( 
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[2] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
    operations = [
        grids.GridOperation( "Edit content", allow_multiple=False, url_args=dict( controller='tracks', action='browser' ) ),
        grids.GridOperation( "Edit attributes", allow_multiple=False, url_args=dict( action='edit') ),
        grids.GridOperation( "Share or Publish", allow_multiple=False, condition=( lambda item: not item.deleted ), async_compatible=False ),
        grids.GridOperation( "Delete", condition=( lambda item: not item.deleted ), async_compatible=True, confirm="Are you sure you want to delete this visualization?" ),
    ]
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, deleted=False )
        
class VisualizationAllPublishedGrid( grids.Grid ):
    # Grid definition
    use_panels = True
    use_async = True
    title = "Published Visualizations"
    model_class = model.Visualization
    default_sort_key = "-update_time"
    default_filter = dict( title="All", username="All" )
    columns = [
        grids.PublicURLColumn( "Title", key="title", model_class=model.Visualization, filterable="advanced" ),
        grids.OwnerAnnotationColumn( "Annotation", key="annotation", model_class=model.Visualization, model_annotation_association_class=model.VisualizationAnnotationAssociation, filterable="advanced" ),
        grids.OwnerColumn( "Owner", key="username", model_class=model.User, filterable="advanced", sortable=False ), 
        grids.CommunityTagsColumn( "Community Tags", "tags", model.Visualization, model.VisualizationTagAssociation, filterable="advanced", grid_name="VisualizationAllPublishedGrid" ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago )
    ]
    columns.append( 
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[1], columns[2], columns[3] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
    def build_initial_query( self, session ):
        # Join so that searching history.user makes sense.
        return session.query( self.model_class ).join( model.User.table )
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter( self.model_class.deleted==False ).filter( self.model_class.published==True )


class VisualizationController( BaseController, Sharable, UsesAnnotations, UsesVisualization ):
    _user_list_grid = VisualizationListGrid()
    _published_list_grid = VisualizationAllPublishedGrid()
    
    @web.expose
    def list_published( self, trans, *args, **kwargs ):
        grid = self._published_list_grid( trans, **kwargs )
        if 'async' in kwargs:
            return grid
        else:
            # Render grid wrapped in panels
            return trans.fill_template( "visualization/list_published.mako", grid=grid )
    
    @web.expose
    @web.require_login("use Galaxy visualizations")
    def list( self, trans, *args, **kwargs ):
        # Handle operation
        if 'operation' in kwargs and 'id' in kwargs:
            session = trans.sa_session
            operation = kwargs['operation'].lower()
            ids = util.listify( kwargs['id'] )
            for id in ids:
                item = session.query( model.Visualization ).get( trans.security.decode_id( id ) )
                if operation == "delete":
                    item.deleted = True
                if operation == "share or publish":
                    return self.sharing( trans, **kwargs )
            session.flush()
            
        # Build list of visualizations shared with user.
        shared_by_others = trans.sa_session \
            .query( model.VisualizationUserShareAssociation ) \
            .filter_by( user=trans.get_user() ) \
            .join( model.Visualization.table ) \
            .filter( model.Visualization.deleted == False ) \
            .order_by( desc( model.Visualization.update_time ) ) \
            .all()
        
        return trans.fill_template( "visualization/list.mako", grid=self._user_list_grid( trans, *args, **kwargs ), shared_by_others=shared_by_others )
        
    @web.expose
    @web.require_login( "modify Galaxy visualizations" )
    def set_slug_async( self, trans, id, new_slug ):
        """ Set item slug asynchronously. """
        visualization = self.get_visualization( trans, id )
        if visualization:
            visualization.slug = new_slug
            trans.sa_session.flush()
            return visualization.slug

    @web.expose
    @web.require_login( "share Galaxy visualizations" )
    def sharing( self, trans, id, **kwargs ):
        """ Handle visualization sharing. """

        # Get session and visualization.
        session = trans.sa_session
        visualization = trans.sa_session.query( model.Visualization ).get( trans.security.decode_id( id ) )

        # Do operation on visualization.
        if 'make_accessible_via_link' in kwargs:
            self._make_item_accessible( trans.sa_session, visualization )
        elif 'make_accessible_and_publish' in kwargs:
            self._make_item_accessible( trans.sa_session, visualization )
            visualization.published = True
        elif 'publish' in kwargs:
            visualization.published = True
        elif 'disable_link_access' in kwargs:
            visualization.importable = False
        elif 'unpublish' in kwargs:
            visualization.published = False
        elif 'disable_link_access_and_unpublish' in kwargs:
            visualization.importable = visualization.published = False
        elif 'unshare_user' in kwargs:
            user = session.query( model.User ).get( trans.security.decode_id( kwargs['unshare_user' ] ) )
            if not user:
                error( "User not found for provided id" )
            association = session.query( model.VisualizationUserShareAssociation ) \
                                 .filter_by( user=user, visualization=visualization ).one()
            session.delete( association )

        session.flush()

        return trans.fill_template( "/sharing_base.mako", item=visualization )

    @web.expose
    @web.require_login( "share Galaxy visualizations" )
    def share( self, trans, id=None, email="", **kwd ):
        """ Handle sharing a visualization with a particular user. """
        msg = mtype = None
        visualization = trans.sa_session.query( model.Visualization ).get( trans.security.decode_id( id ) )
        if email:
            other = trans.sa_session.query( model.User ) \
                                    .filter( and_( model.User.table.c.email==email,
                                                   model.User.table.c.deleted==False ) ) \
                                    .first()
            if not other:
                mtype = "error"
                msg = ( "User '%s' does not exist" % email )
            elif other == trans.get_user():
                mtype = "error"
                msg = ( "You cannot share a visualization with yourself" )
            elif trans.sa_session.query( model.VisualizationUserShareAssociation ) \
                    .filter_by( user=other, visualization=visualization ).count() > 0:
                mtype = "error"
                msg = ( "Visualization already shared with '%s'" % email )
            else:
                share = model.VisualizationUserShareAssociation()
                share.visualization = visualization
                share.user = other
                session = trans.sa_session
                session.add( share )
                self.create_item_slug( session, visualization )
                session.flush()
                trans.set_message( "Visualization '%s' shared with user '%s'" % ( visualization.title, other.email ) )
                return trans.response.send_redirect( url_for( action='sharing', id=id ) )
        return trans.fill_template( "/share_base.mako",
                                    message = msg,
                                    messagetype = mtype,
                                    item=visualization,
                                    email=email )
        

    @web.expose
    def display_by_username_and_slug( self, trans, username, slug ):
        """ Display visualization based on a username and slug. """

        # Get visualization.
        session = trans.sa_session
        user = session.query( model.User ).filter_by( username=username ).first()
        visualization = trans.sa_session.query( model.Visualization ).filter_by( user=user, slug=slug, deleted=False ).first()
        if visualization is None:
            raise web.httpexceptions.HTTPNotFound()
        # Security check raises error if user cannot access visualization.
        self.security_check( trans.get_user(), visualization, False, True)    
        return trans.fill_template_mako( "visualization/display.mako", item=visualization, item_data=None, content_only=True )
        
    @web.expose
    @web.json
    @web.require_login( "get item name and link" )
    def get_name_and_link_async( self, trans, id=None ):
        """ Returns visualization's name and link. """
        visualization = self.get_visualization( trans, id )

        if self.create_item_slug( trans.sa_session, visualization ):
            trans.sa_session.flush()
        return_dict = { "name" : visualization.title, "link" : url_for( action="display_by_username_and_slug", username=visualization.user.username, slug=visualization.slug ) }
        return return_dict

    @web.expose
    @web.require_login("get item content asynchronously")
    def get_item_content_async( self, trans, id ):
        """ Returns item content in HTML format. """
        pass
        
    @web.expose
    @web.require_login( "create visualizations" )
    def create( self, trans, visualization_title="", visualization_slug="", visualization_annotation="" ):
        """
        Create a new visualization
        """
        user = trans.get_user()
        visualization_title_err = visualization_slug_err = visualization_annotation_err = ""
        if trans.request.method == "POST":
            if not visualization_title:
                visualization_title_err = "visualization name is required"
            elif not visualization_slug:
                visualization_slug_err = "visualization id is required"
            elif not VALID_SLUG_RE.match( visualization_slug ):
                visualization_slug_err = "visualization identifier must consist of only lowercase letters, numbers, and the '-' character"
            elif trans.sa_session.query( model.Visualization ).filter_by( user=user, slug=visualization_slug, deleted=False ).first():
                visualization_slug_err = "visualization id must be unique"
            else:
                # Create the new stored visualization
                visualization = model.Visualization()
                visualization.title = visualization_title
                visualization.slug = visualization_slug
                visualization_annotation = sanitize_html( visualization_annotation, 'utf-8', 'text/html' )
                self.add_item_annotation( trans, visualization, visualization_annotation )
                visualization.user = user
                # And the first (empty) visualization revision
                visualization_revision = model.VisualizationRevision()
                visualization_revision.title = visualization_title
                visualization_revision.visualization = visualization
                visualization.latest_revision = visualization_revision
                visualization_revision.content = ""
                # Persist
                session = trans.sa_session
                session.add( visualization )
                session.flush()
                # Display the management visualization
                ## trans.set_message( "Visualization '%s' created" % visualization.title )
                return trans.response.send_redirect( web.url_for( action='list' ) )
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Create new visualization", submit_text="Submit" )
                .add_text( "visualization_title", "Visualization title", value=visualization_title, error=visualization_title_err )
                .add_text( "visualization_slug", "Visualization identifier", value=visualization_slug, error=visualization_slug_err,
                           help="""A unique identifier that will be used for
                                public links to this visualization. A default is generated
                                from the visualization title, but can be edited. This field
                                must contain only lowercase letters, numbers, and
                                the '-' character.""" )
                .add_text( "visualization_annotation", "Visualization annotation", value=visualization_annotation, error=visualization_annotation_err,
                            help="A description of the visualization; annotation is shown alongside published visualizations."),
                template="visualization/create.mako" )
        
    @web.expose
    @web.require_login( "edit visualizations" )
    def edit( self, trans, id, visualization_title="", visualization_slug="", visualization_annotation="" ):
        """
        Edit a visualization's attributes.
        """
        encoded_id = id
        id = trans.security.decode_id( id )
        session = trans.sa_session
        visualization = session.query( model.Visualization ).get( id )
        user = trans.user
        assert visualization.user == user
        visualization_title_err = visualization_slug_err = visualization_annotation_err = ""
        if trans.request.method == "POST":
            if not visualization_title:
                visualization_title_err = "Visualization name is required"
            elif not visualization_slug:
                visualization_slug_err = "Visualization id is required"
            elif not VALID_SLUG_RE.match( visualization_slug ):
                visualization_slug_err = "Visualization identifier must consist of only lowercase letters, numbers, and the '-' character"
            elif visualization_slug != visualization.slug and trans.sa_session.query( model.Visualization ).filter_by( user=user, slug=visualization_slug, deleted=False ).first():
                visualization_slug_err = "Visualization id must be unique"
            elif not visualization_annotation:
                visualization_annotation_err = "Visualization annotation is required"
            else:
                visualization.title = visualization_title
                visualization.slug = visualization_slug
                visualization_annotation = sanitize_html( visualization_annotation, 'utf-8', 'text/html' )
                self.add_item_annotation( trans, visualization, visualization_annotation )
                session.flush()
                # Redirect to visualization list.
                return trans.response.send_redirect( web.url_for( action='list' ) )
        else:
            visualization_title = visualization.title
            # Create slug if it's not already set.
            if visualization.slug is None:
                self.create_item_slug( trans.sa_session, visualization )
            visualization_slug = visualization.slug
            visualization_annotation = self.get_item_annotation_str( trans.sa_session, trans.get_user(), visualization )
            if not visualization_annotation:
                visualization_annotation = ""
        return trans.show_form( 
            web.FormBuilder( web.url_for( id=encoded_id ), "Edit visualization attributes", submit_text="Submit" )
                .add_text( "visualization_title", "Visualization title", value=visualization_title, error=visualization_title_err )
                .add_text( "visualization_slug", "Visualization identifier", value=visualization_slug, error=visualization_slug_err,
                           help="""A unique identifier that will be used for
                                public links to this visualization. A default is generated
                                from the visualization title, but can be edited. This field
                                must contain only lowercase letters, numbers, and
                                the '-' character.""" )
                .add_text( "visualization_annotation", "Visualization annotation", value=visualization_annotation, error=visualization_annotation_err,
                            help="A description of the visualization; annotation is shown alongside published visualizations."),
            template="visualization/create.mako" )
    
    # @web.expose
    # @web.require_login()
    # def list( self, trans, *args, **kwargs ):
    #     return self.list_grid( trans, *args, **kwargs )
    
    #@web.expose
    #@web.require_admin  
    #def index( self, trans, *args, **kwargs ):
    #    # Build grid
    #    grid = self.list( trans, *args, **kwargs )
    #    # Render grid wrapped in panels
    #    return trans.fill_template( "visualization/index.mako", grid=grid )
    
    