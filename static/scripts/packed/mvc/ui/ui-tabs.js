define(["utils/utils"],function(a){var b=Backbone.View.extend({visible:false,list:{},$nav:null,$content:null,optionsDefault:{operations:null,},initialize:function(e){this.options=a.merge(e,this.optionsDefault);var c=$(this._template(this.options));this.$nav=c.find(".tab-navigation");this.$content=c.find(".tab-content");this.setElement(c);if(this.options.operations){var d=this;$.each(this.options.operations,function(f,g){g.$el.prop("id",f);d.$nav.append(g.$el)})}},add:function(c){var d=c.$el;var f=c.title;var g=c.id;var e={$title:$(this._template_tab(c)),$content:$(this._template_tab_content(c))};this.$nav.append(e.$title);e.$content.append(d);this.$content.append(e.$content);this.list[g]=e;if(_.size(this.list)==1){e.$title.addClass("active");e.$content.addClass("active")}},show:function(){this.$el.fadeIn("fast");this.visible=true},hide:function(){this.$el.fadeOut("fast");this.visible=false},hideOperation:function(c){this.$nav.find("#"+c).hide()},showOperation:function(c){this.$nav.find("#"+c).show()},setOperation:function(e,d){var c=this.$nav.find("#"+e);c.off("click");c.on("click",d)},title:function(e,c){var d=this.$el.find("#title-"+e+" a");if(new_title){d.html(new_title)}return d.html()},_template:function(c){return'<div class="tabbable tabs-left"><ul class="tab-navigation nav nav-tabs"/><div class="tab-content"/></div>'},_template_tab:function(c){return'<li id="title-'+c.id+'"><a title="" href="#tab-'+c.id+'" data-toggle="tab" data-original-title="">'+c.title+"</a></li>"},_template_tab_content:function(c){return'<div id="tab-'+c.id+'" class="tab-pane"/>'}});return{View:b}});