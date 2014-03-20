define(["mvc/dataset/hda-model","mvc/base-mvc"],function(d,b){var c=Backbone.View.extend(b.LoggableMixin).extend({tagName:"div",className:"dataset hda history-panel-hda",id:function(){return"hda-"+this.model.get("id")},fxSpeed:"fast",initialize:function(f){if(f.logger){this.logger=this.model.logger=f.logger}this.log(this+".initialize:",f);this.defaultPrimaryActionButtonRenderers=[this._render_showParamsButton];this.linkTarget=f.linkTarget||"_blank";this.selectable=f.selectable||false;this.selected=f.selected||false;this.expanded=f.expanded||false;this.draggable=f.draggable||false;this._setUpListeners()},_setUpListeners:function(){this.model.on("change",function(g,f){if(this.model.changedAttributes().state&&this.model.inReadyState()&&this.expanded&&!this.model.hasDetails()){this.model.fetch()}else{this.render()}},this)},render:function(h){h=(h===undefined)?(true):(h);var f=this;this.$el.find("[title]").tooltip("destroy");this.urls=this.model.urls();var g=this._buildNewRender();if(h){$(f).queue(function(i){this.$el.fadeOut(f.fxSpeed,i)})}$(f).queue(function(i){this.$el.empty().attr("class",f.className).addClass("state-"+f.model.get("state")).append(g.children());if(this.selectable){this.showSelector(0)}i()});if(h){$(f).queue(function(i){this.$el.fadeIn(f.fxSpeed,i)})}$(f).queue(function(i){this.trigger("rendered",f);if(this.model.inReadyState()){this.trigger("rendered:ready",f)}if(this.draggable){this.draggableOn()}i()});return this},_buildNewRender:function(){var f=$(c.templates.skeleton(this.model.toJSON()));f.find(".dataset-primary-actions").append(this._render_titleButtons());f.children(".dataset-body").replaceWith(this._render_body());this._setUpBehaviors(f);return f},_setUpBehaviors:function(f){f=f||this.$el;make_popup_menus(f);f.find("[title]").tooltip({placement:"bottom"})},_render_titleButtons:function(){return[this._render_displayButton()]},_render_displayButton:function(){if((this.model.get("state")===d.HistoryDatasetAssociation.STATES.NOT_VIEWABLE)||(this.model.get("state")===d.HistoryDatasetAssociation.STATES.DISCARDED)||(this.model.get("state")===d.HistoryDatasetAssociation.STATES.NEW)||(!this.model.get("accessible"))){return null}var g={target:this.linkTarget,classes:"dataset-display"};if(this.model.get("purged")){g.disabled=true;g.title=_l("Cannot display datasets removed from disk")}else{if(this.model.get("state")===d.HistoryDatasetAssociation.STATES.UPLOAD){g.disabled=true;g.title=_l("This dataset must finish uploading before it can be viewed")}else{g.title=_l("View data");g.href=this.urls.display;var f=this;g.onclick=function(){if(Galaxy.frame&&Galaxy.frame.active){Galaxy.frame.add({title:"Data Viewer: "+f.model.get("name"),type:"url",content:f.urls.display})}}}}g.faIcon="fa-eye";return faIconButton(g)},_render_downloadButton:function(){if(this.model.get("purged")||!this.model.hasData()){return null}var g=this.urls,h=this.model.get("meta_files");if(_.isEmpty(h)){return $(['<a href="'+g.download+'" title="'+_l("Download")+'" ','class="icon-btn dataset-download-btn">','<span class="fa fa-floppy-o"></span>',"</a>"].join(""))}var i="dataset-"+this.model.get("id")+"-popup",f=['<div popupmenu="'+i+'">','<a href="'+g.download+'">',_l("Download Dataset"),"</a>","<a>"+_l("Additional Files")+"</a>",_.map(h,function(j){return['<a class="action-button" href="',g.meta_download+j.file_type,'">',_l("Download")," ",j.file_type,"</a>"].join("")}).join("\n"),"</div>",'<div class="icon-btn-group">','<a href="'+g.download+'" title="'+_l("Download")+'" ','class="icon-btn dataset-download-btn">','<span class="fa fa-floppy-o"></span>','</a><a class="icon-btn popup" id="'+i+'">','<span class="fa fa-caret-down"></span>',"</a>","</div>"].join("\n");return $(f)},_render_showParamsButton:function(){return faIconButton({title:_l("View details"),classes:"dataset-params-btn",href:this.urls.show_params,target:this.linkTarget,faIcon:"fa-info-circle"})},_render_body:function(){var g=$('<div>Error: unknown dataset state "'+this.model.get("state")+'".</div>'),f=this["_render_body_"+this.model.get("state")];if(_.isFunction(f)){g=f.call(this)}this._setUpBehaviors(g);if(this.expanded){g.show()}return g},_render_stateBodyHelper:function(f,i){i=i||[];var g=this,h=$(c.templates.body(_.extend(this.model.toJSON(),{body:f})));h.find(".dataset-actions .left").append(_.map(i,function(j){return j.call(g)}));return h},_render_body_new:function(){return this._render_stateBodyHelper("<div>"+_l("This is a new dataset and not all of its data are available yet")+"</div>")},_render_body_noPermission:function(){return this._render_stateBodyHelper("<div>"+_l("You do not have permission to view this dataset")+"</div>")},_render_body_discarded:function(){return this._render_stateBodyHelper("<div>"+_l("The job creating this dataset was cancelled before completion")+"</div>",this.defaultPrimaryActionButtonRenderers)},_render_body_queued:function(){return this._render_stateBodyHelper("<div>"+_l("This job is waiting to run")+"</div>",this.defaultPrimaryActionButtonRenderers)},_render_body_upload:function(){return this._render_stateBodyHelper("<div>"+_l("This dataset is currently uploading")+"</div>")},_render_body_setting_metadata:function(){return this._render_stateBodyHelper("<div>"+_l("Metadata is being auto-detected")+"</div>")},_render_body_running:function(){return this._render_stateBodyHelper("<div>"+_l("This job is currently running")+"</div>",this.defaultPrimaryActionButtonRenderers)},_render_body_paused:function(){return this._render_stateBodyHelper("<div>"+_l('This job is paused. Use the "Resume Paused Jobs" in the history menu to resume')+"</div>",this.defaultPrimaryActionButtonRenderers)},_render_body_error:function(){var f=['<span class="help-text">',_l("An error occurred with this dataset"),":</span>",'<div class="job-error-text">',$.trim(this.model.get("misc_info")),"</div>"].join("");if(!this.model.get("purged")){f="<div>"+this.model.get("misc_blurb")+"</div>"+f}return this._render_stateBodyHelper(f,[this._render_downloadButton].concat(this.defaultPrimaryActionButtonRenderers))},_render_body_empty:function(){return this._render_stateBodyHelper("<div>"+_l("No data")+": <i>"+this.model.get("misc_blurb")+"</i></div>",this.defaultPrimaryActionButtonRenderers)},_render_body_failed_metadata:function(){var f=$('<div class="warningmessagesmall"></div>').append($("<strong/>").text(_l("An error occurred setting the metadata for this dataset"))),g=this._render_body_ok();g.prepend(f);return g},_render_body_ok:function(){var f=this,h=$(c.templates.body(this.model.toJSON())),g=[this._render_downloadButton].concat(this.defaultPrimaryActionButtonRenderers);h.find(".dataset-actions .left").append(_.map(g,function(i){return i.call(f)}));if(this.model.isDeletedOrPurged()){return h}return h},events:{"click .dataset-title-bar":"toggleBodyVisibility","keydown .dataset-title-bar":"toggleBodyVisibility","click .dataset-selector":"toggleSelect"},toggleBodyVisibility:function(i,g){var f=32,h=13;if(i&&(i.type==="keydown")&&!(i.keyCode===f||i.keyCode===h)){return true}var j=this.$el.find(".dataset-body");g=(g===undefined)?(!j.is(":visible")):(g);if(g){this.expandBody()}else{this.collapseBody()}return false},expandBody:function(){var f=this;function g(){f.$el.children(".dataset-body").replaceWith(f._render_body());f.$el.children(".dataset-body").slideDown(f.fxSpeed,function(){f.expanded=true;f.trigger("body-expanded",f.model.get("id"))})}if(this.model.inReadyState()&&!this.model.hasDetails()){this.model.fetch({silent:true}).always(function(h){f.urls=f.model.urls();g()})}else{g()}},collapseBody:function(){var f=this;this.$el.children(".dataset-body").slideUp(f.fxSpeed,function(){f.expanded=false;f.trigger("body-collapsed",f.model.get("id"))})},showSelector:function(){if(this.selected){this.select(null,true)}this.selectable=true;this.trigger("selectable",true,this);this.$(".dataset-primary-actions").hide();this.$(".dataset-selector").show()},hideSelector:function(){this.selectable=false;this.trigger("selectable",false,this);this.$(".dataset-selector").hide();this.$(".dataset-primary-actions").show()},toggleSelector:function(){if(!this.$el.find(".dataset-selector").is(":visible")){this.showSelector()}else{this.hideSelector()}},select:function(f){this.$el.find(".dataset-selector span").removeClass("fa-square-o").addClass("fa-check-square-o");if(!this.selected){this.trigger("selected",this);this.selected=true}return false},deselect:function(f){this.$el.find(".dataset-selector span").removeClass("fa-check-square-o").addClass("fa-square-o");if(this.selected){this.trigger("de-selected",this);this.selected=false}return false},toggleSelect:function(f){if(this.selected){this.deselect(f)}else{this.select(f)}},draggableOn:function(){this.draggable=true;this.dragStartHandler=_.bind(this._dragStartHandler,this);this.dragEndHandler=_.bind(this._dragEndHandler,this);var f=this.$el.find(".dataset-title-bar").attr("draggable",true).get(0);f.addEventListener("dragstart",this.dragStartHandler,false);f.addEventListener("dragend",this.dragEndHandler,false)},draggableOff:function(){this.draggable=false;var f=this.$el.find(".dataset-title-bar").attr("draggable",false).get(0);f.removeEventListener("dragstart",this.dragStartHandler,false);f.removeEventListener("dragend",this.dragEndHandler,false)},toggleDraggable:function(){if(this.draggable){this.draggableOff()}else{this.draggableOn()}},_dragStartHandler:function(f){this.trigger("dragstart",this);f.dataTransfer.effectAllowed="move";f.dataTransfer.setData("text",JSON.stringify(this.model.toJSON()));return false},_dragEndHandler:function(f){this.trigger("dragend",this);return false},remove:function(g){var f=this;this.$el.fadeOut(f.fxSpeed,function(){f.$el.remove();f.off();if(g){g()}})},toString:function(){var f=(this.model)?(this.model+""):("(no model)");return"HDABaseView("+f+")"}});var a=['<div class="dataset hda">','<div class="dataset-warnings">',"<% if( hda.error ){ %>",'<div class="errormessagesmall">',_l("There was an error getting the data for this dataset"),":<%- hda.error %>","</div>","<% } %>","<% if( hda.deleted ){ %>","<% if( hda.purged ){ %>",'<div class="dataset-purged-msg warningmessagesmall"><strong>',_l("This dataset has been deleted and removed from disk."),"</strong></div>","<% } else { %>",'<div class="dataset-deleted-msg warningmessagesmall"><strong>',_l("This dataset has been deleted."),"</strong></div>","<% } %>","<% } %>","<% if( !hda.visible ){ %>",'<div class="dataset-hidden-msg warningmessagesmall"><strong>',_l("This dataset has been hidden."),"</strong></div>","<% } %>","</div>",'<div class="dataset-selector">','<span class="fa fa-2x fa-square-o"></span>',"</div>",'<div class="dataset-primary-actions"></div>','<div class="dataset-title-bar clear" tabindex="0">','<span class="dataset-state-icon state-icon"></span>','<div class="dataset-title">','<span class="hda-hid"><%- hda.hid %></span> ','<span class="dataset-name"><%- hda.name %></span>',"</div>","</div>",'<div class="dataset-body"></div>',"</div>"].join("");var e=['<div class="dataset-body">',"<% if( hda.body ){ %>",'<div class="dataset-summary">',"<%= hda.body %>","</div>",'<div class="dataset-actions clear">','<div class="left"></div>','<div class="right"></div>',"</div>","<% } else { %>",'<div class="dataset-summary">',"<% if( hda.misc_blurb ){ %>",'<div class="dataset-blurb">','<span class="value"><%- hda.misc_blurb %></span>',"</div>","<% } %>","<% if( hda.data_type ){ %>",'<div class="dataset-datatype">','<label class="prompt">',_l("format"),"</label>",'<span class="value"><%- hda.data_type %></span>',"</div>","<% } %>","<% if( hda.metadata_dbkey ){ %>",'<div class="dataset-dbkey">','<label class="prompt">',_l("database"),"</label>",'<span class="value">',"<%- hda.metadata_dbkey %>","</span>","</div>","<% } %>","<% if( hda.misc_info ){ %>",'<div class="dataset-info">','<span class="value"><%- hda.misc_info %></span>',"</div>","<% } %>","</div>",'<div class="dataset-actions clear">','<div class="left"></div>','<div class="right"></div>',"</div>","<% if( !hda.deleted ){ %>",'<div class="tags-display"></div>','<div class="annotation-display"></div>','<div class="dataset-display-applications">',"<% _.each( hda.display_apps, function( app ){ %>",'<div class="display-application">','<span class="display-application-location"><%- app.label %></span> ','<span class="display-application-links">',"<% _.each( app.links, function( link ){ %>",'<a target="<%= link.target %>" href="<%= link.href %>">',"<% print( _l( link.text ) ); %>","</a> ","<% }); %>","</span>","</div>","<% }); %>","<% _.each( hda.display_types, function( app ){ %>",'<div class="display-application">','<span class="display-application-location"><%- app.label %></span> ','<span class="display-application-links">',"<% _.each( app.links, function( link ){ %>",'<a target="<%= link.target %>" href="<%= link.href %>">',"<% print( _l( link.text ) ); %>","</a> ","<% }); %>","</span>","</div>","<% }); %>","</div>",'<div class="dataset-peek">',"<% if( hda.peek ){ %>",'<pre class="peek"><%= hda.peek %></pre>',"<% } %>","</div>","<% } %>","<% } %>","</div>"].join("");c.templates={skeleton:function(f){return _.template(a,f,{variable:"hda"})},body:function(f){return _.template(e,f,{variable:"hda"})}};return{HDABaseView:c}});