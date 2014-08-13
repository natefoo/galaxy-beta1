define(["mvc/dataset/states","mvc/base-mvc","utils/localization"],function(a,b,c){var e=b.ListItemView;var d=e.extend({className:e.prototype.className+" dataset",id:function(){return["dataset",this.model.get("id")].join("-")},initialize:function(f){if(f.logger){this.logger=this.model.logger=f.logger}this.log(this+".initialize:",f);e.prototype.initialize.call(this,f);this.linkTarget=f.linkTarget||"_blank";this._setUpListeners()},_setUpListeners:function(){this.on("selectable",function(f){if(f){this.$(".primary-actions").hide()}else{this.$(".primary-actions").show()}});this.model.on("change",function(g,f){if(this.model.changedAttributes().state&&this.model.inReadyState()&&this.expanded&&!this.model.hasDetails()){this.model.fetch()}else{this.render()}},this);this.on("all",function(f){this.log(f)},this)},_fetchModelDetails:function(){var f=this;if(f.model.inReadyState()&&!f.model.hasDetails()){return f.model.fetch({silent:true})}return jQuery.when()},remove:function(g,h){var f=this;g=g||this.fxSpeed;this.$el.fadeOut(g,function(){Backbone.View.prototype.remove.call(f);if(h){h.call(f)}})},render:function(f){return e.prototype.render.call(this,f)},_swapNewRender:function(f){e.prototype._swapNewRender.call(this,f);if(this.model.has("state")){this.$el.addClass("state-"+this.model.get("state"))}return this.$el},_renderPrimaryActions:function(){return[this._renderDisplayButton()]},_renderDisplayButton:function(){var h=this.model.get("state");if((h===a.NOT_VIEWABLE)||(h===a.DISCARDED)||(!this.model.get("accessible"))){return null}var g={target:this.linkTarget,classes:"display-btn"};if(this.model.get("purged")){g.disabled=true;g.title=c("Cannot display datasets removed from disk")}else{if(h===a.UPLOAD){g.disabled=true;g.title=c("This dataset must finish uploading before it can be viewed")}else{if(h===a.NEW){g.disabled=true;g.title=c("This dataset is not yet viewable")}else{g.title=c("View data");g.href=this.model.urls.display;var f=this;g.onclick=function(i){if(Galaxy.frame&&Galaxy.frame.active){Galaxy.frame.add({title:"Data Viewer: "+f.model.get("name"),type:"other",content:function(j){var k=new DATA.TabularDataset({id:f.model.get("id")});$.when(k.fetch()).then(function(){DATA.createTabularDatasetChunkedView({model:k,parent_elt:j,embedded:true,height:"100%"})})}});i.preventDefault()}}}}}g.faIcon="fa-eye";return faIconButton(g)},_renderDetails:function(){if(this.model.get("state")===a.NOT_VIEWABLE){return $(this.templates.noAccess(this.model.toJSON(),this))}var f=e.prototype._renderDetails.call(this);f.find(".actions .left").empty().append(this._renderSecondaryActions());f.find(".summary").html(this._renderSummary()).prepend(this._renderDetailMessages());f.find(".display-applications").html(this._renderDisplayApplications());this._setUpBehaviors(f);return f},_renderSummary:function(){var f=this.model.toJSON(),g=this.templates.summaries[f.state];g=g||this.templates.summaries.unknown;return g(f,this)},_renderDetailMessages:function(){var f=this,h=$('<div class="detail-messages"></div>'),g=f.model.toJSON();_.each(f.templates.detailMessages,function(i){h.append($(i(g,f)))});return h},_renderDisplayApplications:function(){if(this.model.isDeletedOrPurged()){return""}return[this.templates.displayApplications(this.model.get("display_apps"),this),this.templates.displayApplications(this.model.get("display_types"),this)].join("")},_renderSecondaryActions:function(){this.debug("_renderSecondaryActions");switch(this.model.get("state")){case a.NOT_VIEWABLE:return[];case a.OK:case a.FAILED_METADATA:case a.ERROR:return[this._renderDownloadButton(),this._renderShowParamsButton()]}return[this._renderShowParamsButton()]},_renderShowParamsButton:function(){return faIconButton({title:c("View details"),classes:"params-btn",href:this.model.urls.show_params,target:this.linkTarget,faIcon:"fa-info-circle"})},_renderDownloadButton:function(){if(this.model.get("purged")||!this.model.hasData()){return null}if(!_.isEmpty(this.model.get("meta_files"))){return this._renderMetaFileDownloadButton()}return $(['<a class="download-btn icon-btn" href="',this.model.urls.download,'" title="'+c("Download")+'">','<span class="fa fa-floppy-o"></span>',"</a>"].join(""))},_renderMetaFileDownloadButton:function(){var f=this.model.urls;return $(['<div class="metafile-dropdown dropdown">','<a class="download-btn icon-btn" href="javascript:void(0)" data-toggle="dropdown"',' title="'+c("Download")+'">','<span class="fa fa-floppy-o"></span>',"</a>",'<ul class="dropdown-menu" role="menu" aria-labelledby="dLabel">','<li><a href="'+f.download+'">',c("Download dataset"),"</a></li>",_.map(this.model.get("meta_files"),function(g){return['<li><a href="',f.meta_download+g.file_type,'">',c("Download")," ",g.file_type,"</a></li>"].join("")}).join("\n"),"</ul>","</div>"].join("\n"))},toString:function(){var f=(this.model)?(this.model+""):("(no model)");return"DatasetListItemView("+f+")"}});d.prototype.templates=(function(){var h=_.extend({},e.prototype.templates.warnings,{failed_metadata:b.wrapTemplate(['<% if( model.state === "failed_metadata" ){ %>','<div class="warningmessagesmall">',c("An error occurred setting the metadata for this dataset"),"</div>","<% } %>"]),error:b.wrapTemplate(["<% if( model.error ){ %>",'<div class="errormessagesmall">',c("There was an error getting the data for this dataset"),": <%- model.error %>","</div>","<% } %>"]),purged:b.wrapTemplate(["<% if( model.purged ){ %>",'<div class="purged-msg warningmessagesmall">',c("This dataset has been deleted and removed from disk"),"</div>","<% } %>"]),deleted:b.wrapTemplate(["<% if( model.deleted && !model.purged ){ %>",'<div class="deleted-msg warningmessagesmall">',c("This dataset has been deleted"),"</div>","<% } %>"])});var i=b.wrapTemplate(['<div class="details">','<div class="summary"></div>','<div class="actions clear">','<div class="left"></div>','<div class="right"></div>',"</div>","<% if( !dataset.deleted && !dataset.purged ){ %>",'<div class="tags-display"></div>','<div class="annotation-display"></div>','<div class="display-applications"></div>',"<% if( dataset.peek ){ %>",'<pre class="dataset-peek"><%= dataset.peek %></pre>',"<% } %>","<% } %>","</div>"],"dataset");var g=b.wrapTemplate(['<div class="details">','<div class="summary">',c("You do not have permission to view this dataset"),"</div>","</div>"],"dataset");var j={};j[a.OK]=j[a.FAILED_METADATA]=b.wrapTemplate(["<% if( dataset.misc_blurb ){ %>",'<div class="blurb">','<span class="value"><%- dataset.misc_blurb %></span>',"</div>","<% } %>","<% if( dataset.data_type ){ %>",'<div class="datatype">','<label class="prompt">',c("format"),"</label>",'<span class="value"><%- dataset.data_type %></span>',"</div>","<% } %>","<% if( dataset.metadata_dbkey ){ %>",'<div class="dbkey">','<label class="prompt">',c("database"),"</label>",'<span class="value">',"<%- dataset.metadata_dbkey %>","</span>","</div>","<% } %>","<% if( dataset.misc_info ){ %>",'<div class="info">','<span class="value"><%- dataset.misc_info %></span>',"</div>","<% } %>"],"dataset");j[a.NEW]=b.wrapTemplate(["<div>",c("This is a new dataset and not all of its data are available yet"),"</div>"],"dataset");j[a.NOT_VIEWABLE]=b.wrapTemplate(["<div>",c("You do not have permission to view this dataset"),"</div>"],"dataset");j[a.DISCARDED]=b.wrapTemplate(["<div>",c("The job creating this dataset was cancelled before completion"),"</div>"],"dataset");j[a.QUEUED]=b.wrapTemplate(["<div>",c("This job is waiting to run"),"</div>"],"dataset");j[a.RUNNING]=b.wrapTemplate(["<div>",c("This job is currently running"),"</div>"],"dataset");j[a.UPLOAD]=b.wrapTemplate(["<div>",c("This dataset is currently uploading"),"</div>"],"dataset");j[a.SETTING_METADATA]=b.wrapTemplate(["<div>",c("Metadata is being auto-detected"),"</div>"],"dataset");j[a.PAUSED]=b.wrapTemplate(["<div>",c('This job is paused. Use the "Resume Paused Jobs" in the history menu to resume'),"</div>"],"dataset");j[a.ERROR]=b.wrapTemplate(["<% if( !dataset.purged ){ %>","<div><%- dataset.misc_blurb %></div>","<% } %>",'<span class="help-text">',c("An error occurred with this dataset"),":</span>",'<div class="job-error-text"><%- dataset.misc_info %></div>'],"dataset");j[a.EMPTY]=b.wrapTemplate(["<div>",c("No data"),": <i><%- dataset.misc_blurb %></i></div>"],"dataset");j.unknown=b.wrapTemplate(['<div>Error: unknown dataset state: "<%- dataset.state %>"</div>'],"dataset");var k={resubmitted:b.wrapTemplate(["<% if( model.resubmitted ){ %>",'<div class="resubmitted-msg infomessagesmall">',c("The job creating this dataset has been resubmitted"),"</div>","<% } %>"])};var f=b.wrapTemplate(["<% _.each( apps, function( app ){ %>",'<div class="display-application">','<span class="display-application-location"><%- app.label %></span> ','<span class="display-application-links">',"<% _.each( app.links, function( link ){ %>",'<a target="<%= link.target %>" href="<%= link.href %>">',"<% print( _l( link.text ) ); %>","</a> ","<% }); %>","</span>","</div>","<% }); %>"],"apps");return _.extend({},e.prototype.templates,{warnings:h,details:i,noAccess:g,summaries:j,detailMessages:k,displayApplications:f})}());return{DatasetListItemView:d}});