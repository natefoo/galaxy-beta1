var HDAEditView=HDABaseView.extend(LoggableMixin).extend({initialize:function(a){HDABaseView.prototype.initialize.call(this,a);this.defaultPrimaryActionButtonRenderers=[this._render_showParamsButton,this._render_rerunButton]},_render_warnings:function(){return $(jQuery.trim(HDABaseView.templates.messages(_.extend(this.model.toJSON(),{urls:this.urls}))))},_render_titleButtons:function(){var a=$('<div class="historyItemButtons"></div>');a.append(this._render_displayButton());a.append(this._render_editButton());a.append(this._render_deleteButton());return a},_render_editButton:function(){if((this.model.get("state")===HistoryDatasetAssociation.STATES.UPLOAD)||(this.model.get("state")===HistoryDatasetAssociation.STATES.NOT_VIEWABLE)||(!this.model.get("accessible"))){this.editButton=null;return null}var c=this.model.get("purged"),a=this.model.get("deleted"),b={title:_l("Edit Attributes"),href:this.urls.edit,target:"galaxy_main",icon_class:"edit"};if(a||c){b.enabled=false;if(c){b.title=_l("Cannot edit attributes of datasets removed from disk")}else{if(a){b.title=_l("Undelete dataset to edit attributes")}}}this.editButton=new IconButtonView({model:new IconButton(b)});return this.editButton.render().$el},_render_deleteButton:function(){if((this.model.get("state")===HistoryDatasetAssociation.STATES.NOT_VIEWABLE)||(!this.model.get("accessible"))){this.deleteButton=null;return null}var a={title:_l("Delete"),href:this.urls["delete"],id:"historyItemDeleter-"+this.model.get("id"),icon_class:"delete"};if(this.model.get("deleted")||this.model.get("purged")){a={title:_l("Dataset is already deleted"),icon_class:"delete",enabled:false}}this.deleteButton=new IconButtonView({model:new IconButton(a)});return this.deleteButton.render().$el},_render_hdaSummary:function(){var a=_.extend(this.model.toJSON(),{urls:this.urls});if(this.model.get("metadata_dbkey")==="?"&&!this.model.isDeletedOrPurged()){_.extend(a,{dbkey_unknown_and_editable:true})}return HDABaseView.templates.hdaSummary(a)},_render_errButton:function(){if(this.model.get("state")!==HistoryDatasetAssociation.STATES.ERROR){this.errButton=null;return null}this.errButton=new IconButtonView({model:new IconButton({title:_l("View or report this error"),href:this.urls.report_error,target:"galaxy_main",icon_class:"bug"})});return this.errButton.render().$el},_render_rerunButton:function(){this.rerunButton=new IconButtonView({model:new IconButton({title:_l("Run this job again"),href:this.urls.rerun,target:"galaxy_main",icon_class:"arrow-circle"})});return this.rerunButton.render().$el},_render_visualizationsButton:function(){var c=this.model.get("dbkey"),a=this.model.get("visualizations"),f=this.urls.visualization,d={},g={dataset_id:this.model.get("id"),hda_ldda:"hda"};if(c){g.dbkey=c}if(!(this.model.hasData())||!(a&&a.length)||!(f)){this.visualizationsButton=null;return null}this.visualizationsButton=new IconButtonView({model:new IconButton({title:_l("Visualize"),href:f,icon_class:"chart_curve"})});var b=this.visualizationsButton.render().$el;b.addClass("visualize-icon");function e(h){switch(h){case"trackster":return create_trackster_action_fn(f,g,c);case"scatterplot":return create_scatterplot_action_fn(f,g);default:return function(){window.parent.location=f+"/"+h+"?"+$.param(g)}}}if(a.length===1){b.attr("title",a[0]);b.click(e(a[0]))}else{_.each(a,function(i){var h=i.charAt(0).toUpperCase()+i.slice(1);d[_l(h)]=e(i)});make_popupmenu(b,d)}return b},_render_secondaryActionButtons:function(b){var c=$("<div/>"),a=this;c.attr("style","float: right;").attr("id","secondary-actions-"+this.model.get("id"));_.each(b,function(d){c.append(d.call(a))});return c},_render_tagButton:function(){if(!(this.model.hasData())||(!this.urls.tags.get)){this.tagButton=null;return null}this.tagButton=new IconButtonView({model:new IconButton({title:_l("Edit dataset tags"),target:"galaxy_main",href:this.urls.tags.get,icon_class:"tags"})});return this.tagButton.render().$el},_render_annotateButton:function(){if(!(this.model.hasData())||(!this.urls.annotation.get)){this.annotateButton=null;return null}this.annotateButton=new IconButtonView({model:new IconButton({title:_l("Edit dataset annotation"),target:"galaxy_main",icon_class:"annotate"})});return this.annotateButton.render().$el},_render_tagArea:function(){if(!this.urls.tags.set){return null}return $(HDAEditView.templates.tagArea(_.extend(this.model.toJSON(),{urls:this.urls})))},_render_annotationArea:function(){if(!this.urls.annotation.get){return null}return $(HDAEditView.templates.annotationArea(_.extend(this.model.toJSON(),{urls:this.urls})))},_render_body_error:function(a){HDABaseView.prototype._render_body_error.call(this,a);var b=a.find("#primary-actions-"+this.model.get("id"));b.prepend(this._render_errButton())},_render_body_ok:function(a){a.append(this._render_hdaSummary());if(this.model.isDeletedOrPurged()){a.append(this._render_primaryActionButtons([this._render_downloadButton,this._render_showParamsButton,this._render_rerunButton]));return}a.append(this._render_primaryActionButtons([this._render_downloadButton,this._render_showParamsButton,this._render_rerunButton,this._render_visualizationsButton]));a.append(this._render_secondaryActionButtons([this._render_tagButton,this._render_annotateButton]));a.append('<div class="clear"/>');a.append(this._render_tagArea());a.append(this._render_annotationArea());a.append(this._render_displayApps());a.append(this._render_peek())},events:{"click .historyItemTitle":"toggleBodyVisibility","click a.icon-button.tags":"loadAndDisplayTags","click a.icon-button.annotate":"loadAndDisplayAnnotation"},loadAndDisplayTags:function(b){this.log(this+".loadAndDisplayTags",b);var c=this.$el.find(".tag-area"),a=c.find(".tag-elt");if(c.is(":hidden")){if(!jQuery.trim(a.html())){$.ajax({url:this.urls.tags.get,error:function(){alert(_l("Tagging failed"))},success:function(d){a.html(d);a.find(".tooltip").tooltip();c.slideDown("fast")}})}else{c.slideDown("fast")}}else{c.slideUp("fast")}return false},loadAndDisplayAnnotation:function(b){this.log(this+".loadAndDisplayAnnotation",b);var d=this.$el.find(".annotation-area"),c=d.find(".annotation-elt"),a=this.urls.annotation.set;if(d.is(":hidden")){if(!jQuery.trim(c.html())){$.ajax({url:this.urls.annotation.get,error:function(){alert(_l("Annotations failed"))},success:function(e){if(e===""){e="<em>"+_l("Describe or add notes to dataset")+"</em>"}c.html(e);d.find(".tooltip").tooltip();async_save_text(c.attr("id"),c.attr("id"),a,"new_annotation",18,true,4);d.slideDown("fast")}})}else{d.slideDown("fast")}}else{d.slideUp("fast")}return false},toString:function(){var a=(this.model)?(this.model+""):("(no model)");return"HDAView("+a+")"}});HDAEditView.templates={tagArea:Handlebars.templates["template-hda-tagArea"],annotationArea:Handlebars.templates["template-hda-annotationArea"]};function create_scatterplot_action_fn(a,b){action=function(){var d=$(window.parent.document).find("iframe#galaxy_main"),c=a+"/scatterplot?"+$.param(b);d.attr("src",c);$("div.popmenu-wrapper").remove();return false};return action}function create_trackster_action_fn(a,c,b){return function(){var d={};if(b){d["f-dbkey"]=b}$.ajax({url:a+"/list_tracks?"+$.param(d),dataType:"html",error:function(){alert(_l("Could not add this dataset to browser")+".")},success:function(e){var f=window.parent;f.show_modal(_l("View Data in a New or Saved Visualization"),"",{Cancel:function(){f.hide_modal()},"View in saved visualization":function(){f.show_modal(_l("Add Data to Saved Visualization"),e,{Cancel:function(){f.hide_modal()},"Add to visualization":function(){$(f.document).find("input[name=id]:checked").each(function(){var g=$(this).val();c.id=g;f.location=a+"/trackster?"+$.param(c)})}})},"View in new visualization":function(){f.location=a+"/trackster?"+$.param(c)}})}});return false}};