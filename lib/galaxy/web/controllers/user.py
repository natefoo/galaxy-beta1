"""
Contains the user interface in the Universe class
"""
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy import util
import logging, os, string, re, smtplib, socket
from random import choice
from email.MIMEText import MIMEText
from galaxy.web.form_builder import * 
from galaxy.util.json import from_json_string, to_json_string
from galaxy.web.framework.helpers import iff

log = logging.getLogger( __name__ )

require_login_template = """
<h1>Welcome to Galaxy</h1>

<p>
    This installation of Galaxy has been configured such that only users who are logged in may use it.%s
</p>
<p/>
"""
require_login_nocreation_template = require_login_template % ""
require_login_creation_template = require_login_template % "  If you don't already have an account, <a href='%s'>you may create one</a>."

VALID_USERNAME_RE = re.compile( "^[a-z0-9\-]+$" )

class User( BaseController, UsesFormDefinitionWidgets ):
    @web.expose
    def index( self, trans, webapp='galaxy', **kwd ):
        return trans.fill_template( '/user/index.mako', webapp=webapp )
    @web.expose
    def login( self, trans, webapp='galaxy', redirect_url='', refresh_frames=[], **kwd ):
        referer = kwd.get( 'referer', trans.request.referer )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', True ) )
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        header = ''
        user = None
        email = kwd.get( 'email', '' )
        if kwd.get( 'login_button', False ):
            password = kwd.get( 'password', '' )
            referer = kwd.get( 'referer', '' )
            if webapp == 'galaxy' and not refresh_frames:
                if trans.app.config.require_login:
                    refresh_frames = [ 'masthead', 'history', 'tools' ]
                else:
                    refresh_frames = [ 'masthead', 'history' ]
            user = trans.sa_session.query( trans.app.model.User ).filter( trans.app.model.User.table.c.email==email ).first()
            if not user:
                message = "No such user"
                status = 'error'
            elif user.deleted:
                message = "This account has been marked deleted, contact your Galaxy administrator to restore the account."
                status = 'error'
            elif user.external:
                message = "This account was created for use with an external authentication method, contact your local Galaxy administrator to activate it."
                status = 'error'
            elif not user.check_password( password ):
                message = "Invalid password"
                status = 'error'
            else:
                trans.handle_user_login( user, webapp )
                trans.log_event( "User logged in" )
                message = 'You are now logged in as %s.<br>You can <a target="_top" href="%s">go back to the page you were visiting</a> or <a target="_top" href="%s">go to the home page</a>.' % \
                    ( user.email, referer, url_for( '/' ) )
                if trans.app.config.require_login:
                    message += '  <a target="_top" href="%s">Click here</a> to continue to the home page.' % web.url_for( '/static/welcome.html' )
                redirect_url = referer
        if not user and trans.app.config.require_login:
            if trans.app.config.allow_user_creation:
                header = require_login_creation_template % web.url_for( action='create' )
            else:
                header = require_login_nocreation_template
        return trans.fill_template( '/user/login.mako',
                                    webapp=webapp,
                                    email=email,
                                    header=header,
                                    use_panels=use_panels,
                                    redirect_url=redirect_url,
                                    referer=referer,
                                    refresh_frames=refresh_frames,
                                    message=message,
                                    status=status,
                                    active_view="user" )
    @web.expose
    def logout( self, trans, webapp='galaxy' ):
        if webapp == 'galaxy':
            if trans.app.config.require_login:
                refresh_frames = [ 'masthead', 'history', 'tools' ]
            else:
                refresh_frames = [ 'masthead', 'history' ]
        else:
            refresh_frames = [ 'masthead' ]
        # Since logging an event requires a session, we'll log prior to ending the session
        trans.log_event( "User logged out" )
        trans.handle_user_logout()
        message = 'You have been logged out.<br>You can log in again, <a target="_top" href="%s">go back to the page you were visiting</a> or <a target="_top" href="%s">go to the home page</a>.' % \
            ( trans.request.referer, url_for( '/' ) )
        return trans.fill_template( '/user/logout.mako',
                                    webapp=webapp,
                                    refresh_frames=refresh_frames,
                                    message=message,
                                    status='done',
                                    active_view="user" )
    @web.expose
    def create( self, trans, redirect_url='', refresh_frames=[], **kwd ):
        params = util.Params( kwd )
        webapp = params.get( 'webapp', 'galaxy' )
        use_panels = util.string_as_bool( kwd.get( 'use_panels', True ) )
        email = util.restore_text( params.get( 'email', '' ) )
        # Do not sanitize passwords, so take from kwd
        # instead of params ( which were sanitized )
        password = kwd.get( 'password', '' )
        confirm = kwd.get( 'confirm', '' )
        username = util.restore_text( params.get( 'username', '' ) )
        subscribe = params.get( 'subscribe', '' )
        subscribe_checked = CheckboxField.is_checked( subscribe )
        admin_view = util.string_as_bool( params.get( 'admin_view', False ) )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        referer = kwd.get( 'referer', trans.request.referer )
        if not refresh_frames:
            if webapp == 'galaxy':
                if trans.app.config.require_login:
                    refresh_frames = [ 'masthead', 'history', 'tools' ]
                else:
                    refresh_frames = [ 'masthead', 'history' ]
            else:
                refresh_frames = [ 'masthead' ]
        error = ''
        if not trans.app.config.allow_user_creation and not trans.user_is_admin():
            error = 'User registration is disabled.  Please contact your Galaxy administrator for an account.'
        # Create the user, save all the user info and login to Galaxy
        elif params.get( 'create_user_button', False ):
            # Check email and password validity
            error = self.__validate( trans, params, email, password, confirm, username, webapp )
            if not error:
                # all the values are valid
                user = trans.app.model.User( email=email )
                user.set_password_cleartext( password )
                user.username = username
                trans.sa_session.add( user )
                trans.sa_session.flush()
                trans.app.security_agent.create_private_user_role( user )
                message = 'Now logged in as %s.<br><a target="_top" href="%s">Return to the home page.</a>' % ( user.email, url_for( '/' ) )
                if webapp == 'galaxy':
                    # We set default user permissions, before we log in and set the default history permissions
                    trans.app.security_agent.user_set_default_permissions( user,
                                                                           default_access_private=trans.app.config.new_user_dataset_access_role_default_private )
                    # save user info
                    self.__save_user_info( trans, user, action='create', new_user=True, **kwd )
                    if subscribe_checked:
                        # subscribe user to email list
                        if trans.app.config.smtp_server is None:
                            error = "Now logged in as " + user.email + ". However, subscribing to the mailing list has failed because mail is not configured for this Galaxy instance."
                        else:
                            msg = MIMEText( 'Join Mailing list.\n' )
                            to = msg[ 'To' ] = trans.app.config.mailing_join_addr
                            frm = msg[ 'From' ] = email
                            msg[ 'Subject' ] = 'Join Mailing List'
                            try:
                                s = smtplib.SMTP()
                                s.connect( trans.app.config.smtp_server )
                                s.sendmail( frm, [ to ], msg.as_string() )
                                s.close()
                            except:
                                error = "Now logged in as " + user.email + ". However, subscribing to the mailing list has failed."
                    if not error and not admin_view:
                        # The handle_user_login() method has a call to the history_set_default_permissions() method
                        # (needed when logging in with a history), user needs to have default permissions set before logging in
                        trans.handle_user_login( user, webapp )
                        trans.log_event( "User created a new account" )
                        trans.log_event( "User logged in" )
                    elif not error:
                        trans.response.send_redirect( web.url_for( controller='admin',
                                                                   action='users',
                                                                   message='Created new user account (%s)' % user.email,
                                                                   status='done' ) )
                elif not admin_view:
                    # Must be logging into the community space webapp
                    trans.handle_user_login( user, webapp )
            if not error:
                redirect_url = referer
        if error:
            message=error
            status='error'
        if webapp == 'galaxy':
            user_info_select, user_info_form, widgets = self.__user_info_ui( trans, **kwd )
        else:
            user_info_select = []
            user_info_form = []
            widgets = []
        return trans.fill_template( '/user/register.mako',
                                    email=email,
                                    password=password,
                                    confirm=confirm,
                                    username=username,
                                    subscribe_checked=subscribe_checked,
                                    admin_view=admin_view,
                                    user_info_select=user_info_select,
                                    user_info_form=user_info_form,
                                    widgets=widgets,
                                    webapp=webapp,
                                    use_panels=use_panels,
                                    referer=referer,
                                    redirect_url=redirect_url,
                                    refresh_frames=refresh_frames,
                                    message=message,
                                    status=status )
    def __save_user_info(self, trans, user, action, new_user=True, **kwd):
        '''
        This method saves the user information for new users as well as editing user
        info for existing users. For new users, the user info form is retrieved from 
        the one that user has selected. And for existing users, the user info form is 
        retrieved from the db.
        '''
        params = util.Params( kwd )
        # get all the user information forms
        user_info_forms = self.get_all_forms( trans, filter=dict(deleted=False),
                                              form_type=trans.app.model.FormDefinition.types.USER_INFO )
        if new_user:
            # if there are no user forms available then there is nothing to save
            if not len( user_info_forms ):
                return
            user_info_type = params.get( 'user_info_select', 'none'  )
            try:
                user_info_form = trans.sa_session.query( trans.app.model.FormDefinition ).get(int(user_info_type))
            except:
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action=action,
                                                                  message='Invalid user information form id',
                                                                  status='error') )
        else:
            if user.values:
                user_info_form = user.values.form_definition
            else:
                # user was created before any of the user_info forms were created
                if len(user_info_forms) > 1:
                    # when there are multiple user_info forms and the user or admin
                    # can change the user_info form 
                    user_info_type = params.get( 'user_info_select', 'none'  )
                    try:
                        user_info_form = trans.sa_session.query( trans.app.model.FormDefinition ).get(int(user_info_type))
                    except:
                        return trans.response.send_redirect( web.url_for( controller='user',
                                                                          action=action,
                                                                          message='Invalid user information form id',
                                                                          status='error') )      
                else:
                    # when there is only one user_info form then there is no way
                    # to change the user_info form 
                    user_info_form = user_info_forms[0]
        values = []
        for index, field in enumerate(user_info_form.fields):
            if field['type'] == 'AddressField':
                value = util.restore_text(params.get('field_%i' % index, ''))
                if value == 'new':
                    # save this new address in the list of this user's addresses
                    user_address = trans.app.model.UserAddress( user=user )
                    self.save_widget_field( trans, user_address, index, **kwd )
                    trans.sa_session.refresh( user )
                    values.append(int(user_address.id))
                elif value == unicode('none'):
                    values.append('')
                else:
                    values.append(int(value))
            elif field['type'] == 'CheckboxField':
                values.append(CheckboxField.is_checked( params.get('field_%i' % index, '') )) 
            else:
                values.append(util.restore_text(params.get('field_%i' % index, '')))
        if new_user or not user.values:
            # new user or existing 
            form_values = trans.app.model.FormValues(user_info_form, values)
            trans.sa_session.add( form_values )
            trans.sa_session.flush()
            user.values = form_values
        elif user.values:  
            # editing the user info of an existing user with existing user info
            user.values.content = values
            trans.sa_session.add( user.values )
        trans.sa_session.add( user )
        trans.sa_session.flush()
    def __validate_email( self, trans, email, user=None ):
        error = None
        if user and user.email == email:
            return None 
        if len( email ) == 0 or "@" not in email or "." not in email:
            error = "Enter a real email address"
        elif len( email ) > 255:
            error = "Email address exceeds maximum allowable length"
        elif trans.sa_session.query( trans.app.model.User ).filter_by( email=email ).first():
            error = "User with that email already exists"
        return error
    def __validate_username( self, trans, username, user=None ):
        # User names must be at least four characters in length and contain only lower-case
        # letters, numbers, and the '-' character.
        if username in [ 'None', None, '' ]:
            return None
        if user and user.username == username:
            return None
        if len( username ) < 4:
            return "User name must be at least 4 characters in length"
        if len( username ) > 255:
            return "User name cannot be more than 255 characters in length"
        if not( VALID_USERNAME_RE.match( username ) ):
            return "User name must contain only lower-case letters, numbers and '-'"
        if trans.sa_session.query( trans.app.model.User ).filter_by( username=username ).first():
            return "This user name is not available"
        return None
    def __validate_password( self, trans, password, confirm ):
        error = None
        if len( password ) < 6:
            error = "Use a password of at least 6 characters"
        elif password != confirm:
            error = "Passwords do not match"
        return error
    def __validate( self, trans, params, email, password, confirm, username, webapp ):
        # If coming from the community webapp, we'll require a public user name
        if webapp == 'community' and not username:
            return "A public user name is required"
        error = self.__validate_email( trans, email )
        if not error:
            error = self.__validate_password( trans, password, confirm )
        if not error and username:
            error = self.__validate_username( trans, username )
        if not error:
            if webapp == 'galaxy':
                if len( self.get_all_forms( trans, 
                                            filter=dict( deleted=False ),
                                            form_type=trans.app.model.FormDefinition.types.USER_INFO ) ):
                    if not params.get( 'user_info_select', False ):
                        return "Select the user's type and information"
        return error
    def __user_info_ui( self, trans, user=None, **kwd ):
        '''
        This method creates the user type select box & user information form widgets 
        and is called during user registration and editing user information.
        If there exists only one user information form then show it after main
        login info. However, if there are more than one user info forms then 
        show a selectbox containing all the forms, then the user can select 
        the one that fits the user's description the most
        '''
        params = util.Params( kwd )
        # get all the user information forms
        user_info_forms = self.get_all_forms( trans,
                                              filter=dict( deleted=False ),
                                              form_type=trans.app.model.FormDefinition.types.USER_INFO )
        user_info_select = None
        if user:
            if user.values:
                selected_user_form_id = user.values.form_definition.id
            else:
                selected_user_form_id = params.get( 'user_info_select', 'none'  )
        else:
            selected_user_form_id = params.get( 'user_info_select', 'none'  )
        # when there are more than one user information forms then show a select box
        # list all these forms
        if len(user_info_forms) > 1:
            # create the select box
            user_info_select = SelectField('user_info_select', refresh_on_change=True, 
                                           refresh_on_change_values=[str(u.id) for u in user_info_forms])
            if selected_user_form_id == 'none':
                user_info_select.add_option('Select one', 'none', selected=True)
            else:
                user_info_select.add_option('Select one', 'none')
            for u in user_info_forms:
                if selected_user_form_id == str(u.id):
                    user_info_select.add_option(u.name, u.id, selected=True)
                else:
                    user_info_select.add_option(u.name, u.id)
        # when there is just one user information form the just render that form
        elif len(user_info_forms) == 1:
            selected_user_form_id = user_info_forms[0].id
        # user information
        try:
            user_info_form = trans.sa_session.query( trans.app.model.FormDefinition ).get(int(selected_user_form_id))
        except:
            return user_info_select, None, None
        if user:
            if user.values:
                widgets = user_info_form.get_widgets(user=user, 
                                                     contents=user.values.content, 
                                                     **kwd)
            else:
                widgets = user_info_form.get_widgets(None, contents=[], **kwd)
        else:
            widgets = user_info_form.get_widgets(None, contents=[], **kwd)
        return user_info_select, user_info_form, widgets
    @web.expose
    def show_info( self, trans, **kwd ):
        '''
        This method displays the user information page which consists of login 
        information, public user name, reset password & other user information 
        obtained during registration
        '''
        params = util.Params( kwd )
        user_id = params.get( 'user_id', None )
        webapp = params.get( 'webapp', 'galaxy' )
        if user_id:
            user = trans.sa_session.query( trans.app.model.User ).get( int( user_id ) )
        else:
            user = trans.user
        if not user:
            raise AssertionError, "The user id (%s) is not valid" % str( user_id )
        email = util.restore_text( params.get( 'email', user.email ) )
        # Do not sanitize passwords, so take from kwd
        # instead of params ( which were sanitized )
        current = kwd.get( 'current', '' )
        password = kwd.get( 'password', '' )
        confirm = kwd.get( 'confirm', '' )
        username = util.restore_text( params.get( 'username', '' ) )
        if not username:
            username = user.username
        admin_view = util.string_as_bool( params.get( 'admin_view', False ) )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if webapp == 'galaxy':
            user_info_select, user_info_form, widgets = self.__user_info_ui( trans, user, **kwd )
            # user's addresses
            show_filter = util.restore_text( params.get( 'show_filter', 'Active'  ) )
            if show_filter == 'All':
                addresses = [address for address in user.addresses]
            elif show_filter == 'Deleted':
                addresses = [address for address in user.addresses if address.deleted]
            else:
                addresses = [address for address in user.addresses if not address.deleted]
            user_info_forms = self.get_all_forms( trans,
                                                  filter=dict( deleted=False ),
                                                  form_type=trans.app.model.FormDefinition.types.USER_INFO )
            return trans.fill_template( '/webapps/galaxy/user/info.mako',
                                        user=user,
                                        email=email,
                                        current=current,
                                        password=password,
                                        confirm=confirm,
                                        username=username,
                                        user_info_select=user_info_select,
                                        user_info_forms=user_info_forms,
                                        user_info_form=user_info_form,
                                        widgets=widgets, 
                                        addresses=addresses,
                                        show_filter=show_filter,
                                        admin_view=admin_view,
                                        webapp=webapp,
                                        message=message,
                                        status=status )
        else:
            return trans.fill_template( '/webapps/community/user/info.mako',
                                        user=user,
                                        email=email,
                                        current=current,
                                        password=password,
                                        confirm=confirm,
                                        username=username,
                                        admin_view=False,
                                        webapp=webapp,
                                        message=message,
                                        status=status )
    @web.expose
    def edit_info( self, trans, **kwd ):
        params = util.Params( kwd )
        user_id = params.get( 'user_id', None )
        admin_view = util.string_as_bool( params.get( 'admin_view', False ) )
        webapp = params.get( 'webapp', 'galaxy' )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if user_id:
            user = trans.sa_session.query( trans.app.model.User ).get( int( user_id ) )
        else:
            user = trans.user
        # Editing login info ( email & username )
        if params.get( 'login_info_button', False ):
            email = util.restore_text( params.get( 'email', '' ) )
            username = util.restore_text( params.get( 'username', '' ) ).lower()
            # validate the new values
            error = self.__validate_email( trans, email, user )
            if not error and username:
                error = self.__validate_username( trans, username, user )
            if error:
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action='show_info',
                                                                  webapp=webapp,
                                                                  message=error,
                                                                  status='error') )
            # The user's private role name must match the user's login ( email )
            private_role = trans.app.security_agent.get_private_user_role( user )
            private_role.name = email
            private_role.description = 'Private role for ' + email
            # Now change the user info
            user.email = email
            user.username = username
            trans.sa_session.add_all( ( user, private_role ) )
            trans.sa_session.flush()
            message = 'The login information has been updated with the changes'
            if webapp == 'galaxy' and admin_view:
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action='show_info',
                                                                  user_id=user.id,
                                                                  admin_view=admin_view,
                                                                  webapp=webapp,
                                                                  message=message,
                                                                  status='done' ) )
            return trans.response.send_redirect( web.url_for( controller='user',
                                                              action='show_info',
                                                              webapp=webapp,
                                                              message=message,
                                                              status='done') )
        # Change password 
        elif params.get( 'change_password_button', False ):
            # Do not sanitize passwords, so get from kwd and not params
            # ( which were sanitized ).
            password = kwd.get( 'password', '' )
            confirm = kwd.get( 'confirm', '' )
            # When from the user perspective, validate the current password
            if not webapp == 'galaxy' and not admin_view:
                # Do not sanitize passwords, so get from kwd and not params
                # ( which were sanitized ).
                current = kwd.get( 'current', '' )
                if not trans.user.check_password( current ):
                    return trans.response.send_redirect( web.url_for( controller='user',
                                                                      action='show_info',
                                                                      webapp=webapp,
                                                                      message='Invalid current password',
                                                                      status='error') )
            # validate the new values
            error = self.__validate_password( trans, password, confirm )
            if error:
                if webapp == 'galaxy' and admin_view:
                    return trans.response.send_redirect( web.url_for( controller='user',
                                                                      action='show_info',
                                                                      webapp=webapp,
                                                                      user_id=user.id,
                                                                      admin_view=admin_view,
                                                                      message=error,
                                                                      status='error' ) )
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action='show_info',
                                                                  webapp=webapp,
                                                                  message=error,
                                                                  status='error') )
            # save new password
            user.set_password_cleartext( password )
            trans.sa_session.add( user )
            trans.sa_session.flush()
            trans.log_event( "User change password" )
            message = 'The password has been changed.'
            if webapp == 'galaxy' and admin_view:
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action='show_info',
                                                                  webapp=webapp,
                                                                  user_id=user.id,
                                                                  admin_view=admin_view,
                                                                  message=message,
                                                                  status='done' ) )
            return trans.response.send_redirect( web.url_for( controller='user',
                                                              action='show_info',
                                                              webapp=webapp,
                                                              message=message,
                                                              status='done') )
        # Edit user information - webapp MUST BE 'galaxy'
        elif params.get( 'edit_user_info_button', False ):
            self.__save_user_info(trans, user, "show_info", new_user=False, **kwd)
            message = "The user information has been updated with the changes."
            if admin_view:
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action='show_info',
                                                                  webapp=webapp,
                                                                  user_id=user.id,
                                                                  admin_view=admin_view,
                                                                  message=message,
                                                                  status='done' ) )
            return trans.response.send_redirect( web.url_for( controller='user',
                                                              action='show_info',
                                                              webapp=webapp,
                                                              message=message,
                                                              status='done') )
        else:
            if webapp == 'galaxy' and admin_view:
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action='show_info',
                                                                  webapp=webapp,
                                                                  user_id=user.id,
                                                                  admin_view=admin_view ) )
            return trans.response.send_redirect( web.url_for( controller='user',
                                                              action='show_info',
                                                              webapp=webapp ) )
    @web.expose
    def reset_password( self, trans, email=None, webapp='galaxy', **kwd ):
        if trans.app.config.smtp_server is None:
            return trans.show_error_message( "Mail is not configured for this Galaxy instance.  Please contact an administrator." )
        message = util.restore_text( kwd.get( 'message', '' ) )
        status = 'done'
        if kwd.get( 'reset_password_button', False ):
            reset_user = trans.sa_session.query( trans.app.model.User ).filter( trans.app.model.User.table.c.email==email ).first()
            user = trans.get_user()
            if reset_user:
                if user and user.id != reset_user.id:
                    message = "You may only reset your own password"
                    status = 'error'
                else:
                    chars = string.letters + string.digits
                    new_pass = ""
                    for i in range(15):
                        new_pass = new_pass + choice(chars)
                    host = trans.request.host.split(':')[0]
                    if host == 'localhost':
                        host = socket.getfqdn()
                    msg = MIMEText( 'Your password on %s has been reset to:\n\n  %s\n' % ( host, new_pass ) )
                    to = msg[ 'To' ] = email
                    frm = msg[ 'From' ] = 'galaxy-no-reply@' + host
                    msg[ 'Subject' ] = 'Galaxy Password Reset'
                    try:
                        s = smtplib.SMTP()
                        s.connect( trans.app.config.smtp_server )
                        s.sendmail( frm, [ to ], msg.as_string() )
                        s.close()
                        reset_user.set_password_cleartext( new_pass )
                        trans.sa_session.add( reset_user )
                        trans.sa_session.flush()
                        trans.log_event( "User reset password: %s" % email )
                        message = "Password has been reset and emailed to: %s.  <a href='%s'>Click here</a> to return to the login form." % ( email, web.url_for( action='login' ) )
                    except Exception, e:
                        message = 'Failed to reset password: %s' % str( e )
                        status = 'error'
                    return trans.response.send_redirect( web.url_for( controller='user',
                                                                      action='reset_password',
                                                                      message=message,
                                                                      status=status ) )
            elif email != None:
                message = "The specified user does not exist"
                status = 'error'
            elif email is None:
                email = ""
        return trans.fill_template( '/user/reset_password.mako',
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    def set_default_permissions( self, trans, **kwd ):
        """Sets the user's default permissions for the new histories"""
        if trans.user:
            if 'update_roles_button' in kwd:
                p = util.Params( kwd )
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = p.get( k + '_in', [] )
                    if not isinstance( in_roles, list ):
                        in_roles = [ in_roles ]
                    in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in in_roles ]
                    action = trans.app.security_agent.get_action( v.action ).action
                    permissions[ action ] = in_roles
                trans.app.security_agent.user_set_default_permissions( trans.user, permissions )
                return trans.show_ok_message( 'Default new history permissions have been changed.' )
            return trans.fill_template( 'user/permissions.mako' )
        else:
            # User not logged in, history group must be only public
            return trans.show_error_message( "You must be logged in to change your default permitted actions." )   
    @web.expose
    @web.require_login( "to get most recently used tool" )
    @web.json_pretty
    def get_most_recently_used_tool_async( self, trans ):
        """ Returns information about the most recently used tool. """
        
        # Get most recently used tool.
        query = trans.sa_session.query( self.app.model.Job.tool_id ).join( self.app.model.History ). \
                                        filter( self.app.model.History.user==trans.user ). \
                                        order_by( self.app.model.Job.create_time.desc() ).limit(1)
        tool_id = query[0][0] # Get first element in first row of query.
        tool = self.get_toolbox().tools_by_id[ tool_id ]
        
        # Return tool info.
        tool_info = { 
            "id" : tool.id, 
            "link" : url_for( controller='tool_runner', tool_id=tool.id ),
            "target" : tool.target,
            "name" : tool.name, ## TODO: translate this using _()
            "minsizehint" : tool.uihints.get( 'minwidth', -1 ),
            "description" : tool.description
        }
        return tool_info          
    @web.expose
    def manage_addresses(self, trans, **kwd):
        if trans.user:
            params = util.Params( kwd )
            message = util.restore_text( params.get( 'message', ''  ) )
            status = params.get( 'status', 'done' )
            show_filter = util.restore_text( params.get( 'show_filter', 'Active'  ) )
            if show_filter == 'All':
                addresses = [address for address in trans.user.addresses]
            elif show_filter == 'Deleted':
                addresses = [address for address in trans.user.addresses if address.deleted]
            else:
                addresses = [address for address in trans.user.addresses if not address.deleted]
            return trans.fill_template( 'user/address.mako', 
                                        addresses=addresses,
                                        show_filter=show_filter,
                                        message=message,
                                        status=status)
        else:
            # User not logged in, history group must be only public
            return trans.show_error_message( "You must be logged in to change your default permitted actions." )
    @web.expose
    def new_address( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        admin_view = util.string_as_bool( params.get( 'admin_view', False ) )
        user_id = params.get( 'user_id', False )
        if not user_id:
            # User must be logged in to create a new address
            return trans.show_error_message( "You must be logged in to create a new address." )
        user = trans.sa_session.query( trans.app.model.User ).get( int( user_id ) )
        short_desc = util.restore_text( params.get( 'short_desc', ''  ) )
        name = util.restore_text( params.get( 'name', ''  ) )
        institution = util.restore_text( params.get( 'institution', ''  ) )
        address = util.restore_text( params.get( 'address', ''  ) )
        city = util.restore_text( params.get( 'city', ''  ) )
        state = util.restore_text( params.get( 'state', ''  ) )
        postal_code = util.restore_text( params.get( 'postal_code', ''  ) )
        country = util.restore_text( params.get( 'country', ''  ) )
        phone = util.restore_text( params.get( 'phone', ''  ) )
        ok = True
        if not trans.app.config.allow_user_creation and not trans.user_is_admin():
            return trans.show_error_message( 'User registration is disabled.  Please contact your Galaxy administrator for an account.' )
        if params.get( 'new_address_button', False ):
            if not short_desc:
                ok = False
                message = 'Enter a short description for this address'
            elif not name:
                ok = False
                message = 'Enter the name'
            elif not institution:
                ok = False
                message = 'Enter the institution associated with the user'
            elif not address:
                ok = False
                message = 'Enter the address'
            elif not city:
                ok = False
                message = 'Enter the city'
            elif not state:
                ok = False
                message = 'Enter the state/province/region'
            elif not postal_code:
                ok = False
                message = 'Enter the postal code'
            elif not country:
                ok = False
                message = 'Enter the country'
            if ok:
                user_address = trans.model.UserAddress( user=user,
                                                        desc=short_desc,
                                                        name=name,
                                                        institution=institution, 
                                                        address=address,
                                                        city=city,
                                                        state=state,
                                                        postal_code=postal_code, 
                                                        country=country,
                                                        phone=phone )
                trans.sa_session.add( user_address )
                trans.sa_session.flush()
                message = 'Address (%s) has been added' % user_address.desc
                if admin_view:
                    return trans.response.send_redirect( web.url_for( controller='user',
                                                                      action='show_info',
                                                                      admin_view=admin_view,
                                                                      user_id=user.id,
                                                                      message=message,
                                                                      status='done' ) )
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action='show_info',
                                                                  message=message,
                                                                  status='done' ) )
        # Display the address form with the current values filled in
        return trans.fill_template( 'user/new_address.mako',
                                    user=user,
                                    admin_view=admin_view,
                                    short_desc=short_desc,
                                    name=name,
                                    institution=institution,
                                    address=address,
                                    city=city,
                                    state=state,
                                    postal_code=postal_code,
                                    country=country,
                                    phone=phone,
                                    message=message,
                                    status=status )
    @web.expose
    def edit_address( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        admin_view = util.string_as_bool( params.get( 'admin_view', False ) )
        user_id = params.get( 'user_id', False )
        if not user_id:
            # User must be logged in to create a new address
            return trans.show_error_message( "You must be logged in to create a new address." )
        user = trans.sa_session.query( trans.app.model.User ).get( int( user_id ) )
        address_id = params.get( 'address_id', None )
        if not address_id:
            return trans.show_error_message( "No address_id received for editing." )
        address_obj = trans.sa_session.query( trans.app.model.UserAddress ).get( int( address_id ) )     
        if params.get( 'edit_address_button', False  ):
            short_desc = util.restore_text( params.get( 'short_desc', ''  ) )
            name = util.restore_text( params.get( 'name', ''  ) )
            institution = util.restore_text( params.get( 'institution', ''  ) )
            address = util.restore_text( params.get( 'address', ''  ) )
            city = util.restore_text( params.get( 'city', ''  ) )
            state = util.restore_text( params.get( 'state', ''  ) )
            postal_code = util.restore_text( params.get( 'postal_code', ''  ) )
            country = util.restore_text( params.get( 'country', ''  ) )
            phone = util.restore_text( params.get( 'phone', ''  ) )
            ok = True
            if not short_desc:
                ok = False
                message = 'Enter a short description for this address'
            elif not name:
                ok = False
                message = 'Enter the name'
            elif not institution:
                ok = False
                message = 'Enter the institution associated with the user'
            elif not address:
                ok = False
                message = 'Enter the address'
            elif not city:
                ok = False
                message = 'Enter the city'
            elif not state:
                ok = False
                message = 'Enter the state/province/region'
            elif not postal_code:
                ok = False
                message = 'Enter the postal code'
            elif not country:
                ok = False
                message = 'Enter the country'
            if ok:
                address_obj.desc = short_desc
                address_obj.name = name
                address_obj.institution = institution
                address_obj.address = address
                address_obj.city = city
                address_obj.state = state
                address_obj.postal_code = postal_code
                address_obj.country = country
                address_obj.phone = phone
                trans.sa_session.add( address_obj )
                trans.sa_session.flush()
                message = 'Address (%s) has been updated.' % address_obj.desc
                if admin_view:
                    return trans.response.send_redirect( web.url_for( controller='user',
                                                                      action='show_info',
                                                                      user_id=user.id,
                                                                      admin_view=admin_view,
                                                                      message=message,
                                                                      status='done' ) )
                return trans.response.send_redirect( web.url_for( controller='user',
                                                                  action='show_info',
                                                                  message=message,
                                                                  status='done' ) )
        # Display the address form with the current values filled in
        return trans.fill_template( 'user/edit_address.mako',
                                    user=user,
                                    address_obj=address_obj,
                                    admin_view=admin_view,
                                    message=message,
                                    status=status )
    @web.expose
    def delete_address( self, trans, address_id=None, user_id=None, admin_view=False ):
        try:
            user_address = trans.sa_session.query( trans.app.model.UserAddress ).get( int( address_id ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='user',
                                                              action='show_info',
                                                              user_id=user_id,
                                                              admin_view=admin_view,
                                                              message='Invalid address ID',
                                                              status='error' ) )
        user_address.deleted = True
        trans.sa_session.add( user_address )
        trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='user',
                                                          action='show_info',
                                                          admin_view=admin_view,
                                                          user_id=user_id,
                                                          message='Address (%s) deleted' % user_address.desc,
                                                          status='done') )
    @web.expose
    def undelete_address( self, trans, address_id=None, user_id=None, admin_view=False ):
        try:
            user_address = trans.sa_session.query( trans.app.model.UserAddress ).get( int( address_id ) )
        except:
            return trans.response.send_redirect( web.url_for( controller='user',
                                                              action='show_info',
                                                              user_id=user_id,
                                                              admin_view=admin_view,
                                                              message='Invalid address ID',
                                                              status='error' ) )
        user_address.deleted = False
        trans.sa_session.flush()
        return trans.response.send_redirect( web.url_for( controller='user',
                                                          action='show_info',
                                                          admin_view=admin_view,
                                                          user_id=user_id,
                                                          message='Address (%s) undeleted' % user_address.desc,
                                                          status='done') )
    @web.expose
    def set_user_pref_async( self, trans, pref_name, pref_value ):
        """ Set a user preference asynchronously. If user is not logged in, do nothing. """
        if trans.user:
            trans.log_action( trans.get_user(), "set_user_pref", "", { pref_name : pref_value } )
            trans.user.preferences[pref_name] = pref_value
            trans.sa_session.flush()
    @web.expose
    def log_user_action_async( self, trans, action, context, params ):
        """ Log a user action asynchronously. If user is not logged in, do nothing. """
        if trans.user:
            trans.log_action( trans.get_user(), action, context, params )
    @web.expose
    @web.require_login()
    def dbkeys( self, trans, **kwds ):
        user = trans.get_user()
        message = None
        lines_skipped = 0
        if 'dbkeys' not in user.preferences:
            dbkeys = {}
        else:
            dbkeys = from_json_string(user.preferences['dbkeys'])
        
        if 'delete' in kwds:
            key = kwds.get('key', '')
            if key and key in dbkeys:
                del dbkeys[key]
            
        elif 'add' in kwds:
            name     = kwds.get('name', '')
            key      = kwds.get('key', '')
            len_file = kwds.get('len_file', None)
            if getattr(len_file, "file", None): # Check if it's a FieldStorage object
                len_text = len_file.file.read()
            else:
                len_text = kwds.get('len_text', '')
            if not name or not key or not len_text:
                message = "You must specify values for all the fields."
            else:
                # Create new len file
                new_len = trans.app.model.HistoryDatasetAssociation( extension="len", create_dataset=True, sa_session=trans.sa_session )
                trans.sa_session.add( new_len )
                new_len.name = name
                new_len.visible = False
                new_len.state = trans.app.model.Job.states.OK
                new_len.info = "custom build .len file"
                trans.sa_session.flush()
                
                counter = 0
                f = open(new_len.file_name, "w")
                for line in len_text.split("\n"):
                    lst = line.strip().split()
                    if not lst or len(lst) < 2:
                        lines_skipped += 1
                        continue
                    chrom, length = lst[0], lst[1]
                    try:
                        length = int(length)
                    except ValueError:
                        lines_skipped += 1
                        continue
                    counter += 1
                    f.write("%s\t%s\n" % (chrom, length))
                f.close()
                dbkeys[key] = { "name": name, "len": new_len.id, "count": counter }
        
        user.preferences['dbkeys'] = to_json_string(dbkeys)
        trans.sa_session.flush()
        
        return trans.fill_template( 'user/dbkeys.mako',
                                    user=user,
                                    dbkeys=dbkeys,
                                    message=message,
                                    lines_skipped=lines_skipped )          
    @web.expose
    def api_keys( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        error = ''
        if params.get( 'new_api_key_button', None  ) == 'Generate a new key now':
            new_key = trans.app.model.APIKeys()
            new_key.user_id = trans.user.id
            new_key.key = trans.app.security.get_new_guid()
            trans.sa_session.add( new_key )
            trans.sa_session.flush()
            message = "Generated a new web API key"
            status = "done"
        return trans.fill_template( 'webapps/galaxy/user/api_keys.mako',
                                    user=trans.user,
                                    message=message,
                                    status=status )
